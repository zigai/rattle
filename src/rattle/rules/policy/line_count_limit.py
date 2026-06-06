from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path

import libcst as cst
from libcst.metadata import FilePathProvider, PositionProvider

from rattle import CodePosition, Invalid, LintRule, RuleSetting, Valid

_SETTING_NAMES = frozenset({"max_file_lines", "max_function_lines", "max_method_lines"})


@dataclass(frozen=True)
class _LineCountLimits:
    max_file_lines: int
    max_function_lines: int
    max_method_lines: int


def _validate_non_negative_int(value: object) -> bool:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"expected a non-negative integer, got {value!r}")

    return True


def _path_candidates(path: Path) -> tuple[str, ...]:
    candidates = [path.as_posix(), path.name]
    try:
        candidates.append(path.relative_to(Path.cwd()).as_posix())
    except ValueError:
        pass

    return tuple(dict.fromkeys(candidates))


def _matches_path(pattern: str, path: Path) -> bool:
    return any(fnmatch.fnmatchcase(candidate, pattern) for candidate in _path_candidates(path))


def _matches_exact_path(expected_path: str, path: Path) -> bool:
    return expected_path in _path_candidates(path)


def _validate_limit_table(value: object) -> bool:
    assert isinstance(value, dict)

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
    limits: _LineCountLimits,
    configured_limits: dict[str, int],
) -> _LineCountLimits:
    return _LineCountLimits(
        max_file_lines=configured_limits.get("max_file_lines", limits.max_file_lines),
        max_function_lines=configured_limits.get(
            "max_function_lines",
            limits.max_function_lines,
        ),
        max_method_lines=configured_limits.get("max_method_lines", limits.max_method_lines),
    )


def _line_span(range_start_line: int, range_end_line: int) -> int:
    return range_end_line - range_start_line + 1


class LineCountLimit(LintRule):
    """Limit file, function, and method length with optional path-specific settings."""

    MESSAGE = "{target} has {actual_lines} lines, exceeding the configured limit of {max_lines}."
    TAGS = {"architecture", "style"}
    METADATA_DEPENDENCIES = (*LintRule.METADATA_DEPENDENCIES, FilePathProvider, PositionProvider)
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

    VALID = [
        Valid(
            """
            def small() -> None:
                pass
            """,
            options={"max_function_lines": 3},
        ),
        Valid(
            """
            class Service:
                def small(self) -> None:
                    pass
            """,
            options={"max_method_lines": 3},
        ),
        Valid(
            """
            def large() -> None:
                pass

                pass
            """,
            options={
                "max_function_lines": 2,
                "glob_limits": {"*": {"max_function_lines": 10}},
            },
        ),
    ]

    INVALID = [
        Invalid(
            """
            def oversized() -> None:
                first()
                second()
            """,
            expected_message=(
                "Function 'oversized' has 3 lines, exceeding the configured limit of 2."
            ),
            options={"max_function_lines": 2},
        ),
        Invalid(
            """
            class Service:
                def oversized(self) -> None:
                    first()
                    second()
            """,
            expected_message=(
                "Method 'oversized' has 3 lines, exceeding the configured limit of 2."
            ),
            options={"max_method_lines": 2},
        ),
        Invalid(
            """
            one()
            two()
            three()
            """,
            expected_message="File has 3 lines, exceeding the configured limit of 2.",
            options={"max_file_lines": 2},
        ),
    ]

    def __init__(self) -> None:
        super().__init__()

        self._current_file_path: Path | None = None
        self._current_limits = _LineCountLimits(
            max_file_lines=0,
            max_function_lines=0,
            max_method_lines=0,
        )
        self._class_depth = 0
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
        self._current_limits = _LineCountLimits(
            max_file_lines=0,
            max_function_lines=0,
            max_method_lines=0,
        )

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        del node

        self._class_depth += 1

    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        del original_node

        self._class_depth -= 1

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        is_method = self._class_depth > 0 and self._function_depth == 0
        max_lines = (
            self._current_limits.max_method_lines
            if is_method
            else self._current_limits.max_function_lines
        )
        self._function_depth += 1

        if max_lines <= 0:
            return

        code_range = self.get_metadata(PositionProvider, node, None)
        if code_range is None:
            return

        line_count = _line_span(code_range.start.line, code_range.end.line)
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

    def _limits_for_current_file(self) -> _LineCountLimits:
        limits = _LineCountLimits(
            max_file_lines=self.settings["max_file_lines"],
            max_function_lines=self.settings["max_function_lines"],
            max_method_lines=self.settings["max_method_lines"],
        )
        if self._current_file_path is None:
            return limits

        glob_limits = self.settings["glob_limits"]
        for path_pattern, configured_limits in sorted(
            glob_limits.items(), key=lambda item: len(item[0])
        ):
            if not _matches_path(path_pattern, self._current_file_path):
                continue

            limits = _apply_limits(limits, configured_limits)

        per_file_limits = self.settings["per_file_limits"]
        for path_pattern, configured_limits in per_file_limits.items():
            if not _matches_exact_path(path_pattern, self._current_file_path):
                continue

            limits = _apply_limits(limits, configured_limits)

        return limits
