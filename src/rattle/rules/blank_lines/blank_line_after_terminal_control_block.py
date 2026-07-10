from __future__ import annotations

from collections.abc import Sequence

import libcst as cst

from rattle import Invalid, LintRule, RuleSetting, Valid
from rattle.rules.blank_lines.base import BaseBlankLinesRule
from rattle.rules.blank_lines.utils import (
    control_block_statement_groups,
    has_separator,
    is_branch_statement,
    is_compact_guard_if,
    is_control_block_statement,
    is_header_block_statement,
    is_single_line_control_block,
    prepend_blank_line,
)


class BlankLineAfterTerminalControlBlock(BaseBlankLinesRule, LintRule):
    """Require a blank line after control-flow blocks whose body always exits."""

    SOURCE_PATTERNS = (b"return", b"raise", b"break", b"continue")
    MESSAGE = "Add a blank line after this early-exit control-flow block."
    SETTINGS = {
        "allow_compact_guard_ladders": RuleSetting(
            bool,
            default=True,
            description="Allow consecutive early-exit branches without extra blank lines.",
        ),
    }

    VALID = [
        Valid(
            """
            def normalize(value: str | None) -> str:
                if value is None:
                    return ""

                cleaned = value.strip()
                return cleaned
            """
        ),
        Valid(
            """
            def shell_args(shell_name: str, interactive: bool) -> list[str]:
                if shell_name == "zsh":
                    return ["-lic"]
                if interactive:
                    return ["-ic"]
                return ["-lc"]
            """
        ),
        Valid(
            """
            def consume(name: str) -> str:
                parts: list[str] = []
                index = 0
                while index < len(name):
                    ch = name[index]
                    if ch in {"'", '"'}:
                        end = _consume_quoted_segment(name, index)
                        parts.append(name[index:end])
                        index = end
                        continue

                    parts.append(ch)
                    index += 1

                return "".join(parts)
            """
        ),
        Valid(
            """
            def collect(values: list[int]) -> list[int]:
                result: list[int] = []
                for value in values:
                    if value < 0:
                        continue

                    result.append(value)

                return result
            """
        ),
        Valid(
            """
            def render(parser: object, capsys: object) -> object:
                try:
                    parser.run()
                except SystemExit:
                    pass
                out = capsys.readouterr()
                return out
            """
        ),
    ]
    INVALID = [
        Invalid(
            """
            def normalize(value: str | None) -> str:
                if value is None:
                    return ""
                cleaned = value.strip()
                return cleaned
            """,
            expected_replacement="""
            def normalize(value: str | None) -> str:
                if value is None:
                    return ""

                cleaned = value.strip()
                return cleaned
            """,
            expected_message=MESSAGE,
        ),
        Invalid(
            """
            def collect(values: list[int]) -> list[int]:
                result: list[int] = []
                for value in values:
                    if value < 0:
                        continue
                    result.append(value)

                return result
            """,
            expected_replacement="""
            def collect(values: list[int]) -> list[int]:
                result: list[int] = []
                for value in values:
                    if value < 0:
                        continue

                    result.append(value)

                return result
            """,
            expected_message=MESSAGE,
        ),
        Invalid(
            """
            def parse(text: str) -> object:
                try:
                    return json.loads(text)
                except ValueError:
                    pass
                parsed = tomllib.loads(text)
                return parsed
            """,
            expected_replacement="""
            def parse(text: str) -> object:
                try:
                    return json.loads(text)
                except ValueError:
                    pass

                parsed = tomllib.loads(text)
                return parsed
            """,
            expected_message=MESSAGE,
        ),
    ]

    def visit_Module(self, node: cst.Module) -> None:
        self._set_source_lines(node)
        self._check_suite_body(node.body)

    def visit_IndentedBlock(self, node: cst.IndentedBlock) -> None:
        self._check_suite_body(node.body)

    def _check_suite_body(self, body: Sequence[cst.BaseStatement]) -> None:
        if len(body) < 2:
            return

        for index in range(len(body) - 1):
            current_statement = body[index]
            next_statement = body[index + 1]
            if self._should_skip_pair(body, index, current_statement, next_statement):
                continue

            self.report(
                next_statement,
                message=self.MESSAGE,
                position=self._first_line_range(next_statement),
                replacement=prepend_blank_line(next_statement),
            )

    def _should_skip_pair(
        self,
        body: Sequence[cst.BaseStatement],
        index: int,
        current_statement: cst.BaseStatement,
        next_statement: cst.BaseStatement,
    ) -> bool:
        return (
            not self._has_terminal_branch(current_statement)
            or is_single_line_control_block(current_statement)
            or is_header_block_statement(next_statement)
            or has_separator(next_statement)
            or self._is_compact_guard_ladder_transition(body, index, next_statement)
        )

    def _has_terminal_branch(self, statement: cst.BaseStatement) -> bool:
        if not is_control_block_statement(statement):
            return False

        return any(
            statements and is_branch_statement(statements[-1])
            for statements in control_block_statement_groups(statement)
        )

    def _is_compact_guard_ladder_transition(
        self,
        body: Sequence[cst.BaseStatement],
        index: int,
        next_statement: cst.BaseStatement,
    ) -> bool:
        if not self._allow_compact_guard_ladders():
            return False

        current_statement = body[index]
        if not is_compact_guard_if(current_statement):
            return False

        return is_compact_guard_if(next_statement) or (
            is_branch_statement(next_statement)
            and self._preceded_by_compact_guard_ladder(body, index)
        )

    def _preceded_by_compact_guard_ladder(
        self,
        body: Sequence[cst.BaseStatement],
        index: int,
    ) -> bool:
        if index <= 0:
            return False

        return not has_separator(body[index]) and is_compact_guard_if(body[index - 1])

    def _allow_compact_guard_ladders(self) -> bool:
        return bool(self.settings["allow_compact_guard_ladders"])


__all__ = ["BlankLineAfterTerminalControlBlock"]
