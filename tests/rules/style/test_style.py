from pathlib import Path
from textwrap import dedent

import pytest

from rattle.config.models import Config
from rattle.diagnostics import LintViolation
from rattle.engine import LintRunner
from rattle.rule import LintRule
from rattle.rules.style.no_annotated_self import NoAnnotatedSelf
from rattle.rules.style.no_exception_message_variables import NoExceptionMessageVariables
from rattle.rules.style.no_str_exception_translation import NoStrExceptionTranslation
from rattle.rules.style.no_underscore_class import NoUnderscoreClass
from rattle.rules.style.public_method_order import PublicMethodOrder


def _reports(
    rule: LintRule,
    source: str,
    *,
    path: Path = Path("sample.py"),
) -> tuple[LintRunner, list[LintViolation]]:
    runner = LintRunner(path, dedent(source).encode())
    return runner, list(runner.collect_violations([rule], Config(path=path)))


def _fixed(rule: LintRule, source: str) -> tuple[list[LintViolation], str]:
    runner, reports = _reports(rule, source)
    return reports, runner.apply_replacements(reports).code


def test_exception_message_variable_used_by_handler_is_not_throwaway() -> None:
    _runner, reports = _reports(
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
    _runner, reports = _reports(
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
    _runner, reports = _reports(
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
    _runner, reports = _reports(
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
    _runner, reports = _reports(rule, source)

    assert len(reports) == (0 if isinstance(rule, PublicMethodOrder) else 1)


def test_exception_message_global_assignment_is_not_treated_as_local() -> None:
    _runner, reports = _reports(
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
    _runner, reports = _reports(NoUnderscoreClass(), "class _Private:\n    pass")

    assert len(reports) == 1
    assert reports[0].range is not None
    assert reports[0].range.start.column == 6
    assert reports[0].range.end.column == 14


def test_annotated_self_in_conditional_class_body_is_reported() -> None:
    reports, fixed = _fixed(
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
