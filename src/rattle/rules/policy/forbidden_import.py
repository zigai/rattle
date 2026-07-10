from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import libcst as cst

from rattle import LintRule, RuleSetting
from rattle.rules.helpers import optional_setting_text, setting_fields

_CODEGEN_MODULE = cst.Module(body=[])
_IMPORT_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")


@dataclass(frozen=True)
class ForbiddenImportEntry:
    boundary: str
    message: str | None = None


def _parse_forbidden_import(entry: str | ForbiddenImportEntry) -> ForbiddenImportEntry:
    if isinstance(entry, ForbiddenImportEntry):
        return entry

    boundary, message = setting_fields(entry, 2)
    normalized_message = optional_setting_text(message)

    if not _IMPORT_PATTERN.fullmatch(boundary):
        raise ValueError(f"expected import boundary in forbidden import entry, got {entry!r}")
    if normalized_message == "":
        raise ValueError(f"expected non-empty message in forbidden import entry, got {entry!r}")

    return ForbiddenImportEntry(boundary=boundary, message=normalized_message)


def _validate_forbidden_imports(value: object) -> object:
    assert isinstance(value, list)

    for entry in value:
        _parse_forbidden_import(entry)

    return True


def _parse_forbidden_imports_setting(value: object) -> tuple[ForbiddenImportEntry, ...]:
    assert isinstance(value, list | tuple)

    return tuple(_parse_forbidden_import(entry) for entry in value)


def _node_name(node: cst.BaseExpression) -> str:
    return _CODEGEN_MODULE.code_for_node(node)


def _full_imported_name(module_name: str, imported_name: str) -> str:
    if module_name:
        return f"{module_name}.{imported_name}"

    return imported_name


def _matches_import_boundary(imported_name: str, boundary: str) -> bool:
    return imported_name == boundary or imported_name.startswith(f"{boundary}.")


def _matches_relative_import_boundary(imported_name: str, boundary: str) -> bool:
    if _matches_import_boundary(imported_name, boundary):
        return True

    boundary_tail = boundary.rsplit(".", 1)[-1]
    return imported_name == boundary_tail or imported_name.startswith(f"{boundary_tail}.")


class ForbiddenImport(LintRule):
    """Ban imports that cross configured package or module boundaries."""

    MESSAGE = "Do not import across forbidden boundary '{boundary}'."
    SETTINGS = {
        "forbidden_imports": RuleSetting(
            list[str],
            default=[],
            description=(
                "Import boundaries to forbid. Each entry has the form boundary[|message], "
                "for example 'legacy.api|Import from app.api'."
            ),
            validator=_validate_forbidden_imports,
        ),
    }

    VALID = ()
    INVALID = ()

    def __init__(self) -> None:
        super().__init__()

        self._messages_by_boundary: dict[str, str | None] = {}

    def should_lint_file(self, source: bytes, path: Path) -> bool:
        del path

        for entry in _parse_forbidden_imports_setting(self.settings.get("forbidden_imports", ())):
            boundary = entry.boundary
            if boundary.encode() in source:
                return True
            boundary_tail = boundary.rsplit(".", 1)[-1]
            if boundary_tail.encode() in source:
                return True

            module_name, separator, _imported_name = boundary.rpartition(".")
            if separator and module_name.encode() in source:
                return True

        return False

    def visit_Module(self, node: cst.Module) -> None:
        del node

        self._messages_by_boundary = {
            entry.boundary: entry.message
            for entry in _parse_forbidden_imports_setting(self.settings["forbidden_imports"])
        }

    def leave_Module(self, original_node: cst.Module) -> None:
        del original_node

        self._messages_by_boundary = {}

    def visit_Import(self, node: cst.Import) -> None:
        for imported_alias in node.names:
            imported_name = _node_name(imported_alias.name)
            boundary = self._forbidden_boundary_for_import_name(imported_name)
            if boundary is None:
                continue

            self.report(imported_alias, self._message_for_boundary(boundary))

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if node.module is None:
            if not node.relative or isinstance(node.names, cst.ImportStar):
                return

            for imported_alias in node.names:
                imported_name = _node_name(imported_alias.name)
                boundary = self._forbidden_boundary_for_import_name(
                    imported_name, relative=node.relative
                )
                if boundary is None:
                    continue

                self.report(imported_alias, self._message_for_boundary(boundary))

            return

        module_name = _node_name(node.module)
        if isinstance(node.names, cst.ImportStar):
            boundary = self._forbidden_boundary_for_import_name(module_name, relative=node.relative)
            if boundary is not None:
                self.report(node.names, self._message_for_boundary(boundary))

            return

        for imported_alias in node.names:
            imported_name = _node_name(imported_alias.name)
            full_name = _full_imported_name(module_name, imported_name)
            boundary = self._forbidden_boundary_for_import_name(full_name, relative=node.relative)
            if boundary is None:
                continue

            self.report(imported_alias, self._message_for_boundary(boundary))

    def _message_for_boundary(self, boundary: str) -> str:
        message = self._messages_by_boundary[boundary]
        if message is None:
            return self.MESSAGE.format(boundary=boundary)

        return message

    def _forbidden_boundary_for_import_name(
        self, imported_name: str, *, relative: object = False
    ) -> str | None:
        for boundary in self._messages_by_boundary:
            matches = (
                _matches_relative_import_boundary(imported_name, boundary)
                if relative
                else _matches_import_boundary(imported_name, boundary)
            )
            if matches:
                return boundary

        return None
