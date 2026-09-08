# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import libcst as cst
import libcst.matchers as m
from libcst.helpers import ensure_type
from libcst.metadata import ParentNodeProvider

from rattle.rule import Invalid, LintRule, Valid
from rattle.rules.helpers import enclosing_class_defines_method, has_comments

_MEMBERSHIP_ASSERTIONS = {
    ("assertTrue", "in", False): "assertIn",
    ("assertTrue", "in", True): "assertNotIn",
    ("assertTrue", "not in", False): "assertNotIn",
    ("assertFalse", "in", False): "assertNotIn",
}


class UseAssertIn(LintRule):
    """Prefer ``assertIn`` and ``assertNotIn`` for unittest membership checks."""

    SOURCE_PATTERNS = ("assertTrue", "assertFalse")

    MESSAGE: str = "Use `assertIn()` or `assertNotIn()` for membership checks."
    METADATA_DEPENDENCIES = (ParentNodeProvider,)
    REFERENCES = (
        (
            "unittest assertIn",
            "https://docs.python.org/3/library/unittest.html#unittest.TestCase.assertIn",
        ),
    )

    VALID = [
        Valid("self.assertIn(a, b)"),
        Valid("self.assertIn(f(), b)"),
        Valid("self.assertIn(f(x), b)"),
        Valid("self.assertIn(f(g(x)), b)"),
        Valid("self.assertNotIn(a, b)"),
        Valid("self.assertNotIn(f(), b)"),
        Valid("self.assertNotIn(f(x), b)"),
        Valid("self.assertNotIn(f(g(x)), b)"),
        Valid("""
            class Checker:
                def assertTrue(self, expr):
                    print(expr)

                def check(self, a, b):
                    self.assertTrue(a in b)
            """),
    ]

    INVALID = [
        Invalid(
            "self.assertTrue(a in b)",
            expected_replacement="self.assertIn(a, b)",
        ),
        Invalid(
            "self.assertTrue(f() in b)",
            expected_replacement="self.assertIn(f(), b)",
        ),
        Invalid(
            "self.assertTrue(f(x) in b)",
            expected_replacement="self.assertIn(f(x), b)",
        ),
        Invalid(
            "self.assertTrue(f(g(x)) in b)",
            expected_replacement="self.assertIn(f(g(x)), b)",
        ),
        Invalid(
            "self.assertTrue(a not in b)",
            expected_replacement="self.assertNotIn(a, b)",
        ),
        Invalid(
            "self.assertTrue(not a in b)",
            expected_replacement="self.assertNotIn(a, b)",
        ),
        Invalid(
            "self.assertFalse(a in b)",
            expected_replacement="self.assertNotIn(a, b)",
        ),
    ]

    def visit_Call(self, node: cst.Call) -> None:
        if not m.matches(
            node,
            m.Call(
                func=m.Attribute(
                    value=m.Name("self"),
                    attr=m.OneOf(m.Name("assertTrue"), m.Name("assertFalse")),
                ),
                args=[m.Arg()],
            ),
        ):
            return

        assertion_name = ensure_type(node.func, cst.Attribute).attr.value
        comparison = node.args[0].value
        negated = isinstance(comparison, cst.UnaryOperation) and isinstance(
            comparison.operator, cst.Not
        )
        if negated:
            comparison = ensure_type(comparison, cst.UnaryOperation).expression
        if not isinstance(comparison, cst.Comparison) or len(comparison.comparisons) != 1:
            return

        target = comparison.comparisons[0]
        if not isinstance(target.operator, (cst.In, cst.NotIn)):
            return
        operator = "not in" if isinstance(target.operator, cst.NotIn) else "in"
        new_attr = _MEMBERSHIP_ASSERTIONS.get((assertion_name, operator, negated))
        if new_attr is None:
            return
        if enclosing_class_defines_method(
            self, node, assertion_name
        ) or enclosing_class_defines_method(self, node, new_attr):
            return

        new_call = node.with_changes(
            func=cst.Attribute(value=cst.Name("self"), attr=cst.Name(new_attr)),
            args=[cst.Arg(comparison.left), cst.Arg(target.comparator)],
        )
        self.report(
            node,
            self.MESSAGE,
            replacement=None if has_comments(node.args[0]) else new_call,
        )


__all__ = [
    "UseAssertIn",
]
