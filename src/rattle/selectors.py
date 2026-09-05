from __future__ import annotations

import re
from collections.abc import Collection, Container, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeGuard

RuleOptionScalar = str | int | float | bool
RuleOptionValue = RuleOptionScalar | list["RuleOptionValue"] | dict[str, "RuleOptionValue"]
RULE_OPTION_TYPES = (str, int, float, bool)
RuleOptions = dict[str, RuleOptionValue]
RuleOptionsTable = dict[str, RuleOptions]

QUALIFIED_RULE_REGEX = re.compile(
    r"""
    ^
    (?P<module>
        (?P<local>\.)?
        [a-zA-Z0-9_]+(\.[a-zA-Z0-9_]+)*
    )
    (?::(?P<name>[a-z][a-z0-9]*(?:-[a-z0-9]+)*))?
    $
    """,
    re.VERBOSE,
)
RULE_NAME_SELECTOR_REGEX = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


def is_sequence(value: object) -> TypeGuard[Sequence[object]]:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def is_rule_option_value(value: object) -> TypeGuard[RuleOptionValue]:
    if isinstance(value, RULE_OPTION_TYPES):
        return True
    if isinstance(value, list):
        return all(is_rule_option_value(item) for item in value)
    if isinstance(value, Mapping):
        return all(
            isinstance(key, str) and is_rule_option_value(item) for key, item in value.items()
        )
    return False


@dataclass(frozen=True)
class QualifiedRule:
    module: str
    name: str | None = None
    local: str | None = None
    root: Path | None = field(default=None, hash=False, compare=False)

    def __str__(self) -> str:
        return self.module + (f":{self.name}" if self.name else "")

    def __lt__(self, other: object) -> bool:
        if isinstance(other, QualifiedRule):
            return str(self) < str(other)
        return NotImplemented


@dataclass(frozen=True)
class RuleNameSelector:
    value: str

    def __str__(self) -> str:
        return self.value

    def __lt__(self, other: object) -> bool:
        if isinstance(other, RuleNameSelector):
            return self.value < other.value
        return NotImplemented


RuleSelector = QualifiedRule | RuleNameSelector


@dataclass(frozen=True)
class Tags(Container[str]):
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()

    @staticmethod
    def parse(value: str | None) -> Tags:
        if not value:
            return Tags()

        include: set[str] = set()
        exclude: set[str] = set()
        tokens = {token.strip() for token in value.lower().split(",") if token.strip()}
        for token in tokens:
            if token[0] in "!^-":
                exclude.add(token[1:])
            else:
                include.add(token)

        return Tags(include=tuple(sorted(include)), exclude=tuple(sorted(exclude)))

    def __bool__(self) -> bool:
        return bool(self.include) or bool(self.exclude)

    def __contains__(self, value: object) -> bool:
        tags: Collection[str]
        if isinstance(value, str):
            tags = (value,)
        elif isinstance(value, Collection):
            tags = value
        else:
            return False

        if any(tag in self.exclude for tag in tags):
            return False
        return bool(not self.include or any(tag in self.include for tag in tags))


__all__ = [
    "QUALIFIED_RULE_REGEX",
    "RULE_NAME_SELECTOR_REGEX",
    "QualifiedRule",
    "RuleNameSelector",
    "RuleOptionValue",
    "RuleOptions",
    "RuleOptionsTable",
    "RuleSelector",
    "Tags",
    "is_rule_option_value",
    "is_sequence",
]
