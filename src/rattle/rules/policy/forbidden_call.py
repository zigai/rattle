from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import libcst as cst
from libcst.metadata import QualifiedNameProvider, QualifiedNameSource

from rattle import LintRule, RuleSetting
from rattle.rules.helpers import dotted_name, optional_setting_text, setting_fields

_SYMBOL_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+")


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
        raise ValueError(f"expected dotted symbol in forbidden call entry, got {entry!r}")
    if normalized_message == "":
        raise ValueError(f"expected non-empty message in forbidden call entry, got {entry!r}")
    if normalized_use_instead is not None and not _SYMBOL_PATTERN.fullmatch(normalized_use_instead):
        raise ValueError(
            f"expected dotted use_instead symbol in forbidden call entry, got {entry!r}"
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
    METADATA_DEPENDENCIES = (*LintRule.METADATA_DEPENDENCIES, QualifiedNameProvider)
    SETTINGS = {
        "forbidden_calls": RuleSetting(
            list[str],
            default=[],
            validator=_validate_forbidden_calls,
        ),
    }

    VALID: list = []
    INVALID: list = []

    def __init__(self) -> None:
        super().__init__()

        self._forbidden_calls_by_symbol: dict[str, ForbiddenCallEntry] = {}

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
            for entry in _parse_forbidden_calls_setting(self.settings["forbidden_calls"])
        }

    def leave_Module(self, original_node: cst.Module) -> None:
        del original_node

        self._forbidden_calls_by_symbol = {}

    def visit_Call(self, node: cst.Call) -> None:
        symbol = self._forbidden_symbol_for_call(node)
        if symbol is None:
            return

        self.report(node.func, self._message_for_symbol(symbol))

    def _forbidden_symbol_for_call(self, node: cst.Call) -> str | None:
        forbidden_symbols = set(self._forbidden_calls_by_symbol)
        qualified_names = self.get_metadata(QualifiedNameProvider, node.func, set())
        if any(
            qualified_name.source is QualifiedNameSource.LOCAL for qualified_name in qualified_names
        ):
            return None

        for qualified_name in qualified_names:
            if qualified_name.source is not QualifiedNameSource.IMPORT:
                continue
            if qualified_name.name in forbidden_symbols:
                return qualified_name.name

        call_name = dotted_name(node.func)
        if call_name in forbidden_symbols:
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
