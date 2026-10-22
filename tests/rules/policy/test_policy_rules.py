from __future__ import annotations

from pathlib import Path

import pytest

import rattle.rules.policy.forbidden_import as forbidden_import_module
from rattle import Config, LintRule
from rattle.diagnostics import LintViolation
from rattle.engine import LintRunner
from rattle.rule import RuleConfigurationError
from rattle.rules.policy.forbidden_call import ForbiddenCall
from rattle.rules.policy.forbidden_import import ForbiddenImport
from rattle.rules.policy.forbidden_name import ForbiddenName
from rattle.rules.policy.import_contracts import ImportContracts
from rattle.rules.policy.line_count_limit import LineCountLimit
from rattle.rules.policy.no_underscore_import_aliases import NoUnderscoreImportAliases
from rattle.rules.policy.no_unsafe_tempfile_factories import NoUnsafeTempfileFactories
from tests.support import dedent_source


def _run_rule(
    rule: LintRule,
    source: str,
    *,
    path: Path = Path("fixture.py"),
    root: Path | None = None,
) -> list[LintViolation]:
    runner = LintRunner(path, dedent_source(source).encode())

    return list(runner.collect_violations([rule], Config(path=path, root=root or Path.cwd())))


def _run_forbidden_call(
    source: str,
    forbidden_calls: list[str],
) -> list[LintViolation]:
    rule = ForbiddenCall()
    rule.configure({"forbidden_calls": forbidden_calls})

    return _run_rule(rule, source)


def test_forbidden_call_ignores_relative_star_import() -> None:
    reports = _run_forbidden_call('from .os import *\nremove("path")\n', ["os.remove"])

    assert reports == []


def test_forbidden_call_reports_assigned_module_alias() -> None:
    reports = _run_forbidden_call(
        'import os\nplatform = os\nplatform.remove("path")\n', ["os.remove"]
    )

    assert [report.message for report in reports] == ["Do not call forbidden callable 'os.remove'."]


def test_unsafe_tempfile_ignores_relative_star_import() -> None:
    rule = NoUnsafeTempfileFactories()
    rule.configure({"excluded_path_parts": []})

    assert _run_rule(rule, "from .tempfile import *\nmkstemp()\n") == []


@pytest.mark.parametrize(
    "source",
    [
        "import tempfile\nt: object = tempfile\nt.mkstemp()\n",
        "import tempfile\n(t := tempfile).mkdtemp()\n",
    ],
)
def test_unsafe_tempfile_reports_all_assignment_like_module_aliases(source: str) -> None:
    rule = NoUnsafeTempfileFactories()
    rule.configure({"excluded_path_parts": []})

    assert [report.message for report in _run_rule(rule, source)] == [rule.MESSAGE]


@pytest.mark.parametrize("setting_name", ["glob_limits", "per_file_limits"])
def test_line_count_paths_are_matched_relative_to_repo_root(setting_name: str) -> None:
    pattern = "src/*.py" if setting_name == "glob_limits" else "src/x.py"
    options = {
        "max_function_lines": 10,
        setting_name: {pattern: {"max_function_lines": 2}},
    }
    source = "def f():\n    first()\n    second()\n"

    nested_reports = _run_line_count_limit(
        source,
        options,
        path=Path("/repo/vendor/src/x.py"),
        root=Path("/repo"),
    )
    direct_reports = _run_line_count_limit(
        source,
        options,
        path=Path("/repo/src/x.py"),
        root=Path("/repo"),
    )

    assert nested_reports == []
    assert len(direct_reports) == 1


def _run_forbidden_import(
    source: str,
    forbidden_imports: list[str],
    *,
    path: Path = Path("fixture.py"),
) -> list[LintViolation]:
    rule = ForbiddenImport()
    rule.configure({"forbidden_imports": forbidden_imports})

    return _run_rule(rule, source, path=path)


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


def test_forbidden_call_reports_imported_plain_callable_name() -> None:
    reports = _run_forbidden_call(
        """
        from os import remove

        remove("path")
        """,
        ["remove"],
    )

    assert [report.message for report in reports] == ["Do not call forbidden callable 'remove'."]


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


