# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import builtins
import re
import textwrap
import tokenize
import unittest
import warnings
from collections import Counter
from collections.abc import Collection, Iterator, Mapping
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

from rattle.config.models import Config
from rattle.engine import LintRunner, diff_violation
from rattle.rule import Invalid, LintRule, Valid


class _ExecutionProbe:
    __hash__ = object.__hash__

    def __getattr__(self, name: str) -> _ExecutionProbe:
        del name
        return self

    def __call__(self, *args: object, **kwargs: object) -> _ExecutionProbe:
        del args, kwargs
        return self

    def __getitem__(self, key: object) -> _ExecutionProbe:
        del key
        return self

    def __iter__(self) -> Iterator[object]:
        return iter(())

    def __bool__(self) -> bool:
        return False

    def __contains__(self, item: object) -> bool:
        del item
        return False

    def __eq__(self, other: object) -> bool:
        del other
        return False

    def __ne__(self, other: object) -> bool:
        del other
        return True


class _ExecutionNamespace(dict[str, object]):
    def __missing__(self, key: str) -> object:
        if hasattr(builtins, key):
            return getattr(builtins, key)
        value = _ExecutionProbe()
        self[key] = value
        return value


def _execution_outcome(source: str) -> str:
    namespace = _ExecutionNamespace({"__name__": "__rattle_autofix_test__"})
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            code = compile(source, "<autofix-test>", "exec")
        exec(code, namespace)  # noqa: S102 - executes repository-owned regression fixtures
    except Exception as e:  # noqa: BLE001 - compare fixture behavior across an autofix
        return type(e).__name__
    return "success"


def _dedent(src: str) -> str:
    src = re.sub(r"\A\n", "", src)
    return textwrap.dedent(src)


def _comments(source: str) -> Counter[str]:
    return Counter(
        token.string
        for token in tokenize.generate_tokens(StringIO(source).readline)
        if token.type == tokenize.COMMENT
    )


@dataclass(frozen=True)
class TestCasePrecursor:
    rule: LintRule
    test_methods: Mapping[
        str,
        Valid | Invalid,
    ]


class LintRuleTestCase(unittest.TestCase):
    def _test_method(
        self,
        test_case: Valid | Invalid,
        rule: LintRule,
    ) -> None:
        rule.configure(test_case.options or {})
        path = Path.cwd() / ("valid.py" if isinstance(test_case, Valid) else "invalid.py")
        config = Config(path=path)
        source_code = _dedent(test_case.code)
        runner = LintRunner(path, source_code.encode())
        reports = list(runner.collect_violations([rule], config, include_diff=True))

        if isinstance(test_case, Valid):
            assert len(reports) == 0, (
                'Expected zero reports for this "valid" test case. Instead, found:\n'
                + "\n".join(str(e) for e in reports)
            )
            return

        assert len(reports) > 0, (
            'Expected a report for this "invalid" test case but `self.report` was '
            "not called:\n" + test_case.code
        )

        for report in reports:
            if test_case.range is not None:
                assert test_case.range == report.range

            if test_case.expected_message is not None:
                assert test_case.expected_message == report.message

        if test_case.expected_replacement is not None:
            # make sure we produced expected final code
            expected_code = _dedent(test_case.expected_replacement)
            modified_code = runner.apply_replacements(reports).bytes.decode()
            assert expected_code == modified_code
            original_outcome = _execution_outcome(source_code)
            fixed_outcome = _execution_outcome(modified_code)
            assert original_outcome == fixed_outcome or (
                rule.AUTOFIX_MAY_REPAIR_EXECUTION and fixed_outcome == "success"
            ), (
                "Auto-fix changed whether the fixture executes successfully or which exception "
                "it raises.\n"
                f"Original outcome: {original_outcome}; fixed outcome: {fixed_outcome}.\n"
                f"Before:\n{source_code}\nAfter:\n{modified_code}"
            )
            if rule.PRESERVE_COMMENTS:
                assert not (_comments(source_code) - _comments(modified_code)), (
                    "Auto-fix removed source comments.\n"
                    f"Before:\n{source_code}\nAfter:\n{modified_code}"
                )

            converged_rule = type(rule)()
            converged_rule.configure(test_case.options or {})
            converged_runner = LintRunner(path, modified_code.encode())
            remaining = list(converged_runner.collect_violations([converged_rule], config))
            assert remaining == [], (
                "Auto-fix did not converge; the fixed source still violates the same rule:\n"
                + "\n".join(str(report) for report in remaining)
            )

            if len(reports) == 1:
                # make sure we generated a reasonable diff
                expected_diff = diff_violation(path, runner.module, reports[0])
                assert expected_diff == reports[0].diff


