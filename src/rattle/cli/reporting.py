from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from rattle.config import (
    generate_config,
)
from rattle.config.models import Config, Options
from rattle.diagnostics import Result
from rattle.engine import Metrics
from rattle.rendering.console import AsyncConsole, colored
from rattle.rendering.models import OutputFormat
from rattle.rendering.results import ResultPresentation


def _display_path(path: Path) -> Path:
    try:
        return path.relative_to(Path.cwd())
    except ValueError:
        return path


def splash(
    visited: set[Path],
    violation_files: set[Path],
    error_files: set[Path],
    violations: int = 0,
    autofixes: int = 0,
    fixed: int = 0,
) -> str:
    def f(v: int) -> str:
        return "file" if v == 1 else "files"

    if violation_files or error_files or fixed:
        reports = [f"{len(visited)} {f(len(visited))} checked"]
        if violations:
            reports.append(
                colored(
                    f"{violations} violation{'s' if violations != 1 else ''} "
                    f"in {len(violation_files)} {f(len(violation_files))}",
                    "yellow",
                    bold=True,
                )
            )
        if error_files:
            reports.append(
                colored(
                    f"{len(error_files)} {f(len(error_files))} with errors",
                    "yellow",
                    bold=True,
                )
            )
        if autofixes:
            reports.append(colored(f"{autofixes} autofixable", bold=True))
        if fixed:
            word = "fix" if fixed == 1 else "fixes"
            reports.append(colored(f"{fixed} {word} applied", bold=True))

        return ", ".join(reports)

    if not visited:
        return "No Python files found"

    return f"{len(visited)} {f(len(visited))} clean"


def _submit_result(
    console: AsyncConsole,
    result: Result,
    presentation: ResultPresentation,
    *,
    stderr: bool = False,
) -> bool:
    rendered = presentation.render(result, path=_display_path(result.path))
    if rendered is None:
        return False
    console.submit(rendered, err=stderr)
    return True


def _metrics_hook(
    console: AsyncConsole,
    *,
    enabled: bool,
) -> Callable[[Metrics], None] | None:
    if not enabled:
        return None
    return lambda metrics: console.submit(json.dumps(metrics, sort_keys=True), err=True)


def _print_stats(console: AsyncConsole, stats: Counter[str]) -> None:
    if not stats:
        return

    name_width = max(len("Rule"), *(len(rule_name) for rule_name in stats))
    count_width = max(len("Violations"), *(len(str(count)) for count in stats.values()))
    console.submit(f"{'Rule':<{name_width}}  {'Violations':>{count_width}}", err=True)
    console.submit(f"{'─' * name_width}  {'─' * count_width}", err=True)
    for rule_name, count in sorted(stats.items()):
        console.submit(f"{rule_name:<{name_width}}  {count:>{count_width}}", err=True)


def _result_json_data(result: Result) -> dict[str, object]:
    data: dict[str, object] = {"path": _display_path(result.path).as_posix()}
    if violation := result.violation:
        code_range = violation.range
        data["rule"] = violation.rule_name
        data["message"] = violation.message
        data["autofixable"] = violation.autofixable
        data["start"] = (
            {"line": code_range.start.line, "column": code_range.start.column}
            if code_range
            else None
        )
        data["end"] = (
            {"line": code_range.end.line, "column": code_range.end.column} if code_range else None
        )
    if result.error:
        error, _ = result.error
        data["error"] = f"{type(error).__name__}: {error}"
    return data


def _result_config(result: Result, options: Options) -> Config:
    return result.config or generate_config(result.path, options=options)


@dataclass
class LintState:
    exit_code: int = 0
    violations: int = 0
    autofixes: int = 0
    visited: set[Path] = field(default_factory=set)
    violation_files: set[Path] = field(default_factory=set)
    error_files: set[Path] = field(default_factory=set)
    violation_stats: Counter[str] = field(default_factory=Counter)
    diagnostics: list[tuple[Result, Config]] = field(default_factory=list)


@dataclass
class FixState:
    exit_code: int = 0
    violations: int = 0
    autofixes: int = 0
    fixed: int = 0
    violation_stats: Counter[str] = field(default_factory=Counter)


