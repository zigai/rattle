from pathlib import Path
from textwrap import dedent

import pytest

from rattle.engine import LintRunner
from rattle.ftypes import Config, LintViolation
from rattle.rule import LintRule
from rattle.rules.fixit.explicit_frozen_dataclass import ExplicitFrozenDataclass
from rattle.rules.fixit.no_namedtuple import NoNamedTuple
from rattle.rules.fixit.no_static_if_condition import NoStaticIfCondition
from rattle.rules.fixit.sorted_attributes_rule import SortedAttributes
from rattle.rules.fixit.use_rattle_ignore_comment import UseRattleIgnoreComment
from rattle.rules.fixit.use_types_from_typing import UseTypesFromTyping
from rattle.rules.fixit.variadic_callable_syntax import VariadicCallableSyntax


def _reports(rule: LintRule, source: str) -> tuple[LintRunner, list[LintViolation]]:
    path = Path("sample.py")
    runner = LintRunner(path, dedent(source).encode())
    return runner, list(runner.collect_violations([rule], Config(path=path)))


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
    _runner, reports = _reports(ExplicitFrozenDataclass(), source)

    assert len(reports) == 1


def test_explicit_frozen_dataclass_ignores_rebound_module() -> None:
    _runner, reports = _reports(
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
    _runner, reports = _reports(NoNamedTuple(), source)

    assert len(reports) == 1


def test_no_named_tuple_ignores_rebound_collections_module() -> None:
    _runner, reports = _reports(
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
    _runner, reports = _reports(
        NoStaticIfCondition(),
        f"if {condition}:\n    pass\n",
    )

    assert len(reports) == 1


@pytest.mark.parametrize("condition", ['f"{value}"', "[*values]", "{**mapping}"])
def test_no_static_if_condition_keeps_dynamic_truthiness(condition: str) -> None:
    _runner, reports = _reports(
        NoStaticIfCondition(),
        f"if {condition}:\n    pass\n",
    )

    assert reports == []


def test_sorted_attributes_fixes_nested_directive_classes() -> None:
    runner, reports = _reports(
        SortedAttributes(),
        '''
        class Outer:
            """@sorted-attributes"""
            z = 1
            a = 2
            class Inner:
                """@sorted-attributes"""
                z = 1
                a = 2
        ''',
    )

    assert len(reports) == 2
    assert runner.apply_replacements(reports).code == dedent(
        '''
        class Outer:
            """@sorted-attributes"""
            a = 2
            z = 1
            class Inner:
                """@sorted-attributes"""
                a = 2
                z = 1
        ''',
    )


def test_sorted_attributes_does_not_sort_across_blank_lines() -> None:
    _runner, reports = _reports(
        SortedAttributes(),
        '''
        class Constants:
            """@sorted-attributes"""
            z = 1

            a = 2
        ''',
    )

    assert reports == []


@pytest.mark.parametrize(
    "comment",
    ["# noqa", "# NOQA: E123", "# flake8:noqa", "# type: ignore  # noqa"],
)
def test_use_rattle_ignore_comment_detects_noqa_directives(comment: str) -> None:
    _runner, reports = _reports(UseRattleIgnoreComment(), f"value = 1  {comment}\n")

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
    _runner, reports = _reports(UseRattleIgnoreComment(), f"value = 1  {comment}\n")

    assert reports == []


@pytest.mark.parametrize(
    "annotation",
    ["list", "dict", "tuple", "set", "Annotated[str, list]"],
)
def test_use_types_from_typing_allows_non_generic_builtin_annotations(
    annotation: str,
) -> None:
    _runner, reports = _reports(UseTypesFromTyping(), f"value: {annotation}\n")

    assert reports == []


def test_use_types_from_typing_does_not_autofix_to_an_unrelated_name() -> None:
    _runner, reports = _reports(
        UseTypesFromTyping(),
        """
        from graphene import List
        value: list[str]
        """,
    )

    assert len(reports) == 1
    assert reports[0].replacement is None


def test_use_types_from_typing_fixes_qualified_builtin_to_typing_import() -> None:
    runner, reports = _reports(
        UseTypesFromTyping(),
        """
        from typing import List
        import builtins
        value: builtins.list[str]
        """,
    )

    assert len(reports) == 1
    assert runner.apply_replacements(reports).code == dedent(
        """
        from typing import List
        import builtins
        value: List[str]
        """,
    )


def test_use_types_from_typing_detects_alias_before_later_rebinding() -> None:
    _runner, reports = _reports(
        UseTypesFromTyping(),
        """
        from builtins import list as ListType
        Alias = ListType
        value: Alias[str]
        Alias = Custom
        """,
    )

    assert len(reports) == 1


@pytest.mark.parametrize(
    "source",
    [
        """
        from typing import Callable
        Alias = Callable
        value: Alias[[...], int]
        Alias = Other
        """,
        """
        from typing import Callable
        Alias: object = Callable
        value: Alias[[...], int]
        """,
        """
        from typing_extensions import Callable
        value: Callable[[...], int]
        """,
        """
        from typing_extensions import *
        value: Callable[[...], int]
        """,
        """
        import typing
        value: typing.Callable[[...], int]
        typing = other
        """,
    ],
)
def test_variadic_callable_syntax_detects_active_callable_bindings(source: str) -> None:
    runner, reports = _reports(VariadicCallableSyntax(), source)

    assert len(reports) == 1
    assert "[[...]," not in runner.apply_replacements(reports).code


def test_variadic_callable_syntax_ignores_rebound_typing_module() -> None:
    _runner, reports = _reports(
        VariadicCallableSyntax(),
        """
        import typing
        typing = custom_module
        value: typing.Callable[[...], int]
        """,
    )

    assert reports == []
