import pytest

from rattle.rules.modernization.explicit_frozen_dataclass import ExplicitFrozenDataclass
from rattle.rules.modernization.no_named_tuple import NoNamedTuple
from rattle.rules.modernization.no_static_if_condition import NoStaticIfCondition
from rattle.rules.modernization.use_rattle_ignore_comment import UseRattleIgnoreComment
from tests.support import run_rule


@pytest.mark.parametrize(
    "source",
    [
        """
        from dataclasses import dataclass
        alias = dataclass
        @alias
        class Model: pass
        alias = other
        """,
        """
        from dataclasses import dataclass
        alias: object = dataclass
        @alias
        class Model: pass
        """,
        """
        import dataclasses
        @dataclasses.dataclass
        class Model: pass
        dataclasses = other
        """,
    ],
)
def test_explicit_frozen_dataclass_resolves_the_binding_at_the_decorator(
    source: str,
) -> None:
    _runner, reports = run_rule(ExplicitFrozenDataclass(), source)

    assert len(reports) == 1


def test_explicit_frozen_dataclass_ignores_rebound_module() -> None:
    _runner, reports = run_rule(
        ExplicitFrozenDataclass(),
        """
        import dataclasses
        dataclasses = custom_module
        @dataclasses.dataclass
        class Model: pass
        """,
    )

    assert reports == []


@pytest.mark.parametrize(
    "source",
    [
        """
        from typing import NamedTuple
        alias = NamedTuple
        class Record(alias): pass
        alias = other
        """,
        """
        from typing import NamedTuple
        alias: object = NamedTuple
        class Record(alias): pass
        """,
        """
        from collections import namedtuple
        factory = namedtuple
        Record = factory("Record", [])
        """,
        """
        from collections import *
        Record = namedtuple("Record", [])
        """,
        """
        import collections
        Record = collections.namedtuple("Record", [])
        collections = other
        """,
    ],
)
def test_no_named_tuple_detects_active_aliases_and_factories(source: str) -> None:
    _runner, reports = run_rule(NoNamedTuple(), source)

    assert len(reports) == 1


def test_no_named_tuple_ignores_rebound_collections_module() -> None:
    _runner, reports = run_rule(
        NoNamedTuple(),
        """
        import collections
        collections = custom_module
        Record = collections.namedtuple("Record", [])
        """,
    )

    assert reports == []


@pytest.mark.parametrize(
    "condition",
    [
        "False or False",
        "True and True",
        "(item for item in items)",
        '"left" "right"',
        "(flag := True)",
        "lambda: None",
        'f""',
        'f"prefix{value}"',
    ],
)
def test_no_static_if_condition_detects_additional_provably_static_conditions(
    condition: str,
) -> None:
    _runner, reports = run_rule(
        NoStaticIfCondition(),
        f"if {condition}:\n    pass\n",
    )

    assert len(reports) == 1


@pytest.mark.parametrize("condition", ['f"{value}"', "[*values]", "{**mapping}"])
def test_no_static_if_condition_keeps_dynamic_truthiness(condition: str) -> None:
    _runner, reports = run_rule(
        NoStaticIfCondition(),
        f"if {condition}:\n    pass\n",
    )

    assert reports == []


@pytest.mark.parametrize(
    "condition",
    ["1 < 'a'", "1 <= None", "None > 1", "1 >= 'a'", "1 in 2", "1 not in 2", "1 < 2 < 'a'"],
)
def test_static_if_invalid_literal_comparison_is_unknown(condition: str) -> None:
    _runner, reports = run_rule(NoStaticIfCondition(), f"if {condition}:\n    pass\n")

    assert reports == []


def test_static_if_large_integer_does_not_crash() -> None:
    _runner, reports = run_rule(NoStaticIfCondition(), "if " + "1" * 5_000 + ":\n    pass\n")

    assert len(reports) == 1


@pytest.mark.parametrize(
    "comment",
    ["# noqa", "# NOQA: E123", "# flake8:noqa", "# type: ignore  # noqa"],
)
def test_use_rattle_ignore_comment_detects_noqa_directives(comment: str) -> None:
    _runner, reports = run_rule(UseRattleIgnoreComment(), f"value = 1  {comment}\n")

    assert len(reports) == 1


@pytest.mark.parametrize(
    "comment",
    [
        "# noqaed is not a directive",
        "# noqa-compatible tools",
        '# The text "# noqa" names the old syntax.',
        "# See https://example.test/noqa-policy",
    ],
)
def test_use_rattle_ignore_comment_ignores_non_directive_text(comment: str) -> None:
    _runner, reports = run_rule(UseRattleIgnoreComment(), f"value = 1  {comment}\n")

    assert reports == []


def test_static_if_detects_debug_fstring() -> None:
    _runner, reports = run_rule(NoStaticIfCondition(), 'if f"{value=}":\n    pass')

    assert len(reports) == 1


def test_no_static_if_condition_evaluates_literal_comparisons() -> None:
    _runner, reports = run_rule(NoStaticIfCondition(), "if 1 == 1:\n    pass\n")
    assert len(reports) == 1


def test_no_named_tuple_does_not_autofix_to_dataclass() -> None:
    source = """
    from dataclasses import field
    from typing import NamedTuple

    class Foo(NamedTuple):
        x: int
    result = Foo(1).x
    """

    _runner, reports = run_rule(NoNamedTuple(), source)

    assert len(reports) == 1
    assert reports[0].replacement is None
