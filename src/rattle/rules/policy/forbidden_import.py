from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import libcst as cst

from rattle import LintRule, RuleSetting
from rattle.rules.helpers import optional_setting_text, setting_fields

_CODEGEN_MODULE = cst.Module(body=[])


@dataclass(frozen=True)
class ForbiddenImportEntry:
    boundary: str
    message: str | None = None


def _parse_forbidden_import(entry: str | ForbiddenImportEntry) -> ForbiddenImportEntry:
    if isinstance(entry, ForbiddenImportEntry):
        return entry

    boundary, message = setting_fields(entry, 2)
    normalized_message = optional_setting_text(message)

    if not boundary or any(not part.isidentifier() for part in boundary.split(".")):
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
        self._current_file_path: Path | None = None

    def should_lint_file(self, source: bytes, path: Path) -> bool:
        self._current_file_path = path

        if b"from ." in source:
            return True

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
            for entry in _parse_forbidden_imports_setting(
                self.setting("forbidden_imports", list[str])
            )
        }

    def leave_Module(self, original_node: cst.Module) -> None:
        del original_node

        self._messages_by_boundary = {}
        self._current_file_path = None

    def visit_Import(self, node: cst.Import) -> None:
        for imported_alias in node.names:
            imported_name = _node_name(imported_alias.name)
            boundary = self._forbidden_boundary_for_import_name(imported_name)
            if boundary is None:
                continue

            self.report(imported_alias, self._message_for_boundary(boundary))

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if node.module is None:
            self._report_moduleless_relative_import(node)
            return

        module_name = _node_name(node.module)
        if isinstance(node.names, cst.ImportStar):
            boundary = self._forbidden_boundary_for_import_name(
                module_name, relative_level=len(node.relative)
            )
            if boundary is not None:
                self.report(node.names, self._message_for_boundary(boundary))

            return

        for imported_alias in node.names:
            imported_name = _node_name(imported_alias.name)
            full_name = _full_imported_name(module_name, imported_name)
            boundary = self._forbidden_boundary_for_import_name(
                full_name, relative_level=len(node.relative)
            )
            if boundary is None:
                continue

            self.report(imported_alias, self._message_for_boundary(boundary))

    def _report_moduleless_relative_import(self, node: cst.ImportFrom) -> None:
        if not node.relative:
            return
        if isinstance(node.names, cst.ImportStar):
            boundary = self._forbidden_boundary_for_import_name(
                "", relative_level=len(node.relative)
            )
            if boundary is not None:
                self.report(node.names, self._message_for_boundary(boundary))
            return

        for imported_alias in node.names:
            imported_name = _node_name(imported_alias.name)
            boundary = self._forbidden_boundary_for_import_name(
                imported_name, relative_level=len(node.relative)
            )
            if boundary is not None:
                self.report(imported_alias, self._message_for_boundary(boundary))

    def _message_for_boundary(self, boundary: str) -> str:
        message = self._messages_by_boundary[boundary]
        if message is None:
            return self.MESSAGE.format(boundary=boundary)

        return message

    def _forbidden_boundary_for_import_name(
        self, imported_name: str, *, relative_level: int = 0
    ) -> str | None:
        candidates = (
            self._relative_import_candidates(imported_name, relative_level)
            if relative_level
            else (imported_name,)
        )
        for boundary in sorted(
            self._messages_by_boundary,
            key=lambda value: (value.count("."), len(value)),
            reverse=True,
        ):
            if any(_matches_import_boundary(candidate, boundary) for candidate in candidates):
                return boundary

        return None

    def _relative_import_candidates(
        self, imported_name: str, relative_level: int
    ) -> tuple[str, ...]:
        if self._current_file_path is None:
            return ()
        package_parts = list(self._current_file_path.parent.parts)
        parent_levels = relative_level - 1
        if parent_levels:
            package_parts = package_parts[:-parent_levels]
        imported_parts = imported_name.split(".") if imported_name else []
        target_parts = [*package_parts, *imported_parts]
        return tuple(".".join(target_parts[index:]) for index in range(len(package_parts)))
