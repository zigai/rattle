from __future__ import annotations

from rattle import Invalid, LintRule, Valid
from rattle.rules.blank_lines.base import BaseBlockHeaderCuddleRule


class BlockHeaderCuddleStrict(BaseBlockHeaderCuddleRule, LintRule):
    """Allow only the immediately preceding assignment to remain next to a block."""

    STRICT = True
    ALLOW_FIRST_BODY_USAGE = False
    MESSAGE = (
        "Add a blank line before this block; only an immediately preceding assignment "
        "used by the block may remain attached."
    )

    VALID = [
        Valid(
            """
            def f(value: int) -> int:
                prepared = value + 1
                if prepared > 0:
                    return prepared

                return 0
            """
        ),
        Valid(
            """
            def f(value: int) -> int:
                prepared = value + 1

                if value > 0:
                    return value

                return 0
            """
        ),
        Valid(
            '''
            def f(value: int) -> int:
                """Compute value."""
                if value > 0:
                    return value

                return 0
            '''
        ),
    ]
    INVALID = [
        Invalid(
            """
            def f(value: int) -> int:
                header_value = value + 1
                trailing = value + 2
                if header_value > 0:
                    return header_value

                return 0
            """,
            expected_replacement="""
            def f(value: int) -> int:
                header_value = value + 1
                trailing = value + 2

                if header_value > 0:
                    return header_value

                return 0
            """,
            expected_message=MESSAGE,
        ),
        Invalid(
            """
            def f(value: int) -> int:
                prepared = value + 1
                if value > 0:
                    result = prepared
                    return result

                return 0
            """,
            expected_replacement="""
            def f(value: int) -> int:
                prepared = value + 1

                if value > 0:
                    result = prepared
                    return result

                return 0
            """,
            expected_message=MESSAGE,
        ),
    ]


__all__ = ["BlockHeaderCuddleStrict"]