def test_forbidden_call_reports_annotated_assignment_alias() -> None:
    reports = _run_forbidden_call(
        """
        import os

        delete: object = os.remove
        delete("path")
        """,
        ["os.remove"],
    )

    assert [report.message for report in reports] == ["Do not call forbidden callable 'os.remove'."]


def test_forbidden_call_reports_assignment_expression_alias() -> None:
    reports = _run_forbidden_call(
        """
        import os

        if delete := os.remove:
            delete("path")
        """,
        ["os.remove"],
    )

    assert [report.message for report in reports] == ["Do not call forbidden callable 'os.remove'."]


def test_forbidden_call_reports_destructured_literal_alias() -> None:
    reports = _run_forbidden_call(
        """
        import os

        (delete, allowed) = (os.remove, print)
        delete("path")
        """,
        ["os.remove"],
    )

    assert [report.message for report in reports] == ["Do not call forbidden callable 'os.remove'."]


def test_forbidden_call_uses_assignment_reaching_call_before_later_rebinding() -> None:
    reports = _run_forbidden_call(
        """
        import os

        delete = os.remove
        delete("path")
        delete = print
        """,
        ["os.remove"],
    )

    assert [report.message for report in reports] == ["Do not call forbidden callable 'os.remove'."]


def test_forbidden_call_uses_latest_assignment_reaching_call() -> None:
    reports = _run_forbidden_call(
        """
        import os

        delete = print
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


def test_forbidden_call_uses_latest_import_binding() -> None:
    reports = _run_forbidden_call(
        """
        import os
        import fake_os as os

        os.remove("path")
        """,
        ["os.remove"],
    )

    assert reports == []


def test_forbidden_call_uses_import_binding_before_later_rebinding() -> None:
    reports = _run_forbidden_call(
        """
        import os

        os.remove("path")
        os = fake_os
        """,
        ["os.remove"],
    )

    assert [report.message for report in reports] == ["Do not call forbidden callable 'os.remove'."]


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


@pytest.mark.parametrize(
    "statement",
    ["import {module}", "from {module} import name", "from {module} import *"],
)
@pytest.mark.parametrize("whitespace", ["", " ", "\t", " \\\n"])
def test_forbidden_import_matches_dotted_names_with_whitespace(
    statement: str, whitespace: str
) -> None:
    module = f"blocked{whitespace}.{whitespace}internal"

    reports = _run_forbidden_import(statement.format(module=module), ["blocked.internal"])

    assert [report.message for report in reports] == [
        "Do not import across forbidden boundary 'blocked.internal'."
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


@pytest.mark.parametrize("separator", [" ", "  ", "\t", " \\\n"])
@pytest.mark.parametrize("target", [". import name", ".child import name", ". import *"])
def test_forbidden_import_checks_relative_imports_without_boundary_in_source(
    separator: str, target: str
) -> None:
    source = f"from{separator}{target}"
    assert "blocked" not in source

    reports = _run_forbidden_import(source, ["blocked"], path=Path("blocked/module.py"))

    assert [report.message for report in reports] == [
        "Do not import across forbidden boundary 'blocked'."
    ]


def test_forbidden_import_reports_relative_boundary() -> None:
    reports = _run_forbidden_import(
        """
        from .private import X
        """,
        ["private"],
        path=Path("private/module.py"),
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
        path=Path("pkg/module.py"),
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
        path=Path("pkg/module.py"),
    )

    assert [report.message for report in reports] == [
        "Do not import across forbidden boundary 'pkg.private'."
    ]


def test_forbidden_import_does_not_match_relative_import_in_other_package() -> None:
    reports = _run_forbidden_import(
        """
        from .private import X
        """,
        ["pkg.private"],
        path=Path("other/module.py"),
    )

    assert reports == []


def test_forbidden_import_reports_moduleless_relative_star() -> None:
    reports = _run_forbidden_import(
        """
        from . import *
        """,
        ["pkg"],
        path=Path("pkg/module.py"),
    )

    assert [report.message for report in reports] == [
        "Do not import across forbidden boundary 'pkg'."
    ]


def test_forbidden_import_prefers_most_specific_boundary() -> None:
    reports = _run_forbidden_import(
        "import alpha.beta",
        ["alpha", "alpha.beta|specific boundary"],
    )

    assert [report.message for report in reports] == ["specific boundary"]


def test_forbidden_import_accepts_unicode_module_identifier() -> None:
    reports = _run_forbidden_import("import café", ["café"])

    assert len(reports) == 1


def test_forbidden_import_rebuilds_boundary_order_when_rule_is_reconfigured() -> None:
    rule = ForbiddenImport()
    rule.configure({"forbidden_imports": ["alpha.internal"]})
    assert _run_rule(rule, "import alpha.public") == []

    rule.configure({"forbidden_imports": ["alpha|updated policy"]})
    reports = _run_rule(rule, "import alpha.public")

    assert [report.message for report in reports] == ["updated policy"]


@pytest.mark.parametrize(
    ("boundaries", "expected_message"),
    [
        (["aa|original", "bb|other", "aa|updated"], "updated"),
        (["bb|other", "aa|original", "aa|updated"], "other"),
    ],
)
def test_forbidden_import_preserves_tied_precedence_and_last_duplicate_message(
    boundaries: list[str], expected_message: str
) -> None:
    reports = _run_forbidden_import("from . import *", boundaries, path=Path("aa/bb/module.py"))

    assert [report.message for report in reports] == [expected_message]


@pytest.mark.parametrize(
    ("source", "boundaries", "expected_sorts", "expected_messages"),
    [
        ('marker = "alpha"', ["alpha"], 0, []),
        ("from . import first, second", [], 1, []),
        (
            "import alpha, alpha.child",
            ["alpha|blocked"],
            1,
            ["blocked", "blocked"],
        ),
    ],
)
def test_forbidden_import_ranks_boundaries_only_when_needed_once_per_module(
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    boundaries: list[str],
    expected_sorts: int,
    expected_messages: list[str],
) -> None:
    sort_calls = []

    def record_sort(values, **kwargs):
        sort_calls.append(tuple(values))
        return sorted(values, **kwargs)

    monkeypatch.setattr(forbidden_import_module, "sorted", record_sort, raising=False)

    reports = _run_forbidden_import(source, boundaries)

    assert [report.message for report in reports] == expected_messages
    assert len(sort_calls) == expected_sorts


def test_forbidden_import_allows_module_with_boundary_prefix_only() -> None:
    reports = _run_forbidden_import(
        """
        import blocked_package.internalized
        """,
        ["blocked_package.internal"],
    )

    assert reports == []


def test_forbidden_import_reports_parenthesized_aliased_member() -> None:
    reports = _run_forbidden_import(
        """
        from blocked_package import (
            internal as implementation,
        )
        """,
        ["blocked_package.internal"],
    )

    assert [report.message for report in reports] == [
        "Do not import across forbidden boundary 'blocked_package.internal'."
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


def test_forbidden_name_reports_nested_destructuring_targets_once_each() -> None:
    reports = _run_forbidden_name(
        """
        (blocked_name, [*blocked_tail]) = values
        """,
        ["variable:blocked_*"],
    )

    assert [report.message for report in reports] == [
        "Do not use forbidden variable name 'blocked_name'.",
        "Do not use forbidden variable name 'blocked_tail'.",
    ]


def test_forbidden_name_reports_exception_bindings() -> None:
    reports = _run_forbidden_name(
        """
        try:
            run()
        except ValueError as blocked_error:
            pass

        try:
            run()
        except* OSError as blocked_group:
            pass
        """,
        ["variable:blocked_*"],
    )

    assert [report.message for report in reports] == [
        "Do not use forbidden variable name 'blocked_error'.",
        "Do not use forbidden variable name 'blocked_group'.",
    ]


def test_forbidden_name_distinguishes_attribute_from_variable_target() -> None:
    reports = _run_forbidden_name(
        """
        service.blocked_name = value
        """,
        ["variable:blocked_name", "attribute:blocked_name"],
    )

    assert [report.message for report in reports] == [
        "Do not use forbidden attribute name 'blocked_name'."
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


def test_line_count_limit_includes_decorators_in_function_limit() -> None:
    reports = _run_line_count_limit(
        """
        @first
        @second(
            option=True,
        )
        def oversized() -> None:
            pass
        """,
        {"max_function_lines": 5},
    )

    assert [report.message for report in reports] == [
        "Function 'oversized' has 6 lines, exceeding the configured limit of 5."
    ]


def test_line_count_limit_includes_decorators_in_method_limit() -> None:
    reports = _run_line_count_limit(
        """
        class Service:
            @classmethod
            def oversized(cls) -> None:
                pass
        """,
        {"max_method_lines": 2},
    )

    assert [report.message for report in reports] == [
        "Method 'oversized' has 3 lines, exceeding the configured limit of 2."
    ]


def test_unsafe_tempfile_reports_annotated_assignment_alias() -> None:
    rule = NoUnsafeTempfileFactories()
    reports = _run_rule(
        rule,
        """
        import tempfile

        make_temp: object = tempfile.mkstemp
        make_temp()
        """,
    )

    assert [report.message for report in reports] == [rule.MESSAGE]


def test_unsafe_tempfile_reports_assignment_expression_alias() -> None:
    rule = NoUnsafeTempfileFactories()
    reports = _run_rule(
        rule,
        """
        import tempfile

        if make_temp := tempfile.mkdtemp:
            make_temp()
        """,
    )

    assert [report.message for report in reports] == [rule.MESSAGE]


def test_unsafe_tempfile_reports_module_assignment_alias() -> None:
    rule = NoUnsafeTempfileFactories()
    reports = _run_rule(
        rule,
        """
        import tempfile

        temporary = tempfile
        temporary.mkstemp()
        """,
    )

    assert [report.message for report in reports] == [rule.MESSAGE]


def test_unsafe_tempfile_reports_star_imported_factory_alias() -> None:
    rule = NoUnsafeTempfileFactories()
    reports = _run_rule(
        rule,
        """
        from tempfile import *

        make_temp = mkstemp
        make_temp()
        """,
    )

    assert [report.message for report in reports] == [rule.MESSAGE]


def test_unsafe_tempfile_empty_exclusions_include_test_filename() -> None:
    rule = NoUnsafeTempfileFactories()
    rule.configure({"excluded_path_parts": []})
    reports = _run_rule(
        rule,
        """
        import tempfile

        tempfile.mkstemp()
        """,
        path=Path("test_temp.py"),
    )

    assert [report.message for report in reports] == [rule.MESSAGE]


def test_unsafe_tempfile_reports_destructured_literal_alias() -> None:
    rule = NoUnsafeTempfileFactories()
    reports = _run_rule(
        rule,
        """
        import tempfile

        [make_temp, allowed] = [tempfile.mkdtemp, print]
        make_temp()
        """,
    )

    assert [report.message for report in reports] == [rule.MESSAGE]


def test_unsafe_tempfile_uses_assignment_reaching_call_before_later_rebinding() -> None:
    rule = NoUnsafeTempfileFactories()
    reports = _run_rule(
        rule,
        """
        import tempfile

        make_temp = tempfile.mkstemp
        make_temp()
        make_temp = print
        """,
    )

    assert [report.message for report in reports] == [rule.MESSAGE]


def test_unsafe_tempfile_uses_latest_assignment_reaching_call() -> None:
    rule = NoUnsafeTempfileFactories()
    reports = _run_rule(
        rule,
        """
        import tempfile

        make_temp = print
        make_temp = tempfile.mkdtemp
        make_temp()
        """,
    )

    assert [report.message for report in reports] == [rule.MESSAGE]


def test_unsafe_tempfile_uses_latest_import_binding() -> None:
    rule = NoUnsafeTempfileFactories()
    reports = _run_rule(
        rule,
        """
        import tempfile
        import fake_tempfile as tempfile

        tempfile.mkstemp()
        """,
    )

    assert reports == []


def test_unsafe_tempfile_uses_import_binding_before_later_rebinding() -> None:
    rule = NoUnsafeTempfileFactories()
    reports = _run_rule(
        rule,
        """
        import tempfile

        tempfile.mkstemp()
        tempfile = fake_tempfile
        """,
    )

    assert [report.message for report in reports] == [rule.MESSAGE]


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


def test_line_count_limit_glob_matches_repo_relative_path_outside_cwd(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    path = root / "src" / "fixture.py"
    reports = _run_line_count_limit(
        """
        def large() -> None:
            first()
            second()
        """,
        {
            "max_function_lines": 10,
            "glob_limits": {"src/*.py": {"max_function_lines": 2}},
        },
        path=path,
        root=root,
    )

    assert [report.message for report in reports] == [
        "Function 'large' has 3 lines, exceeding the configured limit of 2."
    ]


def test_line_count_limit_exact_glob_overrides_broader_longer_glob(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    path = root / "src" / "a" / "b.py"
    reports = _run_line_count_limit(
        """
        def large() -> None:
            first()
            second()
        """,
        {
            "glob_limits": {
                "src/a/b.py": {"max_function_lines": 2},
                "src/**/b.py": {"max_function_lines": 10},
            }
        },
        path=path,
        root=root,
    )

    assert [report.message for report in reports] == [
        "Function 'large' has 3 lines, exceeding the configured limit of 2."
    ]


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


def test_line_count_limit_class_control_flow_method_uses_method_limit() -> None:
    reports = _run_line_count_limit(
        """
        class Service:
            if enabled:
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


def test_forbidden_name_accepts_documented_leading_glob() -> None:
    reports = _run_forbidden_name("class UserManager: pass", ["class:*Manager"])

    assert len(reports) == 1


def test_forbidden_name_catches_import_from() -> None:
    reports = _run_forbidden_name("from requests import get", ["import:requests"])
    assert len(reports) == 1
    assert "requests" in reports[0].message


def _run_import_contracts(
    source: str,
    contracts: list[dict[str, object]],
    *,
    path: str = "src/parcel/orders/logic.py",
    source_roots: list[str] | None = None,
    ignore_type_checking: bool = True,
) -> list[LintViolation]:
    rule = ImportContracts()
    rule.configure(
        {
            "contracts": contracts,
            "source_roots": source_roots if source_roots is not None else ["src"],
            "ignore_type_checking": ignore_type_checking,
        }
    )
    root = Path("/workspace")
    return _run_rule(rule, source, path=root / path, root=root)


def _transport_contract() -> dict[str, object]:
    return {
        "type": "forbidden",
        "name": "transport-purity",
        "source": ["parcel.**"],
        "forbid": ["webkit", "parcel.*.router"],
        "allow": ["parcel.*.router", "parcel.*.dependencies"],
        "message": "Keep transport at the edge.",
    }


@pytest.mark.parametrize(
    "source",
    [
        "import webkit",
        "import webkit.responses as responses",
        "import webkit . responses as responses",
        "from webkit import Response as R",
        "from webkit.responses import *",
        "from parcel.billing import router as edge",
        "from parcel.billing.router import handle",
        "from ..billing import router",
        "from ..billing.router import handle",
        "from ..billing.router import *",
        "def run():\n    import webkit",
        "class Handler:\n    def run(self):\n        from webkit import Response",
    ],
)
def test_import_contracts_report_all_direct_import_forms(source: str) -> None:
    reports = _run_import_contracts(source, [_transport_contract()])

    assert len(reports) == 1
    assert reports[0].rule_name == "import-contracts"
    assert "transport-purity" in reports[0].message
    assert "Keep transport at the edge." in reports[0].message
    assert reports[0].replacement is None
    assert reports[0].range is not None


@pytest.mark.parametrize(
    ("path", "source", "expected"),
    [
        ("src/parcel/orders/router.py", "import webkit", 0),
        ("src/parcel/orders/dependencies.py", "import webkit", 0),
        ("src/parcel/orders/router/helper.py", "import webkit", 1),
        ("src/parcel/orders/nested/router.py", "import webkit", 1),
        ("src/parcel/__init__.py", "import webkit", 1),
        ("src/parcel/orders/__init__.py", "from . import router", 1),
        ("src/parcel/orders/__init__.py", "from .router import *", 1),
        ("src/parcel/orders/logic.py", "from . import router", 1),
        ("src/parcel/orders/logic.py", "from .. import orders", 0),
        ("src/parcel/orders/logic.py", "from ...billing import router", 0),
        ("src/parcel/orders/logic.py", "from .webkit import Response", 0),
        ("src/parcel/orders/logic.py", "import webkit_extra", 0),
        ("src/parcel/orders/logic.py", "import parcel.billing.router_extra", 0),
        ("src/other/logic.py", "import webkit", 0),
        ("vendor/parcel/orders/logic.py", "import webkit", 0),
    ],
)
def test_import_contracts_resolve_modules_without_filesystem_suffix_guesses(
    path: str, source: str, expected: int
) -> None:
    assert len(_run_import_contracts(source, [_transport_contract()], path=path)) == expected


@pytest.mark.parametrize(
    ("source_pattern", "path", "expected"),
    [
        ("parcel.*.router", "src/parcel/orders/router.py", 1),
        ("parcel.*.router", "src/parcel/orders/nested/router.py", 0),
        ("parcel.**.router", "src/parcel/router.py", 1),
        ("parcel.**.router", "src/parcel/orders/nested/router.py", 1),
        ("parcel.**", "src/parcel/__init__.py", 1),
        ("**.router", "src/router.py", 1),
        ("**", "src/parcel/orders/logic.py", 1),
    ],
)
def test_import_contracts_match_whole_source_module_patterns(
    source_pattern: str, path: str, expected: int
) -> None:
    contract = {
        "type": "forbidden",
        "name": "boundary",
        "source": [source_pattern],
        "forbid": ["blocked"],
    }

    assert len(_run_import_contracts("import blocked", [contract], path=path)) == expected


@pytest.mark.parametrize("ignore", [True, False])
def test_import_contracts_configure_type_checking_imports(ignore: bool) -> None:
    reports = _run_import_contracts(
        "from typing import TYPE_CHECKING as TC\nif TC:\n    import webkit",
        [_transport_contract()],
        ignore_type_checking=ignore,
    )

    assert len(reports) == (0 if ignore else 1)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("import typing as t\nif t.TYPE_CHECKING:\n    import webkit", 0),
        ("from typing_extensions import TYPE_CHECKING\nif TYPE_CHECKING:\n    import webkit", 0),
        (
            "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    if enabled:\n        import webkit",
            0,
        ),
        (
            "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    pass\nelse:\n    import webkit",
            1,
        ),
        ("from typing import TYPE_CHECKING\nif not TYPE_CHECKING:\n    import webkit", 1),
        (
            "from typing import TYPE_CHECKING\nif not TYPE_CHECKING:\n    pass\nelse:\n    import webkit",
            0,
        ),
        ("from typing import TYPE_CHECKING\nif TYPE_CHECKING and enabled:\n    import webkit", 0),
        ("from typing import TYPE_CHECKING\nif TYPE_CHECKING or enabled:\n    import webkit", 1),
        ("TYPE_CHECKING = True\nif TYPE_CHECKING:\n    import webkit", 1),
        (
            "from typing import TYPE_CHECKING\ndef run(TYPE_CHECKING):\n    if TYPE_CHECKING:\n        import webkit",
            1,
        ),
    ],
)
def test_import_contracts_only_ignore_proven_type_checking_branches(
    source: str, expected: int
) -> None:
    assert len(_run_import_contracts(source, [_transport_contract()])) == expected


