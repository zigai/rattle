from __future__ import annotations

from typing import TypeVar

import libcst as cst

DOCSTRING_VALUE_NODES = (cst.ConcatenatedString, cst.SimpleString)
AliasValue = TypeVar("AliasValue")


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
