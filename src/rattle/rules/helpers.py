from __future__ import annotations

import fnmatch
from pathlib import Path

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


def validate_non_negative_int(value: object) -> object:
    if not isinstance(value, int):
        raise TypeError("must be an integer")

    if value < 0:
        raise ValueError("must be greater than or equal to 0")

    return value


__all__ = [
    "alias_name",
    "callable_dotted_name",
    "dotted_name",
    "is_docstring_statement",
    "is_excluded_path",
    "matches_exact_path",
    "matches_path",
    "path_candidates",
    "validate_non_negative_int",
]
