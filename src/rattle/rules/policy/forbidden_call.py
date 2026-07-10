from __future__ import annotations

import re
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

import libcst as cst
from libcst.metadata import (
    PositionProvider,
    QualifiedName,
    QualifiedNameProvider,
    QualifiedNameSource,
    ScopeProvider,
)

from rattle import LintRule, RuleSetting
from rattle.rules.helpers import dotted_name, optional_setting_text, setting_fields

_SYMBOL_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")


@dataclass(frozen=True)
class ForbiddenCallEntry:
    symbol: str
    message: str | None = None
    use_instead: str | None = None


def _parse_forbidden_call(entry: str | ForbiddenCallEntry) -> ForbiddenCallEntry:
    if isinstance(entry, ForbiddenCallEntry):
        return entry

    symbol, message, use_instead = setting_fields(entry, 3)
    normalized_message = optional_setting_text(message)
    normalized_use_instead = optional_setting_text(use_instead)

    if not _SYMBOL_PATTERN.fullmatch(symbol):
        raise ValueError(f"expected callable symbol in forbidden call entry, got {entry!r}")
    if normalized_message == "":
        raise ValueError(f"expected non-empty message in forbidden call entry, got {entry!r}")
    if normalized_use_instead is not None and not _SYMBOL_PATTERN.fullmatch(normalized_use_instead):
        raise ValueError(
            f"expected callable use_instead symbol in forbidden call entry, got {entry!r}"
        )

    return ForbiddenCallEntry(
        symbol=symbol,
        message=normalized_message,
        use_instead=normalized_use_instead,
    )


def _validate_forbidden_calls(value: object) -> object:
    assert isinstance(value, list)

    for entry in value:
        _parse_forbidden_call(entry)

    return True


def _parse_forbidden_calls_setting(value: object) -> tuple[ForbiddenCallEntry, ...]:
    assert isinstance(value, list | tuple)

    return tuple(_parse_forbidden_call(entry) for entry in value)


