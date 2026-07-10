# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import re

import libcst as cst

from rattle import Invalid, LintRule, Valid

NOQA_COMMENT_PATTERN = re.compile(r"(?:^|#)\s*(?:flake8:\s*)?noqa(?=$|[\s:,\[])", re.IGNORECASE)


class UseRattleIgnoreComment(LintRule):
    """
    Use an inline or preceding ``rattle: ignore[...]`` comment to suppress warnings.
    Listing rule names prevents unrelated warnings from being suppressed. Rattle does
    not recognize ``noqa`` because it may also affect other linters.
    """

    MESSAGE: str = "Use `rattle: ignore[rule-name]`; Rattle does not support `noqa`."

    VALID = [
        Valid(
            """
            # rattle: ignore[use-f-string]
            "%s" % "hi"
            """
        ),
        Valid(
            """
            'ab' 'cd'  # rattle: ignore[use-plus-for-string-concat]
            """
        ),
        Valid("fn()  # noqaed by another tool"),
        Valid("fn()  # See https://example.test/noqa-policy"),
    ]
    INVALID = [
        Invalid("fn() # noqa"),
        Invalid("fn() # NOQA"),
        Invalid("# flake8: noqa"),
        Invalid("fn()  # type: ignore  # noqa"),
        Invalid(
            """
            (
             1,
             2,  # noqa
            )
            """
        ),
        Invalid(
            """
            class C:
                # noqa
                ...
            """
        ),
    ]

    def visit_Comment(self, node: cst.Comment) -> None:
        if NOQA_COMMENT_PATTERN.search(node.value):
            self.report(node, self.MESSAGE)


__all__ = [
    "UseRattleIgnoreComment",
]