def _layers_contract() -> dict[str, object]:
    return {
        "type": "layers",
        "name": "architecture",
        "root": "parcel",
        "layers": [
            {"modules": ["http.**", "worker.**"]},
            {
                "modules": ["*.**"],
                "exclude": ["http.**", "worker.**", "adapters.**", "platform.**", "records.**"],
            },
            {"modules": ["adapters.**"]},
            {"modules": ["platform.**"]},
            {"modules": ["records.**"]},
        ],
        "message": "Depend downwards.",
    }


@pytest.mark.parametrize(
    ("module", "target", "expected"),
    [
        ("orders.logic", "parcel.http.router", 1),
        ("adapters.client", "parcel.orders.service", 1),
        ("platform.db", "parcel.adapters.client", 1),
        ("records.item", "parcel.platform.db", 1),
        ("platform.db", "parcel.records.item", 0),
        ("http.router", "parcel.orders.service", 0),
        ("http.router", "parcel.worker.jobs", 0),
        ("orders.logic", "parcel.billing.service", 0),
        ("orders.logic", "parcel.orders.other", 0),
        ("records.item", "external.http.router", 0),
    ],
)
def test_import_contracts_enforce_layers_and_peers(module: str, target: str, expected: int) -> None:
    reports = _run_import_contracts(
        f"import {target}", [_layers_contract()], path=f"src/parcel/{module.replace('.', '/')}.py"
    )

    assert len(reports) == expected
    if reports:
        assert "architecture" in reports[0].message
        assert "Depend downwards." in reports[0].message


