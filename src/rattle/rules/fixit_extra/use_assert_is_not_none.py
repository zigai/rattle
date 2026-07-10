# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from collections.abc import Sequence

import libcst as cst
import libcst.matchers as m
from libcst.helpers import ensure_type

from rattle import Invalid, LintRule, Valid


class UseAssertIsNotNone(LintRule):
    """Prefer ``assertIsNotNone`` and ``assertIsNone`` for unittest ``None`` checks."""

    SOURCE_PATTERNS = ("assertTrue", "assertFalse")

    MESSAGE: str = "Use `assertIsNone()` or `assertIsNotNone()` for `None` checks."

    VALID = [
        Valid("self.assertIsNotNone(x)"),
        Valid("self.assertIsNone(x)"),
        Valid("self.assertIsNone(None)"),
        Valid("self.assertIsNotNone(f(x))"),
        Valid("self.assertIsNone(f(x))"),
        Valid("self.assertIsNone(object.key)"),
        Valid("self.assertIsNotNone(object.key)"),
    ]

    INVALID = [
        Invalid(
            "self.assertTrue(a is not None)",
            expected_replacement="self.assertIsNotNone(a)",
        ),
        Invalid(
            "self.assertTrue(not x is None)",
            expected_replacement="self.assertIsNotNone(x)",
        ),
        Invalid(
            "self.assertTrue(f() is not None)",
            expected_replacement="self.assertIsNotNone(f())",
        ),
        Invalid(
            "self.assertTrue(not x is not None)",
            expected_replacement="self.assertIsNone(x)",
        ),
        Invalid(
            "self.assertTrue(f(x) is not None)",
            expected_replacement="self.assertIsNotNone(f(x))",
        ),
        Invalid("self.assertTrue(x is None)", expected_replacement="self.assertIsNone(x)"),
        Invalid(
            "self.assertFalse(x is not None)",
            expected_replacement="self.assertIsNone(x)",
        ),
        Invalid(
            "self.assertFalse(not x is None)",
            expected_replacement="self.assertIsNone(x)",
        ),
        Invalid(
            "self.assertFalse(f() is not None)",
            expected_replacement="self.assertIsNone(f())",
        ),
        Invalid(
            "self.assertFalse(not x is not None)",
            expected_replacement="self.assertIsNotNone(x)",
        ),
        Invalid(
            "self.assertFalse(f(x) is not None)",
            expected_replacement="self.assertIsNone(f(x))",
        ),
        Invalid(
            "self.assertFalse(x is None)",
            expected_replacement="self.assertIsNotNone(x)",
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

    def _first_extracted_node(
        self,
        extracted: cst.CSTNode | Sequence[cst.CSTNode],
    ) -> cst.CSTNode:
        if isinstance(extracted, Sequence):
            return extracted[0]

        return extracted

    def visit_Call(self, node: cst.Call) -> None:
        match_compare_is_none = m.ComparisonTarget(
            m.SaveMatchedNode(
                m.OneOf(m.Is(), m.IsNot()),
                "comparison_type",
            ),
            comparator=m.Name("None"),
        )
        result = m.extract(
            node,
            m.Call(
                func=m.Attribute(
                    value=m.Name("self"),
                    attr=m.SaveMatchedNode(
                        m.OneOf(m.Name("assertTrue"), m.Name("assertFalse")),
                        "assertion_name",
                    ),
                ),
                args=[
                    m.Arg(
                        m.SaveMatchedNode(
                            m.OneOf(
                                m.Comparison(comparisons=[match_compare_is_none]),
                                m.UnaryOperation(
                                    operator=m.Not(),
                                    expression=m.Comparison(comparisons=[match_compare_is_none]),
                                ),
                            ),
                            "argument",
                        )
                    )
                ],
            ),
        )

        if result:
            assertion_name = ensure_type(
                self._first_extracted_node(result["assertion_name"]),
                cst.Name,
            )
            if self._class_defines_assertion_method(assertion_name.value):
                return

            argument = ensure_type(
                self._first_extracted_node(result["argument"]),
                cst.BaseExpression,
            )
            comparison_type = self._first_extracted_node(result["comparison_type"])

            if m.matches(argument, m.Comparison()):
                assertion_argument = ensure_type(argument, cst.Comparison).left
            else:
                assertion_argument = ensure_type(
                    ensure_type(argument, cst.UnaryOperation).expression, cst.Comparison
                ).left

            negations_seen = 0
            if m.matches(assertion_name, m.Name("assertFalse")):
                negations_seen += 1
            if m.matches(argument, m.UnaryOperation()):
                negations_seen += 1
            if m.matches(comparison_type, m.IsNot()):
                negations_seen += 1

            new_attr = "assertIsNone" if negations_seen % 2 == 0 else "assertIsNotNone"
            new_call = node.with_changes(
                func=cst.Attribute(value=cst.Name("self"), attr=cst.Name(new_attr)),
                args=[cst.Arg(assertion_argument)],
            )

            if new_call is not node:
                self.report(node, self.MESSAGE, replacement=new_call)

    def _class_defines_assertion_method(self, name: str) -> bool:
        return bool(self._class_method_stack and name in self._class_method_stack[-1])


__all__ = [
    "UseAssertIsNotNone",
]
