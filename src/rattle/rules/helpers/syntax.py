from __future__ import annotations

from collections.abc import Iterator
from typing import TypeVar

import libcst as cst
from libcst import MaybeSentinel

DOCSTRING_VALUE_NODES = (cst.ConcatenatedString, cst.SimpleString)
AliasValue = TypeVar("AliasValue")


class _CommentVisitor(cst.CSTVisitor):
    def __init__(self) -> None:
        self.found = False

    def visit_Comment(self, node: cst.Comment) -> bool:
        del node
        self.found = True
        return False


def has_comments(node: cst.CSTNode) -> bool:
    visitor = _CommentVisitor()
    node.visit(visitor)
    return visitor.found


def is_static_literal_expression(node: cst.BaseExpression) -> bool:
    result = False
    if isinstance(node, (cst.BaseNumber, cst.SimpleString, cst.Ellipsis)):
        result = True
    elif isinstance(node, cst.Name):
        result = node.value in {"False", "None", "True"}
    elif isinstance(node, cst.ConcatenatedString):
        result = is_static_literal_expression(node.left) and is_static_literal_expression(
            node.right
        )
    elif isinstance(node, cst.UnaryOperation):
        result = isinstance(node.operator, (cst.Minus, cst.Plus)) and isinstance(
            node.expression, cst.BaseNumber
        )
    elif isinstance(node, (cst.List, cst.Set, cst.Tuple)):
        result = all(
            isinstance(element, cst.Element) and is_static_literal_expression(element.value)
            for element in node.elements
        )
    elif isinstance(node, cst.Dict):
        result = all(
            isinstance(element, cst.DictElement)
            and is_static_literal_expression(element.key)
            and is_static_literal_expression(element.value)
            for element in node.elements
        )
    return result


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