def _independence_contract() -> dict[str, object]:
    return {
        "type": "independence",
        "name": "domain-apis",
        "packages": ["parcel.*"],
        "exclude": ["parcel.platform.**"],
        "public": ["service", "schemas", "dependencies"],
    }


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("import parcel.billing.storage", 1),
        ("from parcel.billing import storage as db", 1),
        ("from ..billing.storage import find", 1),
        ("import parcel.billing", 1),
        ("from parcel import billing", 1),
        ("from parcel.billing import *", 1),
        ("from parcel.billing import service", 0),
        ("from parcel.billing.service import find", 0),
        ("import parcel.billing.service.internal", 0),
        ("from parcel.billing.schemas import *", 0),
        ("from parcel.billing.dependencies import resolve", 0),
        ("import parcel.billing.service_extra", 1),
        ("import parcel.orders.storage", 0),
        ("import parcel.platform.db", 0),
        ("import outside.billing.storage", 0),
    ],
)
def test_import_contracts_require_public_sibling_modules(source: str, expected: int) -> None:
    reports = _run_import_contracts(source, [_independence_contract()])

    assert len(reports) == expected
    if reports:
        assert "domain-apis" in reports[0].message


def test_import_contracts_layers_cover_from_imports_of_exact_modules() -> None:
    reports = _run_import_contracts(
        "from parcel.edge import Handler",
        [
            {
                "type": "layers",
                "name": "flow",
                "root": "parcel",
                "layers": [{"modules": ["edge"]}, {"modules": ["core"]}],
            }
        ],
        path="src/parcel/core.py",
    )

    assert len(reports) == 1


