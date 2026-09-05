from pathlib import Path
from textwrap import dedent

import pytest

from rattle.config.models import Config
from rattle.diagnostics import LintViolation
from rattle.engine import LintRunner
from rattle.rule import LintRule
from rattle.rules.typing.use_types_from_typing import UseTypesFromTyping
from rattle.rules.typing.variadic_callable_syntax import VariadicCallableSyntax


def _reports(rule: LintRule, source: str) -> tuple[LintRunner, list[LintViolation]]:
    path = Path("sample.py")
    runner = LintRunner(path, dedent(source).encode())
    return runner, list(runner.collect_violations([rule], Config(path=path)))


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
    assert "[..., int]" in runner.apply_replacements(reports).code


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


def test_variadic_callable_diagnostic_preserves_comments() -> None:
    _runner, reports = _reports(
        VariadicCallableSyntax(),
        """
        from typing import Callable

        value: Callable[[
            ...  # arbitrary positional parameters
        ], int]
        """,
    )

    assert len(reports) == 1
    assert reports[0].replacement is None


def test_conditionally_imported_typing_name_is_not_used_for_fix() -> None:
    _runner, reports = _reports(
        UseTypesFromTyping(),
        """
        from typing import TYPE_CHECKING

        if TYPE_CHECKING:
            from typing import List

        value: list[str]
        """,
    )

    assert len(reports) == 1
    assert reports[0].replacement is None


def test_unknown_star_import_prevents_builtin_annotation_guess() -> None:
    _runner, reports = _reports(
        UseTypesFromTyping(),
        """
        from customtypes import *

        value: list[str]
        """,
    )

    assert reports == []


def test_qualified_builtin_assignment_alias_is_detected() -> None:
    _runner, reports = _reports(
        UseTypesFromTyping(),
        """
        import builtins

        Alias = builtins.list
        value: Alias[str]
        """,
    )

    assert len(reports) == 1
