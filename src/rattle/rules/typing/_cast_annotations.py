from __future__ import annotations

from collections.abc import Iterable

import libcst as cst
from libcst.metadata import (
    ParentNodeProvider,
    PositionProvider,
    QualifiedNameProvider,
    QualifiedNameSource,
    ScopeProvider,
)

from rattle.rule import LintRule
from rattle.rules.helpers import (
    callable_dotted_name,
    parse_string_expression,
    single_assignment_node,
)

__rattle_collect__ = False

_NEVER_NAMES = {
    "typing.Never",
    "typing.NoReturn",
    "typing_extensions.Never",
    "typing_extensions.NoReturn",
}


class _AnnotationCollector(cst.CSTVisitor):
    def __init__(self, rule: CastAnnotationRule) -> None:
        self.rule = rule

    def visit_Assign(self, node: cst.Assign) -> None:
        if len(node.targets) != 1 or not isinstance(node.targets[0].target, cst.Name):
            return
        self.rule._record_alias((node, node.targets[0].target), node.value)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if isinstance(node.target, cst.Name) and node.value is not None:
            self.rule._record_alias((node, node.target), node.value)

    def visit_TypeAlias(self, node: cst.TypeAlias) -> None:
        self.rule._record_alias((node, node.name), node.value)

    def visit_Comment(self, node: cst.Comment) -> None:
        self.rule._record_comment(node)


