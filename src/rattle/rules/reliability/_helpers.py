from __future__ import annotations

from pathlib import Path

import libcst as cst


def module_name(module: cst.BaseExpression | None) -> str | None:
    if isinstance(module, cst.Name):
        return module.value

    if isinstance(module, cst.Attribute):
        value_name = module_name(module.value)
        if value_name is None:
            return None

        return f"{value_name}.{module.attr.value}"

    return None


def call_name(expression: cst.BaseExpression) -> str | None:
    if isinstance(expression, cst.Name):
        return expression.value

    if isinstance(expression, cst.Attribute):
        value_name = call_name(expression.value)
        if value_name is None:
            return None

        return f"{value_name}.{expression.attr.value}"

    return None


def alias_name(alias: cst.AsName | None, default: str) -> str:
    if alias is None:
        return default
    if isinstance(alias.name, cst.Name):
        return alias.name.value

    return default


def is_excluded_path(path: Path, excluded_path_parts: list[str]) -> bool:
    if path.name.startswith("test_") or path.name.endswith("_test.py"):
        return True

    return any(part in excluded_path_parts for part in path.parts)


__all__ = [
    "alias_name",
    "call_name",
    "is_excluded_path",
    "module_name",
]
