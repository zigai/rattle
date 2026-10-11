import pytest

from rattle.rule import LintRule
from rattle.rules.style.no_annotated_self import NoAnnotatedSelf
from rattle.rules.style.no_exception_message_variables import NoExceptionMessageVariables
from rattle.rules.style.no_str_exception_translation import NoStrExceptionTranslation
from rattle.rules.style.no_underscore_class import NoUnderscoreClass
from rattle.rules.style.public_method_order import PublicMethodOrder
from tests.support import fix_rule, run_rule


def test_exception_message_variable_used_by_handler_is_not_throwaway() -> None:
    _runner, reports = run_rule(
        NoExceptionMessageVariables(),
        """
        try:
            message = "invalid"
            raise ValueError(message)
        except ValueError:
            log(message)
        """,
    )

    assert reports == []


def test_exception_message_variable_ignores_uses_of_an_earlier_binding() -> None:
    _runner, reports = run_rule(
        NoExceptionMessageVariables(),
        """
        message = "earlier"
        log(message)
        message = "invalid"
        raise ValueError(message)
        """,
    )

    assert len(reports) == 1


@pytest.mark.parametrize(
    "expression",
    ["(lambda: formatter)().format(exc)", "formatter % exc"],
)
def test_no_str_exception_translation_ignores_non_string_format_operations(
    expression: str,
) -> None:
    _runner, reports = run_rule(
        NoStrExceptionTranslation(),
        f"""
        try:
            run()
        except ValueError as exc:
            raise RuntimeError({expression}) from exc
        """,
    )

    assert reports == []


def test_no_str_exception_translation_honors_annotated_rebinding() -> None:
    _runner, reports = run_rule(
        NoStrExceptionTranslation(),
        """
        try:
            run()
        except ValueError as exc:
            exc: str = "stable"
            raise RuntimeError(str(exc))
        """,
    )

    assert reports == []


@pytest.mark.parametrize(
    ("rule", "source"),
    [
        (
            NoAnnotatedSelf(),
            """
            class Service:
                @custom
                def run(self: "Service") -> None:
                    pass
            """,
        ),
        (
            NoUnderscoreClass(),
            """
            def factory():
                class _Private:
                    pass
                return _Private
            """,
        ),
        (
            PublicMethodOrder(),
            """
            class Service:
                def __init__(self) -> None:
                    pass

                async def run(self) -> None:
                    pass

                def _helper(self) -> None:
                    pass
            """,
        ),
    ],
)
def test_rules_cover_adversarial_but_unambiguous_cases(
    rule: LintRule,
    source: str,
) -> None:
    _runner, reports = run_rule(rule, source)

    assert len(reports) == (0 if isinstance(rule, PublicMethodOrder) else 1)


def test_exception_message_global_assignment_is_not_treated_as_local() -> None:
    _runner, reports = run_rule(
        NoExceptionMessageVariables(),
        """
        message = "original"

        def fail():
            global message
            message = "invalid"
            raise ValueError(message)
        """,
    )

    assert reports == []


def test_underscore_class_range_targets_class_name() -> None:
    _runner, reports = run_rule(NoUnderscoreClass(), "class _Private:\n    pass")

    assert len(reports) == 1
    assert reports[0].range is not None
    assert reports[0].range.start.column == 6
    assert reports[0].range.end.column == 14


def test_annotated_self_in_conditional_class_body_is_reported() -> None:
    reports, fixed = fix_rule(
        NoAnnotatedSelf(),
        """
        class Service:
            if enabled:
                def run(self: "Service") -> None:
                    pass
        """,
    )

    assert len(reports) == 1
    assert "def run(self) -> None:" in fixed


def test_public_method_order_flags_overload_after_helper() -> None:
    _runner, reports = run_rule(
        PublicMethodOrder(),
        """
        from typing import overload

        class Service:
            def _helper(self):
                pass

            @overload
            def run(self, x: int) -> int: ...
            @overload
            def run(self, x: str) -> str: ...
            def run(self, x):
                return x
        """,
    )
    assert len(reports) == 1
    assert "Public method 'run' appears after private helper '_helper'" in reports[0].message


def test_public_method_order_flags_property_after_helper() -> None:
    _runner, reports = run_rule(
        PublicMethodOrder(),
        """
        class Service:
            def _setup(self) -> None:
                pass

            @property
            def value(self) -> int:
                return 1
        """,
    )
    assert len(reports) == 1
    assert "Public method 'value' appears after private helper '_setup'" in reports[0].message


def test_public_method_order_allows_setter_after_helper_if_getter_precedes() -> None:
    _runner, reports = run_rule(
        PublicMethodOrder(),
        """
        class Service:
            @property
            def value(self) -> int:
                return 1

            def _setup(self) -> None:
                pass

            @value.setter
            def value(self, val: int) -> None:
                pass
        """,
    )
    assert len(reports) == 0


@pytest.mark.parametrize(
    "source",
    [
        "detail = build_detail()\nraise CustomError(code(), detail)\n",
        'message = "safe"  # preserve rationale\nraise ValueError(message)\n',
    ],
)
def test_exception_message_inlining_withholds_unsafe_fixes(source: str) -> None:
    _runner, reports = run_rule(NoExceptionMessageVariables(), source)

    assert len(reports) == 1
    assert reports[0].replacement is None
