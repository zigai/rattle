# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from click.testing import CliRunner

from rattle.cli import main


class CliTest(TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner(mix_stderr=False)

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
                ["fix", "--automatic", path.as_posix()],
                catch_exceptions=False,
            )

            assert result.exit_code == 1

    def test_fix_returns_nonzero_for_syntax_errors(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "bad_syntax.py"
            path.write_text("def f(:\n    pass\n")

            result = self.runner.invoke(
                main,
                ["fix", "--automatic", path.as_posix()],
                catch_exceptions=False,
            )

            assert result.exit_code == 2

    def test_fix_returns_nonzero_when_interactive_fix_is_quit(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "fstring.py"
            path.write_text("name = '{}'.format(user)\n")

            result = self.runner.invoke(
                main,
                ["fix", path.as_posix()],
                input="q\n",
                catch_exceptions=False,
            )

            assert result.exit_code == 1
