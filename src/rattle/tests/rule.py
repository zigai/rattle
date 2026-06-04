# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from pathlib import Path
from textwrap import dedent, indent
from unittest import TestCase
from unittest.mock import MagicMock

import libcst as cst
import pytest
from libcst.metadata import CodePosition, CodeRange

from rattle.engine import LintRunner
from rattle.ftypes import Config, LintViolation
from rattle.rule import LintRule, RuleSetting


class NoopRule(LintRule):
    def __init__(self) -> None:
        super().__init__()
        self.called = False

    def visit_Module(self, node: cst.Module) -> bool:
        self.called = True
        return False

    def leave_Module(self, original_node: cst.Module) -> None:
        pass


class RunnerTest(TestCase):
    def setUp(self) -> None:
        self.runner = LintRunner(Path("fake.py"), b"pass")

    def test_no_rules(self) -> None:
        violations = self.runner.collect_violations([], Config())
        assert list(violations) == []

    def test_noop_rule(self) -> None:
        rule = NoopRule()
        violations = self.runner.collect_violations([rule], Config())
        assert list(violations) == []
        assert rule.called

    def test_source_patterns_skip_rule(self) -> None:
        class PatternRule(NoopRule):
            SOURCE_PATTERNS = ("def ",)

        rule = PatternRule()
        violations = self.runner.collect_violations([rule], Config())
        assert list(violations) == []
        assert not rule.called

    def test_source_patterns_allow_valid_call_whitespace(self) -> None:
        class PatternRule(NoopRule):
            SOURCE_PATTERNS = ("list(",)

        rule = PatternRule()
        runner = LintRunner(Path("fake.py"), b"value = list ((1, 2))\n")

        violations = runner.collect_violations([rule], Config())

        assert list(violations) == []
        assert rule.called

    def test_source_patterns_allow_valid_attribute_whitespace(self) -> None:
        class PatternRule(NoopRule):
            SOURCE_PATTERNS = (".format",)

        rule = PatternRule()
        runner = LintRunner(Path("fake.py"), b'value = "{}" . format(1)\n')

        violations = runner.collect_violations([rule], Config())

        assert list(violations) == []
        assert rule.called

    def test_timing(self) -> None:
        rule = NoopRule()
        for _ in self.runner.collect_violations([rule], Config(), metrics_hook=lambda _: None):
            pass  # exhaust the generator
        assert "Duration.NoopRule.visit_Module" in self.runner.metrics
        assert "Duration.NoopRule.leave_Module" in self.runner.metrics
        assert self.runner.metrics["Duration.NoopRule.visit_Module"] >= 0
        assert "Count.Noop" in self.runner.metrics
        assert "FixCount.Noop" in self.runner.metrics
        assert "Count.Total" in self.runner.metrics

    def test_timing_hook(self) -> None:
        rule = NoopRule()
        hook = MagicMock()
        for i, _ in enumerate(self.runner.collect_violations([rule], Config(), metrics_hook=hook)):
            if i <= 1:
                # only called at the end
                hook.assert_not_called()
        hook.assert_called_once()


class ExerciseReportRule(LintRule):
    MESSAGE = "message on the class"

    def visit_Module(self, node: cst.Module) -> bool:
        self.report(node, "Module")
        return False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        self.report(node, "class def")
        for d in node.decorators:
            self.report(d, "class decorator")
        return False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        if node.name.value == "problem":
            self.report(node, "problem function")
        return False

    def visit_Pass(self, node: cst.Pass) -> bool:
        self.report(node, "I pass")
        return False

    def visit_Ellipsis(self, node: cst.Ellipsis) -> bool:
        self.report(node, "I ellipse", position=CodePosition(line=1, column=1))
        return False

    def visit_Del(self, node: cst.Del) -> bool:
        self.report(node, self.MESSAGE)
        return False


class ConfigurableRule(LintRule):
    SETTINGS = {
        "max_length": RuleSetting(int, default=10),
        "allowed_prefixes": RuleSetting(list[str], default=["TODO"]),
        "structured_entries": RuleSetting(list[dict[str, str]], default=[]),
        "renamed_entries": RuleSetting(
            list[dict[str, str]],
            default=[],
            validator=lambda value: [{"name": entry["old_name"]} for entry in value],
        ),
    }


