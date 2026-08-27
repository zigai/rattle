from __future__ import annotations

import libcst as cst

from rattle.rule import Invalid, Valid
from rattle.rules.typing import _cast_annotations


class NoCastsToNever(_cast_annotations.CastAnnotationRule):
    """Disallow casts whose target is ``Never`` or ``NoReturn``."""

    MESSAGE = (
        "Do not cast a value to `Never` or `NoReturn`; prove exhaustiveness through control flow."
    )

    VALID = [
        Valid("""
            from typing import cast

            value = cast(str, payload)
            """),
        Valid("""
            from typing import cast

            Never = str
            value = cast(Never, payload)
            """),
    ]

    INVALID = [
        Invalid(
            """
            from typing import Never, cast

            value = cast(Never, payload)
            """,
            expected_message=MESSAGE,
        ),
        Invalid(
            """
            import typing as t
            from typing import cast

            Bottom = t.NoReturn
            value = cast("Bottom", payload)
            """,
            expected_message=MESSAGE,
        ),
    ]

    def visit_Call(self, node: cst.Call) -> None:
        arguments = self.cast_arguments(node)
        if arguments is None:
            return
        target = arguments[0]
        if self.is_never_target(target, node):
            self.report(target, self.MESSAGE)
