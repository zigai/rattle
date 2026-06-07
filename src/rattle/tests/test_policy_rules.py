from __future__ import annotations

import re
import textwrap
from pathlib import Path

from rattle import Config, LintRule
from rattle.engine import LintRunner
from rattle.ftypes import LintViolation
from rattle.rules.policy.forbidden_call import ForbiddenCall
from rattle.rules.policy.forbidden_import import ForbiddenImport
from rattle.rules.policy.forbidden_name import ForbiddenName


def _dedent(source: str) -> str:
    return textwrap.dedent(re.sub(r"\A\n", "", source))


def _run_rule(
    rule: LintRule,
    source: str,
) -> list[LintViolation]:
    path = Path("fixture.py")
    runner = LintRunner(path, _dedent(source).encode())

    return list(runner.collect_violations([rule], Config(path=path, root=Path.cwd())))


def _run_forbidden_call(
    source: str,
    forbidden_calls: list[str],
) -> list[LintViolation]:
    rule = ForbiddenCall()
    rule.configure({"forbidden_calls": forbidden_calls})

    return _run_rule(rule, source)


def _run_forbidden_import(
    source: str,
    forbidden_imports: list[str],
) -> list[LintViolation]:
    rule = ForbiddenImport()
    rule.configure({"forbidden_imports": forbidden_imports})

    return _run_rule(rule, source)


def _run_forbidden_name(
    source: str,
    forbidden_names: list[str],
) -> list[LintViolation]:
    rule = ForbiddenName()
    rule.configure({"forbidden_names": forbidden_names})

    return _run_rule(rule, source)


def test_forbidden_call_allows_unconfigured_calls() -> None:
    reports = _run_forbidden_call(
        """
        import allowed_module

        value = allowed_module.allowed_call()
        """,
        ["blocked_module.blocked_call"],
    )

    assert reports == []


def test_forbidden_call_reports_configured_dotted_call() -> None:
    reports = _run_forbidden_call(
        """
        import blocked_module

        value = blocked_module.blocked_call()
        """,
        ["blocked_module.blocked_call"],
    )

    assert [report.message for report in reports] == [
        "Do not call forbidden callable 'blocked_module.blocked_call'."
    ]


def test_forbidden_call_reports_import_alias() -> None:
    reports = _run_forbidden_call(
        """
        import blocked_module as blocked

        value = blocked.blocked_call()
        """,
        ["blocked_module.blocked_call"],
    )

    assert [report.message for report in reports] == [
        "Do not call forbidden callable 'blocked_module.blocked_call'."
    ]


def test_forbidden_call_reports_imported_symbol_with_custom_message() -> None:
    reports = _run_forbidden_call(
        """
        from blocked_module import blocked_call as call_blocked

        value = call_blocked()
        """,
        ["blocked_module.blocked_call|Use allowed_module.allowed_call instead."],
    )

    assert [report.message for report in reports] == ["Use allowed_module.allowed_call instead."]


def test_forbidden_call_appends_use_instead_when_configured() -> None:
    reports = _run_forbidden_call(
        """
        import blocked_module

        value = blocked_module.blocked_call()
        """,
        [
            "blocked_module.blocked_call|Do not call blocked_call.|allowed_module.allowed_call",
        ],
    )

    assert [report.message for report in reports] == [
        "Do not call blocked_call. Use instead: allowed_module.allowed_call."
    ]


def test_forbidden_import_allows_unconfigured_imports() -> None:
    reports = _run_forbidden_import(
        """
        import allowed_package.public_api
        """,
        ["blocked_package.internal"],
    )

    assert reports == []


def test_forbidden_import_reports_configured_module_import() -> None:
    reports = _run_forbidden_import(
        """
        import blocked_package.internal
        """,
        ["blocked_package.internal"],
    )

    assert [report.message for report in reports] == [
        "Do not import across forbidden boundary 'blocked_package.internal'."
    ]


def test_forbidden_import_reports_configured_submodule_import() -> None:
    reports = _run_forbidden_import(
        """
        import blocked_package.internal.helpers
        """,
        ["blocked_package.internal"],
    )

    assert [report.message for report in reports] == [
        "Do not import across forbidden boundary 'blocked_package.internal'."
    ]


def test_forbidden_import_reports_from_import_member() -> None:
    reports = _run_forbidden_import(
        """
        from blocked_package import internal
        """,
        ["blocked_package.internal"],
    )

    assert [report.message for report in reports] == [
        "Do not import across forbidden boundary 'blocked_package.internal'."
    ]


def test_forbidden_import_reports_custom_message() -> None:
    reports = _run_forbidden_import(
        """
        from blocked_package.internal import *
        """,
        ["blocked_package.internal|Import through blocked_package.public_api instead."],
    )

    assert [report.message for report in reports] == [
        "Import through blocked_package.public_api instead."
    ]


def test_forbidden_name_allows_unconfigured_names() -> None:
    reports = _run_forbidden_name(
        """
        allowed_name = load_value()
        """,
        ["variable:blocked_name"],
    )

    assert reports == []


def test_forbidden_name_reports_configured_variable_name() -> None:
    reports = _run_forbidden_name(
        """
        blocked_name = load_value()
        """,
        ["variable:blocked_name"],
    )

    assert [report.message for report in reports] == [
        "Do not use forbidden variable name 'blocked_name'."
    ]


def test_forbidden_name_reports_configured_glob_with_custom_message() -> None:
    reports = _run_forbidden_name(
        """
        def blocked_helper() -> None: ...
        """,
        ["function:blocked_*|Use a public helper name."],
    )

    assert [report.message for report in reports] == ["Use a public helper name."]


def test_forbidden_name_reports_configured_class_name() -> None:
    reports = _run_forbidden_name(
        """
        class BlockedType: ...
        """,
        ["class:BlockedType"],
    )

    assert [report.message for report in reports] == [
        "Do not use forbidden class name 'BlockedType'."
    ]
