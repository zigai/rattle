from __future__ import annotations

import libcst as cst

DOCSTRING_VALUE_NODES = (cst.ConcatenatedString, cst.SimpleString)


def is_docstring_statement(statement: cst.BaseStatement) -> bool:
    if not isinstance(statement, cst.SimpleStatementLine):
        return False

    if len(statement.body) != 1:
        return False

    expression = statement.body[0]
    if not isinstance(expression, cst.Expr):
        return False

    return isinstance(expression.value, DOCSTRING_VALUE_NODES)


def validate_non_negative_int(value: object) -> object:
    if not isinstance(value, int):
        raise TypeError("must be an integer")

    if value < 0:
        raise ValueError("must be greater than or equal to 0")

    return value


__all__ = [
    "is_docstring_statement",
    "validate_non_negative_int",
]
