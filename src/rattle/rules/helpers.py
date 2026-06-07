from __future__ import annotations

import fnmatch
from pathlib import Path

import libcst as cst
from libcst import MaybeSentinel

DOCSTRING_VALUE_NODES = (cst.ConcatenatedString, cst.SimpleString)


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
    "callable_dotted_name",
    "dotted_name",
    "is_docstring_statement",
    "is_excluded_path",
    "is_name",
    "matches_any_pattern",
    "matches_exact_path",
    "matches_path",
    "normalize_import_alias",
    "optional_setting_text",
    "ordinary_parameters",
    "path_candidates",
    "setting_fields",
    "single_small_statement",
    "target_names",
    "validate_non_negative_int",
]
