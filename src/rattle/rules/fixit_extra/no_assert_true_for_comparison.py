# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import libcst as cst
import libcst.matchers as m

from rattle import Invalid, LintRule, Valid


class NoAssertTrueForComparisons(LintRule):
    """Prefer specific unittest comparison assertions over assertTrue comparisons."""

    NAME = "use-assert-equal"
    SOURCE_PATTERNS = ("assertTrue",)

    MESSAGE: str = (
        '"assertTrue" does not compare its arguments, use "assertEqual" or other '
        "appropriate functions."
    )

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
            expected_replacement="self.assertNotEqual(a, b)",
        ),
        Invalid(
            "self.assertTrue(not a != b)",
            expected_replacement="self.assertEqual(a, b)",
        ),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._class_method_stack: list[set[str]] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        self._class_method_stack.append(
            {
                statement.name.value
                for statement in node.body.body
                if isinstance(statement, cst.FunctionDef)
            }
        )

    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        del original_node

        self._class_method_stack.pop()

    def visit_Call(self, node: cst.Call) -> None:
        if not m.matches(
            node.func,
            m.Attribute(value=m.Name("self"), attr=m.Name("assertTrue")),
        ):
            return
        if self._class_defines_assertion_method("assertTrue"):
            return
        if not node.args:
            return

        first_arg = node.args[0]
        if first_arg.keyword is not None or first_arg.star:
            return

        assertion_name, comparison = _assertion_for_condition(first_arg.value)
        if assertion_name is None or comparison is None:
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

    def _class_defines_assertion_method(self, name: str) -> bool:
        return bool(self._class_method_stack and name in self._class_method_stack[-1])


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
