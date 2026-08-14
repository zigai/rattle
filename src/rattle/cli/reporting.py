from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from stdl.st import colored

from rattle.config import (
    generate_config,
)
from rattle.config.models import Config, Options
from rattle.diagnostics import Result
from rattle.engine import Metrics
from rattle.rendering.console import AsyncConsole
from rattle.rendering.models import OutputFormat
from rattle.rendering.results import render_console_result


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
        reports = [colored(f"{len(visited)} {f(len(visited))} checked")]
        if violations:
            reports.append(
                colored(
                    f"{violations} violation{'s' if violations != 1 else ''} "
                    f"in {len(violation_files)} {f(len(violation_files))}",
                    color="yellow",
                    style="bold",
                )
            )
        if error_files:
            reports.append(
                colored(
                    f"{len(error_files)} {f(len(error_files))} with errors",
                    color="yellow",
                    style="bold",
                )
            )
        if autofixes:
            reports.append(colored(f"{autofixes} autofixable", style="bold"))
        if fixed:
            word = "fix" if fixed == 1 else "fixes"
            reports.append(colored(f"{fixed} {word} applied", style="bold"))

        return ", ".join(reports)

    if not visited:
        return "No Python files found"

    return f"{len(visited)} {f(len(visited))} clean"


def _submit_result(
    console: AsyncConsole,
    result: Result,
    *,
    show_diff: bool,
    stderr: bool = False,
    output_format: OutputFormat,
    output_template: str,
    brief: bool,
    brief_rule_width: int | None = None,
) -> bool:
    rendered = render_console_result(
        result,
        path=_display_path(result.path),
        show_diff=show_diff,
        output_format=output_format,
        output_template=output_template,
        brief=brief,
        brief_rule_width=brief_rule_width,
    )
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
    return lambda metrics: console.submit(str(metrics))


def _print_stats(console: AsyncConsole, stats: Counter[str]) -> None:
    if not stats:
        return

    console.submit("Violation stats by rule:", err=True)
    width = max(len(rule_name) for rule_name in stats)
    for rule_name, count in sorted(stats.items()):
        console.submit(f"  {rule_name:<{width}}  {count}", err=True)


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
    state: LintState = field(default_factory=LintState)

    def record(self, result: Result) -> None:
        self.state.visited.add(result.path)
        if not result.violation and not result.error:
            return

        config = result.config or generate_config(result.path, options=self.options)
        _record_lint_result(result, config, state=self.state, stats=self.stats)

    def submit(self) -> None:
        if not self.quiet:
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
            self.state.exit_code |= 2

        if not self.quiet:
            _submit_result(
                self.console,
                result,
                show_diff=False,
                stderr=self.is_stdin,
                output_format=config.output_format,
                output_template=config.output_template,
                brief=self.compact,
            )

    def submit_applied_fix(self, result: Result, *, show_diff: bool) -> None:
        violation = result.violation
        if self.quiet or violation is None or not violation.autofixable:
            return

        config = _result_config(result, self.options)
        _submit_result(
            self.console,
            result,
            show_diff=show_diff,
            stderr=self.is_stdin,
            output_format=config.output_format,
            output_template=config.output_template,
            brief=self.compact,
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
        state.exit_code |= 2


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
            show_diff=diff,
            output_format=config.output_format,
            output_template=config.output_template,
            brief=compact,
            brief_rule_width=compact_rule_width,
        )


__all__ = ["FixReport", "LintReport"]
