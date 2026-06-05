# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from pathlib import Path

import libcst as cst
import libcst.matchers as m
from libcst.metadata import ScopeProvider

from rattle import FileContent, Invalid, LintRule, Valid


class ReplaceUnionWithOptional(LintRule):
    """Enforces the use of ``Optional[T]`` over ``Union[T, None]`` and ``Union[None, T]``."""

    MESSAGE: str = "`Optional[T]` is preferred over `Union[T, None]` or `Union[None, T]`."
    REFERENCES = (
        ("typing.Optional", "https://docs.python.org/3/library/typing.html#typing.Optional"),
    )
    METADATA_DEPENDENCIES = (ScopeProvider,)
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
            expected_replacement="""
            from typing import Optional
            def func() -> Optional[Dict[str, int]]:
                pass
            """,
        ),
        Invalid(
            """
            from typing import Optional
            def func() -> Union[str, None]:
                pass
            """,
            expected_replacement="""
            from typing import Optional
            def func() -> Optional[str]:
                pass
            """,
        ),
        Invalid(
            """
            from typing import Optional
            def func() -> Union[Dict, None]:
                pass
            """,
            expected_replacement="""
            from typing import Optional
            def func() -> Optional[Dict]:
                pass
            """,
        ),
    ]

    def should_lint_file(self, source: FileContent, path: Path) -> bool:
        del path
        return b"Union" in source and b"None" in source

    def leave_Annotation(self, original_node: cst.Annotation) -> None:
        if self.contains_union_with_none(original_node):
            scope = self.get_metadata(ScopeProvider, original_node, None)
            nones = 0
            indexes = []
            replacement = None
            if scope is not None and "Optional" in scope:
                for s in cst.ensure_type(original_node.annotation, cst.Subscript).slice:
                    if m.matches(s, m.SubscriptElement(m.Index(m.Name("None")))):
                        nones += 1
                    else:
                        indexes.append(s.slice)
                if not (nones > 1) and len(indexes) == 1:
                    replacement = original_node.with_changes(
                        annotation=cst.Subscript(
                            value=cst.Name("Optional"),
                            slice=(cst.SubscriptElement(indexes[0]),),
                        )
                    )
                    # TODO(T57106602) refactor lint replacement once extract exists
            self.report(original_node, self.MESSAGE, replacement=replacement)

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
