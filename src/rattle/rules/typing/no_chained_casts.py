from __future__ import annotations

import libcst as cst

from rattle.rule import Invalid, Valid
from rattle.rules.typing import _cast_annotations


class NoChainedCasts(_cast_annotations.CastAnnotationRule):
    """Disallow using one ``typing.cast`` directly as the value of another."""

    MESSAGE = (
        "This cast chain discards type evidence. Keep the original precise type or "
        "validate the value once."
    )

    VALID = [
        Valid("""
            from typing import cast

            value = cast(str, payload)
            """),
        Valid("""
            def cast(target, value):
                return value

            value = cast(str, cast(bytes, payload))
            """),
    ]

    INVALID = [
        Invalid(
            """
            from typing import cast

            value = cast(str, cast(bytes, payload))
            """,
            expected_message=MESSAGE,
        ),
        Invalid(
            """
            import typing

            checked = typing.cast
            value = checked(str, (checked(bytes, payload)))
            """,
            expected_message=MESSAGE,
        ),
    ]

    def visit_Call(self, node: cst.Call) -> None:
        arguments = self.cast_arguments(node)
        if arguments is None or self.is_nested_cast_value(node):
            return
        value = arguments[1]
        if isinstance(value, cst.Call) and self.cast_arguments(value) is not None:
            self.report(node, self.MESSAGE)
