from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import libcst as cst
from libcst.metadata import (
    PositionProvider,
    QualifiedNameProvider,
    QualifiedNameSource,
    ScopeProvider,
)

from rattle import LintRule, RuleSetting
from rattle.rules.helpers import (
    assignment_leaf_pairs,
    dotted_name,
    latest_assignment_node,
    optional_setting_text,
    qualified_names_for_reaching_binding,
    setting_fields,
)

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
        assignment_node = latest_assignment_node(self, node)
        if assignment_node is None:
            return None
        return self._aliases_by_assignment_node.get(assignment_node)

    def _record_alias(
        self,
        target: cst.BaseExpression,
        value: cst.BaseExpression,
    ) -> None:
        for leaf_target, leaf_value in assignment_leaf_pairs(target, value):
            if not isinstance(leaf_target, cst.Name):
                continue

            forbidden_symbol = self._forbidden_symbol_for_expression(leaf_value)
            if forbidden_symbol is None and isinstance(leaf_value, cst.Name):
                forbidden_symbol = self._alias_symbol_for_name(leaf_value)

            self._aliases_by_assignment_node[leaf_target] = forbidden_symbol

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
        qualified_names = qualified_names_for_reaching_binding(self, node)
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

    def _message_for_symbol(self, symbol: str) -> str:
        forbidden_call = self._forbidden_calls_by_symbol[symbol]
        message = forbidden_call.message
        if message is None:
            message = self.MESSAGE.format(symbol=symbol)

        if forbidden_call.use_instead is None:
            return message

        return f"{message} Use instead: {forbidden_call.use_instead}."
