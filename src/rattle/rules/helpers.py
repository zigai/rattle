from __future__ import annotations

import fnmatch
from collections.abc import Collection, Iterator, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst
from libcst import MaybeSentinel
from libcst.metadata import (
    ParentNodeProvider,
    PositionProvider,
    QualifiedName,
    QualifiedNameProvider,
    ScopeProvider,
)
from libcst.metadata.scope_provider import Assignment, BaseAssignment

if TYPE_CHECKING:
    from rattle.rule import LintRule

DOCSTRING_VALUE_NODES = (cst.ConcatenatedString, cst.SimpleString)


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
) -> BaseAssignment | None:
    scope = rule.get_metadata(ScopeProvider, name, None)
    reference_position = rule.get_metadata(PositionProvider, name, None)
    if scope is None or reference_position is None:
        return None

    try:
        assignments = scope[name.value]
    except KeyError:
        return None

    preceding_assignments: list[tuple[int, int, BaseAssignment]] = []
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


def latest_assignment_node(rule: LintRule, expression: cst.BaseExpression) -> cst.CSTNode | None:
    if not isinstance(expression, cst.Name):
        return None
    assignment = latest_assignment(rule, expression)
    return assignment.node if isinstance(assignment, Assignment) else None


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


def single_small_statement(
    statement: cst.BaseStatement,
    *,
    allow_leading_lines: bool = True,
) -> cst.BaseSmallStatement | None:
    if not isinstance(statement, cst.SimpleStatementLine):
        return None
    if not allow_leading_lines and statement.leading_lines:
        return None
    if len(statement.body) != 1:
        return None

    return statement.body[0]


def is_docstring_statement(statement: cst.BaseStatement) -> bool:
    expression = single_small_statement(statement)
    if not isinstance(expression, cst.Expr):
        return False

    return isinstance(expression.value, DOCSTRING_VALUE_NODES)


def is_name(node: cst.CSTNode | None, value: str) -> bool:
    return isinstance(node, cst.Name) and node.value == value


def dotted_name(node: cst.CSTNode | None) -> str | None:
    if isinstance(node, cst.Name):
        return node.value

    if isinstance(node, cst.Attribute):
        parent_name = dotted_name(node.value)
        if parent_name is None:
            return None

        return f"{parent_name}.{node.attr.value}"

    return None


def callable_dotted_name(node: cst.CSTNode | None) -> str | None:
    if isinstance(node, cst.Name):
        return node.value

    if isinstance(node, cst.Attribute):
        parent_name = callable_dotted_name(node.value)
        if parent_name is None:
            return node.attr.value

        return f"{parent_name}.{node.attr.value}"

    if isinstance(node, cst.Call):
        return callable_dotted_name(node.func)

    if isinstance(node, cst.Subscript):
        return callable_dotted_name(node.value)

    return None


def alias_name(alias: cst.AsName | None, default: str) -> str:
    if alias is None:
        return default
    if isinstance(alias.name, cst.Name):
        return alias.name.value

    return default


def ordinary_parameters(parameters: cst.Parameters) -> list[cst.Param]:
    ordinary_params: list[cst.Param] = [
        *parameters.posonly_params,
        *parameters.params,
        *parameters.kwonly_params,
    ]

    if isinstance(parameters.star_arg, cst.Param):
        ordinary_params.append(parameters.star_arg)

    if parameters.star_kwarg is not None:
        ordinary_params.append(parameters.star_kwarg)

    return ordinary_params


def normalize_import_alias(alias: cst.ImportAlias) -> cst.ImportAlias:
    return alias.with_changes(comma=MaybeSentinel.DEFAULT)


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


def assignment_leaf_pairs(
    target: cst.BaseExpression,
    value: cst.BaseExpression,
) -> Iterator[tuple[cst.BaseExpression, cst.BaseExpression]]:
    if isinstance(target, cst.List | cst.Tuple) and isinstance(value, cst.List | cst.Tuple):
        if len(target.elements) != len(value.elements):
            return
        for target_element, value_element in zip(target.elements, value.elements, strict=True):
            yield from assignment_leaf_pairs(target_element.value, value_element.value)
        return

    yield target, value


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


def matches_any_pattern(patterns: list[str], value: str) -> bool:
    return any(fnmatch.fnmatchcase(value, pattern) for pattern in patterns)


def path_candidates(path: Path) -> tuple[str, ...]:
    candidates = [path.as_posix(), path.name]
    try:
        candidates.append(path.relative_to(Path.cwd()).as_posix())
    except ValueError:
        pass

    return tuple(dict.fromkeys(candidates))


def matches_path(pattern: str, path: Path) -> bool:
    return any(fnmatch.fnmatchcase(candidate, pattern) for candidate in path_candidates(path))


def matches_exact_path(expected_path: str, path: Path) -> bool:
    return expected_path in path_candidates(path)


def is_excluded_path(path: Path, excluded_path_parts: list[str]) -> bool:
    if path.name.startswith("test_") or path.name.endswith("_test.py"):
        return True

    return any(part in excluded_path_parts for part in path.parts)


def setting_fields(entry: str, field_count: int) -> tuple[str, ...]:
    parts = entry.split("|", field_count - 1)
    return (*parts, *("" for _ in range(field_count - len(parts))))


def optional_setting_text(value: str) -> str | None:
    return value.strip() or None


def validate_non_negative_int(value: object) -> object:
    if not isinstance(value, int):
        raise TypeError("must be an integer")

    if value < 0:
        raise ValueError("must be greater than or equal to 0")

    return value


__all__ = [
    "alias_name",
    "assignment_imports_module",
    "assignment_leaf_pairs",
    "attribute_root_is_imported_module",
    "callable_dotted_name",
    "dotted_name",
    "enclosing_class_defines_method",
    "has_name_declaration",
    "is_docstring_statement",
    "is_excluded_path",
    "is_name",
    "latest_assignment",
    "latest_assignment_node",
    "matches_any_pattern",
    "matches_exact_path",
    "matches_path",
    "normalize_import_alias",
    "optional_setting_text",
    "ordinary_parameters",
    "path_candidates",
    "qualified_names_for_reaching_binding",
    "setting_fields",
    "single_small_statement",
    "target_names",
    "validate_non_negative_int",
]
