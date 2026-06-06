from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import libcst as cst

from rattle import Invalid, LintRule, RuleSetting, Valid

_CODEGEN_MODULE = cst.Module(body=[])
_IMPORT_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")


@dataclass(frozen=True)
class _ForbiddenImport:
    boundary: str
    message: str | None = None


def _parse_forbidden_import(entry: str | _ForbiddenImport) -> _ForbiddenImport:
    if isinstance(entry, _ForbiddenImport):
        return entry

    boundary, _, message = entry.partition("|")
    normalized_message = message.strip() or None

    if not _IMPORT_PATTERN.fullmatch(boundary):
        raise ValueError(f"expected import boundary in forbidden import entry, got {entry!r}")
    if normalized_message == "":
        raise ValueError(f"expected non-empty message in forbidden import entry, got {entry!r}")

    return _ForbiddenImport(boundary=boundary, message=normalized_message)


def _validate_forbidden_imports(value: object) -> object:
    assert isinstance(value, list)

    for entry in value:
        _parse_forbidden_import(entry)

    return True


def _parse_forbidden_imports_setting(value: object) -> tuple[_ForbiddenImport, ...]:
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
    TAGS = {"architecture", "imports"}
    SETTINGS = {
        "forbidden_imports": RuleSetting(
            list[str],
            default=[],
            validator=_validate_forbidden_imports,
        ),
    }

    VALID = [
        Valid("import services.public_api", options={"forbidden_imports": ["services.internal"]}),
        Valid(
            "from services import public_api", options={"forbidden_imports": ["services.internal"]}
        ),
        Valid("import services_internal", options={"forbidden_imports": ["services.internal"]}),
    ]

    INVALID = [
        Invalid(
            "import services.internal",
            expected_message="Do not import across forbidden boundary 'services.internal'.",
            options={"forbidden_imports": ["services.internal"]},
        ),
        Invalid(
            "import services.internal.jobs",
            expected_message="Do not import across forbidden boundary 'services.internal'.",
            options={"forbidden_imports": ["services.internal"]},
        ),
        Invalid(
            "from services import internal",
            expected_message="Do not import across forbidden boundary 'services.internal'.",
            options={"forbidden_imports": ["services.internal"]},
        ),
        Invalid(
            "from services.internal import jobs",
            expected_message="Do not import across forbidden boundary 'services.internal'.",
            options={"forbidden_imports": ["services.internal"]},
        ),
        Invalid(
            "from services.internal import *",
            expected_message="Import through services.public_api instead.",
            options={
                "forbidden_imports": [
                    "services.internal|Import through services.public_api instead.",
                ],
            },
        ),
    ]

    def __init__(self) -> None:
        super().__init__()

        self._messages_by_boundary: dict[str, str | None] = {}

    def should_lint_file(self, source: bytes, path: Path) -> bool:
        del path

        for entry in _parse_forbidden_imports_setting(self.settings.get("forbidden_imports", ())):
            boundary = entry.boundary
            if boundary.encode() in source:
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
        if node.relative:
            return
        if node.module is None:
            return

        module_name = _node_name(node.module)
        if isinstance(node.names, cst.ImportStar):
            boundary = self._forbidden_boundary_for_import_name(module_name)
            if boundary is not None:
                self.report(node.names, self._message_for_boundary(boundary))

            return

        for imported_alias in node.names:
            imported_name = _node_name(imported_alias.name)
            full_name = _full_imported_name(module_name, imported_name)
            boundary = self._forbidden_boundary_for_import_name(full_name)
            if boundary is None:
                continue

            self.report(imported_alias, self._message_for_boundary(boundary))

    def _message_for_boundary(self, boundary: str) -> str:
        message = self._messages_by_boundary[boundary]
        if message is None:
            return self.MESSAGE.format(boundary=boundary)

        return message

    def _forbidden_boundary_for_import_name(self, imported_name: str) -> str | None:
        for boundary in self._messages_by_boundary:
            if _matches_import_boundary(imported_name, boundary):
                return boundary

        return None