@dataclass
class LintReport:
    console: AsyncConsole
    options: Options
    diff: bool
    compact: bool
    quiet: bool
    stats: bool
    json: bool = False
    state: LintState = field(default_factory=LintState)

    def record(self, result: Result) -> None:
        self.state.visited.add(result.path)
        if not result.violation and not result.error:
            return

        config = result.config or generate_config(result.path, options=self.options)
        _record_lint_result(result, config, state=self.state, stats=self.stats)

    def submit(self) -> None:
        if self.json:
            diagnostics = [_result_json_data(result) for result, _config in self.state.diagnostics]
            self.console.submit(json.dumps(diagnostics, ensure_ascii=False, indent=2))
        elif not self.quiet:
            _submit_lint_diagnostics(
                self.console,
                self.state.diagnostics,
                diff=self.diff,
                compact=self.compact,
            )
        self.console.submit(
            splash(
                self.state.visited,
                self.state.violation_files,
                self.state.error_files,
                self.state.violations,
                self.state.autofixes,
            ),
            err=True,
        )
        if self.stats:
            _print_stats(self.console, self.state.violation_stats)


@dataclass
class FixReport:
    console: AsyncConsole
    options: Options
    is_stdin: bool
    quiet: bool
    compact: bool
    stats: bool
    state: FixState = field(default_factory=FixState)
    visited: set[Path] = field(default_factory=set)
    violation_files: set[Path] = field(default_factory=set)
    error_files: set[Path] = field(default_factory=set)

    def record_verified(self, result: Result) -> None:
        self.visited.add(result.path)
        if not result.violation and not result.error:
            return

        config = _result_config(result, self.options)
        if result.violation:
            self.violation_files.add(result.path)
            self.state.violations += 1
            self.state.exit_code |= 1
            if result.violation.autofixable:
                self.state.autofixes += 1
            if self.stats:
                self.state.violation_stats[result.violation.rule_name] += 1
        if result.error:
            self.error_files.add(result.path)
            self.state.exit_code |= 1

        if not self.quiet:
            _submit_result(
                self.console,
                result,
                ResultPresentation(
                    output_format=config.output_format,
                    output_template=config.output_template,
                    brief=self.compact,
                ),
                stderr=self.is_stdin,
            )

    def submit_applied_fix(self, result: Result, *, show_diff: bool) -> None:
        violation = result.violation
        if self.quiet or violation is None or not violation.autofixable:
            return

        config = _result_config(result, self.options)
        _submit_result(
            self.console,
            result,
            ResultPresentation(
                output_format=config.output_format,
                output_template=config.output_template,
                show_diff=show_diff,
                brief=self.compact,
            ),
            stderr=self.is_stdin,
        )

    def submit(self) -> None:
        self.console.submit(
            splash(
                self.visited,
                self.violation_files,
                self.error_files,
                self.state.violations,
                self.state.autofixes,
                self.state.fixed,
            ),
            err=True,
        )
        if self.stats:
            _print_stats(self.console, self.state.violation_stats)


def _record_lint_result(
    result: Result,
    config: Config,
    *,
    state: LintState,
    stats: bool,
) -> None:
    state.diagnostics.append((result, config))
    if result.violation:
        state.violation_files.add(result.path)
        state.violations += 1
        if stats:
            state.violation_stats[result.violation.rule_name] += 1
        state.exit_code |= 1
        if result.violation.autofixable:
            state.autofixes += 1
    if result.error:
        state.error_files.add(result.path)
        state.exit_code |= 1


def _compact_rule_width(diagnostics: list[tuple[Result, Config]], *, compact: bool) -> int | None:
    if not compact:
        return None

    rule_names = [
        result.violation.rule_name
        for result, config in diagnostics
        if result.violation and config.output_format == OutputFormat.rattle
    ]
    if not rule_names:
        return None

    return max(len(rule_name) for rule_name in rule_names)


def _submit_lint_diagnostics(
    console: AsyncConsole,
    diagnostics: list[tuple[Result, Config]],
    *,
    diff: bool,
    compact: bool,
) -> None:
    compact_rule_width = _compact_rule_width(diagnostics, compact=compact)
    for result, config in diagnostics:
        _submit_result(
            console,
            result,
            ResultPresentation(
                output_format=config.output_format,
                output_template=config.output_template,
                show_diff=diff,
                brief=compact,
                brief_rule_width=compact_rule_width,
            ),
        )


__all__ = ["FixReport", "LintReport"]
