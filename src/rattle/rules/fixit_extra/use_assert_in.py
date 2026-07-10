# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import libcst as cst
import libcst.matchers as m
from libcst.helpers import ensure_type

from rattle import Invalid, LintRule, Valid


class UseAssertIn(LintRule):
    """Prefer ``assertIn`` and ``assertNotIn`` for unittest membership checks."""

    SOURCE_PATTERNS = ("assertTrue", "assertFalse")

    MESSAGE: str = "Use `assertIn()` or `assertNotIn()` for membership checks."
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
        # Todo: Make use of single extract instead of having several
        # if else statements to make the code more robust and readable.
        if m.matches(
            node,
            m.Call(
                func=m.Attribute(value=m.Name("self"), attr=m.Name("assertTrue")),
                args=[m.Arg(m.Comparison(comparisons=[m.ComparisonTarget(operator=m.In())]))],
            ),
        ):
            if self._class_defines_assertion_method("assertTrue"):
                return

            # self.assertTrue(a in b) -> self.assertIn(a, b)
            new_call = node.with_changes(
                func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("assertIn")),
                args=[
                    cst.Arg(ensure_type(node.args[0].value, cst.Comparison).left),
                    cst.Arg(
                        ensure_type(node.args[0].value, cst.Comparison).comparisons[0].comparator
                    ),
                ],
            )
            self.report(node, self.MESSAGE, replacement=new_call)
        else:
            # ... -> self.assertNotIn(a, b)
            matched, arg1, arg2 = False, None, None
            if m.matches(
                node,
                m.Call(
                    func=m.Attribute(value=m.Name("self"), attr=m.Name("assertTrue")),
                    args=[
                        m.Arg(
                            m.UnaryOperation(
                                operator=m.Not(),
                                expression=m.Comparison(
                                    comparisons=[m.ComparisonTarget(operator=m.In())]
                                ),
                            )
                        )
                    ],
                ),
            ):
                # self.assertTrue(not a in b) -> self.assertNotIn(a, b)
                if self._class_defines_assertion_method("assertTrue"):
                    return
                matched = True
                arg1 = cst.Arg(
                    ensure_type(
                        ensure_type(node.args[0].value, cst.UnaryOperation).expression,
                        cst.Comparison,
                    ).left
                )
                arg2 = cst.Arg(
                    ensure_type(
                        ensure_type(node.args[0].value, cst.UnaryOperation).expression,
                        cst.Comparison,
                    )
                    .comparisons[0]
                    .comparator
                )
            elif m.matches(
                node,
                m.Call(
                    func=m.Attribute(value=m.Name("self"), attr=m.Name("assertTrue")),
                    args=[m.Arg(m.Comparison(comparisons=[m.ComparisonTarget(m.NotIn())]))],
                ),
            ):
                # self.assertTrue(a not in b) -> self.assertNotIn(a, b)
                if self._class_defines_assertion_method("assertTrue"):
                    return
                matched = True
                arg1 = cst.Arg(ensure_type(node.args[0].value, cst.Comparison).left)
                arg2 = cst.Arg(
                    ensure_type(node.args[0].value, cst.Comparison).comparisons[0].comparator
                )
            elif m.matches(
                node,
                m.Call(
                    func=m.Attribute(value=m.Name("self"), attr=m.Name("assertFalse")),
                    args=[m.Arg(m.Comparison(comparisons=[m.ComparisonTarget(m.In())]))],
                ),
            ):
                # self.assertFalse(a in b) -> self.assertNotIn(a, b)
                if self._class_defines_assertion_method("assertFalse"):
                    return
                matched = True
                arg1 = cst.Arg(ensure_type(node.args[0].value, cst.Comparison).left)
                arg2 = cst.Arg(
                    ensure_type(node.args[0].value, cst.Comparison).comparisons[0].comparator
                )

            if matched:
                new_call = node.with_changes(
                    func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("assertNotIn")),
                    args=[arg1, arg2],
                )
                self.report(node, self.MESSAGE, replacement=new_call)

    def _class_defines_assertion_method(self, name: str) -> bool:
        return bool(self._class_method_stack and name in self._class_method_stack[-1])


__all__ = [
    "UseAssertIn",
]