class RuleTest(TestCase):
    def setUp(self) -> None:
        self.rules = [ExerciseReportRule()]

    def test_pass_happy(self) -> None:
        runner = LintRunner(Path("fake.py"), b"pass")

        # Since the "pass" code is part of a Module and ExerciseReportRule() visit's the Module
        # 2 violations are collected.
        module_violation, pass_violation = list(runner.collect_violations(self.rules, Config()))
        assert isinstance(module_violation.node, cst.Module)
        assert isinstance(pass_violation.node, cst.Pass)

        assert module_violation == LintViolation(
            "ExerciseReport",
            CodeRange(start=CodePosition(1, 0), end=CodePosition(2, 0)),
            "Module",
            module_violation.node,
            None,
        )
        assert pass_violation == LintViolation(
            "ExerciseReport",
            CodeRange(start=CodePosition(1, 0), end=CodePosition(1, 4)),
            "I pass",
            pass_violation.node,
            None,
        )

    def test_ellipsis_position_override(self) -> None:
        runner = LintRunner(Path("fake.py"), b"...")

        # Since the "..." code is part of a Module and ExerciseReportRule() visit's the Module
        # 2 violations are collected.
        module_violation, ellipses_violation = list(runner.collect_violations(self.rules, Config()))
        assert isinstance(module_violation.node, cst.Module)
        assert isinstance(ellipses_violation.node, cst.Ellipsis)

        assert module_violation == LintViolation(
            "ExerciseReport",
            CodeRange(start=CodePosition(1, 0), end=CodePosition(2, 0)),
            "Module",
            module_violation.node,
            None,
        )
        assert ellipses_violation == LintViolation(
            "ExerciseReport",
            CodeRange(start=CodePosition(1, 1), end=CodePosition(2, 0)),
            "I ellipse",
            ellipses_violation.node,
            None,
        )

    def test_del_uses_class_message(self) -> None:
        runner = LintRunner(Path("fake.py"), b"del foo")

        # Since the "del foo" code is part of a Module and ExerciseReportRule() visit's the Module
        # 2 violations are collected.
        violations = list(runner.collect_violations(self.rules, Config()))
        module_violation, del_violation = violations
        assert len(violations) == 2
        assert isinstance(module_violation.node, cst.Module)
        assert isinstance(del_violation.node, cst.Del)

        assert module_violation == LintViolation(
            "ExerciseReport",
            CodeRange(start=CodePosition(1, 0), end=CodePosition(2, 0)),
            "Module",
            module_violation.node,
            None,
        )
        assert del_violation == LintViolation(
            "ExerciseReport",
            CodeRange(start=CodePosition(1, 0), end=CodePosition(1, 7)),
            "message on the class",
            del_violation.node,
            None,
        )

    def test_report_requires_message(self) -> None:
        with pytest.raises(TypeError):
            self.rules[0].report(cst.Pass())  # pyright: ignore[reportCallIssue]

    def test_ignore_lint(self) -> None:
        for idx, (code, message, position) in enumerate(
            (
                ("pass  # random comment\n", "I pass", (1, 0)),
                ("pass\n", "I pass", (1, 0)),
                ("pass  # rattle: ignore\n", None, None),
                ("pass  # rattle: ignore[ExerciseReport]\n", None, None),
                ("pass  # rattle: ignore[ExerciseReportRule]\n", None, None),
                ("pass  # rattle: ignore[SomethingElse, ExerciseReport]\n", None, None),
                ("pass  # rattle: ignore[SomethingElse]\n", "I pass", (1, 0)),
                ("# random comment\npass\n", "I pass", (2, 0)),
                ("# rattle: ignore\npass\n", None, None),
                ("# rattle: ignore[ExerciseReport]\npass\n", None, None),
                ("# rattle: ignore[SomethingElse, ExerciseReport]\npass\n", None, None),
                ("# rattle: ignore[SomethingElse]\npass\n", "I pass", (2, 0)),
                ("def foo(bar): pass\n", "I pass", (1, 14)),
                ("def foo(bar): pass  # rattle: ignore\n", None, None),
                ("# rattle: ignore\ndef foo(bar): pass\n", None, None),
                ("import sys\n# rattle: ignore\ndef foo(bar): pass\n", None, None),
                ("class bar(object): value = 1\n", "class def", (1, 0)),
                ("class bar(object): value = 1  # rattle: ignore\n", None, None),
                ("# rattle: ignore\nclass bar(object): value = 1\n", None, None),
                ("import sys\n# rattle: ignore\nclass bar(object): value = 1\n", None, None),
                (
                    """
                    import sys

                    class Foo(object):
                        value = 1
                """,
                    "class def",
                    (4, 0),
                ),
                (
                    """
                    import sys

                    class Foo(object):  # comment
                        value = 1
                """,
                    "class def",
                    (4, 0),
                ),
                (
                    """
                    import sys

                    class Foo(object):  # type: ignore # rattle: ignore
                        value = 1
                """,
                    None,
                    None,
                ),
                (
                    """
                    import sys

                    class Foo(object):  # rattle: ignore[ExerciseReport]
                        value = 1
                """,
                    None,
                    None,
                ),
                (
                    """
                    import sys

                    # type:ignore  # rattle: ignore  # justification
                    class Foo(object):
                        value = 1
                """,
                    None,
                    None,
                ),
                (
                    """
                    import sys

                    # rattle: ignore[UnrelatedRule]
                    class Foo(object):
                        value = 1
                """,
                    "class def",
                    (5, 0),
                ),
                (
                    # before function decorators
                    """
                    import sys

                    # rattle: ignore[ExerciseReport]
                    @contextmanager
                    def problem():
                        yield True
                """,
                    None,
                    None,
                ),
                (
                    # after function decorators
                    """
                    import sys

                    @contextmanager
                    # rattle: ignore[ExerciseReport]
                    def problem():
                        yield True
                """,
                    None,
                    None,
                ),
                (
                    # before class decorators
                    """
                    import dataclasses

                    # rattle: ignore[ExerciseReport]
                    @dataclasses.dataclass
                    class C:
                        value = 1
                """,
                    None,
                    None,
                ),
                (
                    # after class decorators
                    """
                    import dataclasses

                    @dataclasses.dataclass
                    # rattle: ignore[ExerciseReport]
                    class C:
                        value = 1
                """,
                    None,
                    None,
                ),
                (
                    # above comprehension
                    """
                    # rattle: ignore[ExerciseReport]
                    [... for _ in range(1)]
                """,
                    None,
                    None,
                ),
                (
                    # inside comprehension
                    """
                    [
                        # rattle: ignore[ExerciseReport]
                        ... for _ in range(1)
                    ]
                """,
                    None,
                    None,
                ),
                (
                    # after comprehension
                    """
                    [... for _ in range(1)]  # rattle: ignore[ExerciseReport]
                """,
                    None,
                    None,
                ),
                (
                    # trailing inline comprehension
                    """
                    [
                        ... for _ in range(1)  # rattle: ignore[ExerciseReport]
                    ]
                """,
                    None,
                    None,
                ),
                (
                    # before list element
                    """
                    [
                        # rattle: ignore[ExerciseReport]
                        ...,
                        None,
                    ]
                """,
                    None,
                    None,
                ),
                (
                    # trailing list element
                    """
                    [
                        ...,  # rattle: ignore[ExerciseReport]
                        None,
                    ]
                """,
                    None,
                    None,
                ),
            ),
            start=1,
        ):
            content = dedent(code).encode("utf-8")
            with self.subTest(f"test ignore {idx}"):
                runner = LintRunner(Path("fake.py"), content)
                violations = list(runner.collect_violations([ExerciseReportRule()], Config()))

                if message and position:
                    assert len(violations) in (1, 2)

                    # There's always going to be at least 1 violation (A module node violation).
                    # So, let's just assert it is a module then remove it to make the test simpler.
                    if len(violations) == 2:
                        assert isinstance(violations[0].node, cst.Module)
                        violations.pop(0)

                    (violation,) = violations

                    assert violation.message == message
                    assert violation.range is not None
                    assert violation.range.start == CodePosition(*position)

                else:
                    if len(violations) == 1:
                        assert isinstance(violations[0].node, cst.Module)
                        violations.pop(0)

                    assert len(violations) == 0, (
                        f"Unexpected lint errors reported:\n{indent(dedent(code), '    ')}\n"
                        + "\n".join(
                            f":{v.range.start.line}:{v.range.start.column} {v.rule_name}: {v.message}"
                            for v in violations
                            if v.range is not None
                        )
                    )

    def test_rule_setting_defaults(self) -> None:
        rule = ConfigurableRule()
        assert dict(rule.settings) == {}
        rule.configure({})
        assert rule.settings["max_length"] == 10
        assert rule.settings["allowed_prefixes"] == ["TODO"]

    def test_rule_setting_configure_overrides(self) -> None:
        rule = ConfigurableRule()
        rule.configure(
            {
                "max_length": 20,
                "allowed_prefixes": ["TODO", "FIXME"],
                "structured_entries": [{"name": "alpha", "message": "Use alpha."}],
            }
        )
        assert rule.settings["max_length"] == 20
        assert rule.settings["allowed_prefixes"] == ["TODO", "FIXME"]
        assert rule.settings["structured_entries"] == [{"name": "alpha", "message": "Use alpha."}]

    def test_rule_setting_unknown_key(self) -> None:
        rule = ConfigurableRule()
        with pytest.raises(ValueError, match="unknown setting"):
            rule.configure({"unknown": 1})

    def test_rule_setting_invalid_type(self) -> None:
        rule = ConfigurableRule()
        with pytest.raises(ValueError, match=r"allowed_prefixes\[0\]"):
            rule.configure({"allowed_prefixes": [1]})

    def test_rule_setting_invalid_nested_type(self) -> None:
        rule = ConfigurableRule()
        with pytest.raises(ValueError, match=r"structured_entries\[0\]\.name"):
            rule.configure({"structured_entries": [{"name": 1}]})

    def test_rule_setting_validator_can_normalize_value(self) -> None:
        rule = ConfigurableRule()
        rule.configure({"renamed_entries": [{"old_name": "alpha"}]})
        assert rule.settings["renamed_entries"] == [{"name": "alpha"}]

    def test_runner_applies_default_settings(self) -> None:
        runner = LintRunner(Path("fake.py"), b"pass")
        rule = ConfigurableRule()
        list(runner.collect_violations([rule], Config()))
        assert rule.settings["max_length"] == 10
