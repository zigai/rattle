from __future__ import annotations

from collections.abc import Sequence

import libcst as cst

from rattle import Invalid, LintRule, RuleSetting, Valid
from rattle.rules.blank_lines.base import BaseBlockHeaderCuddleRule, validate_non_negative_int


class BlockHeaderCuddleRelaxed(BaseBlockHeaderCuddleRule, LintRule):
    """Require a blank line before a block unrelated to the preceding statements."""

    NAME = "blank-line-before-unrelated-block"
    SOURCE_PATTERNS = (b":",)

    STRICT = False
    BODY_USAGE_LOOKAHEAD = 4
    SETTINGS = {
        "body_usage_lookahead": RuleSetting(
            int,
            default=4,
            validator=validate_non_negative_int,
            description="Number of block statements checked for uses of preceding values.",
        ),
        "setup_run_lookback": RuleSetting(
            int,
            default=3,
            validator=validate_non_negative_int,
            description="Number of preceding setup statements that may remain next to a block.",
        ),
        "allow_setup_before_compact_guard_ladder": RuleSetting(
            bool,
            default=True,
            description="Allow setup statements before consecutive early-exit branches.",
        ),
    }
    MESSAGE = (
        "Add a blank line before this block; the preceding statements do not prepare "
        "values used by it."
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
                    result = prepared
                    return result

                return 0
            """
        ),
        Valid(
            """
            def f(value: int) -> int:
                log_start()
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
                not_used = value + 2

                if value > 0:
                    return value

                return prepared
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
        Valid(
            """
            def f(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
                merged = dict(base)
                for key, value in override.items():
                    if key not in merged:
                        merged[key] = value
                        continue
                    merged[key] = value

                return merged
            """
        ),
        Valid(
            """
            def f(directory: str) -> None:
                queue = Queue()
                queue.put(directory)
                while not queue.empty():
                    item = queue.get()
                    visit(item)
            """
        ),
        Valid(
            """
            def f(shell_name: str) -> list[str]:
                interactive = shell_name == "zsh"
                if shell_name == "zsh":
                    return ["-lic"]
                if interactive:
                    return ["-ic"]
                return ["-lc"]
            """
        ),
        Valid(
            """
            def f(candidate: object, parser_input: str, style: object) -> object:
                display_value = parser_input or str(candidate)
                if supports_live_interaction():
                    highlight(display_value, style)
                else:
                    summarize(display_value, style)
                return candidate
            """
        ),
        Valid(
            """
            def f(override_name: str | None) -> str:
                display_name = "guest"
                if override_name is not None:
                    display_name = override_name
                return display_name
            """
        ),
        Valid(
            """
            def f(default_value: object) -> dict[str, object]:
                prompt_kwargs: dict[str, object] = {}
                if default_value:
                    prompt_kwargs["placeholder"] = str(default_value)
                return prompt_kwargs
            """
        ),
        Valid(
            """
            def f() -> None:
                session = build_session()
                session.refresh()
                if session.is_stale():
                    reset_session(session)
                    return
                cleanup()
            """
        ),
    ]

    def _assignment_run(
        self,
        body: Sequence[cst.BaseStatement],
        block_index: int,
    ) -> Sequence[cst.BaseStatement]:
        return body[block_index - 1 : block_index]

    INVALID = [
        Invalid(
            """
            def f(value: int) -> int:
                prepared = value + 1
                if value > 0:
                    return value

                return 0
            """,
            expected_replacement="""
            def f(value: int) -> int:
                prepared = value + 1

                if value > 0:
                    return value

                return 0
            """,
            expected_message=MESSAGE,
        ),
        Invalid(
            """
            def f(value: int) -> int:
                prepared = value + 1
                log(prepared)
                if prepared > 0:
                    return prepared

                return 0
            """,
            expected_replacement="""
            def f(value: int) -> int:
                prepared = value + 1
                log(prepared)

                if prepared > 0:
                    return prepared

                return 0
            """,
            expected_message=MESSAGE,
        ),
        Invalid(
            """
            def f(value: int) -> int:
                prepared = value + 1
                trailing = value + 2
                if prepared > 0:
                    return prepared

                return 0
            """,
            expected_replacement="""
            def f(value: int) -> int:
                prepared = value + 1
                trailing = value + 2

                if prepared > 0:
                    return prepared

                return 0
            """,
            expected_message=MESSAGE,
        ),
        Invalid(
            """
            def f(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
                merged = dict(base)
                for key, value in override.items():
                    log_key(key)
                    audit(value)
                    publish(key, value)
                    notify_team(key)
                    merged[key] = value

                return merged
            """,
            expected_replacement="""
            def f(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
                merged = dict(base)

                for key, value in override.items():
                    log_key(key)
                    audit(value)
                    publish(key, value)
                    notify_team(key)
                    merged[key] = value

                return merged
            """,
            expected_message=MESSAGE,
        ),
    ]


__all__ = ["BlockHeaderCuddleRelaxed"]
