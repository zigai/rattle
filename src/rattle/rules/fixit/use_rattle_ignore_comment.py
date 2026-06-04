# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import libcst as cst

from rattle import Invalid, LintRule, Valid


class UseRattleIgnoreComment(LintRule):
    """
    To silence a lint warning, use ``rattle: ignore[RuleName]`` comments.
    The comment may be a trailing inline comment or a standalone comment line above the code.
    Rule names are optional, but explicitly listing one or more comma-separated rule names avoids
    accidentally silencing unrelated warnings.
    ``noqa`` is deprecated and not supported because it is shared by other Python linters and can
    accidentally silence warnings unexpectedly.
    """

    MESSAGE: str = "noqa is deprecated. Use `rattle: ignore[RuleName]` instead."

    VALID = [
        Valid(
            """
            # rattle: ignore[UseFstringRule]
            "%s" % "hi"
            """
        ),
        Valid(
            """
            'ab' 'cd'  # rattle: ignore[UsePlusForStringConcatRule]
            """
        ),
    ]
    INVALID = [
        Invalid("fn() # noqa"),
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
        target = "# noqa"
        if node.value[: len(target)].lower() == target:
            self.report(node, self.MESSAGE)


__all__ = [
    "UseRattleIgnoreComment",
]
