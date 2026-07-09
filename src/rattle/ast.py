from __future__ import annotations

import ast
import platform
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import libcst as cst
from libcst.metadata import BatchableMetadataProvider, CodePosition, CodeRange


class AstParseError(SyntaxError):
    """Raised when the running Python interpreter cannot build a requested AST."""

    def __init__(self, syntax_error: SyntaxError) -> None:
        self.syntax_error = syntax_error
        self.python_version = platform.python_version()
        self.message = syntax_error.msg
        self.line = max(syntax_error.lineno or 1, 1)
        self.column = max((syntax_error.offset or 1) - 1, 0)
        end_line = getattr(syntax_error, "end_lineno", None)
        end_column = getattr(syntax_error, "end_offset", None)
        self.end_line = end_line if isinstance(end_line, int) else None
        self.end_column = (
            max(end_column - 1, 0) if isinstance(end_column, int) and end_column > 0 else None
        )
        super().__init__(
            f"Unable to build an AST using Python {self.python_version}: {self.message}"
        )


@runtime_checkable
class _PositionedAstNode(Protocol):
    lineno: int
    col_offset: int
    end_lineno: int | None
    end_col_offset: int | None


@dataclass(frozen=True)
class AstContext:
    """A parsed Python AST and source-aware conversion to Rattle code ranges."""

    tree: ast.Module
    _source_lines: tuple[str, ...]

    def code_range(self, node: ast.AST) -> CodeRange:
        """Return the Rattle source range for a positioned AST node."""
        if (
            not isinstance(node, _PositionedAstNode)
            or node.end_lineno is None
            or node.end_col_offset is None
        ):
            raise ValueError(f"{type(node).__name__} does not have a complete source position")

        start = self._code_position(node.lineno, node.col_offset)
        end = self._code_position(node.end_lineno, node.end_col_offset)
        if (end.line, end.column) < (start.line, start.column):
            raise ValueError(f"{type(node).__name__} has an invalid source position")
        return CodeRange(start=start, end=end)

    def _code_position(self, line: int, byte_column: int) -> CodePosition:
        if line < 1 or line > len(self._source_lines):
            raise ValueError(f"AST source line {line} is outside the parsed module")
        if byte_column < 0:
            raise ValueError(f"AST source column {byte_column} cannot be negative")

        source_line = self._source_lines[line - 1]
        encoded_line = source_line.encode("utf-8")
        if byte_column > len(encoded_line):
            raise ValueError(f"AST source column {byte_column} is outside source line {line}")

        try:
            column = len(encoded_line[:byte_column].decode("utf-8"))
        except UnicodeDecodeError as e:
            raise ValueError(
                f"AST source column {byte_column} splits a character on source line {line}"
            ) from e
        return CodePosition(line=line, column=column)


class AstProvider(BatchableMetadataProvider[AstContext]):
    """Provide a cached CPython AST for the current LibCST module."""

    def visit_Module(self, node: cst.Module) -> None:
        source = node.code
        try:
            tree = ast.parse(source, type_comments=True)
        except SyntaxError as e:
            raise AstParseError(e) from e

        source_lines = tuple(source.splitlines(keepends=True))
        if not source_lines:
            source_lines = ("",)
        self.set_metadata(node, AstContext(tree=tree, _source_lines=source_lines))


__all__ = ["AstContext", "AstParseError", "AstProvider"]
