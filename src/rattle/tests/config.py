# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import re
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import List, Sequence, Tuple, Type
from unittest import TestCase

import pytest
from click.testing import CliRunner

from rattle import config
from rattle.cli import main
from rattle.ftypes import (
    AliasSelector,
    CodeSelector,
    Config,
    Options,
    OutputFormat,
    QualifiedRule,
    RawConfig,
    Tags,
    Version,
)
from rattle.rule import LintRule
from rattle.util import chdir


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
                disable = ["rattle.rules.SomethingSpecific"]
                python-version = "3.8"

                [[tool.rattle.overrides]]
                path = "other"
                enable = ["other.stuff", ".globalrules"]
                disable = ["rattle.rules"]
                options = {"other.stuff:Whatever"={key="value"}}
                python-version = "3.10"
                """
            )
        )
        (self.outer / "pyproject.toml").write_text(
            dedent(
                """
                [tool.rattle]
                enable = [".localrules"]
                disable = ["rattle.rules"]
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

    def test_locate_configs(self) -> None:
        for name, path, root, expected in (
            ("top", self.tdp, None, [self.tdp / "pyproject.toml"]),
            ("top file", self.tdp / "hello.py", None, [self.tdp / "pyproject.toml"]),
            (
                "outer",
                self.outer,
                None,
                [self.outer / "pyproject.toml", self.tdp / "pyproject.toml"],
            ),
            (
                "outer file",
                self.outer / "frob.py",
                None,
                [self.outer / "pyproject.toml", self.tdp / "pyproject.toml"],
            ),
            (
                "inner",
                self.inner,
                None,
                [
                    self.inner / "pyproject.toml",
                    self.outer / "pyproject.toml",
                    self.tdp / "pyproject.toml",
                ],
            ),
            (
                "inner file",
                self.inner / "test.py",
                None,
                [
                    self.inner / "pyproject.toml",
                    self.outer / "pyproject.toml",
                    self.tdp / "pyproject.toml",
                ],
            ),
            ("outer from outer", self.outer, self.outer, [self.outer / "pyproject.toml"]),
            (
                "inner from outer",
                self.inner,
                self.outer,
                [
                    self.inner / "pyproject.toml",
                    self.outer / "pyproject.toml",
                ],
            ),
            (
                "inner from inner",
                self.inner,
                self.inner,
                [self.inner / "pyproject.toml"],
            ),
        ):
            with self.subTest(name):
                actual = config.locate_configs(path, root)
                assert expected == actual

    def test_read_configs(self) -> None:
        # in-out priority order
        inner = self.inner / "pyproject.toml"
        noise = self.noise / "pyproject.toml"
        outer = self.outer / "pyproject.toml"
        top = self.tdp / "pyproject.toml"

        for name, paths, expected in (
            (
                "inner",
                [inner, noise, outer, top],
                [
                    RawConfig(
                        inner,
                        {
                            "root": True,
                            "enable": ["fake8", "make8"],
                            "disable": ["foo.bar"],
                            "unknown": "hello",
                        },
                    )
                ],
            ),
            (
                "inner partial",
                [noise, outer, top],
                [
                    RawConfig(outer, {"enable": [".localrules"], "disable": ["rattle.rules"]}),
                    RawConfig(
                        top,
                        {
                            "root": True,
                            "enable-root-import": True,
                            "enable": ["more.rules"],
                            "disable": ["rattle.rules.SomethingSpecific"],
                            "python-version": "3.8",
                            "overrides": [
                                {
                                    "path": "other",
                                    "enable": ["other.stuff", ".globalrules"],
                                    "disable": ["rattle.rules"],
                                    "options": {"other.stuff:Whatever": {"key": "value"}},
                                    "python-version": "3.10",
                                },
                            ],
                        },
                    ),
                ],
            ),
            (
                "outer",
                [outer, top],
                [
                    RawConfig(outer, {"enable": [".localrules"], "disable": ["rattle.rules"]}),
                    RawConfig(
                        top,
                        {
                            "root": True,
                            "enable-root-import": True,
                            "enable": ["more.rules"],
                            "disable": ["rattle.rules.SomethingSpecific"],
                            "python-version": "3.8",
                            "overrides": [
                                {
                                    "path": "other",
                                    "enable": ["other.stuff", ".globalrules"],
                                    "disable": ["rattle.rules"],
                                    "options": {"other.stuff:Whatever": {"key": "value"}},
                                    "python-version": "3.10",
                                },
                            ],
                        },
                    ),
                ],
            ),
            (
                "top",
                [top],
                [
                    RawConfig(
                        top,
                        {
                            "root": True,
                            "enable-root-import": True,
                            "enable": ["more.rules"],
                            "disable": ["rattle.rules.SomethingSpecific"],
                            "python-version": "3.8",
                            "overrides": [
                                {
                                    "path": "other",
                                    "enable": ["other.stuff", ".globalrules"],
                                    "disable": ["rattle.rules"],
                                    "options": {"other.stuff:Whatever": {"key": "value"}},
                                    "python-version": "3.10",
                                },
                            ],
                        },
                    ),
                ],
            ),
        ):
            with self.subTest(name):
                actual = config.read_configs(paths)
                assert expected == actual

    def test_merge_configs(self) -> None:
        root = self.tdp
        target = root / "a" / "b" / "c" / "foo.py"

        params: Sequence[Tuple[str, List[RawConfig], Config]] = (
            (
                "empty",
                [],
                Config(
                    path=target,
                    root=Path(target.anchor),
                    enable=[QualifiedRule("rattle.rules")],
                ),
            ),
            (
                "single",
                [
                    RawConfig(
                        (root / "pyproject.toml"),
                        {
                            "enable": ["foo", "bar"],
                            "disable": ["bar"],
                        },
                    ),
                ],
                Config(
                    path=target,
                    root=root,
                    enable=[QualifiedRule("foo"), QualifiedRule("rattle.rules")],
                    disable=[QualifiedRule("bar")],
                ),
            ),
            (
                "without root",
                [
                    RawConfig(
                        (root / "a/b/c/pyproject.toml"),
                        {"enable": ["foo"], "python-version": "3.10"},
                    ),
                    RawConfig(
                        (root / "a/b/pyproject.toml"),
                        {"enable": ["bar"], "disable": ["foo"]},
                    ),
                    RawConfig(
                        (root / "a/pyproject.toml"),
                        {"enable": ["foo"], "python-version": "3.8"},
                    ),
                ],
                Config(
                    path=target,
                    root=(root / "a"),
                    enable=[
                        QualifiedRule("bar"),
                        QualifiedRule("foo"),
                        QualifiedRule("rattle.rules"),
                    ],
                    python_version=Version("3.10"),
                ),
            ),
            (
                "with root",
                [
                    RawConfig(
                        (root / "a/b/c/pyproject.toml"),
                        {"enable": ["foo"], "root": True},
                    ),
                    RawConfig(
                        (root / "a/b/pyproject.toml"),
                        {},
                    ),
                    RawConfig(
                        (root / "a/pyproject.toml"),
                        {},
                    ),
                ],
                Config(
                    path=target,
                    root=(root / "a/b/c"),
                    enable=[QualifiedRule("foo"), QualifiedRule("rattle.rules")],
                ),
            ),
            (
                "option merge",
                [
                    RawConfig(
                        (root / "a/b/c/pyproject.toml"),
                        {
                            "options": {
                                "rattle.rules:UseFstring": {"allowed_prefixes": ["TODO", "FIXME"]}
                            }
                        },
                    ),
                    RawConfig(
                        (root / "a/b/pyproject.toml"),
                        {
                            "options": {
                                "rattle.rules:UseFstring": {"simple_expression_max_length": 60}
                            }
                        },
                    ),
                    RawConfig(
                        (root / "a/pyproject.toml"),
                        {
                            "options": {
                                "rattle.rules:UseFstring": {
                                    "simple_expression_max_length": 30,
                                    "allow_dot_format": False,
                                }
                            }
                        },
                    ),
                ],
                Config(
                    path=target,
                    root=(root / "a"),
                    options={
                        "rattle.rules:UseFstring": {
                            "simple_expression_max_length": 60,
                            "allow_dot_format": False,
                            "allowed_prefixes": ["TODO", "FIXME"],
                        }
                    },
                ),
            ),
        )
        for name, raw_configs, expected in params:
            with self.subTest(name):
                actual = config.merge_configs(target, raw_configs)
                assert expected == actual

        with self.subTest("per-file rule toggles"):
            target = root / "tests" / "unit" / "special.py"
            raw_configs = [
                RawConfig(
                    (root / "pyproject.toml"),
                    {
                        "enable": ["bar"],
                        "overrides": [{"path": "tests", "disable": ["bar", "foo"]}],
                        "per-file-enable": {"tests/unit/special.py": ["foo"]},
                        "per-file-disable": {"tests/**/*.py": ["bar"]},
                    },
                )
            ]

            actual = config.merge_configs(target, raw_configs)

            assert actual == Config(
                path=target,
                root=root,
                enable=[QualifiedRule("foo"), QualifiedRule("rattle.rules")],
                disable=[QualifiedRule("bar")],
            )

        with self.subTest("short selectors"):
            raw_configs = [
                RawConfig(
                    (root / "pyproject.toml"),
                    {
                        "enable": ["UseFstring"],
                        "disable": ["RAT"],
                    },
                )
            ]

            actual = config.merge_configs(target, raw_configs)

            assert actual == Config(
                path=target,
                root=root,
                enable=[AliasSelector("UseFstring"), QualifiedRule("rattle.rules")],
                disable=[CodeSelector("RAT")],
            )

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
                        QualifiedRule("fake8"),
                        QualifiedRule("make8"),
                        QualifiedRule("rattle.rules"),
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
                        QualifiedRule("rattle.rules"),
                        QualifiedRule("rattle.rules.SomethingSpecific"),
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
                    disable=[QualifiedRule("rattle.rules")],
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
                        QualifiedRule("rattle.rules"),
                        QualifiedRule("rattle.rules.SomethingSpecific"),
                    ],
                    options={"other.stuff:Whatever": {"key": "value"}},
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
                    enable=[QualifiedRule("more.rules"), QualifiedRule("rattle.rules")],
                    disable=[QualifiedRule("rattle.rules.SomethingSpecific")],
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
                    enable=[QualifiedRule("more.rules"), QualifiedRule("rattle.rules")],
                    disable=[QualifiedRule("rattle.rules.SomethingSpecific")],
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
                    enable=[QualifiedRule("bar"), QualifiedRule("rattle.rules")],
                    disable=[QualifiedRule("foo")],
                )
            ) == asdict(actual)

        with self.subTest("short selectors and exact option targets"):
            path = self.tdp / "short_selectors.py"
            path.write_text("pass\n")
            (self.tdp / "pyproject.toml").write_text(
                dedent(
                    """
                    [tool.rattle]
                    root = true
                    enable = ["UseFstring"]
                    disable = ["RAT"]

                    [tool.rattle.options]
                    "RAT024" = {simple_expression_max_length = 42}
                    """
                )
            )

            actual = config.generate_config(path)

            assert asdict(
                Config(
                    path=path,
                    root=self.tdp,
                    enable=[AliasSelector("UseFstring"), QualifiedRule("rattle.rules")],
                    disable=[CodeSelector("RAT")],
                    options={"RAT024": {"simple_expression_max_length": 42}},
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

    def test_invalid_config(self) -> None:
        with self.subTest("inner enable-root-import"):
            (self.tdp / "pyproject.toml").write_text("[tool.rattle]\nroot = true\n")
            (self.tdp / "outer" / "pyproject.toml").write_text(
                "[tool.rattle]\nenable-root-import = true\n"
            )

            with pytest.raises(config.ConfigError, match="enable-root-import"):
                config.generate_config(self.tdp / "outer" / "foo.py")

        with self.subTest("inner output-format"):
            (self.tdp / "pyproject.toml").write_text("[tool.rattle]\nroot = true\n")
            (self.tdp / "outer" / "pyproject.toml").write_text(
                "[tool.rattle]\noutput-format = 'this is some weird format'\n"
            )

            with pytest.raises(config.ConfigError, match="output-format"):
                config.generate_config(self.tdp / "outer" / "foo.py")

        with self.subTest("options require concrete rule"):
            (self.tdp / "pyproject.toml").write_text(
                dedent(
                    """
                    [tool.rattle]
                    root = true

                    [tool.rattle.options]
                    "rattle.rules" = {foo = 1}
                    """
                )
            )

            with pytest.raises(config.ConfigError, match="module:ClassName"):
                config.generate_config(self.tdp / "foo.py")

        with self.subTest("options value must be scalar or scalar array"):
            (self.tdp / "pyproject.toml").write_text(
                dedent(
                    """
                    [tool.rattle]
                    root = true

                    [tool.rattle.options]
                    "rattle.rules:UseFstring" = { simple_expression_max_length = { nested = true } }
                    """
                )
            )

            with pytest.raises(config.ConfigError, match="TOML scalar or array of scalars"):
                config.generate_config(self.tdp / "foo.py")

    def test_collect_rules(self) -> None:
        from rattle.rules.avoid_or_in_except import AvoidOrInExcept
        from rattle.rules.cls_in_classmethod import UseClsInClassmethod
        from rattle.rules.extra.explicit_frozen_dataclass import ExplicitFrozenDataclass
        from rattle.rules.no_namedtuple import NoNamedTuple
        from rattle.rules.use_fstring import UseFstring
        from rattle.rules.use_types_from_typing import UseTypesFromTyping

        AvoidOrInExcept.TAGS = {"exceptions"}
        UseTypesFromTyping.TAGS = {"typing"}
        NoNamedTuple.TAGS = {"typing", "tuples"}

        def collect_types(cfg: Config) -> List[Type[LintRule]]:
            return sorted([type(rule) for rule in config.collect_rules(cfg)], key=str)

        with self.subTest("everything"):
            rules = collect_types(
                Config(
                    python_version=None,
                )
            )
            assert UseClsInClassmethod in rules
            assert UseTypesFromTyping in rules

        with self.subTest("opt-out"):
            rules = collect_types(
                Config(
                    disable=[QualifiedRule("rattle.rules", "UseClsInClassmethod")],
                    python_version=None,
                )
            )
            assert UseClsInClassmethod not in rules
            assert UseTypesFromTyping in rules

        with self.subTest("opt-in"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules", "UseClsInClassmethod")],
                    python_version=None,
                )
            )
            assert [UseClsInClassmethod] == rules

        with self.subTest("opt-in by code"):
            rules = collect_types(
                Config(
                    enable=[CodeSelector("RAT024")],
                    disable=[],
                    python_version=None,
                )
            )
            assert [UseFstring] == rules

        with self.subTest("opt-in by alias"):
            rules = collect_types(
                Config(
                    enable=[AliasSelector("UseFstring")],
                    disable=[],
                    python_version=None,
                )
            )
            assert [UseFstring] == rules

        with self.subTest("prefix enable includes builtins family"):
            rules = collect_types(
                Config(
                    enable=[CodeSelector("RAT")],
                    disable=[],
                    python_version=None,
                )
            )
            assert UseFstring in rules
            assert ExplicitFrozenDataclass in rules

        with self.subTest("disable builtins"):
            rules = collect_types(
                Config(
                    disable=[QualifiedRule("rattle.rules")],
                    python_version=None,
                )
            )
            assert [] == rules

        with self.subTest("override broad disable with exact code"):
            rules = collect_types(
                Config(
                    disable=[CodeSelector("RAT")],
                    enable=[CodeSelector("RAT024")],
                    python_version=None,
                )
            )
            assert [UseFstring] == rules

        with self.subTest("override broad disable with alias"):
            rules = collect_types(
                Config(
                    disable=[QualifiedRule("rattle.rules")],
                    enable=[AliasSelector("UseFstring")],
                    python_version=None,
                )
            )
            assert [UseFstring] == rules

        with self.subTest("override broad opt-out"):
            rules = collect_types(
                Config(
                    disable=[QualifiedRule("rattle.rules")],
                    enable=[QualifiedRule("rattle.rules", "UseClsInClassmethod")],
                )
            )
            assert [UseClsInClassmethod] == rules

        with self.subTest("version match"):
            rules = collect_types(
                Config(
                    python_version=Version("3.7.10"),
                )
            )
            assert UseTypesFromTyping in rules

        with self.subTest("version match alpha"):
            rules = collect_types(
                Config(
                    python_version=Version("3.7.10a3"),
                )
            )
            assert UseTypesFromTyping in rules

        with self.subTest("version mismatch"):
            rules = collect_types(
                Config(
                    python_version=Version("3.10.5"),
                )
            )
            assert UseTypesFromTyping not in rules

        with self.subTest("version mismatch alpha"):
            rules = collect_types(
                Config(
                    python_version=Version("3.10.5a4"),
                )
            )
            assert UseTypesFromTyping not in rules

        with self.subTest("tag select"):
            rules = collect_types(
                Config(
                    python_version=None,
                    tags=Tags.parse("typing"),
                )
            )
            assert [
                NoNamedTuple,
                UseTypesFromTyping,
            ] == rules

        with self.subTest("tag filter"):
            rules = collect_types(
                Config(
                    python_version=None,
                    tags=Tags.parse("^exceptions"),
                )
            )
            assert AvoidOrInExcept not in rules

        with self.subTest("tag select and filter"):
            rules = collect_types(
                Config(
                    python_version=None,
                    tags=Tags.parse("typing,^tuples"),
                )
            )
            assert [UseTypesFromTyping] == rules

        with self.subTest("rule settings apply"):
            (rule,) = config.collect_rules(
                Config(
                    enable=[CodeSelector("RAT024")],
                    disable=[],
                    options={"RAT024": {"simple_expression_max_length": 80}},
                    python_version=None,
                )
            )
            assert isinstance(rule, UseFstring)
            assert rule.settings["simple_expression_max_length"] == 80

        with self.subTest("rule settings apply by alias"):
            (rule,) = config.collect_rules(
                Config(
                    enable=[AliasSelector("UseFstring")],
                    disable=[],
                    options={"UseFstring": {"simple_expression_max_length": 70}},
                    python_version=None,
                )
            )
            assert isinstance(rule, UseFstring)
            assert rule.settings["simple_expression_max_length"] == 70

        with (
            self.subTest("invalid rule setting name fails"),
            pytest.raises(ValueError, match="unknown setting"),
        ):
            config.collect_rules(
                Config(
                    enable=[QualifiedRule("rattle.rules", "UseFstring")],
                    disable=[],
                    options={"rattle.rules:UseFstring": {"not_a_setting": 80}},
                    python_version=None,
                )
            )

    def test_format_output(self) -> None:
        with chdir(self.tdp):
            (self.tdp / "pyproject.toml").write_text(
                dedent(
                    """
                    [tool.rattle]
                    output-format = "vscode"
                    """
                )
            )

            runner = CliRunner(mix_stderr=False)
            content = "name = '{name}'.format(name='Jane Doe')"
            filepath = self.tdp / "f_string.py"
            filepath.write_text(content)
            output_format_regex = r".*f_string\.py:\d+:\d+ UseFstring: .+"

            with self.subTest("linting vscode"):
                result = runner.invoke(main, ["lint", filepath.as_posix()], catch_exceptions=False)
                assert re.search(output_format_regex, result.output)

            with self.subTest("fixing vscode"):
                result = runner.invoke(main, ["fix", filepath.as_posix()], catch_exceptions=False)
                assert re.search(output_format_regex, result.output)

            custom_output_format_regex = r".*f_string\.py|\d+|\d+ UseFstring: .+"
            custom_output_format = "{path}|{start_line}|{start_col} {rule_name}: {message}"
            (self.tdp / "pyproject.toml").write_text(
                dedent(
                    f"""
                    [tool.rattle]
                    output-format = 'custom'
                    output-template = '{custom_output_format}'
                    """
                )
            )

            with self.subTest("linting custom"):
                result = runner.invoke(main, ["lint", filepath.as_posix()], catch_exceptions=False)
                assert re.search(custom_output_format_regex, result.output)

            with self.subTest("fixing custom"):
                result = runner.invoke(main, ["fix", filepath.as_posix()], catch_exceptions=False)
                assert re.search(custom_output_format_regex, result.output)

            with self.subTest("override output-format"):
                result = runner.invoke(
                    main,
                    ["--output-format", "vscode", "lint", filepath.as_posix()],
                    catch_exceptions=True,
                )
                assert re.search(output_format_regex, result.output)

            with self.subTest("override output-template"):
                result = runner.invoke(
                    main,
                    [
                        "--output-template",
                        "file {path} line {start_line} rule {rule_name}",
                        "lint",
                        filepath.as_posix(),
                    ],
                    catch_exceptions=True,
                )
                assert re.search(r"file .*f_string\.py line \d+ rule UseFstring", result.output)

    def test_validate_config(self) -> None:
        with self.subTest("validate-config valid"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                    [tool.rattle]
                    disable = ["rattle.rules"]
                    root = true
                    """
            )

            results = config.validate_config(path)

            assert results == []

        with self.subTest("validate-config valid with options"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                    [tool.rattle]
                    root = true

                    [tool.rattle.options]
                    "rattle.rules.use_fstring:UseFstring" = {simple_expression_max_length = 42}
                    """
            )

            results = config.validate_config(path)

            assert results == []

        with self.subTest("validate-config valid with short selectors"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true
                enable = ["UseFstring"]
                disable = ["RAT014"]
                per-file-enable = {"tests/**/*.py" = ["RAT024"]}

                [tool.rattle.options]
                "RAT024" = {simple_expression_max_length = 42}
                "UseFstring" = {simple_expression_max_length = 64}
                """
            )

            results = config.validate_config(path)

            assert results == []

        with self.subTest("validate-config invalid options key"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true

                [tool.rattle.options]
                "rattle.rules" = {simple_expression_max_length = 42}
                """
            )

            results = config.validate_config(path)

            assert any("Failed to parse options for global options" in result for result in results)

        with (
            self.subTest("validate-config invalid options prefix code"),
            TemporaryDirectory() as td,
        ):
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true

                [tool.rattle.options]
                "RAT" = {simple_expression_max_length = 42}
                """
            )

            results = config.validate_config(path)

            assert any("exact code or alias" in result for result in results)

        with self.subTest("validate-config invalid options value"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true

                [tool.rattle.options]
                "rattle.rules.use_fstring:UseFstring" = {simple_expression_max_length = "long"}
                """
            )

            results = config.validate_config(path)

            assert any(
                "Failed to validate options for `rattle.rules.use_fstring:UseFstring`" in result
                for result in results
            )

        with self.subTest("validate-config invalid unknown code"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true
                enable = ["RAT999"]
                """
            )

            results = config.validate_config(path)

            assert results == [
                "Failed to import rule `RAT999` for global enable: CollectionError: could not find rule RAT999"
            ]

        with self.subTest("validate-config valid with per-file tables"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true
                per-file-enable = {"tests/**/*.py" = ["rattle.rules:UseFstring"]}
                per-file-disable = {"tests/generated.py" = ["rattle.rules:UseFstring"]}
                """
            )

            results = config.validate_config(path)

            assert results == []

        with self.subTest("validate-config invalid per-file table"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true
                per-file-enable = {"tests/**/*.py" = "rattle.rules:UseFstring"}
                """
            )

            results = config.validate_config(path)

            assert results == [
                "Failed to parse per-file-enable: ConfigError: 'per-file-enable' value for 'tests/**/*.py' must be array of values, got <class 'str'>"
            ]

        with self.subTest("validate-config invalid inherit-ruff-files"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true
                inherit-ruff-files = "yes"
                """
            )

            results = config.validate_config(path)

            assert results == [
                "Failed to parse inherit-ruff-files: ConfigError: 'inherit-ruff-files' must be a boolean"
            ]

    def test_validate_config_with_override(self) -> None:
        with self.subTest("validate-config valid with overrides"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            (tdp / "rule/ruledir").mkdir(parents=True, exist_ok=True)

            (tdp / "rule/rule.py").write_text("# Rule")
            (tdp / "rule/ruledir/rule.py").write_text("# Rule")
            path.write_text(
                """
                [tool.rattle]
                disable = ["rattle.rules"]
                root = true

                [[tool.rattle.overrides]]
                path = "SUPER_REAL_PATH"
                enable = [".rule.rule"]

                [[tool.rattle.overrides]]
                path = "SUPER_REAL_PATH/BUT_ACTUALLY_REAL"
                enable = [".rule.ruledir.rule"]
                """
            )

            results = config.validate_config(path)

            assert results == []

        with self.subTest("validate-config valid override options"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true

                [[tool.rattle.overrides]]
                path = "SUPER_REAL_PATH"

                [tool.rattle.overrides.options."rattle.rules.use_fstring:UseFstring"]
                simple_expression_max_length = 52
                """
            )

            results = config.validate_config(path)

            assert results == []

        with (
            self.subTest("validate-config valid override options legacy table"),
            TemporaryDirectory() as td,
        ):
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true

                [[tool.rattle.overrides]]
                path = "SUPER_REAL_PATH"

                [[tool.rattle.overrides.options]]
                "rattle.rules.use_fstring:UseFstring" = {simple_expression_max_length = 52}
                """
            )

            results = config.validate_config(path)

            assert results == []

        with self.subTest("validate-config invalid config"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                enable = ["rattle/rules:DeprecatedABCImport"]
                disable = ["rattle.rules"]
                root = true
                """
            )

            results = config.validate_config(path)

            assert results == [
                "Failed to parse rule `rattle/rules:DeprecatedABCImport` for global enable: ConfigError: invalid rule name 'rattle/rules:DeprecatedABCImport'"
            ]

        with self.subTest("validate-config multiple errors"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            config_path = tdp / "pyproject.toml"
            config_path.write_text(
                """
                [tool.rattle]
                enable = ["rattle/rules:DeprecatedABCImport"]
                disable = ["rattle.rules"]
                root = true

                [[tool.rattle.overrides]]
                path = "SUPER_REAL_PATH"
                enable = ["rattle.rules:DeprecatedABCImport_SUPER_REAL"]
                """
            )

            path = tdp / "file.py"
            path.write_text("error")

            results = config.validate_config(config_path)

            assert results == [
                "Failed to parse rule `rattle/rules:DeprecatedABCImport` for global enable: ConfigError: invalid rule name 'rattle/rules:DeprecatedABCImport'",
                "Failed to import rule `rattle.rules:DeprecatedABCImport_SUPER_REAL` for override enable: `SUPER_REAL_PATH`: CollectionError: could not find rule rattle.rules:DeprecatedABCImport_SUPER_REAL",
            ]
