# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest import TestCase
from unittest.mock import patch

import pytest
from packaging.version import Version

from rattle import config, rule_loading
from rattle.config import collect_rules
from rattle.config.models import Config
from rattle.engine import LintRunner
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

        registry = config.RuleRegistry(root=self.tdp)
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

        registry = config.RuleRegistry(root=self.tdp)
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

        registry = config.RuleRegistry(root=self.tdp)
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


def test_import_contracts_load_nested_toml_options(tmp_path: Path) -> None:
    project = tmp_path / "pyproject.toml"
    project.write_text(
        dedent(
            """\
            [tool.rattle]
            root = true
            enable = ["import-contracts"]
            enable-root-import = true

            [tool.rattle.options.import-contracts]
            source_roots = ["packages/server/src"]

            [[tool.rattle.options.import-contracts.contracts]]
            type = "layers"
            name = "application-flow"
            root = "parcel"
            message = "Core stays independent."
            layers = [{modules = ["edge.**"]}, {modules = ["core.**"]}]

            [[tool.rattle.options.import-contracts.contracts]]
            type = "forbidden"
            name = "core-transport"
            source = ["parcel.core.**"]
            forbid = ["webkit"]
            """
        )
    )
    path = tmp_path / "packages/server/src/parcel/core/__init__.py"
    cfg = config.generate_config(path)
    rules = collect_rules(cfg)
    reports = list(
        LintRunner(path, b"from ..edge import handler\nimport webkit\n").collect_violations(
            rules, cfg
        )
    )

    assert config.validate_config(project) == []
    assert len(reports) == 2
    assert "application-flow" in reports[0].message
    assert "Core stays independent." in reports[0].message
    assert "core-transport" in reports[1].message


def test_import_contracts_validation_checks_nested_contract_fields(tmp_path: Path) -> None:
    project = tmp_path / "pyproject.toml"
    project.write_text(
        '[tool.rattle]\nroot = true\nenable = ["import-contracts"]\n'
        "[[tool.rattle.options.import-contracts.contracts]]\n"
        'type = "forbidden"\nname = "boundary"\nsource = ["parcel.**"]\n'
        'forbid = ["webkit"]\nallow_indirect_imports = true\n'
    )

    errors = config.validate_config(project)

    assert len(errors) == 1
    assert "import-contracts" in errors[0]


def test_local_rule_plans_keep_each_configuration_directory(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.rattle]\nroot = true\n")
    first = tmp_path / "first"
    second = tmp_path / "second"
    for directory in (first, second):
        directory.mkdir()
        (directory / "pyproject.toml").write_text('[tool.rattle]\nenable = [".rules:local-rule"]\n')
        (directory / "rules.py").write_text(
            "from rattle import LintRule\n"
            "class LocalRule(LintRule):\n"
            "    def visit_Module(self, node):\n"
            f"        self.report(node, {directory.name!r})\n"
        )

    first_config = config.generate_config(first / "sample.py")
    second_config = config.generate_config(second / "sample.py")
    first_reports = list(
        LintRunner(first_config.path, b"pass\n").collect_violations(
            collect_rules(first_config), first_config
        )
    )
    second_reports = list(
        LintRunner(second_config.path, b"pass\n").collect_violations(
            collect_rules(second_config), second_config
        )
    )

    assert [report.message for report in first_reports] == ["first"]
    assert [report.message for report in second_reports] == ["second"]


def test_builtin_collections_resolve_rules() -> None:
    for collection in [
        "rattle.rules.exports",
        "rattle.rules.modernization",
        "rattle.rules.legacy",
        "rattle.rules.policy",
        "rattle.rules.style",
        "rattle.rules.typing",
    ]:
        rules = collect_rules(Config(enable=[QualifiedRule(collection)], python_version=None))
        assert len(rules) > 0, f"Collection {collection} resolved 0 rules"


@pytest.mark.parametrize(
    ("module", "source", "reason", "cause_type"),
    [
        (
            ".rules",
            None,
            "Rule module '.rules' was not found",
            ModuleNotFoundError,
        ),
        (
            "missing_rule_collection",
            None,
            "Rule module 'missing_rule_collection' was not found",
            ModuleNotFoundError,
        ),
        (
            "missing_rule_collection.rules",
            None,
            "Rule module 'missing_rule_collection.rules' was not found",
            ModuleNotFoundError,
        ),
        (
            ".rules",
            "import missing_rule_dependency\n",
            "Dependency module 'missing_rule_dependency' was not found",
            ModuleNotFoundError,
        ),
        (
            ".rules",
            "from .missing_support import VALUE\n",
            "Dependency module '.missing_support' was not found",
            ModuleNotFoundError,
        ),
        (
            ".rules",
            'raise ImportError("private import detail")\n',
            "ImportError while importing '.rules'",
            ImportError,
        ),
    ],
)
def test_rule_import_errors_explain_failure_and_preserve_cause(
    tmp_path: Path,
    module: str,
    source: str | None,
    reason: str,
    cause_type: type[ImportError],
) -> None:
    if source is not None:
        (tmp_path / "rules.py").write_text(source, encoding="utf-8")
    rule = QualifiedRule(module, local="." if module.startswith(".") else None, root=tmp_path)

    with pytest.raises(config.CollectionError) as caught:
        list(config.find_rules(rule))

    error = caught.value
    assert error.rule == rule
    assert reason in str(error)
    assert f"Python interpreter: {sys.executable}" in str(error)
    assert type(error.__cause__) is cause_type
    assert "private import detail" not in str(error)
    if cause_type is ImportError:
        assert error.__cause__.args == ("private import detail",)
        assert "Dependency module" not in str(error)


@pytest.mark.parametrize("strict", [False, True], ids=["non-strict", "strict"])
def test_rule_import_errors_preserve_registry_loading_policy(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, strict: bool
) -> None:
    (tmp_path / "rules.py").write_text("import missing_rule_dependency\n", encoding="utf-8")
    rule = QualifiedRule(".rules", local=".", root=tmp_path)

    if strict:
        with pytest.raises(config.CollectionError) as caught:
            config.RuleRegistry.load([rule], root=tmp_path, strict=True)
        assert caplog.records == []
    else:
        registry = config.RuleRegistry.load([rule], root=tmp_path, strict=False)
        with pytest.raises(config.CollectionError) as caught:
            registry.resolve(rule)
        assert "Dependency module 'missing_rule_dependency' was not found" in caplog.text
        assert registry.imported_rules[rule] == ()

    assert "Dependency module 'missing_rule_dependency' was not found" in str(caught.value)
    assert isinstance(caught.value.__cause__, ModuleNotFoundError)
