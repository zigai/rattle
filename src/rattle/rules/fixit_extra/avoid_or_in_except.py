# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import libcst as cst
import libcst.matchers as m

from rattle import Invalid, LintRule, Valid


class AvoidOrInExcept(LintRule):
    """Require tuples instead of or-expressions when catching multiple exception types."""

    NAME = "no-or-in-except"

    REFERENCES = (
        (
            "Python exception handling",
            "https://docs.python.org/3/tutorial/errors.html#handling-exceptions",
        ),
    )

    MESSAGE: str = (
        "Use `except (ValueError, TypeError):`; `except ValueError or TypeError:` "
        "catches only `ValueError`."
    )
    VALID = [
        Valid(
            """
            try:
                print()
            except (ValueError, TypeError) as err:
                pass
            """
        )
    ]

    INVALID = [
        Invalid(
            """
            try:
                print()
            except ValueError or TypeError:
                pass
            """,
        ),
        Invalid(
            """
            try:
                print()
            except ValueError:
                pass
            except TypeError or OSError:
                pass
            """,
        ),
    ]

    def visit_ExceptHandler(self, node: cst.ExceptHandler) -> None:
        self._report_or_expression(node.type)

    def visit_ExceptStarHandler(self, node: cst.ExceptStarHandler) -> None:
        self._report_or_expression(node.type)

    def _report_or_expression(self, expression: cst.BaseExpression | None) -> None:
        if expression is None:
            return
        if m.findall(expression, m.BooleanOperation(operator=m.Or())):
            self.report(expression, self.MESSAGE)


__all__ = [
    "AvoidOrInExcept",
]
