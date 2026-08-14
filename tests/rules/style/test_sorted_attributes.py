from pathlib import Path
from textwrap import dedent

from rattle.config.models import Config
from rattle.diagnostics import LintViolation
from rattle.engine import LintRunner
from rattle.rule import LintRule
from rattle.rules.style.sorted_attributes import SortedAttributes


def _reports(rule: LintRule, source: str) -> tuple[LintRunner, list[LintViolation]]:
    path = Path("sample.py")
    runner = LintRunner(path, dedent(source).encode())
    return runner, list(runner.collect_violations([rule], Config(path=path)))


def _fixed(rule: LintRule, source: str) -> tuple[list[LintViolation], str]:
    runner, reports = _reports(rule, source)
    return reports, runner.apply_replacements(reports).code


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


def test_sorted_attributes_preserves_assignment_comments() -> None:
    reports, fixed = _fixed(
        SortedAttributes(),
        '''
        class Constants:
            """@sorted-attributes"""
            z = 1
            # documentation for a
            a = 2
        ''',
    )

    assert len(reports) == 1
    assert "    # documentation for a\n    a = 2" in fixed


def test_sorted_attributes_withholds_fix_for_runtime_dependencies() -> None:
    runner, reports = _reports(
        SortedAttributes(),
        '''
        class Constants:
            """@sorted-attributes"""
            z = 1
            a = z
        ''',
    )

    assert len(reports) == 1
    assert reports[0].replacement is None
    assert runner.apply_replacements(reports).code == dedent(
        '''
        class Constants:
            """@sorted-attributes"""
            z = 1
            a = z
        ''',
    )


def test_sorted_attributes_literal_fix_preserves_runtime_values() -> None:
    source = dedent(
        '''
        class Constants:
            """@sorted-attributes"""
            z = 1
            a = 2
        ''',
    )
    reports, fixed = _fixed(SortedAttributes(), source)
    original_namespace: dict[str, object] = {}
    fixed_namespace: dict[str, object] = {}

    exec(source, original_namespace)
    exec(fixed, fixed_namespace)

    assert reports[0].replacement is not None
    original = original_namespace["Constants"]
    updated = fixed_namespace["Constants"]
    assert (vars(original)["a"], vars(original)["z"]) == (
        vars(updated)["a"],
        vars(updated)["z"],
    )


def test_sorted_attributes_preserves_group_boundary_and_converges() -> None:
    reports, fixed = _fixed(
        SortedAttributes(),
        '''
        class Constants:
            """@sorted-attributes"""
            z = 1

            b = 2
            a = 3
        ''',
    )

    assert len(reports) == 1
    assert "    z = 1\n\n    a = 3\n    b = 2" in fixed
    _runner, remaining_reports = _reports(SortedAttributes(), fixed)
    assert remaining_reports == []