def test_import_contracts_support_literal_siblings_and_excluded_sources() -> None:
    contract = _independence_contract()
    contract["packages"] = ["parcel.orders", "parcel.billing"]
    reports = _run_import_contracts(
        "import parcel.orders.storage", [contract], path="src/parcel/billing/logic.py"
    )
    excluded = _run_import_contracts(
        "import parcel.orders.storage", [_independence_contract()], path="src/parcel/platform/db.py"
    )

    assert len(reports) == 1
    assert excluded == []


@pytest.mark.parametrize("source", ["from . import *", "def run():\n    from . import storage"])
def test_import_contracts_keep_function_local_relative_imports_and_package_stars(
    source: str,
) -> None:
    contract = {
        "type": "forbidden",
        "name": "leaf",
        "source": ["parcel.orders.**"],
        "forbid": ["parcel.orders"],
    }
    reports = _run_import_contracts(source, [contract])

    assert len(reports) == 1


def test_import_contracts_do_not_follow_other_files_or_reexports(tmp_path: Path) -> None:
    (tmp_path / "wrapper.py").write_text("import webkit\n")
    source = b"import wrapper\n"
    rule = ImportContracts()
    rule.configure(
        {
            "contracts": [
                {"type": "forbidden", "name": "direct", "source": ["**"], "forbid": ["webkit"]}
            ]
        }
    )
    path = tmp_path / "consumer.py"

    assert (
        list(LintRunner(path, source).collect_violations([rule], Config(path=path, root=tmp_path)))
        == []
    )


