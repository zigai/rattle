# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest import TestCase
from unittest.mock import patch

import pytest
from packaging.version import Version

from rattle import config, rule_loading
from rattle.config.models import Config
from rattle.rule import LintRule
from rattle.selectors import QualifiedRule, RuleNameSelector, Tags


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

    def test_rule_registry_resolves_selectors(self) -> None:
        class AlphaRule(LintRule):
            pass

        class BetaRule(LintRule):
            pass

        registry = config.RuleRegistry()
        registry.register(BetaRule)
        registry.register(AlphaRule)

        alpha_resolution = registry.resolve(RuleNameSelector("alpha-rule"))
        assert alpha_resolution.rules == (AlphaRule,)
        assert alpha_resolution.concrete

        with pytest.raises(config.CollectionError, match="could not find rule alpha"):
            registry.resolve(RuleNameSelector("alpha"))

        beta_resolution = registry.resolve(RuleNameSelector("beta-rule"))
        assert beta_resolution.rules == (BetaRule,)
        assert beta_resolution.concrete

        missing_selector = RuleNameSelector("definitely-missing-rule")
        with pytest.raises(
            config.CollectionError, match="could not find rule definitely-missing-rule"
        ):
            registry.resolve(missing_selector)

    def test_rule_registry_resolves_canonical_name(self) -> None:
        class Gamma(LintRule):
            pass

        registry = config.RuleRegistry()
        registry.register(Gamma)

        gamma_resolution = registry.resolve(RuleNameSelector("gamma"))
        assert gamma_resolution.rules == (Gamma,)
        assert gamma_resolution.concrete

    def test_parse_rule_accepts_blank_lines_collection(self) -> None:
        assert config.parse_rule("blank-lines", self.tdp) == QualifiedRule(
            "rattle.rules.blank_lines"
        )

    def test_rule_registry_rejects_ambiguous_short_selector(self) -> None:
        first_rule = type("DuplicateRule", (LintRule,), {"__module__": "first.rules"})
        second_rule = type("DuplicateRule", (LintRule,), {"__module__": "second.rules"})

        registry = config.RuleRegistry()
        registry.register(first_rule)
        registry.register(second_rule)

        with pytest.raises(config.CollectionError, match="ambiguous rule name 'duplicate-rule'"):
            registry.resolve(RuleNameSelector("duplicate-rule"))

    def test_collect_rules(self) -> None:
        from rattle.rules.legacy.avoid_or_in_except import AvoidOrInExcept
        from rattle.rules.legacy.cls_in_classmethod import UseClsInClassmethod
        from rattle.rules.legacy.use_fstring import UseFstring
        from rattle.rules.modernization.explicit_frozen_dataclass import ExplicitFrozenDataclass
        from rattle.rules.modernization.no_named_tuple import NoNamedTuple
        from rattle.rules.typing.use_types_from_typing import UseTypesFromTyping

        for patcher in (
            patch.object(AvoidOrInExcept, "TAGS", {"exceptions"}),
            patch.object(UseTypesFromTyping, "TAGS", {"typing"}),
            patch.object(NoNamedTuple, "TAGS", {"typing", "tuples"}),
            patch.object(rule_loading, "_rule_plan_cache", {}),
        ):
            self.addCleanup(patcher.stop)
            patcher.start()

        def collect_types(cfg: Config) -> list[type[LintRule]]:
            return sorted([type(rule) for rule in config.collect_rules(cfg)], key=str)

        with self.subTest("empty config enables no rules"):
            rules = collect_types(
                Config(
                    python_version=None,
                )
            )
            assert [] == rules

        with self.subTest("modernization collection"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules.modernization")],
                    python_version=None,
                )
            )
            assert NoNamedTuple in rules

        with self.subTest("opt-out"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules.modernization")],
                    disable=[QualifiedRule("rattle.rules.modernization", "no-named-tuple")],
                    python_version=None,
                )
            )
            assert NoNamedTuple not in rules

        with self.subTest("opt-in"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules.legacy", "use-cls-in-classmethod")],
                    python_version=None,
                )
            )
            assert [UseClsInClassmethod] == rules

        with self.subTest("opt-in by rule name"):
            rules = collect_types(
                Config(
                    enable=[RuleNameSelector("use-f-string")],
                    disable=[],
                    python_version=None,
                )
            )
            assert [UseFstring] == rules

        with self.subTest("module enable includes module rules"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules.modernization")],
                    disable=[],
                    python_version=None,
                )
            )
            assert NoNamedTuple in rules
            assert UseFstring not in rules

        with self.subTest("legacy module enable includes Ruff-covered rules"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules.legacy")],
                    disable=[],
                    python_version=None,
                )
            )
            assert UseFstring in rules
            assert ExplicitFrozenDataclass not in rules

        with self.subTest("disable builtins"):
            rules = collect_types(
                Config(
                    disable=[QualifiedRule("rattle.rules.modernization")],
                    python_version=None,
                )
            )
            assert [] == rules

        with self.subTest("override broad disable with rule name"):
            rules = collect_types(
                Config(
                    disable=[QualifiedRule("rattle.rules.modernization")],
                    enable=[RuleNameSelector("use-f-string")],
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
                    disable=[RuleNameSelector("skip-rule")],
                    python_version=None,
                )
            )
            assert [rule.__name__ for rule in rules] == ["KeepRule"]

        with self.subTest("rule imports resolve local short override without enabling collection"):
            (self.tdp / "override_rules.py").write_text(
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
                    rule_imports=[QualifiedRule("override_rules")],
                    enable=[RuleNameSelector("skip-rule")],
                    python_version=None,
                )
            )
            assert [rule.__name__ for rule in rules] == ["SkipRule"]

        with self.subTest("override broad opt-out"):
            rules = collect_types(
                Config(
                    disable=[QualifiedRule("rattle.rules.modernization")],
                    enable=[QualifiedRule("rattle.rules.legacy", "use-cls-in-classmethod")],
                )
            )
            assert [UseClsInClassmethod] == rules

        with self.subTest("version match"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules.typing")],
                    python_version=Version("3.7.10"),
                )
            )
            assert UseTypesFromTyping in rules

        with self.subTest("version match alpha"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules.typing")],
                    python_version=Version("3.7.10a3"),
                )
            )
            assert UseTypesFromTyping in rules

        with self.subTest("version mismatch"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules.typing")],
                    python_version=Version("3.10.5"),
                )
            )
            assert UseTypesFromTyping not in rules

        with self.subTest("version mismatch alpha"):
            rules = collect_types(
                Config(
                    enable=[QualifiedRule("rattle.rules.typing")],
                    python_version=Version("3.10.5a4"),
                )
            )
            assert UseTypesFromTyping not in rules

        with self.subTest("tag select"):
            rules = collect_types(
                Config(
                    enable=[
                        QualifiedRule("rattle.rules.modernization"),
                        QualifiedRule("rattle.rules.typing"),
                    ],
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
                    enable=[QualifiedRule("rattle.rules.legacy")],
                    python_version=None,
                    tags=Tags.parse("^exceptions"),
                )
            )
            assert AvoidOrInExcept not in rules

        with self.subTest("tag select and filter"):
            rules = collect_types(
                Config(
                    enable=[
                        QualifiedRule("rattle.rules.modernization"),
                        QualifiedRule("rattle.rules.typing"),
                    ],
                    python_version=None,
                    tags=Tags.parse("typing,^tuples"),
                )
            )
            assert [UseTypesFromTyping] == rules

        with self.subTest("rule settings apply"):
            (rule,) = config.collect_rules(
                Config(
                    enable=[RuleNameSelector("use-f-string")],
                    disable=[],
                    options={"use-f-string": {"simple_expression_max_length": 80}},
                    python_version=None,
                )
            )
            assert isinstance(rule, UseFstring)
            assert rule.settings["simple_expression_max_length"] == 80

        with self.subTest("rule settings apply by qualified name"):
            (rule,) = config.collect_rules(
                Config(
                    enable=[RuleNameSelector("use-f-string")],
                    disable=[],
                    options={
                        "rattle.rules.legacy:use-f-string": {"simple_expression_max_length": 70}
                    },
                    python_version=None,
                )
            )
            assert isinstance(rule, UseFstring)
            assert rule.settings["simple_expression_max_length"] == 70

        with self.subTest("cached rule plan materializes fresh rule instances"):
            cfg = Config(
                enable=[RuleNameSelector("use-f-string")],
                disable=[],
                options={"use-f-string": {"simple_expression_max_length": 60}},
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
                    enable=[QualifiedRule("rattle.rules.legacy", "use-f-string")],
                    disable=[],
                    options={"rattle.rules.legacy:use-f-string": {"not_a_setting": 80}},
                    python_version=None,
                )
            )
