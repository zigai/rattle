from __future__ import annotations

import fnmatch
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import libcst as cst
from libcst.metadata import FilePathProvider, ParentNodeProvider, PositionProvider

from rattle import CodePosition, LintRule, RuleSetting
from rattle.rules.helpers import matches_exact_path, matches_path

_SETTING_NAMES = frozenset({"max_file_lines", "max_function_lines", "max_method_lines"})


@dataclass(frozen=True)
class LineCountLimits:
    max_file_lines: int
    max_function_lines: int
    max_method_lines: int


def _validate_non_negative_int(value: object) -> bool:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"expected a non-negative integer, got {value!r}")

    return True


def _validate_limit_table(value: object) -> bool:
    assert isinstance(value, Mapping)

    for path_pattern, limits in value.items():
        if not path_pattern:
            raise ValueError("expected non-empty path pattern")

        if not limits:
            raise ValueError(f"expected at least one limit for path pattern {path_pattern!r}")

        unknown_settings = sorted(set(limits) - _SETTING_NAMES)
        if unknown_settings:
            expected = ", ".join(sorted(_SETTING_NAMES))
            raise ValueError(
                f"unexpected setting(s) {unknown_settings!r} for path pattern {path_pattern!r}; "
                f"expected one of {expected}"
            )

        for setting_name, limit in limits.items():
            if limit < 0:
                raise ValueError(
                    f"expected non-negative {setting_name} for path pattern {path_pattern!r}"
                )

    return True


def _apply_limits(
    limits: LineCountLimits,
    configured_limits: dict[str, int],
) -> LineCountLimits:
    return LineCountLimits(
        max_file_lines=configured_limits.get("max_file_lines", limits.max_file_lines),
        max_function_lines=configured_limits.get(
            "max_function_lines",
            limits.max_function_lines,
        ),
        max_method_lines=configured_limits.get("max_method_lines", limits.max_method_lines),
    )


def _line_span(range_start_line: int, range_end_line: int) -> int:
    return range_end_line - range_start_line + 1


def _glob_specificity(pattern: str) -> tuple[int, int, int]:
    wildcard_count = sum(pattern.count(character) for character in "*?[")
    literal_count = len(pattern) - wildcard_count
    return literal_count, -wildcard_count, len(pattern)


