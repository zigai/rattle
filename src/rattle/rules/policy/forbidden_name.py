from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path

import libcst as cst

from rattle import Invalid, LintRule, RuleSetting, Valid
from rattle.rules.helpers import optional_setting_text, setting_fields, target_names

_ENTRY_PATTERN = re.compile(
    r"(?P<kind>any|variable|parameter|function|class|attribute|import|alias):(?P<pattern>[A-Za-z_][A-Za-z0-9_*?\[\]!-]*)"
)
_GLOB_CHARS = frozenset("*?[")


@dataclass(frozen=True)
class ForbiddenNameEntry:
    kind: str
    pattern: str
    message: str | None = None

    @property
    def rule(self) -> str:
        return f"{self.kind}:{self.pattern}"


def _parse_forbidden_name(entry: str | ForbiddenNameEntry) -> ForbiddenNameEntry:
    if isinstance(entry, ForbiddenNameEntry):
        return entry

    rule, message = setting_fields(entry, 2)
    kind, _, pattern = rule.partition(":")
    normalized_message = optional_setting_text(message)

    rule = f"{kind}:{pattern}"
    if not _ENTRY_PATTERN.fullmatch(rule):
        raise ValueError(f"expected forbidden name entry with kind and pattern, got {entry!r}")
    if normalized_message == "":
        raise ValueError(f"expected non-empty message in forbidden name entry, got {entry!r}")

    return ForbiddenNameEntry(kind=kind, pattern=pattern, message=normalized_message)


def _validate_forbidden_names(value: object) -> object:
    assert isinstance(value, list)

    for entry in value:
        _parse_forbidden_name(entry)

    return True


def _parse_forbidden_names_setting(value: object) -> tuple[ForbiddenNameEntry, ...]:
    assert isinstance(value, list | tuple)

    return tuple(_parse_forbidden_name(entry) for entry in value)


def _is_glob(pattern: str) -> bool:
    return any(char in _GLOB_CHARS for char in pattern)


def _matches_pattern(pattern: str, name: str) -> bool:
    if _is_glob(pattern):
        return fnmatch.fnmatchcase(name, pattern)

    return name == pattern


def _dotted_names(node: cst.BaseExpression) -> list[cst.Name]:
    if isinstance(node, cst.Name):
        return [node]

    if isinstance(node, cst.Attribute):
        return [*_dotted_names(node.value), node.attr]

    return []


class ForbiddenName(LintRule):
    """Ban configured names by identifier kind and pattern."""

    MESSAGE = "Do not use forbidden {kind} name '{name}'."
    SETTINGS = {
        "forbidden_names": RuleSetting(
            list[str],
            default=[],
            validator=_validate_forbidden_names,
        ),
    }

    VALID: list[Valid] = []
    INVALID: list[Invalid] = []

    def __init__(self) -> None:
        super().__init__()

        self._messages_by_rule: dict[str, str | None] = {}

    def should_lint_file(self, source: bytes, path: Path) -> bool:
        del path

        for entry in _parse_forbidden_names_setting(self.settings.get("forbidden_names", ())):
            pattern = entry.pattern
            if _is_glob(pattern):
                return True
            if pattern.encode() in source:
                return True

        return False

    def visit_Module(self, node: cst.Module) -> None:
        del node

        self._messages_by_rule = {
            entry.rule: entry.message
            for entry in _parse_forbidden_names_setting(self.settings["forbidden_names"])
        }

    def leave_Module(self, original_node: cst.Module) -> None:
        del original_node

        self._messages_by_rule = {}

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        self._report_for_name(node.name, "class")

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        self._report_for_name(node.name, "function")

    def visit_Param(self, node: cst.Param) -> None:
        self._report_for_name(node.name, "parameter")

    def visit_AssignTarget(self, node: cst.AssignTarget) -> None:
        self._report_for_target(node.target)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        self._report_for_target(node.target)

    def visit_AugAssign(self, node: cst.AugAssign) -> None:
        self._report_for_target(node.target)

    def visit_For(self, node: cst.For) -> None:
        self._report_for_target(node.target)

    def visit_CompFor(self, node: cst.CompFor) -> None:
        self._report_for_target(node.target)

    def visit_NamedExpr(self, node: cst.NamedExpr) -> None:
        self._report_for_target(node.target)

    def visit_WithItem(self, node: cst.WithItem) -> None:
        if node.asname is None:
            return

        self._report_for_target(node.asname.name)

    def visit_ExceptHandler(self, node: cst.ExceptHandler) -> None:
        if node.name is None:
            return

        self._report_for_target(node.name.name)

    def visit_Attribute(self, node: cst.Attribute) -> None:
        self._report_for_name(node.attr, "attribute")

    def visit_ImportAlias(self, node: cst.ImportAlias) -> None:
        if node.asname is not None:
            alias_name = node.asname.name
            if isinstance(alias_name, cst.Name):
                self._report_for_name(alias_name, "alias")

            return

        for name in _dotted_names(node.name):
            self._report_for_name(name, "import")

    def _report_for_target(self, target: cst.BaseExpression) -> None:
        for name in target_names(target):
            self._report_for_name(name, "variable")

    def _report_for_name(self, node: cst.Name, kind: str) -> None:
        name = node.value
        rule = self._matching_rule(kind, name)
        if rule is None:
            return

        message = self._messages_by_rule[rule]
        if message is None:
            message = self.MESSAGE.format(kind=kind, name=name)

        self.report(node, message)

    def _matching_rule(self, kind: str, name: str) -> str | None:
        for rule in self._messages_by_rule:
            rule_kind, _, pattern = rule.partition(":")
            if rule_kind not in {kind, "any"}:
                continue
            if _matches_pattern(pattern, name):
                return rule

        return None
