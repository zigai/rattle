from pathlib import Path
from textwrap import dedent

import pytest

from rattle.config.models import Config
from rattle.diagnostics import LintViolation
from rattle.engine import LintRunner
from rattle.rule import LintRule
from rattle.rules.typing.no_any_type_aliases import NoAnyTypeAliases
from rattle.rules.typing.no_known_value_to_any import NoKnownValueToAny

ALIAS_MESSAGE = "Do not hide `Any` behind a type alias; use a concrete owner type."
KNOWN_VALUE_MESSAGE = (
    "This explicit `Any` annotation discards known type evidence. "
    "Keep inference or use a concrete owner contract."
)


def _reports(
    rule: LintRule,
    source: str,
    *,
    path: Path = Path("sample.py"),
) -> tuple[LintRunner, list[LintViolation]]:
    runner = LintRunner(path, dedent(source).encode())
    return runner, list(runner.collect_violations([rule], Config(path=path)))


def test_public_rule_names_match_the_documented_selectors() -> None:
    assert NoAnyTypeAliases.name == "no-any-type-aliases"
    assert NoKnownValueToAny.name == "no-known-value-to-any"


@pytest.mark.parametrize(
    "source",
    [
        """
        from typing import Any

        type Payload = Any
        """,
        """
        from typing import Any as Dynamic, TypeAlias as AliasMarker

        Payload: AliasMarker = Dynamic
        """,
        """
        import typing as t

        Payload: t.TypeAlias = t.Any
        """,
    ],
)
def test_any_alias_rule_resolves_pep_695_and_legacy_alias_spellings(
    source: str,
) -> None:
    _runner, reports = _reports(NoAnyTypeAliases(), source)

    assert [report.message for report in reports] == [ALIAS_MESSAGE]


@pytest.mark.parametrize(
    "expression",
    [
        "Annotated[Any, 'owner metadata']",
        "Required[Any]",
        "NotRequired[Any]",
        "ReadOnly[Any]",
        "Optional[Any]",
        "Union[int, Any]",
        "Any | None",
    ],
)
def test_any_alias_rule_looks_through_transparent_wrappers(expression: str) -> None:
    _runner, reports = _reports(
        NoAnyTypeAliases(),
        f"""
        from typing import Annotated, Any, NotRequired, Optional, Required, Union
        from typing_extensions import ReadOnly

        type Payload = {expression}
        """,
    )

    assert [report.message for report in reports] == [ALIAS_MESSAGE]


def test_any_alias_rule_follows_alias_chains_and_reports_each_alias_owner() -> None:
    _runner, reports = _reports(
        NoAnyTypeAliases(),
        """
        from typing import Any, TypeAlias

        Base: TypeAlias = Any
        Payload: TypeAlias = Base
        value: Payload
        """,
    )

    assert [report.message for report in reports] == [ALIAS_MESSAGE, ALIAS_MESSAGE]
    assert [report.range.start.line for report in reports if report.range is not None] == [
        4,
        5,
    ]


def test_any_alias_rule_owns_only_wholly_any_aliases_not_nested_any() -> None:
    _runner, reports = _reports(
        NoAnyTypeAliases(),
        """
        from typing import Any

        type Direct = Any
        type Nested = list[Any]
        direct: Direct
        nested: Nested
        """,
    )

    assert [report.message for report in reports] == [ALIAS_MESSAGE]
    assert reports[0].range is not None
    assert reports[0].range.start.line == 4


@pytest.mark.parametrize(
    "source",
    [
        """
        class Any:
            pass

        type Payload = Any
        """,
        """
        from typing import Any

        Any = object
        type Payload = Any
        """,
        """
        import typing

        class LocalTyping:
            Any = object
            TypeAlias = object

        typing = LocalTyping()
        Payload: typing.TypeAlias = typing.Any
        """,
        """
        from typing import Any

        class TypeAlias:
            pass

        Payload: TypeAlias = Any
        """,
        """
        if use_extensions:
            from typing import Any
        else:
            from custom_types import Any

        type Payload = Any
        """,
    ],
)
def test_any_alias_rule_respects_shadowing_rebinding_and_ambiguity(source: str) -> None:
    _runner, reports = _reports(NoAnyTypeAliases(), source)

    assert reports == []


@pytest.mark.parametrize(
    "initializer",
    [
        "1",
        "True",
        "False",
        "1.5",
        "2j",
        "'known'",
        "b'known'",
        "f'{item}'",
        "[1, 2]",
        "(1, 2)",
        "{1, 2}",
        "{'key': 1}",
        "[item for item in items]",
        "{item for item in items}",
        "{item: item for item in items}",
        "(item for item in items)",
        "lambda item: item",
        "build_value()",
    ],
)
def test_known_value_rule_reports_direct_initializer_evidence(initializer: str) -> None:
    _runner, reports = _reports(
        NoKnownValueToAny(),
        f"""
        from typing import Any

        value: Any = {initializer}
        """,
    )

    assert [report.message for report in reports] == [KNOWN_VALUE_MESSAGE]


@pytest.mark.parametrize(
    "annotation",
    [
        "Dynamic",
        "types.Any",
        "Annotated[Dynamic, 'owner metadata']",
        "Optional[Dynamic]",
        "Union[int, Dynamic]",
        "Dynamic | None",
        "Required[Dynamic]",
        "NotRequired[Dynamic]",
        "ReadOnly[Dynamic]",
    ],
)
def test_known_value_rule_resolves_aliases_and_transparent_wrappers(
    annotation: str,
) -> None:
    _runner, reports = _reports(
        NoKnownValueToAny(),
        f"""
        import typing as types
        from typing import (
            Annotated,
            Any as Dynamic,
            NotRequired,
            Optional,
            Required,
            Union,
        )
        from typing_extensions import ReadOnly

        value: {annotation} = create_value()
        """,
    )

    assert [report.message for report in reports] == [KNOWN_VALUE_MESSAGE]


