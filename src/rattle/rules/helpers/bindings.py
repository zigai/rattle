from __future__ import annotations

from collections.abc import Callable, Collection, Sequence
from typing import TYPE_CHECKING, Generic, TypeVar

import libcst as cst
from libcst.metadata import (
    ParentNodeProvider,
    PositionProvider,
    QualifiedName,
    QualifiedNameProvider,
    ScopeProvider,
)
from libcst.metadata.scope_provider import Assignment, BaseAssignment

from rattle.rules.helpers.syntax import assignment_leaf_pairs, dotted_name

if TYPE_CHECKING:
    from rattle.rule import LintRule

AliasValue = TypeVar("AliasValue")


class AssignmentAliasTracker(Generic[AliasValue]):
    """Track assignment aliases and resolve the bindings that reach each name use."""

    def __init__(self, rule: LintRule) -> None:
        self._rule = rule
        self._values_by_assignment_node: dict[cst.CSTNode, AliasValue] = {}

    def reset(self) -> None:
        self._values_by_assignment_node.clear()

    def record(
        self,
        target: cst.BaseExpression,
        value: cst.BaseExpression,
        resolve_value: Callable[[cst.BaseExpression], AliasValue | None],
    ) -> None:
        for leaf_target, leaf_value in assignment_leaf_pairs(target, value):
            if not isinstance(leaf_target, cst.Name):
                continue

            resolved = resolve_value(leaf_value)
            if resolved is None:
                self._values_by_assignment_node.pop(leaf_target, None)
            else:
                self._values_by_assignment_node[leaf_target] = resolved

    def resolve(self, expression: cst.BaseExpression) -> AliasValue | None:
        if not isinstance(expression, cst.Name):
            return None
        assignment = latest_assignment(self._rule, expression)
        if assignment is None:
            return None
        return self._values_by_assignment_node.get(assignment.node)


class _NameDeclarationVisitor(cst.CSTVisitor):
    def __init__(self, name: str) -> None:
        self.name = name
        self.found = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        del node
        return False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        del node
        return False

    def visit_Lambda(self, node: cst.Lambda) -> bool:
        del node
        return False

    def visit_Global(self, node: cst.Global) -> None:
        self._record(node.names)

    def visit_Nonlocal(self, node: cst.Nonlocal) -> None:
        self._record(node.names)

    def _record(self, names: Sequence[cst.NameItem]) -> None:
        if any(item.name.value == self.name for item in names):
            self.found = True


def has_name_declaration(node: cst.CSTNode, name: str) -> bool:
    visitor = _NameDeclarationVisitor(name)
    node.visit(visitor)
    return visitor.found


def enclosing_class_defines_method(
    rule: LintRule,
    node: cst.CSTNode,
    name: str,
) -> bool:
    parent = rule.get_metadata(ParentNodeProvider, node, None)
    while parent is not None:
        if isinstance(parent, cst.ClassDef):
            return any(
                isinstance(statement, cst.FunctionDef) and statement.name.value == name
                for statement in parent.body.body
            )
        parent = rule.get_metadata(ParentNodeProvider, parent, None)
    return False


def latest_assignment(
    rule: LintRule,
    name: cst.Name,
    *,
    same_scope_only: bool = False,
) -> Assignment | None:
    scope = rule.get_metadata(ScopeProvider, name, None)
    reference_position = rule.get_metadata(PositionProvider, name, None)
    if scope is None or reference_position is None:
        return None

    try:
        assignments = scope[name.value]
    except KeyError:
        return None

    preceding_assignments: list[tuple[int, int, Assignment]] = []
    for assignment in assignments:
        if same_scope_only and assignment.scope is not scope:
            continue
        if not isinstance(assignment, Assignment):
            continue
        assignment_node = assignment.node
        assignment_position = rule.get_metadata(PositionProvider, assignment_node, None)
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
    return max(preceding_assignments, key=lambda item: item[:2])[2]


def qualified_names_for_reaching_binding(
    rule: LintRule,
    expression: cst.BaseExpression,
) -> Collection[QualifiedName]:
    qualified_names = rule.get_metadata(QualifiedNameProvider, expression, set())
    root_name = expression
    while isinstance(root_name, cst.Attribute):
        root_name = root_name.value
    if not isinstance(root_name, cst.Name):
        return qualified_names

    assignment = latest_assignment(rule, root_name, same_scope_only=True)
    if assignment is None:
        return qualified_names
    binding_names = set(assignment.get_qualified_names_for(root_name.value))

    expression_name = dotted_name(expression)
    if expression_name is None:
        return qualified_names
    _, _, suffix = expression_name.partition(".")
    if not suffix:
        return binding_names

    return {
        QualifiedName(name=f"{binding_name.name}.{suffix}", source=binding_name.source)
        for binding_name in binding_names
    }


def target_names(target: cst.BaseExpression) -> list[cst.Name]:
    if isinstance(target, cst.Name):
        return [target]

    if isinstance(target, cst.List | cst.Tuple):
        names: list[cst.Name] = []
        for element in target.elements:
            names.extend(target_names(element.value))

        return names

    if isinstance(target, cst.StarredElement):
        return target_names(target.value)

    return []


def assignment_imports_module(
    assignment: BaseAssignment,
    bound_name: str,
    module_name: str,
) -> bool:
    if not isinstance(assignment, Assignment) or not isinstance(assignment.node, cst.Import):
        return False

    for alias in assignment.node.names:
        if dotted_name(alias.name) != module_name:
            continue
        imported_name = (
            dotted_name(alias.asname.name)
            if alias.asname is not None
            else module_name.partition(".")[0]
        )
        if imported_name == bound_name:
            return True
    return False


def attribute_root_is_imported_module(
    rule: LintRule,
    expression: cst.BaseExpression,
    module_names: Collection[str],
) -> bool:
    if not isinstance(expression, cst.Attribute):
        return False

    root: cst.BaseExpression = expression
    while isinstance(root, cst.Attribute):
        root = root.value
    if not isinstance(root, cst.Name):
        return False

    scope = rule.get_metadata(ScopeProvider, root, None)
    if scope is None:
        return False
    try:
        assignments = scope[root.value]
    except KeyError:
        return False

    reference_assignments = [
        assignment
        for assignment in assignments
        if any(access.node is root for access in assignment.references)
    ]
    return bool(reference_assignments) and all(
        any(
            assignment_imports_module(assignment, root.value, module_name)
            for module_name in module_names
        )
        for assignment in reference_assignments
    )
