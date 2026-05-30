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

from rattle import config
from rattle.cli import main
from rattle.ftypes import (
    Config,
    Options,
    OutputFormat,
    QualifiedRule,
    RawConfig,
    RuleNameSelector,
    Tags,
    Version,
)
from rattle.rule import LintRule
from rattle.util import chdir

from .helpers import make_cli_runner


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
                disable = ["fixit"]
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
                disable = ["fixit"]
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
                    RawConfig(outer, {"enable": [".localrules"], "disable": ["fixit"]}),
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
                                    "disable": ["fixit"],
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
                    RawConfig(outer, {"enable": [".localrules"], "disable": ["fixit"]}),
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
                                    "disable": ["fixit"],
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
                                    "disable": ["fixit"],
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

    def test_config_merger(self) -> None:
        root = self.tdp
        target = root / "a" / "b" / "c" / "foo.py"

        params: Sequence[Tuple[str, List[RawConfig], Config]] = (
            (
                "empty",
                [],
                Config(
                    path=target,
                    root=Path(target.anchor),
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
                    enable=[QualifiedRule("foo")],
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
                    enable=[QualifiedRule("foo")],
                ),
            ),
            (
                "option merge",
                [
                    RawConfig(
                        (root / "a/b/c/pyproject.toml"),
                        {
                            "options": {
                                "rattle.rules.fixit_extra:UseFstring": {
                                    "allowed_prefixes": ["TODO", "FIXME"],
                                    "structured_entries": [
                                        {"symbol": "typing.cast", "message": "Avoid cast."}
                                    ],
                                }
                            }
                        },
                    ),
                    RawConfig(
                        (root / "a/b/pyproject.toml"),
                        {
                            "options": {
                                "rattle.rules.fixit_extra:UseFstring": {
                                    "simple_expression_max_length": 60
                                }
                            }
                        },
                    ),
                    RawConfig(
                        (root / "a/pyproject.toml"),
                        {
                            "options": {
                                "rattle.rules.fixit_extra:UseFstring": {
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
                        "rattle.rules.fixit_extra:UseFstring": {
                            "simple_expression_max_length": 60,
                            "allow_dot_format": False,
                            "allowed_prefixes": ["TODO", "FIXME"],
                            "structured_entries": [
                                {"symbol": "typing.cast", "message": "Avoid cast."}
                            ],
                        }
                    },
                ),
            ),
        )
        for name, raw_configs, expected in params:
            with self.subTest(name):
                actual = config.ConfigMerger(target, raw_configs).merge()
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

            actual = config.ConfigMerger(target, raw_configs).merge()

            assert actual == Config(
                path=target,
                root=root,
                enable=[QualifiedRule("foo")],
                disable=[QualifiedRule("bar")],
            )

        with self.subTest("rule name selectors"):
            raw_configs = [
                RawConfig(
                    (root / "pyproject.toml"),
                    {
                        "enable": ["UseFstring"],
                        "disable": ["NoStaticIfCondition"],
                    },
                )
            ]

            actual = config.ConfigMerger(target, raw_configs).merge()

            assert actual == Config(
                path=target,
                root=root,
                enable=[RuleNameSelector("UseFstring")],
                disable=[RuleNameSelector("NoStaticIfCondition")],
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
                        QualifiedRule("rattle.rules.SomethingSpecific"),
                        QualifiedRule("rattle.rules.fixit"),
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
                    disable=[QualifiedRule("rattle.rules.fixit")],
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
                        QualifiedRule("rattle.rules.SomethingSpecific"),
                        QualifiedRule("rattle.rules.fixit"),
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
                    enable=[QualifiedRule("more.rules")],
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
                    enable=[QualifiedRule("more.rules")],
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
                    enable=[QualifiedRule("bar")],
                    disable=[QualifiedRule("foo")],
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
                    enable = ["UseFstring"]
                    disable = ["NoStaticIfCondition"]

                    [tool.rattle.options]
                    "UseFstring" = {simple_expression_max_length = 42}
                    """
                )
            )

            actual = config.generate_config(path)

            assert asdict(
                Config(
                    path=path,
                    root=self.tdp,
                    enable=[RuleNameSelector("UseFstring")],
                    disable=[RuleNameSelector("NoStaticIfCondition")],
                    options={"UseFstring": {"simple_expression_max_length": 42}},
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

            with pytest.raises(
                config.ConfigError,
                match=r"unknown value 'this is some weird format'",
            ):
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

        with self.subTest("options support structured values"):
            (self.tdp / "pyproject.toml").write_text(
                dedent(
                    """
                    [tool.rattle]
                    root = true

                    [tool.rattle.options]
                    "rattle.rules.fixit_extra:UseFstring" = { structured_entries = [{symbol = "typing.cast", message = "Avoid cast."}] }
                    """
                )
            )

            actual = config.generate_config(self.tdp / "foo.py")
            assert actual.options["rattle.rules.fixit_extra:UseFstring"]["structured_entries"] == [
                {"symbol": "typing.cast", "message": "Avoid cast."}
            ]

        with self.subTest("options value must be TOML-shaped"):
            (self.tdp / "pyproject.toml").write_text(
                dedent(
                    """
                    [tool.rattle]
                    root = true

                    [tool.rattle.options]
                    "rattle.rules.fixit_extra:UseFstring" = { simple_expression_max_length = 1979-05-27 }
                    """
                )
            )

            with pytest.raises(config.ConfigError, match="TOML scalar, array, or table"):
                config.generate_config(self.tdp / "foo.py")

    def test_rule_registry_resolves_selectors(self) -> None:
        class AlphaRule(LintRule):
            pass

        class BetaRule(LintRule):
            pass

        registry = config.RuleRegistry()
        registry.register(BetaRule)
        registry.register(AlphaRule)

        alpha_resolution = registry.resolve(RuleNameSelector("AlphaRule"))
        assert alpha_resolution.rules == (AlphaRule,)
        assert alpha_resolution.concrete

        missing_selector = RuleNameSelector("DefinitelyMissingRule")
        with pytest.raises(
            config.CollectionError, match="could not find rule DefinitelyMissingRule"
        ):
            registry.resolve(missing_selector)

    def test_rule_registry_rejects_ambiguous_short_selector(self) -> None:
        first_rule = type("DuplicateRule", (LintRule,), {"__module__": "first.rules"})
        second_rule = type("DuplicateRule", (LintRule,), {"__module__": "second.rules"})

        registry = config.RuleRegistry()
        registry.register(first_rule)
        registry.register(second_rule)

        with pytest.raises(config.CollectionError, match="ambiguous rule name 'DuplicateRule'"):
            registry.resolve(RuleNameSelector("DuplicateRule"))

    def test_collect_rules(self) -> None:
        from rattle.rules.fixit.explicit_frozen_dataclass import ExplicitFrozenDataclass
        from rattle.rules.fixit.no_namedtuple import NoNamedTuple
        from rattle.rules.fixit.use_types_from_typing import UseTypesFromTyping
        from rattle.rules.fixit_extra.avoid_or_in_except import AvoidOrInExcept
        from rattle.rules.fixit_extra.cls_in_classmethod import UseClsInClassmethod
        from rattle.rules.fixit_extra.use_fstring import UseFstring

        AvoidOrInExcept.TAGS = {"exceptions"}
        UseTypesFromTyping.TAGS = {"typing"}
        NoNamedTuple.TAGS = {"typing", "tuples"}

        def collect_types(cfg: Config) -> List[Type[LintRule]]:
            return sorted([type(rule) for rule in config.collect_rules(cfg)], key=str)

        with self.subTest("empty config enables no rules"):
            rules = collect_types(
                Config(
                    python_version=None,
                )
            )
            assert [] == rules

        with self.subTest("fixit pack"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules.fixit")],
                    python_version=None,
                )
            )
            assert NoNamedTuple in rules
            assert UseTypesFromTyping in rules

        with self.subTest("opt-out"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules.fixit")],
                    disable=[QualifiedRule("rattle.rules.fixit", "NoNamedTuple")],
                    python_version=None,
                )
            )
            assert NoNamedTuple not in rules
            assert UseTypesFromTyping in rules

        with self.subTest("opt-in"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules.fixit_extra", "UseClsInClassmethod")],
                    python_version=None,
                )
            )
            assert [UseClsInClassmethod] == rules

        with self.subTest("opt-in by rule name"):
            rules = collect_types(
                Config(
                    enable=[RuleNameSelector("UseFstring")],
                    disable=[],
                    python_version=None,
                )
            )
            assert [UseFstring] == rules

        with self.subTest("module enable includes module rules"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules.fixit")],
                    disable=[],
                    python_version=None,
                )
            )
            assert NoNamedTuple in rules
            assert UseFstring not in rules

        with self.subTest("fixit_extra module enable includes Ruff-covered rules"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules.fixit_extra")],
                    disable=[],
                    python_version=None,
                )
            )
            assert UseFstring in rules
            assert ExplicitFrozenDataclass not in rules

        with self.subTest("disable builtins"):
            rules = collect_types(
                Config(
                    disable=[QualifiedRule("rattle.rules.fixit")],
                    python_version=None,
                )
            )
            assert [] == rules

        with self.subTest("override broad disable with rule name"):
            rules = collect_types(
                Config(
                    disable=[QualifiedRule("rattle.rules.fixit")],
                    enable=[RuleNameSelector("UseFstring")],
                    python_version=None,
                )
            )
            assert [UseFstring] == rules

        with self.subTest("local module rules can be disabled by unique rule name"):
            (self.tdp / "custom_rules.py").write_text(
                dedent(
                    """
                    from rattle import LintRule

                    class KeepRule(LintRule):
                        pass

                    class SkipRule(LintRule):
                        pass
                    """
                )
            )
            rules = collect_types(
                Config(
                    root=self.tdp,
                    enable_root_import=True,
                    enable=[QualifiedRule("custom_rules")],
                    disable=[RuleNameSelector("SkipRule")],
                    python_version=None,
                )
            )
            assert [rule.__name__ for rule in rules] == ["KeepRule"]

        with self.subTest("override broad opt-out"):
            rules = collect_types(
                Config(
                    disable=[QualifiedRule("rattle.rules.fixit")],
                    enable=[QualifiedRule("rattle.rules.fixit_extra", "UseClsInClassmethod")],
                )
            )
            assert [UseClsInClassmethod] == rules

        with self.subTest("version match"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules.fixit")],
                    python_version=Version("3.7.10"),
                )
            )
            assert UseTypesFromTyping in rules

        with self.subTest("version match alpha"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules.fixit")],
                    python_version=Version("3.7.10a3"),
                )
            )
            assert UseTypesFromTyping in rules

        with self.subTest("version mismatch"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules.fixit")],
                    python_version=Version("3.10.5"),
                )
            )
            assert UseTypesFromTyping not in rules

        with self.subTest("version mismatch alpha"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules.fixit")],
                    python_version=Version("3.10.5a4"),
                )
            )
            assert UseTypesFromTyping not in rules

        with self.subTest("tag select"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules.fixit")],
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
                    enable=[QualifiedRule("rattle.rules.fixit_extra")],
                    python_version=None,
                    tags=Tags.parse("^exceptions"),
                )
            )
            assert AvoidOrInExcept not in rules

        with self.subTest("tag select and filter"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules.fixit")],
                    python_version=None,
                    tags=Tags.parse("typing,^tuples"),
                )
            )
            assert [UseTypesFromTyping] == rules

        with self.subTest("rule settings apply"):
            (rule,) = config.collect_rules(
                Config(
                    enable=[RuleNameSelector("UseFstring")],
                    disable=[],
                    options={"UseFstring": {"simple_expression_max_length": 80}},
                    python_version=None,
                )
            )
            assert isinstance(rule, UseFstring)
            assert rule.settings["simple_expression_max_length"] == 80

        with self.subTest("rule settings apply by qualified name"):
            (rule,) = config.collect_rules(
                Config(
                    enable=[RuleNameSelector("UseFstring")],
                    disable=[],
                    options={
                        "rattle.rules.fixit_extra:UseFstring": {"simple_expression_max_length": 70}
                    },
                    python_version=None,
                )
            )
            assert isinstance(rule, UseFstring)
            assert rule.settings["simple_expression_max_length"] == 70

        with self.subTest("cached rule plan materializes fresh rule instances"):
            cfg = Config(
                enable=[RuleNameSelector("UseFstring")],
                disable=[],
                options={"UseFstring": {"simple_expression_max_length": 60}},
                python_version=None,
            )
            (first_rule,) = config.collect_rules(cfg)
            (second_rule,) = config.collect_rules(cfg)
            assert first_rule is not second_rule
            assert isinstance(second_rule, UseFstring)
            assert second_rule.settings["simple_expression_max_length"] == 60

        with (
            self.subTest("invalid rule setting name fails"),
            pytest.raises(ValueError, match="unknown setting"),
        ):
            config.collect_rules(
                Config(
                    enable=[QualifiedRule("rattle.rules.fixit_extra", "UseFstring")],
                    disable=[],
                    options={"rattle.rules.fixit_extra:UseFstring": {"not_a_setting": 80}},
                    python_version=None,
                )
            )

    def test_format_output(self) -> None:
        with chdir(self.tdp):
            (self.tdp / "pyproject.toml").write_text(
                dedent(
                    """
                    [tool.rattle]
                    enable = ["UseFstring"]
                    output-format = "vscode"
                    """
                )
            )

            runner = make_cli_runner()
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
                    enable = ["UseFstring"]
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
                    ["lint", "-o", "vscode", filepath.as_posix()],
                    catch_exceptions=True,
                )
                assert re.search(output_format_regex, result.output)

            with self.subTest("override output-template"):
                result = runner.invoke(
                    main,
                    [
                        "lint",
                        "--output-template",
                        "file {path} line {start_line} rule {rule_name}",
                        filepath.as_posix(),
                    ],
                    catch_exceptions=True,
                )
                assert re.search(r"file .*f_string\.py line \d+ rule UseFstring", result.output)

            with self.subTest("per-file output-format"):
                nested = self.tdp / "nested"
                nested.mkdir()
                (self.tdp / "pyproject.toml").write_text(
                    dedent(
                        """
                        [tool.rattle]
                        enable = ["UseFstring"]
                        output-format = "vscode"
                        """
                    )
                )
                (nested / "pyproject.toml").write_text(
                    dedent(
                        """
                        [tool.rattle]
                        enable = ["UseFstring"]
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
                assert re.search(r"CUSTOM UseFstring .*nested_f_string\.py", result.output)

    def test_validate_config(self) -> None:
        with self.subTest("validate-config valid"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                    [tool.rattle]
                    disable = ["fixit"]
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
                    "rattle.rules.fixit_extra.use_fstring:UseFstring" = {simple_expression_max_length = 42}
                    """
            )

            results = config.validate_config(path)

            assert results == []

        with (
            self.subTest("validate-config valid with structured options"),
            TemporaryDirectory() as td,
        ):
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            (tdp / "structured_rule.py").write_text(
                dedent(
                    """
                from rattle import LintRule, RuleSetting

                class StructuredRule(LintRule):
                    SETTINGS = {
                        "entries": RuleSetting(list[dict[str, str]], default=[]),
                    }
                """
                )
            )
            path.write_text(
                """
                [tool.rattle]
                root = true
                enable = [".structured_rule:StructuredRule"]

                [tool.rattle.options.".structured_rule:StructuredRule"]
                entries = [
                    {symbol = "typing.cast", message = "Avoid cast."},
                    {symbol = "typing_extensions.cast", message = "Avoid cast."},
                ]
                """
            )

            results = config.validate_config(path)

            assert results == []

        with self.subTest("validate-config valid with rule names"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true
                enable = ["UseFstring"]
                disable = ["NoStaticIfCondition"]
                per-file-enable = {"tests/**/*.py" = ["UseFstring"]}

                [tool.rattle.options]
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
            self.subTest("validate-config invalid options unknown rule name"),
            TemporaryDirectory() as td,
        ):
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true

                [tool.rattle.options]
                "DefinitelyMissingRule" = {simple_expression_max_length = 42}
                """
            )

            results = config.validate_config(path)

            assert any("could not find rule DefinitelyMissingRule" in result for result in results)

        with self.subTest("validate-config invalid options value"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true

                [tool.rattle.options]
                "rattle.rules.fixit_extra.use_fstring:UseFstring" = {simple_expression_max_length = "long"}
                """
            )

            results = config.validate_config(path)

            assert any(
                "Failed to validate options for `rattle.rules.fixit_extra.use_fstring:UseFstring`"
                in result
                for result in results
            )

        with self.subTest("validate-config invalid unknown rule name"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true
                enable = ["DefinitelyMissingRule"]
                """
            )

            results = config.validate_config(path)

            assert results == [
                "Failed to import rule `DefinitelyMissingRule` for global enable: CollectionError: could not find rule DefinitelyMissingRule"
            ]

        with self.subTest("validate-config valid with per-file tables"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true
                per-file-enable = {"tests/**/*.py" = ["rattle.rules.fixit_extra:UseFstring"]}
                per-file-disable = {"tests/generated.py" = ["rattle.rules.fixit_extra:UseFstring"]}
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
                per-file-enable = {"tests/**/*.py" = "rattle.rules.fixit_extra:UseFstring"}
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

        with self.subTest("validate-config invalid exclude"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true
                exclude = "build"
                """
            )

            results = config.validate_config(path)

            assert results == [
                "Failed to parse exclude: ConfigError: 'exclude' must be array of values, got <class 'str'>"
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
                disable = ["fixit"]
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

                [tool.rattle.overrides.options."rattle.rules.fixit_extra.use_fstring:UseFstring"]
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
                "rattle.rules.fixit_extra.use_fstring:UseFstring" = {simple_expression_max_length = 52}
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
                disable = ["fixit"]
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
                disable = ["fixit"]
                root = true

                [[tool.rattle.overrides]]
                path = "SUPER_REAL_PATH"
                enable = ["rattle.rules.fixit_extra:DeprecatedABCImport_SUPER_REAL"]
                """
            )

            path = tdp / "file.py"
            path.write_text("error")

            results = config.validate_config(config_path)

            assert results == [
                "Failed to parse rule `rattle/rules:DeprecatedABCImport` for global enable: ConfigError: invalid rule name 'rattle/rules:DeprecatedABCImport'",
                "Failed to import rule `rattle.rules.fixit_extra:DeprecatedABCImport_SUPER_REAL` for override enable: `SUPER_REAL_PATH`: CollectionError: could not find rule rattle.rules.fixit_extra:DeprecatedABCImport_SUPER_REAL",
            ]
