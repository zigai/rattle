# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from pathlib import Path

import libcst as cst
import libcst.matchers as m

from rattle import FileContent, Invalid, LintRule, Valid


class ReplaceUnionWithOptional(LintRule):
    """Enforces the use of ``Optional[T]`` over ``Union[T, None]`` and ``Union[None, T]``."""

    MESSAGE: str = "`Optional[T]` is preferred over `Union[T, None]` or `Union[None, T]`."
    REFERENCES = (
        ("typing.Optional", "https://docs.python.org/3/library/typing.html#typing.Optional"),
    )
    VALID = [
        Valid(
            """
            def func() -> Optional[str]:
                pass
            """
        ),
        Valid(
            """
            def func() -> Optional[Dict]:
                pass
            """
        ),
        Valid(
            """
            def func() -> Union[str, int, None]:
                pass
            """
        ),
    ]
    INVALID = [
        Invalid(
            """
            def func() -> Union[str, None]:
                pass
            """,
        ),
        Invalid(
            """
            from typing import Optional
            def func() -> Union[Dict[str, int], None]:
                pass
            """,
        ),
        Invalid(
            """
            from typing import Optional
            def func() -> Union[str, None]:
                pass
            """,
        ),
        Invalid(
            """
            from typing import Optional
            def func() -> Union[Dict, None]:
                pass
            """,
        ),
    ]

    def should_lint_file(self, source: FileContent, path: Path) -> bool:
        del path
        return b"Union" in source and b"None" in source

    def leave_Annotation(self, original_node: cst.Annotation) -> None:
        if self.contains_union_with_none(original_node):
            self.report(original_node, self.MESSAGE)

    def contains_union_with_none(self, node: cst.Annotation) -> bool:
        return m.matches(
            node,
            m.Annotation(
                m.Subscript(
                    value=m.Name("Union"),
                    slice=m.OneOf(
                        [
                            m.SubscriptElement(m.Index()),
                            m.SubscriptElement(m.Index(m.Name("None"))),
                        ],
                        [
                            m.SubscriptElement(m.Index(m.Name("None"))),
                            m.SubscriptElement(m.Index()),
                        ],
                    ),
                )
            ),
        )


__all__ = [
    "ReplaceUnionWithOptional",
]