def gen_test_methods_for_rule(rule: LintRule) -> TestCasePrecursor:
    """
    Aggregates all of the cases inside a single LintRule's VALID and INVALID
    attributes and maps them to altered names with a `test_` prefix so that 'unittest'
    can discover them later on and an index postfix so that individual tests can be
    selected from the command line.
    """
    valid_tcs = {}
    invalid_tcs = {}
    for idx, test_case_or_str in enumerate(rule.VALID):
        name = f"test_VALID_{idx}"
        valid_test_case = (
            Valid(code=test_case_or_str) if isinstance(test_case_or_str, str) else test_case_or_str
        )
        valid_tcs[name] = valid_test_case
    for idx, inv_test_case_or_str in enumerate(rule.INVALID):
        name = f"test_INVALID_{idx}"
        invalid_test_case = (
            Invalid(code=inv_test_case_or_str)
            if isinstance(inv_test_case_or_str, str)
            else inv_test_case_or_str
        )
        invalid_tcs[name] = invalid_test_case

    return TestCasePrecursor(
        rule=rule,
        test_methods={**valid_tcs, **invalid_tcs},
    )


def generate_lint_rule_test_cases(
    rules: Collection[LintRule],
) -> list[type[unittest.TestCase]]:
    test_case_classes: list[type[unittest.TestCase]] = []
    for rule in rules:
        if not isinstance(rule, LintRule):
            continue

        test_case = gen_test_methods_for_rule(rule)
        rule_type_name = type(test_case.rule).__name__
        rule_display_name = test_case.rule.name
        test_methods_to_add: dict[str, Any] = {"__qualname__": rule_display_name}

        for test_method_name, test_method_data in test_case.test_methods.items():

            def test_method(
                self: LintRuleTestCase,
                data: Valid | Invalid = test_method_data,
                rule: LintRule = test_case.rule,
            ) -> None:
                # instantiate a new rule for every test
                rule_ty = type(rule)
                return self._test_method(data, rule_ty())

            test_method.__name__ = test_method_name
            test_methods_to_add[test_method_name] = test_method

        test_case_class = type(rule_type_name, (LintRuleTestCase,), test_methods_to_add)
        test_case_classes.append(test_case_class)

    return test_case_classes


def add_lint_rule_tests_to_module(
    module_attrs: dict[str, Any], rules: Collection[LintRule]
) -> None:
    """
    Generate LintRuleTestCase subclasses from rule instances and install them in a module.

    Generated classes expose each rule's VALID and INVALID cases for unittest
    discovery, allowing `python -m unittest <your testing module name>` to run them.

    Args:
        module_attrs: Module attributes to receive the generated classes, typically
            supplied with `globals()`.
        rules: LintRule instances whose embedded cases should become tests.
    """
    test_case_classes = generate_lint_rule_test_cases(rules)
    for test_case_class in test_case_classes:
        module_attrs[test_case_class.__name__] = test_case_class

    # Rewrite the module for each generated test case to match the location calling
    # this function. This enables better integration with test case discovery methods
    # that depend on listing test cases separately from running them.
    if "__package__" in module_attrs:
        test_module = module_attrs.get("__package__")
        assert isinstance(test_module, str)
        for test_case_class in test_case_classes:
            test_case_class.__module__ = test_module


__all__ = [
    "LintRuleTestCase",
    "TestCasePrecursor",
    "add_lint_rule_tests_to_module",
    "gen_test_methods_for_rule",
    "generate_lint_rule_test_cases",
]
