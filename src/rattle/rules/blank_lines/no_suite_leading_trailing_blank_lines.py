from __future__ import annotations

from collections.abc import Sequence

import libcst as cst

from rattle import Invalid, LintRule, Valid
from rattle.rules.blank_lines.base import BaseBlankLinesRule
from rattle.rules.blank_lines.utils import is_blank_line, statement_leading_lines


class NoSuiteLeadingTrailingBlankLines(BaseBlankLinesRule, LintRule):
    """Disallow leading/trailing empty lines at suite boundaries."""

    LEADING_MESSAGE = "Leading blank lines in a suite are not allowed."
    TRAILING_MESSAGE = "Trailing blank lines in a suite are not allowed."

    VALID = [
        Valid(
            """
            def f() -> int:
                value = 1
                return value
            """
        ),
        Valid(
            """
            def f() -> int:
                # comment lines are separators, not blank lines
                value = 1
                return value
            """
        ),
        Valid(
            """
            def f(items: list[int]) -> None:

                def emit() -> None:
                    print(items)
            """
        ),
        Valid(
            """
            def f(items: list[int]) -> None:
                for item in items:

                    @track(item)
                    def emit() -> None:
                        print(item)
            """
        ),
    ]
    INVALID = [
        Invalid(
            """
            def f() -> int:

                value = 1
                return value
            """,
            expected_replacement="""
            def f() -> int:
                value = 1
                return value
            """,
            expected_message=LEADING_MESSAGE,
        ),
        Invalid(
            """
            def f(items: list[int]) -> None:


                def emit() -> None:
                    print(items)
            """,
            expected_replacement="""
            def f(items: list[int]) -> None:

                def emit() -> None:
                    print(items)
            """,
            expected_message=LEADING_MESSAGE,
        ),
        Invalid(
            """
            def f(items: list[int]) -> None:
                for item in items:


                    @track(item)
                    def emit() -> None:
                        print(item)
            """,
            expected_replacement="""
            def f(items: list[int]) -> None:
                for item in items:

                    @track(item)
                    def emit() -> None:
                        print(item)
            """,
            expected_message=LEADING_MESSAGE,
        ),
        Invalid(
            """
            def f() -> int:
                value = 1
                return value

            """,
            expected_replacement="""
            def f() -> int:
                value = 1
                return value
            """,
            expected_message=TRAILING_MESSAGE,
        ),
    ]

    def visit_Module(self, node: cst.Module) -> None:
        self._set_source_lines(node)
        self._check_suite(node, node.body, node.footer)

    def visit_IndentedBlock(self, node: cst.IndentedBlock) -> None:
        self._check_suite(node, node.body, node.footer)

    def _check_suite(
        self,
        suite: cst.Module | cst.IndentedBlock,
        body: Sequence[cst.BaseStatement],
        footer: Sequence[cst.EmptyLine],
    ) -> None:
        if body:
            first_statement = body[0]
            allowed_blank_prefix = self._allowed_leading_blank_prefix(suite, first_statement)
            drop_count = 0
            leading_lines = statement_leading_lines(first_statement)
            for leading_line in leading_lines:
                if is_blank_line(leading_line):
                    drop_count += 1
                    continue
                break

            if drop_count > allowed_blank_prefix:
                replacement = first_statement.with_changes(
                    leading_lines=tuple(leading_lines[drop_count - allowed_blank_prefix :])
                )
                self.report(
                    first_statement,
                    message=self.LEADING_MESSAGE,
                    replacement=replacement,
                )
        keep_count = len(footer)
        while keep_count > 0 and is_blank_line(footer[keep_count - 1]):
            keep_count -= 1

        if keep_count != len(footer):
            suite_replacement = suite.with_changes(footer=tuple(footer[:keep_count]))
            self.report(
                suite,
                message=self.TRAILING_MESSAGE,
                replacement=suite_replacement,
            )

    def _allowed_leading_blank_prefix(
        self,
        suite: cst.Module | cst.IndentedBlock,
        first_statement: cst.BaseStatement,
    ) -> int:
        if not isinstance(first_statement, (cst.ClassDef, cst.FunctionDef)):
            return 0

        if isinstance(suite, cst.Module):
            return 0

        parent = self.get_metadata(cst.metadata.ParentNodeProvider, suite)
        if isinstance(parent, cst.FunctionDef):
            return 1

        if isinstance(parent, cst.ClassDef):
            return 0

        if all(is_blank_line(line) for line in first_statement.leading_lines):
            return 1

        return 0


__all__ = ["NoSuiteLeadingTrailingBlankLines"]
