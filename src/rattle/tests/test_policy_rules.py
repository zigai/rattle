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
from rattle.rules.policy.line_count_limit import LineCountLimit


def _dedent(source: str) -> str:
    return textwrap.dedent(re.sub(r"\A\n", "", source))


def _run_rule(
    rule: LintRule,
    source: str,
    *,
    path: Path = Path("fixture.py"),
    root: Path | None = None,
) -> list[LintViolation]:
    runner = LintRunner(path, _dedent(source).encode())

    return list(runner.collect_violations([rule], Config(path=path, root=root or Path.cwd())))


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


def _run_line_count_limit(
    source: str,
    options: dict[str, object],
    *,
    path: Path = Path("fixture.py"),
    root: Path | None = None,
) -> list[LintViolation]:
    rule = LineCountLimit()
    rule.configure(options)

    return _run_rule(rule, source, path=path, root=root)


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


def test_forbidden_call_reports_direct_builtin_call() -> None:
    reports = _run_forbidden_call(
        """
        value = open("path.txt")
        """,
        ["builtins.open"],
    )

    assert [report.message for report in reports] == [
        "Do not call forbidden callable 'builtins.open'."
    ]


def test_forbidden_call_accepts_plain_callable_name() -> None:
    reports = _run_forbidden_call(
        """
        print("debug")
        """,
        ["print"],
    )

    assert [report.message for report in reports] == ["Do not call forbidden callable 'print'."]


def test_forbidden_call_reports_local_alias_to_imported_symbol() -> None:
    reports = _run_forbidden_call(
        """
        from blocked_module import blocked_call

        alias = blocked_call
        alias()
        """,
        ["blocked_module.blocked_call"],
    )

    assert [report.message for report in reports] == [
        "Do not call forbidden callable 'blocked_module.blocked_call'."
    ]


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


def test_forbidden_call_reports_assignment_alias() -> None:
    reports = _run_forbidden_call(
        """
        import os

        delete = os.remove
        delete("path")
        """,
        ["os.remove"],
    )

    assert [report.message for report in reports] == ["Do not call forbidden callable 'os.remove'."]


def test_forbidden_call_reports_function_scope_assignment_alias() -> None:
    reports = _run_forbidden_call(
        """
        import os

        def cleanup():
            delete = os.remove
            delete("path")
        """,
        ["os.remove"],
    )

    assert [report.message for report in reports] == ["Do not call forbidden callable 'os.remove'."]


def test_forbidden_call_reports_multi_target_assignment_alias() -> None:
    reports = _run_forbidden_call(
        """
        import os

        delete = remove_file = os.remove
        remove_file("path")
        """,
        ["os.remove"],
    )

    assert [report.message for report in reports] == ["Do not call forbidden callable 'os.remove'."]


def test_forbidden_call_reports_alias_chain() -> None:
    reports = _run_forbidden_call(
        """
        import os

        delete = os.remove
        remove_file = delete
        remove_file("path")
        """,
        ["os.remove"],
    )

    assert [report.message for report in reports] == ["Do not call forbidden callable 'os.remove'."]


def test_forbidden_call_allows_shadowed_assignment_alias() -> None:
    reports = _run_forbidden_call(
        """
        import os

        delete = os.remove

        def cleanup(delete):
            delete("path")
        """,
        ["os.remove"],
    )

    assert reports == []


def test_forbidden_call_reports_star_import() -> None:
    reports = _run_forbidden_call(
        """
        from os import *

        remove("path")
        """,
        ["os.remove"],
    )

    assert [report.message for report in reports] == ["Do not call forbidden callable 'os.remove'."]


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


def test_forbidden_import_reports_relative_boundary() -> None:
    reports = _run_forbidden_import(
        """
        from .private import X
        """,
        ["private"],
    )

    assert [report.message for report in reports] == [
        "Do not import across forbidden boundary 'private'."
    ]


def test_forbidden_import_reports_relative_boundary_tail() -> None:
    reports = _run_forbidden_import(
        """
        from .private import X
        """,
        ["pkg.private"],
    )

    assert [report.message for report in reports] == [
        "Do not import across forbidden boundary 'pkg.private'."
    ]


