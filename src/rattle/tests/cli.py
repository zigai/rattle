# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import json
import os
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast
from unittest import TestCase
from unittest.mock import patch

from rattle.cli import _find_uv_project_root, _rule_line, _should_reexec_with_uv, main
from rattle.ftypes import Metrics, Options
from rattle.rule import LintRule
from rattle.rules.fixit_extra.use_fstring import UseFstring

from .helpers import CliRunner


def assert_brief_diagnostic(stdout: str, path: Path) -> None:
    line = stdout.strip()
    prefix = (
        "no-redundant-f-string [*] f-string doesn't have placeholders, "
        "remove redundant f-string.  --> "
    )

    assert line.startswith(prefix)
    location = line.removeprefix(prefix)
    path_text, line_number, column = location.rsplit(":", 2)
    assert Path(path_text).resolve() == path.resolve()
    assert (line_number, column) == ("1", "9")


def write_config(path: Path, *, enable: str) -> Path:
    config_path = path / "pyproject.toml"
    config_path.write_text(f'[tool.rattle]\nroot = true\nenable = ["{enable}"]\n')
    return config_path


def write_clean_file(path: Path) -> Path:
    file_path = path / "clean.py"
    file_path.write_text("value = 1\n")
    return file_path


class CliTest(TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_upgrade_command_removed(self) -> None:
        result = self.runner.invoke(main, ["upgrade"], catch_exceptions=False)
        assert result.exit_code == 2
        assert "invalid choice: 'upgrade'" in result.stderr

    def test_rules_test_uses_enabled_rules_from_config(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            config = write_config(root, enable="use-f-string")
            path = write_clean_file(root)
            result = self.runner.invoke(
                main,
                ["rules", "--test", "--config", config.as_posix(), path.as_posix()],
                catch_exceptions=False,
            )

        assert result.exit_code == 0

    def test_rules_test_displays_canonical_rule_name(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            config = write_config(root, enable="use-f-string")
            path = write_clean_file(root)
            result = self.runner.invoke(
                main,
                ["rules", "--test", "--config", config.as_posix(), path.as_posix()],
                catch_exceptions=False,
            )

        output = result.stdout + result.stderr
        assert result.exit_code == 0
        assert "rattle.testing.use-f-string" in output
        assert "rattle.testing.UseFstring" not in output

    def test_rules_test_returns_nonzero_for_missing_rule(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            config = write_config(root, enable="definitely-missing-rule")
            path = write_clean_file(root)
            result = self.runner.invoke(
                main,
                ["rules", "--test", "--config", config.as_posix(), path.as_posix()],
                catch_exceptions=False,
            )

        assert result.exit_code != 0

    def test_test_command_removed(self) -> None:
        result = self.runner.invoke(main, ["test", "use-f-string"], catch_exceptions=False)

        assert result.exit_code == 2
        assert "invalid choice: 'test'" in result.stderr

    def test_help_is_supported_for_commands(self) -> None:
        short_result = self.runner.invoke(main, ["lint", "-h"], catch_exceptions=False)
        long_result = self.runner.invoke(main, ["lint", "--help"], catch_exceptions=False)

        assert short_result.exit_code == 0
        assert "-h, --help" in short_result.stdout
        assert long_result.exit_code == 0
        assert "-h, --help" in long_result.stdout

    def test_lsp_does_not_expose_stdio_alias(self) -> None:
        help_result = self.runner.invoke(main, ["lsp", "--help"], catch_exceptions=False)
        alias_result = self.runner.invoke(main, ["lsp", "--stdio"], catch_exceptions=False)

        assert help_result.exit_code == 0
        assert "--no-stdio" in help_result.stdout
        assert "--stdio" not in help_result.stdout
        assert alias_result.exit_code == 2
        assert "unrecognized arguments: --stdio" in alias_result.stderr

    def test_rules_command_displays_enabled_rules(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            config = write_config(root, enable="use-f-string")
            path = write_clean_file(root)
            result = self.runner.invoke(
                main,
                ["rules", "--config", config.as_posix(), path.as_posix()],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "Rules for " in result.stdout
        assert "1 enabled" in result.stdout
        assert "use-f-string - Do not use printf style formatting" in result.stdout
        assert "[fix]" not in result.stdout
        assert "simple_expression_max_length" not in result.stdout
        assert "rattle.rules.fixit_extra.use_fstring:use-f-string" not in result.stdout
        assert "Options(" not in result.stdout
        assert "Config(" not in result.stdout

    def test_rules_command_displays_disabled_rules_with_canonical_names(self) -> None:
        result = self.runner.invoke(main, ["rules"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "Disabled" in result.stdout
        assert "  explicit-frozen-dataclass (disabled)" in result.stdout
        assert "  use-rattle-ignore-comment (disabled)" in result.stdout
        assert "  use-types-from-typing (python-version)" in result.stdout
        assert "ExplicitFrozenDataclass" not in result.stdout
        assert "UseRattleIgnoreComment" not in result.stdout
        assert "UseTypesFromTyping" not in result.stdout

    def test_explain_command_displays_builtin_rule_info(self) -> None:
        with TemporaryDirectory() as td:
            config = write_config(Path(td), enable="use-f-string")
            result = self.runner.invoke(
                main,
                ["explain", "--config", config.as_posix(), "use-f-string"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        first_line = result.stdout.splitlines()[0]
        assert "use-f-string [*]  Enabled" in first_line
        assert "rattle.rules.fixit_extra.use_fstring" in first_line
        assert "Do not use printf style formatting or .format()." in result.stdout
        assert "Selector:" not in result.stdout
        assert "module:" not in result.stdout
        assert "Python: Any" in result.stdout
        assert "Patterns: .format, %" in result.stdout
        assert "Metadata" not in result.stdout

    def test_explain_command_accepts_qualified_selector(self) -> None:
        with TemporaryDirectory() as td:
            config = write_config(Path(td), enable="use-f-string")
            result = self.runner.invoke(
                main,
                [
                    "explain",
                    "--config",
                    config.as_posix(),
                    "rattle.rules.fixit_extra.use_fstring:use-f-string",
                ],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "use-f-string [*]  Enabled" in result.stdout
        assert "Selector:" not in result.stdout

    def test_explain_command_reports_missing_rule(self) -> None:
        result = self.runner.invoke(
            main,
            ["explain", "definitely-missing-rule"],
            catch_exceptions=False,
        )

        assert result.exit_code == 2
        assert "could not find rule definitely-missing-rule" in result.stderr

    def test_explain_command_displays_disabled_status(self) -> None:
        result = self.runner.invoke(
            main,
            ["explain", "explicit-frozen-dataclass"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        first_line = result.stdout.splitlines()[0]
        assert "explicit-frozen-dataclass  Disabled" in first_line
        assert "rattle.rules.fixit.explicit_frozen_dataclass" in first_line
        assert "Python: Any" in result.stdout

    def test_explain_command_indents_multiline_examples(self) -> None:
        result = self.runner.invoke(
            main,
            ["explain", "explicit-frozen-dataclass"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "    from dataclasses import dataclass" in result.stdout
        assert "\nfrom dataclasses import dataclass" not in result.stdout
        assert "    @dataclass(frozen=False)" in result.stdout
        assert "\n@dataclass(frozen=False)" not in result.stdout

    def test_explain_command_displays_settings_references_and_examples(self) -> None:
        with TemporaryDirectory() as td:
            config = write_config(Path(td), enable="use-f-string")
            result = self.runner.invoke(
                main,
                ["explain", "--config", config.as_posix(), "use-f-string"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "Settings" in result.stdout
        assert "simple_expression_max_length  int  default: 30" in result.stdout
        assert "References" in result.stdout
        assert "PEP 498: https://www.python.org/dev/peps/pep-0498/" in result.stdout
        assert "Examples" in result.stdout
        assert "Valid:" in result.stdout
        assert "Invalid:" in result.stdout
        assert '"%s" % "hi"  ->  f"{\'hi\'}"' in result.stdout

    def test_explain_command_json_output(self) -> None:
        with TemporaryDirectory() as td:
            config = write_config(Path(td), enable="use-f-string")
            result = self.runner.invoke(
                main,
                ["explain", "--json", "--config", config.as_posix(), "use-f-string"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["name"] == "use-f-string"
        assert data["status"] == "Enabled"
        assert data["selector"] == "rattle.rules.fixit_extra.use_fstring:use-f-string"
        assert data["autofix"] is True
        assert data["settings"][0]["name"] == "simple_expression_max_length"
        assert data["settings"][0]["type"] == "int"
        assert data["settings"][0]["default"] == 30
        assert data["references"] == [
            {"label": "PEP 498", "url": "https://www.python.org/dev/peps/pep-0498/"}
        ]
        assert data["examples"]["invalid"][1]["replacement"] == "f\"{'hi'}\""
        assert "Invalid(" not in result.stdout
        assert "Valid(" not in result.stdout

    def test_rule_line_omits_rule_tags(self) -> None:
        class TaggedRule(LintRule):
            MESSAGE = "Use the narrow rules listing."
            TAGS = {"architecture", "local"}

        assert _rule_line(TaggedRule()) == "  tagged-rule - Use the narrow rules listing."

    def test_rule_line_only_colors_rule_name(self) -> None:
        def fake_colored(
            text: str,
            color: str | None = None,
            background: str | None = None,
            style: str | None = None,
        ) -> str:
            del background, color, style
            return f"<colored>{text}</colored>"

        with patch("rattle.cli.colored", side_effect=fake_colored):
            line = _rule_line(UseFstring())

        assert line.startswith("  <colored>use-f-string</colored> - ")
        assert " - Do not use printf style formatting" in line
        assert " - <colored>Do not use printf style formatting" not in line

    def test_find_uv_project_root_accepts_uv_lock(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            nested = root / "src" / "pkg"
            nested.mkdir(parents=True)
            (root / "uv.lock").write_text("")

            assert _find_uv_project_root(nested) == root

    def test_find_uv_project_root_accepts_tool_uv(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            nested = root / "src" / "pkg"
            nested.mkdir(parents=True)
            (root / "pyproject.toml").write_text("[tool.uv]\n")

            assert _find_uv_project_root(nested) == root

    def test_uv_reexec_is_limited_to_rule_loading_commands(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("rattle.cli.shutil.which", return_value="/usr/bin/uv"),
            patch("rattle.cli._find_uv_project_root", return_value=Path.cwd()),
        ):
            assert _should_reexec_with_uv(["lint"])
            assert _should_reexec_with_uv(["fix", "."])
            assert _should_reexec_with_uv(["rules"])
            assert not _should_reexec_with_uv(["--version"])
            assert not _should_reexec_with_uv(["upgrade"])

    def test_uv_reexec_guard_prevents_loop(self) -> None:
        with (
            patch.dict(os.environ, {"RATTLE_UV_RUN_REEXEC": "1"}, clear=True),
            patch("rattle.cli.shutil.which", return_value="/usr/bin/uv"),
            patch("rattle.cli._find_uv_project_root", return_value=Path.cwd()),
        ):
            assert not _should_reexec_with_uv(["lint"])

    def test_debug_command_removed(self) -> None:
        result = self.runner.invoke(main, ["debug"], catch_exceptions=False)

        assert result.exit_code == 2
        assert "invalid choice: 'debug'" in result.stderr

    def test_validate_config_command_removed(self) -> None:
        result = self.runner.invoke(main, ["validate-config"], catch_exceptions=False)

        assert result.exit_code == 2
        assert "invalid choice: 'validate-config'" in result.stderr

    def test_validate_command_accepts_config_file(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "pyproject.toml"
            path.write_text("[tool.rattle]\nroot = true\n")

            result = self.runner.invoke(main, ["validate", path.as_posix()], catch_exceptions=False)

        assert result.exit_code == 0

    def test_validate_command_validates_explicit_config_file(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "pyproject.toml"
            path.write_text('[tool.rattle]\nroot = true\nenable = ["definitely-missing-rule"]\n')

            result = self.runner.invoke(main, ["validate", path.as_posix()], catch_exceptions=False)

        assert result.exit_code == 1
        assert "definitely-missing-rule" in result.stderr

    def test_validate_command_defaults_to_pyproject_toml(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text("[tool.rattle]\nroot = true\n")
            original_cwd = Path.cwd()
            os.chdir(root)
            try:
                result = self.runner.invoke(main, ["validate"], catch_exceptions=False)
            finally:
                os.chdir(original_cwd)

        assert result.exit_code == 0

    def test_validate_command_reports_missing_default_pyproject_toml(self) -> None:
        with TemporaryDirectory() as td:
            original_cwd = Path.cwd()
            os.chdir(td)
            try:
                result = self.runner.invoke(main, ["validate"], catch_exceptions=False)
            finally:
                os.chdir(original_cwd)

        assert result.exit_code == 2
        assert "path must be an existing file: pyproject.toml" in result.stderr

    def test_lint_returns_usage_error_for_missing_path(self) -> None:
        result = self.runner.invoke(
            main,
            ["lint", "missing.py"],
            catch_exceptions=False,
        )
        assert result.exit_code == 2
        assert "path must be an existing path: missing.py" in result.stderr

    def test_fix_returns_usage_error_for_missing_path(self) -> None:
        result = self.runner.invoke(
            main,
            ["fix", "missing.py"],
            catch_exceptions=False,
        )
        assert result.exit_code == 2
        assert "path must be an existing path: missing.py" in result.stderr

    def test_fix_returns_nonzero_for_unfixable_violations(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "bad_async.py"
            path.write_text("import time\nasync def f():\n    time.sleep(1)\n")

            result = self.runner.invoke(
                main,
                ["fix", "-r", "use-async-sleep-in-async-def", path.as_posix()],
                catch_exceptions=False,
            )

            assert result.exit_code == 1

    def test_fix_only_prints_unfixed_violations_by_default(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "mixed.py"
            path.write_text(
                'import time\nasync def f():\n    value = f"hello"\n    time.sleep(1)\n'
            )

            result = self.runner.invoke(
                main,
                [
                    "fix",
                    "-r",
                    "no-redundant-f-string,use-async-sleep-in-async-def",
                    path.as_posix(),
                ],
                catch_exceptions=False,
            )
            fixed_content = path.read_text()

        assert result.exit_code == 1
        assert "use-async-sleep-in-async-def" in result.stdout
        assert "no-redundant-f-string" not in result.stdout
        assert "1 file checked, 2 violations in 1 file, 1 autofixable, 1 fix applied" in (
            result.stderr
        )
        assert (
            fixed_content == 'import time\nasync def f():\n    value = "hello"\n    time.sleep(1)\n'
        )

    def test_fix_returns_nonzero_for_syntax_errors(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "bad_syntax.py"
            path.write_text("def f(:\n    pass\n")

            result = self.runner.invoke(
                main,
                ["fix", "-r", "no-redundant-f-string", path.as_posix()],
                catch_exceptions=False,
            )

            assert result.exit_code == 2

    def test_fix_applies_autofixes_by_default(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "fstring.py"
            path.write_text('value = f"hello"\n')

            result = self.runner.invoke(
                main,
                ["fix", "-r", "no-redundant-f-string", path.as_posix()],
                catch_exceptions=False,
            )

            assert result.exit_code == 0
            assert result.stdout == ""
            assert result.stderr == (
                "1 file checked, 1 violation in 1 file, 1 autofixable, 1 fix applied\n"
            )
            assert path.read_text() == 'value = "hello"\n'

    def test_fix_diff_prints_applied_fixes(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "fstring.py"
            path.write_text('value = f"hello"\n')

            result = self.runner.invoke(
                main,
                ["fix", "-r", "no-redundant-f-string", "--diff", path.as_posix()],
                catch_exceptions=False,
            )

            assert result.exit_code == 0
            assert "no-redundant-f-string [*]" in result.stdout
            assert "--- a/fstring.py" in result.stdout
            assert 'value = f"hello"' in result.stdout
            assert path.read_text() == 'value = "hello"\n'

    def test_fix_no_format_flag_removed(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "fstring.py"
            path.write_text("value = f'hello'\n")

            result = self.runner.invoke(
                main,
                ["fix", "-r", "no-redundant-f-string", "-n", path.as_posix()],
                catch_exceptions=False,
            )

        assert result.exit_code == 2
        assert "unrecognized arguments: -n" in result.stderr

    def test_lint_compact_prints_one_line_diagnostics(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "fstring.py"
            path.write_text('value = f"hello"\n')

            result = self.runner.invoke(
                main,
                ["lint", "-r", "no-redundant-f-string", "--compact", path.as_posix()],
                catch_exceptions=False,
            )

            assert result.exit_code == 1
            assert_brief_diagnostic(result.stdout, path)

    def test_lint_quiet_prints_only_summary(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "fstring.py"
            path.write_text('value = f"hello"\n')

            result = self.runner.invoke(
                main,
                ["lint", "-r", "no-redundant-f-string", "--quiet", path.as_posix()],
                catch_exceptions=False,
            )

        assert result.exit_code == 1
        assert result.stdout == ""
        assert result.stderr == "1 file checked, 1 violation in 1 file, 1 autofixable\n"

    def test_lint_quiet_rejects_diff(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "fstring.py"
            path.write_text('value = f"hello"\n')

            result = self.runner.invoke(
                main,
                ["lint", "-r", "no-redundant-f-string", "--quiet", "--diff", path.as_posix()],
                catch_exceptions=False,
            )

        assert result.exit_code == 2
        assert "--quiet and --diff cannot be used together" in result.stderr

    def test_lint_stats_prints_violations_by_rule(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "fstring.py"
            path.write_text('first = f"hello"\nsecond = f"world"\n')

            result = self.runner.invoke(
                main,
                ["lint", "-r", "no-redundant-f-string", "--stats", path.as_posix()],
                catch_exceptions=False,
            )

        assert result.exit_code == 1
        assert "Violation stats by rule:" in result.stderr
        assert "no-redundant-f-string  2" in result.stderr

    def test_lint_accepts_jobs_option(self) -> None:
        seen_jobs: list[int | None] = []

        def rattle_paths_stub(*_args: object, **kwargs: object) -> object:
            seen_jobs.append(cast(Options, kwargs["options"]).jobs)
            return iter(())

        with (
            patch("rattle.cli.rattle_paths", side_effect=rattle_paths_stub),
            TemporaryDirectory() as td,
        ):
            path = Path(td) / "clean.py"
            path.write_text("value = 1\n")
            result = self.runner.invoke(
                main,
                ["lint", "-j", "2", path.as_posix()],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert seen_jobs == [2]

    def test_lint_metrics_env_uses_cli_output_path(self) -> None:
        def rattle_paths_stub(*_args: object, **kwargs: object) -> object:
            metrics_hook = cast(Callable[[Metrics], None], kwargs["metrics_hook"])
            metrics_hook({"Count.Total": 1})
            return iter(())

        with (
            patch.dict(os.environ, {"RATTLE_METRICS": "1"}),
            patch("rattle.cli.rattle_paths", side_effect=rattle_paths_stub),
            TemporaryDirectory() as td,
        ):
            path = Path(td) / "clean.py"
            path.write_text("value = 1\n")
            result = self.runner.invoke(
                main,
                ["lint", path.as_posix()],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "{'Count.Total': 1}" in result.stdout
        assert result.stderr == "No Python files found\n"

    def test_fix_compact_omits_fixed_diagnostics(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "fstring.py"
            path.write_text('value = f"hello"\n')

            result = self.runner.invoke(
                main,
                ["fix", "-r", "no-redundant-f-string", "--compact", path.as_posix()],
                catch_exceptions=False,
            )

            assert result.exit_code == 0
            assert result.stdout == ""
            assert result.stderr == (
                "1 file checked, 1 violation in 1 file, 1 autofixable, 1 fix applied\n"
            )
            assert path.read_text() == 'value = "hello"\n'

    def test_fix_stats_prints_violations_by_rule(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "fstring.py"
            path.write_text('first = f"hello"\nsecond = f"world"\n')

            result = self.runner.invoke(
                main,
                ["fix", "-r", "no-redundant-f-string", "--stats", path.as_posix()],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert result.stdout == ""
        assert "Violation stats by rule:" in result.stderr
        assert "no-redundant-f-string  2" in result.stderr

    def test_fix_quiet_rejects_interactive(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "fstring.py"
            path.write_text('value = f"hello"\n')

            result = self.runner.invoke(
                main,
                ["fix", "-r", "no-redundant-f-string", "--quiet", "--interactive", path.as_posix()],
                catch_exceptions=False,
            )

        assert result.exit_code == 2
        assert "--quiet and --interactive cannot be used together" in result.stderr

    def test_fix_logs_missing_rule_collection_once(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                '[tool.rattle]\ndisable = ["missing_rules_collection.rules"]\n'
            )
            first = root / "first.py"
            second = root / "second.py"
            first.write_text("value = 1\n")
            second.write_text("other = 2\n")

            with self.assertLogs("rattle.config", level="WARNING") as logs:
                result = self.runner.invoke(
                    main,
                    ["fix", first.as_posix(), second.as_posix()],
                    catch_exceptions=False,
                )

            assert result.exit_code == 0
            assert result.stdout == ""
            assert result.stderr == "2 files clean\n"
            assert (
                sum(
                    "Failed to load rules 'missing_rules_collection.rules'" in message
                    for message in logs.output
                )
                == 1
            )

    def test_fix_returns_nonzero_when_interactive_fix_is_quit(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "fstring.py"
            path.write_text('value = f"hello"\n')

            result = self.runner.invoke(
                main,
                ["fix", "-r", "no-redundant-f-string", "--interactive", path.as_posix()],
                input="q",
                catch_exceptions=False,
            )

            assert result.exit_code == 1
            assert path.read_text() == 'value = f"hello"\n'

    def test_fix_interactive_accepts_single_keypress(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "fstring.py"
            path.write_text('value = f"hello"\n')

            result = self.runner.invoke(
                main,
                ["fix", "-r", "no-redundant-f-string", "--interactive", path.as_posix()],
                input="y",
                catch_exceptions=False,
            )

            assert result.exit_code == 0
            assert path.read_text() == 'value = "hello"\n'
