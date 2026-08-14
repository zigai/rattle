from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from libcst import CSTNode, CSTNodeT, FlattenSentinel, ParserSyntaxError, RemovalSentinel
from libcst._add_slots import add_slots
from libcst.metadata import CodePosition, CodeRange

from rattle.errors import RattleError, RattleExecutionError

if TYPE_CHECKING:
    from rattle.config.models import Config

FileContent = bytes
NodeReplacement = CSTNodeT | FlattenSentinel[CSTNodeT] | RemovalSentinel


@add_slots
@dataclass(frozen=True)
class LintViolation:
    """An individual lint error, with an optional replacement and expected diff."""

    rule_name: str
    range: CodeRange | None
    message: str
    node: CSTNode
    replacement: NodeReplacement[CSTNode] | None
    diff: str = ""
    position_node: CSTNode | None = None

    @property
    def autofixable(self) -> bool:
        """Whether the violation includes a suggested replacement."""
        return bool(self.replacement)


@dataclass
class Result:
    """A single lint result for a given file and lint rule."""

    path: Path
    violation: LintViolation | None
    error: tuple[Exception, str] | None = None
    source: FileContent | None = None
    config: Config | None = None

    @classmethod
    def from_exception(
        cls,
        path: Path,
        error: Exception,
        *,
        operation: str = "Rattle operation",
        source: FileContent | None = None,
        config: Config | None = None,
    ) -> Result:
        from rattle.ast import AstParseError

        safe_error = (
            error
            if isinstance(error, (AstParseError, ParserSyntaxError, RattleError))
            else RattleExecutionError(operation, type(error).__name__)
        )
        return cls(
            path,
            violation=None,
            error=(safe_error, ""),
            source=source,
            config=config,
        )


__all__ = [
    "CodePosition",
    "CodeRange",
    "FileContent",
    "LintViolation",
    "NodeReplacement",
    "Result",
]
