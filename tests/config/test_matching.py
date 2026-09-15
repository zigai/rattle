# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import re
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest import TestCase

from packaging.version import Version

from rattle import config
from rattle.cli import main
from rattle.config.models import Config, Options
from rattle.rendering.models import OutputFormat
from rattle.selectors import QualifiedRule, RuleNameSelector
from rattle.util import chdir
from tests.support import CliRunner


class ConfigTest(TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.td = TemporaryDirectory()
        self.tdp = Path(self.td.name).resolve()

        self.noise = self.tdp / "noise"
        self.outer = self.tdp / "outer"
        self.inner = self.tdp / "outer" / "inner"
        self.noise.mkdir()
        self.inner.mkdir(parents=True)

        (self.tdp / "pyproject.toml").write_text(
            dedent(
                """
                [tool.rattle]
                root = true
                enable-root-import = true
                enable = ["more.rules"]
                disable = ["rattle.rules.something_specific"]
                python-version = "3.8"

                [[tool.rattle.overrides]]
                path = "other"
                enable = ["other.stuff", ".globalrules"]
                disable = ["modernization"]
                options = {"other.stuff:whatever"={key="value"}}
                python-version = "3.10"
                """
            )
        )
        (self.outer / "pyproject.toml").write_text(
            dedent(
                """
                [tool.rattle]
                enable = [".localrules"]
                disable = ["modernization"]
                """
            )
        )
        (self.noise / "pyproject.toml").write_text(
            dedent(
                """
                [tool.fuzzball]
                something = "whatever"
                """
            )
        )
        (self.inner / "pyproject.toml").write_text(
            dedent(
                """
                [tool.rattle]
                root = true
                enable = ["fake8", "make8"]
                disable = ["foo.bar"]
                unknown = "hello"
                """
            )
        )

    def tearDown(self) -> None:
        self.td.cleanup()

    def test_generate_config(self) -> None:
        for name, path, root, options, expected in (
            (
                "inner",
                self.inner / "foo.py",
                None,
                None,
                Config(
                    path=self.inner / "foo.py",
                    root=self.inner,
                    enable=[
                        RuleNameSelector("fake8"),
                        RuleNameSelector("make8"),
                    ],
                    disable=[QualifiedRule("foo.bar")],
                ),
            ),
            (
                "outer",
                self.outer / "foo.py",
                None,
                None,
                Config(
                    path=self.outer / "foo.py",
                    root=self.tdp,
                    enable_root_import=True,
                    enable=[
                        QualifiedRule(".localrules", local=".", root=self.outer),
                        QualifiedRule("more.rules"),
                    ],
                    disable=[
                        QualifiedRule("rattle.rules.modernization"),
                        QualifiedRule("rattle.rules.something_specific"),
                    ],
                    python_version=Version("3.8"),
                ),
            ),
            (
                "outer with root",
                self.outer / "foo.py",
                self.outer,
                None,
                Config(
                    path=self.outer / "foo.py",
                    root=self.outer,
                    enable=[QualifiedRule(".localrules", local=".", root=self.outer)],
                    disable=[QualifiedRule("rattle.rules.modernization")],
                ),
            ),
            (
                "other",
                self.tdp / "other" / "foo.py",
                None,
                None,
                Config(
                    path=self.tdp / "other" / "foo.py",
                    root=self.tdp,
                    enable_root_import=True,
                    enable=[
                        QualifiedRule(".globalrules", local=".", root=self.tdp),
                        QualifiedRule("more.rules"),
                        QualifiedRule("other.stuff"),
                    ],
                    disable=[
                        QualifiedRule("rattle.rules.modernization"),
                        QualifiedRule("rattle.rules.something_specific"),
                    ],
                    options={"other.stuff:whatever": {"key": "value"}},
                    python_version=Version("3.10"),
                ),
            ),
            (
                "root",
                self.tdp / "foo.py",
                None,
                None,
                Config(
                    path=self.tdp / "foo.py",
                    root=self.tdp,
                    enable_root_import=True,
                    enable=[QualifiedRule("more.rules")],
                    disable=[QualifiedRule("rattle.rules.something_specific")],
                    python_version=Version("3.8"),
                ),
            ),
            (
                "root with options",
                self.tdp / "foo.py",
                None,
                Options(output_format=OutputFormat.custom, output_template="foo-bar"),
                Config(
                    path=self.tdp / "foo.py",
                    root=self.tdp,
                    enable_root_import=True,
                    enable=[QualifiedRule("more.rules")],
                    disable=[QualifiedRule("rattle.rules.something_specific")],
                    python_version=Version("3.8"),
                    output_format=OutputFormat.custom,
                    output_template="foo-bar",
                ),
            ),
        ):
            with self.subTest(name):
                actual = config.generate_config(path, root, options=options)
                assert asdict(expected) == asdict(actual)

        with self.subTest("per-file rule toggles"):
            path = self.tdp / "tests" / "nested" / "case.py"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("pass\n")
            (self.tdp / "pyproject.toml").write_text(
                dedent(
                    """
                    [tool.rattle]
                    root = true
                    enable = ["foo"]
                    disable = ["bar"]
                    per-file-enable = {"tests/**/*.py" = ["bar"]}
                    per-file-disable = {"tests/nested/case.py" = ["foo"]}
                    """
                )
            )

            actual = config.generate_config(path)

            assert asdict(
                Config(
                    path=path,
                    root=self.tdp,
                    enable=[RuleNameSelector("bar")],
                    disable=[RuleNameSelector("foo")],
                )
            ) == asdict(actual)

        with self.subTest("rule name selectors and exact option targets"):
            path = self.tdp / "rule_name_selectors.py"
            path.write_text("pass\n")
            (self.tdp / "pyproject.toml").write_text(
                dedent(
                    """
                    [tool.rattle]
                    root = true
                    enable = ["use-f-string"]
                    disable = ["no-static-if-condition"]

                    [tool.rattle.options]
                    "use-f-string" = {simple_expression_max_length = 42}
                    """
                )
            )

            actual = config.generate_config(path)

            assert asdict(
                Config(
                    path=path,
                    root=self.tdp,
                    enable=[RuleNameSelector("use-f-string")],
                    disable=[RuleNameSelector("no-static-if-condition")],
                    options={"use-f-string": {"simple_expression_max_length": 42}},
                )
            ) == asdict(actual)

        with self.subTest("inherit Ruff file exclusion"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            target = tdp / "build" / "ignored.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("pass\n")
            (tdp / "pyproject.toml").write_text(
                dedent(
                    """
                    [tool.rattle]
                    root = true
                    inherit-ruff-files = true

                    [tool.ruff]
                    exclude = ["build"]
                    """
                )
            )

            actual = config.generate_config(target)

            assert actual.excluded is True

        with self.subTest("Rattle file exclusion"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            target = tdp / "build" / "ignored.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("pass\n")
            (tdp / "pyproject.toml").write_text(
                dedent(
                    """
                    [tool.rattle]
                    root = true
                    exclude = ["build"]
                    """
                )
            )

            actual = config.generate_config(target)

            assert actual.excluded is True

    def test_path_matches_glob_nested_directory_wildcard(self) -> None:
        from rattle.config.matching import _path_matches_glob

        assert _path_matches_glob("tests/unit/test_foo.py", "tests/**") is True
        assert _path_matches_glob("tests/test_foo.py", "tests/**") is True
        assert _path_matches_glob("other/test_foo.py", "tests/**") is False
        assert _path_matches_glob("tests/unit/test_foo.py", "tests/*.py") is False
        assert _path_matches_glob("tests/test_foo.py", "tests/*.py") is True

    def test_path_matches_glob_trailing_slash(self) -> None:
        from rattle.config.matching import _path_matches_glob

        assert _path_matches_glob("build/foo.py", "build/") is True
        assert _path_matches_glob("build/sub/foo.py", "build/") is True
        assert _path_matches_glob("build", "build/") is True
        assert _path_matches_glob("other/foo.py", "build/") is False
        assert _path_matches_glob("foo/sub/bar/baz.py", "foo/*/bar/") is True

    def test_format_output(self) -> None:
        with chdir(self.tdp):
            (self.tdp / "pyproject.toml").write_text(
                dedent(
                    """
                    [tool.rattle]
                    enable = ["use-f-string"]
                    output-format = "vscode"
                    """
                )
            )

            runner = CliRunner()
            content = "name = '%s' % (first_name,)"
            filepath = self.tdp / "f_string.py"
            output_format_regex = rf"{re.escape(filepath.name)}:\d+:\d+ use-f-string: .+"

            with self.subTest("linting vscode"):
                filepath.write_text(content)
                result = runner.invoke(main, ["lint", filepath.as_posix()], catch_exceptions=False)
                assert result.exit_code == 1
                assert any(
                    re.fullmatch(output_format_regex, line) for line in result.stdout.splitlines()
                )

            with self.subTest("fixing vscode"):
                filepath.write_text(content)
                result = runner.invoke(
                    main, ["fix", "--diff", filepath.as_posix()], catch_exceptions=False
                )
                assert result.exit_code == 0
                assert any(
                    re.fullmatch(output_format_regex, line) for line in result.stdout.splitlines()
                )

            custom_output_format_regex = rf"{re.escape(filepath.name)}\|\d+\|\d+ use-f-string: .+"
            custom_output_format = "{path}|{start_line}|{start_col} {rule_name}: {message}"
            (self.tdp / "pyproject.toml").write_text(
                dedent(
                    f"""
                    [tool.rattle]
                    enable = ["use-f-string"]
                    output-format = 'custom'
                    output-template = '{custom_output_format}'
                    """
                )
            )

            with self.subTest("linting custom"):
                filepath.write_text(content)
                result = runner.invoke(main, ["lint", filepath.as_posix()], catch_exceptions=False)
                assert result.exit_code == 1
                assert any(
                    re.fullmatch(custom_output_format_regex, line)
                    for line in result.stdout.splitlines()
                )

            with self.subTest("fixing custom"):
                filepath.write_text(content)
                result = runner.invoke(
                    main, ["fix", "--diff", filepath.as_posix()], catch_exceptions=False
                )
                assert result.exit_code == 0
                assert any(
                    re.fullmatch(custom_output_format_regex, line)
                    for line in result.stdout.splitlines()
                )

            with self.subTest("per-file output-format"):
                nested = self.tdp / "nested"
                nested.mkdir()
                (self.tdp / "pyproject.toml").write_text(
                    dedent(
                        """
                        [tool.rattle]
                        enable = ["use-f-string"]
                        output-format = "vscode"
                        """
                    )
                )
                (nested / "pyproject.toml").write_text(
                    dedent(
                        """
                        [tool.rattle]
                        enable = ["use-f-string"]
                        output-format = "custom"
                        output-template = "CUSTOM {rule_name} {path}"
                        """
                    )
                )
                nested_file = nested / "nested_f_string.py"
                nested_file.write_text("name = '{name}'.format(name='Jane Doe')")

                result = runner.invoke(
                    main, ["lint", nested_file.as_posix()], catch_exceptions=False
                )
                assert re.search(r"CUSTOM use-f-string .*nested_f_string\.py", result.output)
