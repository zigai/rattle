# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import libcst as cst
import libcst.matchers as m
from libcst.metadata import ParentNodeProvider

from rattle import Invalid, LintRule, Valid
from rattle.rules.helpers import enclosing_class_defines_method


class NoAssertTrueForComparisons(LintRule):
    """Prefer specific unittest assertions over comparisons passed to ``assertTrue``."""

    NAME = "use-assert-equal"
    SOURCE_PATTERNS = ("assertTrue",)

    MESSAGE: str = (
        "Use `assertEqual()` or `assertNotEqual()` instead of wrapping an equality "
        "comparison in `assertTrue()`."
    )
    METADATA_DEPENDENCIES = (ParentNodeProvider,)

    VALID = [
        Valid("self.assertEqual(a, b)"),
        Valid("self.assertNotEqual(a, b)"),
        Valid("self.assertTrue(a < b)"),
        Valid("self.assertTrue(a == b == c)"),
        Valid('self.assertTrue(data.is_valid(), "is_valid() method")'),
        Valid("self.assertTrue(validate(len(obj.getName(type=SHORT))))"),
        Valid("self.assertTrue(condition, message_string)"),
        Valid("self.assertTrue(a, 3)"),
        Valid("self.assertTrue(optional, None)"),
    ]

    INVALID = [
        Invalid(
            "self.assertTrue(a == b)",
            expected_replacement="self.assertEqual(a, b)",
        ),
        Invalid(
            "self.assertTrue(a != b)",
            expected_replacement="self.assertNotEqual(a, b)",
        ),
        Invalid(
            'self.assertTrue(a == b, "message")',
            expected_replacement='self.assertEqual(a, b, "message")',
        ),
        Invalid(
            "self.assertTrue(not a == b)",
        ),
        Invalid(
            "self.assertTrue(not a != b)",
        ),
    ]

    def visit_Call(self, node: cst.Call) -> None:
        first_arg = self._comparison_argument(node)
        if first_arg is None:
            return

        assertion_name, comparison = _assertion_for_condition(first_arg.value)
        if assertion_name is None or comparison is None:
            return
        if enclosing_class_defines_method(self, node, assertion_name):
            return

        is_negated = isinstance(first_arg.value, cst.UnaryOperation)
        has_comment = "#" in cst.Module([]).code_for_node(first_arg)
        if is_negated or has_comment:
            self.report(node, self.MESSAGE)
            return

        target = comparison.comparisons[0]
        replacement = node.with_changes(
            func=cst.Attribute(value=cst.Name("self"), attr=cst.Name(assertion_name)),
            args=[
                cst.Arg(comparison.left),
                cst.Arg(target.comparator),
                *node.args[1:],
            ],
        )
        self.report(node, self.MESSAGE, replacement=replacement)

    def _comparison_argument(self, node: cst.Call) -> cst.Arg | None:
        if not m.matches(
            node.func,
            m.Attribute(value=m.Name("self"), attr=m.Name("assertTrue")),
        ):
            return None
        if enclosing_class_defines_method(self, node, "assertTrue"):
            return None
        if not node.args:
            return None

        first_arg = node.args[0]
        if first_arg.keyword is not None or first_arg.star:
            return None
        return first_arg


def _assertion_for_condition(
    value: cst.BaseExpression,
) -> tuple[str | None, cst.Comparison | None]:
    if isinstance(value, cst.Comparison):
        return _assertion_for_comparison(value, negated=False), value
    if (
        isinstance(value, cst.UnaryOperation)
        and isinstance(value.operator, cst.Not)
        and isinstance(value.expression, cst.Comparison)
    ):
        return (
            _assertion_for_comparison(value.expression, negated=True),
            value.expression,
        )
    return None, None


def _assertion_for_comparison(comparison: cst.Comparison, *, negated: bool) -> str | None:
    if len(comparison.comparisons) != 1:
        return None

    operator = comparison.comparisons[0].operator
    if isinstance(operator, cst.Equal):
        return "assertNotEqual" if negated else "assertEqual"
    if isinstance(operator, cst.NotEqual):
        return "assertEqual" if negated else "assertNotEqual"
    return None


__all__ = [
    "NoAssertTrueForComparisons",
]
