# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest import TestCase

from rattle import __version__
from rattle.cli import main
from rattle.tests.helpers import CliRunner


class SmokeTest(TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_cli_version(self) -> None:
        result = self.runner.invoke(main, ["--version"])
        expected = rf"rattle {__version__}"
        assert expected in result.stdout

    def test_file_with_formatting(self) -> None:
        content = dedent(
            """\
                import foo
                import bar

                def func():
                    value = f"hello world"
            """
        )
        expected_fix = dedent(
            """\
                import foo
                import bar

                def func():
                    value = "hello world"
            """
        )
        expected_format = dedent(
            """\
                import bar
                import foo


                def func():
                    value = "hello world"
            """
        )
        with TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "file.py"

            with self.subTest("linting"):
                path.write_text(content)
                result = self.runner.invoke(
                    main,
                    ["lint", "-r", "no-redundant-f-string", path.as_posix()],
                    catch_exceptions=False,
                )

                assert result.output != ""
                assert result.exit_code != 0
                assert "no-redundant-f-string [*]" in result.output
                assert re.search(r" --> .*file\.py:5:13", result.output)
                assert '5 |     value = f"hello world"' in result.output
                assert "help: Apply the available autofix" in result.output
                assert content == path.read_text(), "file unexpectedly changed"

            with self.subTest("linting with diff"):
                path.write_text(content)
                result = self.runner.invoke(
                    main,
                    ["lint", "-r", "no-redundant-f-string", "--diff", path.as_posix()],
                    catch_exceptions=False,
                )

                assert result.output != ""
                assert result.exit_code != 0
                assert "no-redundant-f-string [*]" in result.output
                assert "--- a/file.py" in result.output
                assert "+++ b/file.py" in result.output

            with self.subTest("fixing"):
                path.write_text(content)
                result = self.runner.invoke(
                    main,
                    ["fix", "-r", "no-redundant-f-string", path.as_posix()],
                    catch_exceptions=False,
                )

                assert result.stdout == ""
                assert result.exit_code == 0
                assert result.stderr == "1 file checked, 1 fix applied\n"
                assert expected_fix == path.read_text(), "unexpected file output"

            with self.subTest("fixing with formatting"):
                (tdp / "pyproject.toml").write_text("[tool.rattle]\nformatter='ufmt'\n")

                path.write_text(content)
                result = self.runner.invoke(
                    main,
                    ["fix", "-r", "no-redundant-f-string", path.as_posix()],
                    catch_exceptions=False,
                )

                assert result.stdout == ""
                assert result.exit_code == 0
                assert result.stderr == "1 file checked, 1 fix applied\n"
                assert expected_format == path.read_text(), "unexpected file output"

            with self.subTest("fixing with ruff formatting"):
                ruff_content = dedent(
                    """\
                        import foo
                        import bar

                        def func( ):
                            value = f'hello world'
                    """
                )
                expected_ruff_format = dedent(
                    """\
                        import foo
                        import bar


                        def func():
                            value = "hello world"
                    """
                )
                (tdp / "pyproject.toml").write_text("[tool.rattle]\nformatter='ruff'\n")

                path.write_text(ruff_content)
                result = self.runner.invoke(
                    main,
                    ["fix", "-r", "no-redundant-f-string", path.as_posix()],
                    catch_exceptions=False,
                )

                assert result.stdout == ""
                assert result.exit_code == 0
                assert result.stderr == "1 file checked, 1 fix applied\n"
                assert expected_ruff_format == path.read_text(), "unexpected file output"

            with self.subTest("fixing with auto ruff formatting"):
                (tdp / "pyproject.toml").write_text(
                    dedent(
                        """\
                            [tool.rattle]
                            formatter='auto'

                            [tool.ruff.format]
                            quote-style = "double"
                        """
                    )
                )

                path.write_text(ruff_content)
                result = self.runner.invoke(
                    main,
                    ["fix", "-r", "no-redundant-f-string", path.as_posix()],
                    catch_exceptions=False,
                )

                assert result.stdout == ""
                assert result.exit_code == 0
                assert result.stderr == "1 file checked, 1 fix applied\n"
                assert expected_ruff_format == path.read_text(), "unexpected file output"

            with self.subTest("fixing with auto and no formatter config"):
                (tdp / "pyproject.toml").write_text("[tool.rattle]\nformatter='auto'\n")

                path.write_text(content)
                result = self.runner.invoke(
                    main,
                    ["fix", "-r", "no-redundant-f-string", path.as_posix()],
                    catch_exceptions=False,
                )

                assert result.stdout == ""
                assert result.exit_code == 0
                assert result.stderr == "1 file checked, 1 fix applied\n"
                assert expected_fix == path.read_text(), "unexpected file output"

            with self.subTest("linting via stdin"):
                result = self.runner.invoke(
                    main,
                    ["lint", "-r", "no-redundant-f-string", "-", path.as_posix()],
                    input=content,
                    catch_exceptions=False,
                )

                assert result.output != ""
                assert result.exit_code != 0
                assert "no-redundant-f-string [*]" in result.output
                assert re.search(r" --> .*file\.py:5:13", result.output)
                assert '5 |     value = f"hello world"' in result.output

            with self.subTest("fixing with formatting via stdin"):
                (tdp / "pyproject.toml").write_text("[tool.rattle]\nformatter='ufmt'\n")

                result = self.runner.invoke(
                    main,
                    ["fix", "-r", "no-redundant-f-string", "-", path.as_posix()],
                    input=content,
                    catch_exceptions=False,
                )

                assert result.exit_code == 0
                assert expected_format == result.stdout, "unexpected stdout"

    def test_this_file_is_clean(self) -> None:
        path = Path(__file__).resolve().as_posix()
        result = self.runner.invoke(main, ["lint", path], catch_exceptions=False)
        assert result.stdout == ""
        assert result.exit_code == 0
        assert result.stderr == "1 file clean\n"

    def test_this_project_is_clean(self) -> None:
        project_dir = Path(__file__).resolve().parent.parent.as_posix()
        result = self.runner.invoke(main, ["lint", project_dir], catch_exceptions=False)
        assert result.stdout == ""
        assert result.exit_code == 0

    def test_directory_with_violations(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            (tdp / "clean.py").write_text("name = 'Kirby'\nprint(f'hello {name}')")
            (tdp / "dirty.py").write_text("name = 'Kirby'\nprint('hello %s' % name)\n")

            result = self.runner.invoke(main, ["lint", "-r", "use-f-string", td])
            assert "use-f-string [*] Use an f-string instead of `%` formatting" in result.output
            assert re.search(r" --> .*dirty\.py:2:7", result.output)
            assert result.exit_code == 1
            assert result.stderr == "2 files checked, 1 violation in 1 file, 1 autofixable\n"

    def test_directory_with_selector_overrides_from_cli(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            dirty = tdp / "dirty.py"
            dirty.write_text("name = 'Kirby'\nprint('hello %s' % name)\n")

            result = self.runner.invoke(
                main,
                ["lint", "-r", "use-f-string", dirty.as_posix()],
                catch_exceptions=False,
            )
            assert "use-f-string [*] Use an f-string instead of `%` formatting" in result.output
            assert result.exit_code == 1

    def test_cli_short_rule_selector_resolves_configured_local_rule(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            (tdp / "pyproject.toml").write_text(
                dedent(
                    """
                    [tool.rattle]
                    root = true
                    enable = [".my_rules"]
                    """
                )
            )
            (tdp / "my_rules.py").write_text(
                dedent(
                    """
                    from rattle import LintRule

                    class ProjectOnlyRule(LintRule):
                        MESSAGE = "Use the project-only local rule."

                        def visit_Name(self, node):
                            if node.value == "x":
                                self.report(node, self.MESSAGE)
                    """
                )
            )
            dirty = tdp / "dirty.py"
            dirty.write_text("x = 1\n")

            result = self.runner.invoke(
                main,
                [
                    "lint",
                    "--config",
                    (tdp / "pyproject.toml").as_posix(),
                    "--rules",
                    "project-only-rule",
                    dirty.as_posix(),
                ],
                catch_exceptions=False,
            )

            assert "project-only-rule Use the project-only local rule." in result.output
            assert result.exit_code == 1

    def test_directory_respects_inherited_ruff_file_excludes(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            (tdp / "pyproject.toml").write_text(
                dedent(
                    """
                    [tool.rattle]
                    root = true
                    inherit-ruff-files = true

                    [tool.ruff]
                    exclude = ["ignored.py"]
                    """
                )
            )
            (tdp / "included.py").write_text("name = 'Kirby'\nprint('hello %s' % name)\n")
            (tdp / "ignored.py").write_text("name = 'Kirby'\nprint('hello %s' % name)\n")

            result = self.runner.invoke(
                main,
                ["lint", "-r", "use-f-string", td],
                catch_exceptions=False,
            )

            assert "included.py" in result.output
            assert "ignored.py" not in result.output
            assert result.exit_code == 1
            assert result.stderr == "1 file checked, 1 violation in 1 file, 1 autofixable\n"

    def test_directory_respects_rattle_file_excludes(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            (tdp / "pyproject.toml").write_text(
                dedent(
                    """
                    [tool.rattle]
                    root = true
                    exclude = ["ignored.py"]
                    """
                )
            )
            (tdp / "included.py").write_text("name = 'Kirby'\nprint('hello %s' % name)\n")
            (tdp / "ignored.py").write_text("name = 'Kirby'\nprint('hello %s' % name)\n")

            result = self.runner.invoke(
                main,
                ["lint", "-r", "use-f-string", td],
                catch_exceptions=False,
            )

            assert "included.py" in result.output
            assert "ignored.py" not in result.output
            assert result.exit_code == 1
            assert result.stderr == "1 file checked, 1 violation in 1 file, 1 autofixable\n"

    def test_directory_respects_cli_exclude(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            (tdp / "included.py").write_text("name = 'Kirby'\nprint('hello %s' % name)\n")
            (tdp / "ignored.py").write_text("name = 'Kirby'\nprint('hello %s' % name)\n")
            (tdp / "skipped.py").write_text("name = 'Kirby'\nprint('hello %s' % name)\n")

            result = self.runner.invoke(
                main,
                [
                    "lint",
                    "-r",
                    "use-f-string",
                    td,
                    "--exclude",
                    "ignored.py",
                    "--exclude",
                    "skipped.py",
                ],
                catch_exceptions=False,
            )

            assert "included.py" in result.output
            assert "ignored.py" not in result.output
            assert "skipped.py" not in result.output
            assert result.exit_code == 1
            assert result.stderr == "1 file checked, 1 violation in 1 file, 1 autofixable\n"

    def test_cli_exclude_overrides_inherited_ruff_file_excludes(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            (tdp / "pyproject.toml").write_text(
                dedent(
                    """
                    [tool.rattle]
                    root = true
                    inherit-ruff-files = true

                    [tool.ruff]
                    exclude = ["ignored.py"]
                    """
                )
            )
            (tdp / "included.py").write_text("name = 'Kirby'\nprint('hello %s' % name)\n")
            (tdp / "ignored.py").write_text("name = 'Kirby'\nprint('hello %s' % name)\n")

            result = self.runner.invoke(
                main,
                ["lint", "-r", "use-f-string", td, "--exclude", "included.py"],
                catch_exceptions=False,
            )

            assert "included.py" not in result.output
            assert "ignored.py" in result.output
            assert result.exit_code == 1
            assert result.stderr == "1 file checked, 1 violation in 1 file, 1 autofixable\n"

    def test_directory_respects_cli_extend_exclude(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            (tdp / "included.py").write_text("name = 'Kirby'\nprint('hello %s' % name)\n")
            (tdp / "generated.py").write_text("name = 'Kirby'\nprint('hello %s' % name)\n")

            result = self.runner.invoke(
                main,
                ["lint", "-r", "use-f-string", td, "--extend-exclude", "generated.py"],
                catch_exceptions=False,
            )

            assert "included.py" in result.output
            assert "generated.py" not in result.output
            assert result.exit_code == 1
            assert result.stderr == "1 file checked, 1 violation in 1 file, 1 autofixable\n"

    def test_lint_stats_groups_violations_by_rule(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            nested = tdp / "pkg"
            nested.mkdir()
            (tdp / "root.py").write_text("name = 'Kirby'\nprint('hello %s' % name)\n")
            (nested / "one.py").write_text("name = 'Kirby'\nprint('hello %s' % name)\n")
            (nested / "two.py").write_text("name = 'Kirby'\nprint('hello %s' % name)\n")

            original_cwd = Path.cwd()
            os.chdir(tdp.parent)
            try:
                result = self.runner.invoke(
                    main,
                    ["lint", "-r", "use-f-string", "--stats", tdp.as_posix()],
                    catch_exceptions=False,
                )
            finally:
                os.chdir(original_cwd)

            assert result.exit_code == 1
            assert "Violation stats by rule:" in result.stderr
            assert "use-f-string  3" in result.stderr

    def test_directory_with_errors(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            (tdp / "clean.py").write_text("name = 'Kirby'\nprint(f'hello {name}')")
            (tdp / "broken.py").write_text("print)\n")

            result = self.runner.invoke(main, ["lint", "-r", "use-f-string", td])
            assert "invalid-syntax: tokenizer error: unmatched ')'" in result.output
            assert re.search(r" --> .*broken\.py:1:1", result.output)
            assert result.exit_code == 2
            assert result.stderr == "2 files checked, 1 file with errors\n"

    def test_directory_with_violations_and_errors(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            (tdp / "clean.py").write_text("name = 'Kirby'\nprint(f'hello {name}')")
            (tdp / "dirty.py").write_text("name = 'Kirby'\nprint('hello %s' % name)\n")
            (tdp / "broken.py").write_text("print)\n")

            result = self.runner.invoke(main, ["lint", "-r", "use-f-string", td])
            assert "use-f-string [*] Use an f-string instead of `%` formatting" in result.output
            assert re.search(r" --> .*dirty\.py:2:7", result.output)
            assert "invalid-syntax: tokenizer error: unmatched ')'" in result.output
            assert re.search(r" --> .*broken\.py:1:1", result.output)
            assert result.exit_code == 3
            assert (
                result.stderr
                == "3 files checked, 1 violation in 1 file, 1 file with errors, 1 autofixable\n"
            )

    def test_directory_with_autofixes(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            clean = tdp / "clean.py"
            clean.write_text(
                dedent(
                    """
                    GLOBAL = 'hello'

                    def foo():
                        value = 'test'
                        if value is False:
                            pass
                    """
                )
            )
            single = tdp / "single.py"
            single.write_text(
                dedent(
                    """
                    GLOBAL = f'hello'

                    def foo():
                        value = 'test'
                        if value is False:
                            pass
                    """
                )
            )
            multi = tdp / "multi.py"
            multi.write_text(
                dedent(
                    """
                    GLOBAL = f'hello'

                    def foo():
                        value = f'test'
                        if value == False:
                            pass
                    """
                )
            )

            expected = clean.read_text()

            result = self.runner.invoke(main, ["fix", "-r", "fixit-extra", td])

            with self.subTest("clean"):
                assert expected == clean.read_text()

            with self.subTest("single fix"):
                assert expected == single.read_text()

            with self.subTest("multiple fixes"):
                assert expected == multi.read_text()

            assert result.stdout == ""
            assert result.stderr == "3 files checked, 4 fixes applied\n"

    def test_lint_directory_with_no_rules_enabled(self) -> None:
        content = dedent(
            """\
                import foo
                import bar

                def func():
                    value = f"hello world"
            """
        )
        with self.subTest("lint"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "file.py"

            (tdp / "pyproject.toml").write_text("[tool.rattle]\ndisable=['fixit']\n")

            path.write_text(content)
            result = self.runner.invoke(
                main,
                ["lint", path.as_posix()],
                catch_exceptions=False,
            )

            assert result.stdout == ""
            assert result.exit_code == 0

        with self.subTest("fix"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "file.py"

            (tdp / "pyproject.toml").write_text("[tool.rattle]\ndisable=['fixit']\n")

            path.write_text(content)
            result = self.runner.invoke(
                main,
                ["fix", path.as_posix()],
                catch_exceptions=False,
            )

            assert result.stdout == ""
            assert result.exit_code == 0
