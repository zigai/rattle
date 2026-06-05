# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

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

from .helpers import make_cli_runner


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


class CliTest(TestCase):
    def setUp(self) -> None:
        self.runner = make_cli_runner()

    def test_upgrade_command_removed(self) -> None:
        result = self.runner.invoke(main, ["upgrade"], catch_exceptions=False)
        assert result.exit_code == 2
        assert "invalid choice: 'upgrade'" in result.stderr

    def test_rules_test_accepts_rule_name_selector(self) -> None:
        result = self.runner.invoke(
            main,
            ["rules", "--test", "-r", "use-f-string"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0

    def test_rules_test_displays_canonical_rule_name(self) -> None:
        result = self.runner.invoke(
            main,
            ["rules", "--test", "-r", "use-f-string"],
            catch_exceptions=False,
        )

        output = result.stdout + result.stderr
        assert result.exit_code == 0
        assert "rattle.testing.use-f-string" in output
        assert "rattle.testing.UseFstring" not in output

    def test_rules_test_returns_nonzero_for_missing_rule(self) -> None:
        result = self.runner.invoke(
            main,
            ["rules", "--test", "-r", "definitely-missing-rule"],
            catch_exceptions=False,
        )
        assert result.exit_code == 1

    def test_test_command_removed(self) -> None:
        result = self.runner.invoke(main, ["test", "use-f-string"], catch_exceptions=False)

        assert result.exit_code == 2
        assert "invalid choice: 'test'" in result.stderr

    def test_rules_command_displays_enabled_rules(self) -> None:
        result = self.runner.invoke(main, ["rules", "-r", "use-f-string"], catch_exceptions=False)

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
            assert path.read_text() == 'value = "hello"\n'

    def test_fix_no_format_overrides_configured_formatter(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text("[tool.rattle]\nformatter='ruff'\n")
            path = root / "fstring.py"
            path.write_text("def f( ):\n    value = f'hello'\n")

            result = self.runner.invoke(
                main,
                ["fix", "-r", "no-redundant-f-string", "-n", path.as_posix()],
                catch_exceptions=False,
            )

            assert result.exit_code == 0
            assert path.read_text() == "def f( ):\n    value = 'hello'\n"

    def test_lint_brief_prints_one_line_diagnostics(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "fstring.py"
            path.write_text('value = f"hello"\n')

            result = self.runner.invoke(
                main,
                ["lint", "-r", "no-redundant-f-string", "-b", path.as_posix()],
                catch_exceptions=False,
            )

            assert result.exit_code == 1
            assert_brief_diagnostic(result.stdout, path)

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

    def test_lint_print_metrics_uses_cli_output_path(self) -> None:
        def rattle_paths_stub(*_args: object, **kwargs: object) -> object:
            metrics_hook = cast(Callable[[Metrics], None], kwargs["metrics_hook"])
            metrics_hook({"Count.Total": 1})
            return iter(())

        with (
            patch("rattle.cli.rattle_paths", side_effect=rattle_paths_stub),
            TemporaryDirectory() as td,
        ):
            path = Path(td) / "clean.py"
            path.write_text("value = 1\n")
            result = self.runner.invoke(
                main,
                ["lint", "--print-metrics", path.as_posix()],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "{'Count.Total': 1}" in result.stdout
        assert result.stderr == "0 files clean\n"

    def test_fix_brief_prints_one_line_diagnostics(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "fstring.py"
            path.write_text('value = f"hello"\n')

            result = self.runner.invoke(
                main,
                ["fix", "-r", "no-redundant-f-string", "--brief", path.as_posix()],
                catch_exceptions=False,
            )

            assert result.exit_code == 0
            assert_brief_diagnostic(result.stdout, path)
            assert path.read_text() == 'value = "hello"\n'

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
