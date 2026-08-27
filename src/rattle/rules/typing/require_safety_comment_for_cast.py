from __future__ import annotations

import libcst as cst

from rattle.rule import Invalid, Valid
from rattle.rules.typing import _cast_annotations


class RequireSafetyCommentForCast(_cast_annotations.CastAnnotationRule):
    """Require an immediately preceding ``SAFETY:`` justification for every cast."""

    MESSAGE = (
        "This cast has no `SAFETY:` justification. State the invariant immediately "
        "before the cast or its containing statement."
    )

    VALID = [
        Valid("""
            from typing import cast

            # SAFETY: validation established that payload is text.
            value = cast(str, payload)
            """),
        Valid("""
            import typing

            value = consume(
                # SAFETY: the producer always emits bytes.
                typing.cast(bytes, payload)
            )
            """),
    ]

    INVALID = [
        Invalid(
            """
            from typing import cast

            value = cast(str, payload)
            """,
            expected_message=MESSAGE,
        ),
        Invalid(
            """
            from typing import cast

            # SAFETY: this belongs to the earlier statement.
            prepare()
            value = cast(str, payload)
            """,
            expected_message=MESSAGE,
        ),
    ]

    def visit_Call(self, node: cst.Call) -> None:
        if self.cast_arguments(node) is None or self.has_safety_comment(node):
            return
        self.report(node, self.MESSAGE)