def test_forbidden_import_reports_relative_import_without_module() -> None:
    reports = _run_forbidden_import(
        """
        from . import private
        """,
        ["pkg.private"],
    )

    assert [report.message for report in reports] == [
        "Do not import across forbidden boundary 'pkg.private'."
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


def test_forbidden_name_does_not_report_parameter_as_variable() -> None:
    reports = _run_forbidden_name(
        """
        def f(blocked_name):
            pass
        """,
        ["variable:blocked_name"],
    )

    assert reports == []


def test_forbidden_name_reports_named_expression_target() -> None:
    reports = _run_forbidden_name(
        """
        if (blocked_name := load_value()):
            pass
        """,
        ["variable:blocked_name"],
    )

    assert [report.message for report in reports] == [
        "Do not use forbidden variable name 'blocked_name'."
    ]


def test_forbidden_name_reports_comprehension_target() -> None:
    reports = _run_forbidden_name(
        """
        values = [blocked_name for blocked_name in items]
        """,
        ["variable:blocked_name"],
    )

    assert [report.message for report in reports] == [
        "Do not use forbidden variable name 'blocked_name'.",
    ]


def test_forbidden_name_reports_dotted_import_component() -> None:
    reports = _run_forbidden_name(
        """
        import pkg.blocked_name
        """,
        ["import:blocked_name"],
    )

    assert [report.message for report in reports] == [
        "Do not use forbidden import name 'blocked_name'."
    ]


def test_forbidden_name_reports_match_star_target() -> None:
    reports = _run_forbidden_name(
        """
        match value:
            case [*blocked_name]:
                pass
        """,
        ["variable:blocked_name"],
    )

    assert [report.message for report in reports] == [
        "Do not use forbidden variable name 'blocked_name'."
    ]


def test_forbidden_name_reports_match_mapping_rest_target() -> None:
    reports = _run_forbidden_name(
        """
        match value:
            case {"x": value, **blocked_name}:
                pass
        """,
        ["variable:blocked_name"],
    )

    assert [report.message for report in reports] == [
        "Do not use forbidden variable name 'blocked_name'."
    ]


def test_line_count_limit_reports_function_limit() -> None:
    reports = _run_line_count_limit(
        """
        def oversized() -> None:
            first()
            second()
        """,
        {"max_function_lines": 2},
    )

    assert [report.message for report in reports] == [
        "Function 'oversized' has 3 lines, exceeding the configured limit of 2."
    ]


def test_line_count_limit_reports_method_limit() -> None:
    reports = _run_line_count_limit(
        """
        class Service:
            def oversized(self) -> None:
                first()
                second()
        """,
        {"max_method_lines": 2},
    )

    assert [report.message for report in reports] == [
        "Method 'oversized' has 3 lines, exceeding the configured limit of 2."
    ]


def test_line_count_limit_reports_outer_function_for_nested_function_lines() -> None:
    reports = _run_line_count_limit(
        """
        def outer() -> None:
            def inner() -> None:
                first()
                second()
        """,
        {"max_function_lines": 2},
    )

    assert [report.message for report in reports] == [
        "Function 'outer' has 4 lines, exceeding the configured limit of 2."
    ]


def test_line_count_limit_glob_limits_override_base_limit() -> None:
    reports = _run_line_count_limit(
        """
        def large() -> None:
            pass

            pass
        """,
        {
            "max_function_lines": 2,
            "glob_limits": {"*": {"max_function_lines": 10}},
        },
    )

    assert reports == []


def test_line_count_limit_per_file_limits_match_repo_relative_path(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    path = root / "src" / "fixture.py"
    reports = _run_line_count_limit(
        """
        one()
        two()
        three()
        """,
        {
            "max_file_lines": 10,
            "per_file_limits": {"src/fixture.py": {"max_file_lines": 2}},
        },
        path=path,
        root=root,
    )

    assert [report.message for report in reports] == [
        "File has 3 lines, exceeding the configured limit of 2."
    ]


def test_line_count_limit_nested_class_method_uses_method_limit() -> None:
    reports = _run_line_count_limit(
        """
        def outer():
            class Service:
                def oversized(self):
                    first()
                    second()
        """,
        {
            "max_function_lines": 10,
            "max_method_lines": 2,
        },
    )

    assert [report.message for report in reports] == [
        "Method 'oversized' has 3 lines, exceeding the configured limit of 2."
    ]
