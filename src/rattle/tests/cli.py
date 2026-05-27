# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast
from unittest import TestCase
from unittest.mock import patch

from rattle.cli import main
from rattle.ftypes import Options

from .helpers import make_cli_runner


class CliTest(TestCase):
    def setUp(self) -> None:
        self.runner = make_cli_runner()

    def test_upgrade_command_removed(self) -> None:
        result = self.runner.invoke(main, ["upgrade"], catch_exceptions=False)
        assert result.exit_code == 2
        assert "No such command 'upgrade'" in result.stderr

    def test_test_command_accepts_code_selector(self) -> None:
        result = self.runner.invoke(main, ["test", "RAT024"], catch_exceptions=False)
        assert result.exit_code == 0

    def test_fix_returns_nonzero_for_unfixable_violations(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "bad_async.py"
            path.write_text("import time\nasync def f():\n    time.sleep(1)\n")

            result = self.runner.invoke(
                main,
                ["fix", path.as_posix()],
                catch_exceptions=False,
            )

            assert result.exit_code == 1

    def test_fix_returns_nonzero_for_syntax_errors(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "bad_syntax.py"
            path.write_text("def f(:\n    pass\n")

            result = self.runner.invoke(
                main,
                ["fix", path.as_posix()],
                catch_exceptions=False,
            )

            assert result.exit_code == 2

    def test_fix_applies_autofixes_by_default(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "fstring.py"
            path.write_text('value = f"hello"\n')

            result = self.runner.invoke(main, ["fix", path.as_posix()], catch_exceptions=False)

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
                ["--no-format", "fix", path.as_posix()],
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
                ["lint", "--brief", path.as_posix()],
                catch_exceptions=False,
            )

            assert result.exit_code == 1
            assert result.stdout.splitlines() == [
                "NoRedundantFString [*] f-string doesn't have placeholders, "
                f"remove redundant f-string.  --> {path.as_posix()}:1:9"
            ]

    def test_lint_accepts_jobs_option(self) -> None:
        seen_jobs: list[int | None] = []

        def rattle_paths_stub(*_args: object, **kwargs: object) -> object:
            seen_jobs.append(cast(Options, kwargs["options"]).jobs)
            return iter(())

        with patch("rattle.cli.rattle_paths", side_effect=rattle_paths_stub):
            result = self.runner.invoke(
                main,
                ["--jobs", "2", "lint", "clean.py"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert seen_jobs == [2]

    def test_fix_brief_prints_one_line_diagnostics(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "fstring.py"
            path.write_text('value = f"hello"\n')

            result = self.runner.invoke(
                main,
                ["fix", "--brief", path.as_posix()],
                catch_exceptions=False,
            )

            assert result.exit_code == 0
            assert result.stdout.splitlines() == [
                "NoRedundantFString [*] f-string doesn't have placeholders, "
                f"remove redundant f-string.  --> {path.as_posix()}:1:9"
            ]
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
                ["fix", "--interactive", path.as_posix()],
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
                ["fix", "--interactive", path.as_posix()],
                input="y",
                catch_exceptions=False,
            )

            assert result.exit_code == 0
            assert path.read_text() == 'value = "hello"\n'