def test_import_contracts_reset_module_identity_between_files() -> None:
    rule = ImportContracts()
    rule.configure({"source_roots": ["src"], "contracts": [_transport_contract()]})
    root = Path("/workspace")

    assert (
        len(_run_rule(rule, "import webkit", path=root / "src/parcel/orders/logic.py", root=root))
        == 1
    )
    assert (
        _run_rule(rule, "import webkit", path=root / "vendor/parcel/orders/logic.py", root=root)
        == []
    )
    rule.configure({"source_roots": ["src"], "contracts": []})
    assert (
        _run_rule(rule, "import webkit", path=root / "src/parcel/orders/logic.py", root=root) == []
    )


def test_import_contracts_apply_every_matching_contract_per_import() -> None:
    reports = _run_import_contracts(
        "import parcel.billing.router as edge",
        [_transport_contract(), _independence_contract()],
    )

    assert len(reports) == 2
    assert "transport-purity" in reports[0].message
    assert "domain-apis" in reports[1].message


def test_import_contracts_check_each_alias_separately() -> None:
    reports = _run_import_contracts(
        "from parcel.billing import router as r, service as s",
        [_transport_contract()],
    )

    assert len(reports) == 1
    assert reports[0].range is not None
    assert reports[0].range.start.column == 27


def test_import_contracts_use_the_most_specific_source_root() -> None:
    reports = _run_import_contracts(
        "import webkit",
        [_transport_contract()],
        path="apps/server/src/parcel/orders/logic.py",
        source_roots=[".", "apps/server/src"],
    )

    assert len(reports) == 1