class LineCountLimit(LintRule):
    """Limit file, function, and method length with optional path-specific settings."""

    MESSAGE = "{target} has {actual_lines} lines, exceeding the configured limit of {max_lines}."
    METADATA_DEPENDENCIES = (
        *LintRule.METADATA_DEPENDENCIES,
        FilePathProvider,
        ParentNodeProvider,
        PositionProvider,
    )
    SETTINGS = {
        "max_file_lines": RuleSetting(
            int,
            default=0,
            validator=_validate_non_negative_int,
            description="Maximum lines allowed in a file. Set to 0 to disable.",
        ),
        "max_function_lines": RuleSetting(
            int,
            default=0,
            validator=_validate_non_negative_int,
            description="Maximum lines allowed in top-level functions. Set to 0 to disable.",
        ),
        "max_method_lines": RuleSetting(
            int,
            default=0,
            validator=_validate_non_negative_int,
            description="Maximum lines allowed in methods. Set to 0 to disable.",
        ),
        "glob_limits": RuleSetting(
            dict[str, dict[str, int]],
            default={},
            validator=_validate_limit_table,
            description=(
                "Glob-specific limit settings keyed by path glob. More specific matching globs "
                "override less specific matching globs."
            ),
        ),
        "per_file_limits": RuleSetting(
            dict[str, dict[str, int]],
            default={},
            validator=_validate_limit_table,
            description=(
                "Exact per-file limit settings keyed by repo-relative path. These override "
                "base settings and glob_limits."
            ),
        ),
    }

    VALID = ()
    INVALID = ()

    def __init__(self) -> None:
        super().__init__()

        self._current_file_path: Path | None = None
        self._current_limits = LineCountLimits(
            max_file_lines=0,
            max_function_lines=0,
            max_method_lines=0,
        )
        self._function_depth = 0

    def visit_Module(self, node: cst.Module) -> None:
        file_path = self.get_metadata(FilePathProvider, node, None)
        self._current_file_path = file_path if isinstance(file_path, Path) else None
        self._current_limits = self._limits_for_current_file()

        max_file_lines = self._current_limits.max_file_lines
        if max_file_lines <= 0:
            return

        line_count = len(node.code.splitlines())
        if line_count <= max_file_lines:
            return

        self.report(
            node,
            self.MESSAGE.format(
                target="File",
                actual_lines=line_count,
                max_lines=max_file_lines,
            ),
            position=CodePosition(line=1, column=0),
        )

    def leave_Module(self, original_node: cst.Module) -> None:
        del original_node

        self._current_file_path = None
        self._current_limits = LineCountLimits(
            max_file_lines=0,
            max_function_lines=0,
            max_method_lines=0,
        )

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        is_method = self._is_class_member(node)
        is_nested_function = self._function_depth > 0 and not is_method
        max_lines = (
            self._current_limits.max_method_lines
            if is_method
            else self._current_limits.max_function_lines
        )
        self._function_depth += 1

        if is_nested_function or max_lines <= 0:
            return

        range_node = node.decorators[0] if node.decorators else node
        code_range = self.get_metadata(PositionProvider, range_node, None)
        definition_range = self.get_metadata(PositionProvider, node, None)
        if code_range is None or definition_range is None:
            return

        line_count = _line_span(code_range.start.line, definition_range.end.line)
        if line_count <= max_lines:
            return

        target_kind = "Method" if is_method else "Function"
        self.report(
            node.name,
            self.MESSAGE.format(
                target=f"{target_kind} '{node.name.value}'",
                actual_lines=line_count,
                max_lines=max_lines,
            ),
        )

    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        del original_node

        self._function_depth -= 1

    def _limits_for_current_file(self) -> LineCountLimits:
        limits = LineCountLimits(
            max_file_lines=self.setting("max_file_lines", int),
            max_function_lines=self.setting("max_function_lines", int),
            max_method_lines=self.setting("max_method_lines", int),
        )
        if self._current_file_path is None:
            return limits

        glob_limits = self.setting("glob_limits", dict[str, dict[str, int]])
        for path_pattern, configured_limits in sorted(
            glob_limits.items(), key=lambda item: _glob_specificity(item[0])
        ):
            if not self._matches_glob_path(path_pattern, self._current_file_path):
                continue

            limits = _apply_limits(limits, configured_limits)

        per_file_limits = self.setting("per_file_limits", dict[str, dict[str, int]])
        for path_pattern, configured_limits in per_file_limits.items():
            if not self._matches_per_file_path(path_pattern, self._current_file_path):
                continue

            limits = _apply_limits(limits, configured_limits)

        return limits

    def _matches_glob_path(self, path_pattern: str, file_path: Path) -> bool:
        if matches_path(path_pattern, file_path):
            return True

        if Path(path_pattern).is_absolute():
            return False

        normalized_path = file_path.as_posix()
        normalized_pattern = Path(path_pattern).as_posix()
        return fnmatch.fnmatchcase(normalized_path, f"*/{normalized_pattern}")

    def _is_class_member(self, node: cst.FunctionDef) -> bool:
        current: cst.CSTNode = node
        while (parent := self.get_metadata(ParentNodeProvider, current, None)) is not None:
            if isinstance(parent, cst.ClassDef):
                return True
            if isinstance(parent, (cst.FunctionDef, cst.Lambda)):
                return False
            current = parent
        return False

    def _matches_per_file_path(self, path_pattern: str, file_path: Path) -> bool:
        if matches_exact_path(path_pattern, file_path):
            return True

        normalized_path = file_path.as_posix()
        normalized_pattern = Path(path_pattern).as_posix()
        return normalized_path == normalized_pattern or normalized_path.endswith(
            f"/{normalized_pattern}"
        )