def test_known_value_rule_follows_explicit_type_alias_chains() -> None:
    _runner, reports = _reports(
        NoKnownValueToAny(),
        """
        from typing import Any

        type Dynamic = Any
        type AlsoDynamic = Dynamic
        value: AlsoDynamic = create_value()
        """,
    )

    assert [report.message for report in reports] == [KNOWN_VALUE_MESSAGE]
    assert reports[0].range is not None
    assert reports[0].range.start.line == 6


def test_known_value_rule_reports_name_and_attribute_targets() -> None:
    _runner, reports = _reports(
        NoKnownValueToAny(),
        """
        from typing import Any

        local: Any = 1
        namespace.value: Any = make_value()
        """,
    )

    assert [report.message for report in reports] == [
        KNOWN_VALUE_MESSAGE,
        KNOWN_VALUE_MESSAGE,
    ]
    assert [report.range.start.line for report in reports if report.range is not None] == [
        4,
        5,
    ]


def test_known_value_rule_uses_stable_local_initializer_evidence() -> None:
    _runner, reports = _reports(
        NoKnownValueToAny(),
        """
        from typing import Any

        precise = {"id": 1}
        widened: Any = precise
        """,
    )

    assert [report.message for report in reports] == [KNOWN_VALUE_MESSAGE]
    assert reports[0].range is not None
    assert reports[0].range.start.line == 5


@pytest.mark.parametrize(
    "source",
    [
        """
        from typing import Any

        precise = 1
        precise = load_value()
        widened: Any = precise
        """,
        """
        from typing import Any

        widened: Any = unknown_value
        """,
        """
        from typing import Any

        def widen(precise):
            widened: Any = precise
            return widened
        """,
    ],
)
def test_known_value_rule_requires_unambiguous_stable_local_evidence(
    source: str,
) -> None:
    _runner, reports = _reports(NoKnownValueToAny(), source)

    assert reports == []


def test_known_value_rule_ignores_nested_any_annotations() -> None:
    _runner, reports = _reports(
        NoKnownValueToAny(),
        """
        from typing import Any

        values: list[Any] = [1]
        mapping: dict[str, Any] = {"key": 1}
        """,
    )

    assert reports == []


def test_known_value_rule_ignores_declarations_signatures_and_placeholders() -> None:
    _runner, reports = _reports(
        NoKnownValueToAny(),
        """
        from typing import Any

        declared: Any
        none_value: Any = None
        stub_value: Any = ...

        def transform(argument: Any) -> Any:
            return argument

        class Owner:
            declared: Any
        """,
    )

    assert reports == []


@pytest.mark.parametrize(
    "source",
    [
        """
        class Any:
            pass

        value: Any = 1
        """,
        """
        from typing import Any

        Any = object
        value: Any = 1
        """,
        """
        import typing

        class LocalTyping:
            Any = object

        typing = LocalTyping()
        value: typing.Any = 1
        """,
        """
        if use_extensions:
            from typing import Any
        else:
            from custom_types import Any

        value: Any = 1
        """,
    ],
)
def test_known_value_rule_respects_shadowing_rebinding_and_ambiguity(
    source: str,
) -> None:
    _runner, reports = _reports(NoKnownValueToAny(), source)

    assert reports == []


@pytest.mark.parametrize(
    ("rule", "source"),
    [
        (
            NoAnyTypeAliases(),
            "from typing import Any\ntype Payload = Any\n",
        ),
        (
            NoKnownValueToAny(),
            "from typing import Any\nvalue: Any = 1\n",
        ),
    ],
)
def test_any_policy_rules_use_the_default_test_path_exclusion(
    rule: LintRule,
    source: str,
) -> None:
    _runner, reports = _reports(rule, source, path=Path("tests/sample.py"))

    assert reports == []


@pytest.mark.parametrize(
    ("rule", "source", "message"),
    [
        (
            NoAnyTypeAliases(),
            "from typing import Any\ntype Payload = Any\n",
            ALIAS_MESSAGE,
        ),
        (
            NoKnownValueToAny(),
            "from typing import Any\nvalue: Any = 1\n",
            KNOWN_VALUE_MESSAGE,
        ),
    ],
)
def test_any_policy_path_exclusion_is_configurable(
    rule: LintRule,
    source: str,
    message: str,
) -> None:
    rule.configure({"excluded_path_parts": []})
    _runner, reports = _reports(rule, source, path=Path("tests/sample.py"))

    assert [report.message for report in reports] == [message]


@pytest.mark.parametrize(
    ("rule", "source", "message"),
    [
        (
            NoAnyTypeAliases(),
            "from typing import Any\ntype Payload = Any\n",
            ALIAS_MESSAGE,
        ),
        (
            NoKnownValueToAny(),
            "from typing import Any\nvalue: Any = make_value()\n",
            KNOWN_VALUE_MESSAGE,
        ),
    ],
)
def test_any_policy_diagnostics_have_exact_messages_and_no_replacements(
    rule: LintRule,
    source: str,
    message: str,
) -> None:
    runner, reports = _reports(rule, source)

    assert [report.message for report in reports] == [message]
    assert [report.replacement for report in reports] == [None]
    assert runner.apply_replacements(reports).code == source