class ForbiddenCall(LintRule):
    """Ban calls to configured functions, constructors, and helper APIs."""

    MESSAGE = "Do not call forbidden callable '{symbol}'."
    METADATA_DEPENDENCIES = (
        *LintRule.METADATA_DEPENDENCIES,
        QualifiedNameProvider,
        PositionProvider,
        ScopeProvider,
    )
    SETTINGS = {
        "forbidden_calls": RuleSetting(
            list[str],
            default=[],
            description=(
                "Callable symbols to forbid. Each entry has the form "
                "symbol[|message[|recommended_callable]], for example "
                "'os.system|Use subprocess.run|subprocess.run'."
            ),
            validator=_validate_forbidden_calls,
        ),
    }

    VALID = ()
    INVALID = ()

    def __init__(self) -> None:
        super().__init__()

        self._forbidden_calls_by_symbol: dict[str, ForbiddenCallEntry] = {}
        self._aliases_by_assignment_node: dict[cst.CSTNode, str | None] = {}
        self._star_import_modules: set[str] = set()

    def should_lint_file(self, source: bytes, path: Path) -> bool:
        del path

        return any(
            entry.symbol.rsplit(".", 1)[-1].encode() in source
            for entry in _parse_forbidden_calls_setting(self.settings.get("forbidden_calls", ()))
        )

    def visit_Module(self, node: cst.Module) -> None:
        del node

        self._forbidden_calls_by_symbol = {
            entry.symbol: entry
            for entry in _parse_forbidden_calls_setting(self.setting("forbidden_calls", list[str]))
        }
        self._aliases_by_assignment_node = {}
        self._star_import_modules = set()

    def leave_Module(self, original_node: cst.Module) -> None:
        del original_node

        self._forbidden_calls_by_symbol = {}
        self._aliases_by_assignment_node = {}
        self._star_import_modules = set()

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if not isinstance(node.names, cst.ImportStar):
            return

        module_name = dotted_name(node.module)
        if module_name is not None:
            self._star_import_modules.add(module_name)

    def visit_Assign(self, node: cst.Assign) -> None:
        for assign_target in node.targets:
            self._record_alias(assign_target.target, node.value)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if node.value is not None:
            self._record_alias(node.target, node.value)

    def visit_NamedExpr(self, node: cst.NamedExpr) -> None:
        self._record_alias(node.target, node.value)

    def visit_Call(self, node: cst.Call) -> None:
        symbol = self._forbidden_symbol_for_call(node)
        if symbol is None:
            return

        self.report(node.func, self._message_for_symbol(symbol))

    def _forbidden_symbol_for_call(self, node: cst.Call) -> str | None:
        if isinstance(node.func, cst.Name):
            alias_symbol = self._alias_symbol_for_name(node.func)
            if alias_symbol is not None:
                return alias_symbol

            star_import_symbol = self._star_import_symbol_for_call_name(node.func)
            if star_import_symbol is not None:
                return star_import_symbol

        return self._forbidden_symbol_for_expression(node.func)

    def _alias_symbol_for_name(self, node: cst.Name) -> str | None:
        scope = self.get_metadata(ScopeProvider, node, None)
        if scope is None:
            return None

        try:
            assignments = scope[node.value]
        except KeyError:
            return None

        reference_position = self.get_metadata(PositionProvider, node, None)
        if reference_position is None:
            return None

        preceding_assignments: list[tuple[int, int, cst.CSTNode]] = []
        for assignment in assignments:
            assignment_node = getattr(assignment, "node", None)
            if not isinstance(assignment_node, cst.CSTNode):
                continue
            assignment_position = self.get_metadata(PositionProvider, assignment_node, None)
            if assignment_position is None or (
                assignment_position.start.line,
                assignment_position.start.column,
            ) > (reference_position.start.line, reference_position.start.column):
                continue
            preceding_assignments.append(
                (
                    assignment_position.start.line,
                    assignment_position.start.column,
                    assignment_node,
                )
            )

        if not preceding_assignments:
            return None

        assignment_node = max(preceding_assignments, key=lambda item: item[:2])[2]
        return self._aliases_by_assignment_node.get(assignment_node)

    def _record_alias(
        self,
        target: cst.BaseExpression,
        value: cst.BaseExpression,
    ) -> None:
        if isinstance(target, cst.List | cst.Tuple) and isinstance(value, cst.List | cst.Tuple):
            if len(target.elements) != len(value.elements):
                return
            for target_element, value_element in zip(target.elements, value.elements, strict=True):
                self._record_alias(target_element.value, value_element.value)
            return

        if not isinstance(target, cst.Name):
            return

        forbidden_symbol = self._forbidden_symbol_for_expression(value)
        if forbidden_symbol is None and isinstance(value, cst.Name):
            forbidden_symbol = self._alias_symbol_for_name(value)

        self._aliases_by_assignment_node[target] = forbidden_symbol

    def _star_import_symbol_for_call_name(self, node: cst.Name) -> str | None:
        if not self._star_import_modules:
            return None

        qualified_names = self.get_metadata(QualifiedNameProvider, node, set())
        if qualified_names:
            return None

        for symbol in self._forbidden_calls_by_symbol:
            module_name, separator, call_name = symbol.rpartition(".")
            if separator and call_name == node.value and module_name in self._star_import_modules:
                return symbol

        return None

    def _forbidden_symbol_for_expression(self, node: cst.BaseExpression) -> str | None:
        forbidden_symbols = set(self._forbidden_calls_by_symbol)
        qualified_names = self._qualified_names_for_reaching_binding(node)
        if any(
            qualified_name.source is QualifiedNameSource.LOCAL for qualified_name in qualified_names
        ):
            return None

        for qualified_name in qualified_names:
            if qualified_name.source not in {
                QualifiedNameSource.IMPORT,
                QualifiedNameSource.BUILTIN,
            }:
                continue
            if qualified_name.name in forbidden_symbols:
                return qualified_name.name
            if qualified_name.source is QualifiedNameSource.BUILTIN:
                builtin_name = qualified_name.name.removeprefix("builtins.")
                if builtin_name in forbidden_symbols:
                    return builtin_name

        call_name = dotted_name(node)
        if call_name in forbidden_symbols and (not qualified_names or "." not in call_name):
            return call_name

        return None

    def _qualified_names_for_reaching_binding(
        self,
        node: cst.BaseExpression,
    ) -> Collection[QualifiedName]:
        qualified_names = self.get_metadata(QualifiedNameProvider, node, set())
        root_name = node
        while isinstance(root_name, cst.Attribute):
            root_name = root_name.value
        if not isinstance(root_name, cst.Name):
            return qualified_names

        binding_names = self._latest_same_scope_binding_names(root_name)
        if binding_names is None:
            return qualified_names

        expression_name = dotted_name(node)
        if expression_name is None:
            return qualified_names
        _, _, suffix = expression_name.partition(".")
        if not suffix:
            return binding_names

        return {
            QualifiedName(name=f"{binding_name.name}.{suffix}", source=binding_name.source)
            for binding_name in binding_names
        }

    def _latest_same_scope_binding_names(
        self,
        root_name: cst.Name,
    ) -> Collection[QualifiedName] | None:
        scope = self.get_metadata(ScopeProvider, root_name, None)
        reference_position = self.get_metadata(PositionProvider, root_name, None)
        if scope is None or reference_position is None:
            return None

        try:
            assignments = scope[root_name.value]
        except KeyError:
            return None

        preceding_assignments = []
        for assignment in assignments:
            if assignment.scope is not scope:
                continue
            assignment_node = getattr(assignment, "node", None)
            if not isinstance(assignment_node, cst.CSTNode):
                continue
            assignment_position = self.get_metadata(PositionProvider, assignment_node, None)
            if assignment_position is None or (
                assignment_position.start.line,
                assignment_position.start.column,
            ) > (reference_position.start.line, reference_position.start.column):
                continue
            preceding_assignments.append(
                (
                    assignment_position.start.line,
                    assignment_position.start.column,
                    assignment,
                )
            )

        if not preceding_assignments:
            return None

        assignment = max(preceding_assignments, key=lambda item: item[:2])[2]
        return set(assignment.get_qualified_names_for(root_name.value))

    def _message_for_symbol(self, symbol: str) -> str:
        forbidden_call = self._forbidden_calls_by_symbol[symbol]
        message = forbidden_call.message
        if message is None:
            message = self.MESSAGE.format(symbol=symbol)

        if forbidden_call.use_instead is None:
            return message

        return f"{message} Use instead: {forbidden_call.use_instead}."