@pytest.mark.parametrize(
    "contract",
    [
        {"type": "unknown", "name": "bad"},
        {"type": "forbidden", "name": "bad", "source": [], "forbid": ["x"]},
        {"type": "forbidden", "name": "bad", "source": ["x"], "forbid": []},
        {"type": "forbidden", "name": "", "source": ["x"], "forbid": ["y"]},
        {"type": "forbidden", "name": "bad", "source": ["x..y"], "forbid": ["y"]},
        {"type": "forbidden", "name": "bad", "source": ["x*"], "forbid": ["y"]},
        {"type": "forbidden", "name": "bad", "source": ["x"], "forbid": ["y"], "typo": "x"},
        {
            "type": "layers",
            "name": "bad",
            "root": "x.*",
            "layers": [{"modules": ["x"]}, {"modules": ["y"]}],
        },
        {"type": "layers", "name": "bad", "layers": [{"modules": ["x"]}]},
        {"type": "layers", "name": "bad", "layers": [{"modules": []}, {"modules": ["y"]}]},
        {"type": "independence", "name": "bad", "packages": ["x.**"], "public": ["api"]},
        {"type": "independence", "name": "bad", "packages": ["x.one", "y.two"], "public": ["api"]},
    ],
)
def test_import_contracts_reject_invalid_contracts(contract: dict[str, object]) -> None:
    with pytest.raises(RuleConfigurationError):
        ImportContracts().configure({"contracts": [contract]})


@pytest.mark.parametrize("roots", [[], ["/absolute"], ["../outside"]])
def test_import_contracts_reject_invalid_source_roots(roots: list[str]) -> None:
    with pytest.raises(RuleConfigurationError):
        ImportContracts().configure({"source_roots": roots})


def test_import_contracts_reject_duplicate_contract_names() -> None:
    with pytest.raises(RuleConfigurationError):
        ImportContracts().configure({"contracts": [_transport_contract(), _transport_contract()]})


def test_underscore_import_alias_range_targets_alias_name() -> None:
    reports = _run_rule(NoUnderscoreImportAliases(), "import json as _json")

    assert len(reports) == 1
    assert reports[0].range is not None
    assert reports[0].range.start.column == 15
    assert reports[0].range.end.column == 20