class CastAnnotationRule(LintRule):
    """Shared semantic support for diagnostic-only rules around ``typing.cast``."""

    METADATA_DEPENDENCIES = (
        *LintRule.METADATA_DEPENDENCIES,
        ParentNodeProvider,
        PositionProvider,
        QualifiedNameProvider,
        ScopeProvider,
    )

    def __init__(self) -> None:
        super().__init__()
        self._aliases: dict[cst.CSTNode, cst.BaseExpression] = {}
        self._standalone_comment_lines: set[int] = set()
        self._safety_comment_lines: set[int] = set()

    def visit_Module(self, node: cst.Module) -> None:
        self._aliases = {}
        self._standalone_comment_lines = set()
        self._safety_comment_lines = set()
        node.visit(_AnnotationCollector(self))

    def leave_Module(self, original_node: cst.Module) -> None:
        del original_node
        self._aliases = {}
        self._standalone_comment_lines = set()
        self._safety_comment_lines = set()

    def cast_arguments(  # noqa: PLR0911 - flat argument guards preserve parser clarity
        self, call: cst.Call
    ) -> tuple[cst.BaseExpression, cst.BaseExpression] | None:
        if not self._is_cast_callable(call.func, call, frozenset()):
            return None

        values: dict[str, cst.BaseExpression] = {}
        positional_names = iter(("typ", "val"))
        for argument in call.args:
            if argument.star:
                return None
            if argument.keyword is None:
                name = next(positional_names, None)
                if name is None:
                    return None
            else:
                name = argument.keyword.value
                if name not in {"typ", "val"}:
                    return None
            if name in values:
                return None
            values[name] = argument.value

        target = values.get("typ")
        value = values.get("val")
        if target is None or value is None:
            return None
        return target, value

    def is_never_target(self, expression: cst.BaseExpression, context: cst.CSTNode) -> bool:
        return self._is_never_target(expression, context, frozenset())

    def is_nested_cast_value(self, call: cst.Call) -> bool:
        parent = self.get_metadata(ParentNodeProvider, call, None)
        if not isinstance(parent, cst.Arg):
            return False
        outer = self.get_metadata(ParentNodeProvider, parent, None)
        if not isinstance(outer, cst.Call):
            return False
        arguments = self.cast_arguments(outer)
        return arguments is not None and arguments[1] is call

    def has_safety_comment(self, call: cst.Call) -> bool:
        call_position = self.get_metadata(PositionProvider, call, None)
        if call_position is not None and self._has_safety_block_before(call_position.start.line):
            return True

        owner = self._nearest_statement_owner(call)
        if owner is None:
            return False
        owner_position = self.get_metadata(PositionProvider, owner, None)
        return owner_position is not None and self._has_safety_block_before(
            owner_position.start.line
        )

    def _is_cast_callable(
        self,
        expression: cst.BaseExpression,
        context: cst.CSTNode,
        resolving: frozenset[cst.CSTNode],
    ) -> bool:
        alias = self._resolve_alias(expression, context)
        if alias is not None:
            alias_node, alias_value = alias
            if alias_node in resolving:
                return False
            return self._is_cast_callable(alias_value, context, resolving | {alias_node})
        return self._qualified_name(expression, context) == "typing.cast"

    def _is_never_target(
        self,
        expression: cst.BaseExpression,
        context: cst.CSTNode,
        resolving: frozenset[cst.CSTNode],
    ) -> bool:
        parsed = parse_string_expression(expression)
        if parsed is not None:
            return self._is_never_target(parsed, context, resolving)

        alias = self._resolve_alias(expression, context)
        if alias is not None:
            alias_node, alias_value = alias
            if alias_node in resolving:
                return False
            return self._is_never_target(alias_value, context, resolving | {alias_node})
        return self._qualified_name(expression, context) in _NEVER_NAMES

    def _resolve_alias(
        self, expression: cst.BaseExpression, context: cst.CSTNode
    ) -> tuple[cst.CSTNode, cst.BaseExpression] | None:
        if not isinstance(expression, cst.Name):
            return None
        assignment_node = single_assignment_node(self, expression, context=context)
        if assignment_node is None:
            return None
        value = self._aliases.get(assignment_node)
        if value is None:
            return None
        return assignment_node, value

    def _qualified_name(  # noqa: PLR0911 - ordered metadata fallbacks are clearest
        self, expression: cst.BaseExpression, context: cst.CSTNode
    ) -> str | None:
        qualified_names = self.get_metadata(QualifiedNameProvider, expression, set())
        if qualified_names:
            if any(name.source is QualifiedNameSource.LOCAL for name in qualified_names):
                return None
            names = {
                name.name
                for name in qualified_names
                if name.source in {QualifiedNameSource.BUILTIN, QualifiedNameSource.IMPORT}
            }
            return next(iter(names)) if len(names) == 1 else None

        dotted_name = callable_dotted_name(expression)
        if dotted_name is None:
            return None
        root, separator, suffix = dotted_name.partition(".")
        scope = self.get_metadata(ScopeProvider, context, None)
        if scope is None:
            return None
        try:
            assignments = tuple(scope[root])
        except KeyError:
            return None
        names = {
            name.name
            for assignment in assignments
            for name in assignment.get_qualified_names_for(root)
            if name.source in {QualifiedNameSource.BUILTIN, QualifiedNameSource.IMPORT}
        }
        if len(names) != 1:
            return None
        qualified_root = next(iter(names))
        return f"{qualified_root}.{suffix}" if separator else qualified_root

    def _record_alias(self, nodes: Iterable[cst.CSTNode], value: cst.BaseExpression) -> None:
        for node in nodes:
            self._aliases[node] = value

    def _record_comment(self, comment: cst.Comment) -> None:
        parent = self.get_metadata(ParentNodeProvider, comment, None)
        if isinstance(parent, cst.TrailingWhitespace):
            container = self.get_metadata(ParentNodeProvider, parent, None)
            if isinstance(container, cst.SimpleStatementLine | cst.SimpleStatementSuite):
                return
        elif not isinstance(parent, cst.EmptyLine):
            return
        position = self.get_metadata(PositionProvider, comment, None)
        if position is None:
            return
        line = position.start.line
        self._standalone_comment_lines.add(line)
        if "SAFETY:" in comment.value:
            self._safety_comment_lines.add(line)

    def _has_safety_block_before(self, line: int) -> bool:
        candidate = line - 1
        while candidate in self._standalone_comment_lines:
            if candidate in self._safety_comment_lines:
                return True
            candidate -= 1
        return False

    def _nearest_statement_owner(self, node: cst.CSTNode) -> cst.CSTNode | None:
        current: cst.CSTNode | None = node
        nearest_statement: cst.BaseStatement | None = None
        while current is not None:
            current = self.get_metadata(ParentNodeProvider, current, None)
            if isinstance(current, cst.BaseSmallStatement):
                return current
            if nearest_statement is None and isinstance(current, cst.BaseStatement):
                nearest_statement = current
        return nearest_statement
