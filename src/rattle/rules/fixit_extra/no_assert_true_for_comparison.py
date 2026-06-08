# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import libcst as cst

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
        Valid("self.assertTrue(a == b)"),
        Valid('self.assertTrue(data.is_valid(), "is_valid() method")'),
        Valid("self.assertTrue(validate(len(obj.getName(type=SHORT))))"),
        Valid("self.assertTrue(condition, message_string)"),
        Valid("self.assertTrue(a, 3)"),
        Valid("self.assertTrue(optional, None)"),
        Valid("self.assertTrue(b == a, True)"),
    ]

    INVALID: list[Invalid] = []

    def visit_Call(self, node: cst.Call) -> None:
        del node


__all__ = [
    "NoAssertTrueForComparisons",
]
