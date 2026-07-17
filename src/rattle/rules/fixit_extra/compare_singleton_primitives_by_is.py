# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import libcst as cst

from rattle import Invalid, LintRule, Valid


class CompareSingletonPrimitivesByIs(LintRule):
    """Require identity operators when comparing ``None``, ``True``, and ``False``."""

    NAME = "use-is-for-singletons"

    REFERENCES = (
        ("Flake8 E711", "https://www.flake8rules.com/rules/E711.html"),
        ("Flake8 E712", "https://www.flake8rules.com/rules/E712.html"),
    )

    MESSAGE: str = "Compare `None`, `True`, and `False` with `is` or `is not`."
    VALID = [
        Valid("if x: pass"),
        Valid("if not x: pass"),
        Valid("x is True"),
        Valid("x is False"),
        Valid("x is None"),
        Valid("x is not None"),
        Valid("x is True is not y"),
        Valid("y is None is not x"),
        Valid("None is y"),
        Valid("True is x"),
        Valid("False is x"),
        Valid("x == 2"),
        Valid("2 != x"),
        Valid("1 == True"),
        Valid("True == 1"),
        Valid("1 != False"),
        Valid('"True" == "True"'),
        Valid('"True" != "False".lower()'),
    ]
    INVALID = [
        Invalid(
            code="x != True",
            expected_replacement="x is not True",
        ),
        Invalid(
            code="x != False",
            expected_replacement="x is not False",
        ),
        Invalid(
            code="x == False",
            expected_replacement="x is False",
        ),
        Invalid(
            code="x == None",
            expected_replacement="x is None",
        ),
        Invalid(
            code="x != None",
            expected_replacement="x is not None",
        ),
        Invalid(
            code="False == x",
            expected_replacement="False is x",
        ),
        Invalid(
            code="x is True == y",
            expected_replacement="x is True is y",
        ),
    ]

    def is_singleton(self, node: cst.BaseExpression) -> bool:
        return isinstance(node, cst.Name) and node.value in {"True", "False", "None"}

    def is_bool_singleton_number_comparison(
        self, left: cst.BaseExpression, right: cst.BaseExpression
    ) -> bool:
        return (
            isinstance(left, cst.Name)
            and left.value in {"True", "False"}
            and self.is_number_literal(right)
        ) or (
            isinstance(right, cst.Name)
            and right.value in {"True", "False"}
            and self.is_number_literal(left)
        )

    def is_number_literal(self, node: cst.BaseExpression) -> bool:
        if isinstance(node, cst.BaseNumber):
            return True
        return (
            isinstance(node, cst.UnaryOperation)
            and isinstance(node.operator, (cst.Plus, cst.Minus))
            and isinstance(node.expression, cst.BaseNumber)
        )

    def visit_Comparison(self, node: cst.Comparison) -> None:
        # Initialize the needs_report flag as False to begin with
        needs_report = False
        left_comp = node.left
        altered_comparisons = []
        for target in node.comparisons:
            operator, right_comp = target.operator, target.comparator
            if self.is_bool_singleton_number_comparison(left_comp, right_comp):
                altered_comparisons.append(target)
                left_comp = right_comp
                continue
            if isinstance(operator, (cst.Equal, cst.NotEqual)) and (
                self.is_singleton(left_comp) or self.is_singleton(right_comp)
            ):
                needs_report = True
                altered_comparisons.append(
                    target.with_changes(operator=self.alter_operator(operator))
                )
            else:
                altered_comparisons.append(target)
            # Continue the check down the line of comparisons, if more than one
            left_comp = right_comp

        if needs_report:
            self.report(
                node, self.MESSAGE, replacement=node.with_changes(comparisons=altered_comparisons)
            )

    def alter_operator(self, original_op: cst.Equal | cst.NotEqual) -> cst.Is | cst.IsNot:
        whitespace_before = self._identity_operator_whitespace(original_op.whitespace_before)
        whitespace_after = self._identity_operator_whitespace(original_op.whitespace_after)
        return (
            cst.IsNot(
                whitespace_before=whitespace_before,
                whitespace_after=whitespace_after,
            )
            if isinstance(original_op, cst.NotEqual)
            else cst.Is(
                whitespace_before=whitespace_before,
                whitespace_after=whitespace_after,
            )
        )

    def _identity_operator_whitespace(
        self, whitespace: cst.BaseParenthesizableWhitespace
    ) -> cst.BaseParenthesizableWhitespace:
        if isinstance(whitespace, cst.SimpleWhitespace) and not whitespace.value:
            return cst.SimpleWhitespace(" ")
        return whitespace


__all__ = [
    "CompareSingletonPrimitivesByIs",
]
