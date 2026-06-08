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
        "Avoid using 'or' in an except block. For example:"
        "'except ValueError or TypeError' only catches 'ValueError'. Instead, use "
        "parentheses, 'except (ValueError, TypeError)'"
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
        if m.matches(node, m.ExceptHandler(type=m.BooleanOperation(operator=m.Or()))):
            self.report(node, self.MESSAGE)


__all__ = [
    "AvoidOrInExcept",
]
