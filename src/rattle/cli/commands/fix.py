from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from rattle.api import rattle_bytes, rattle_paths
from rattle.cli.options import _resolve_input_paths, build_options, usage_error
from rattle.cli.reporting import FixReport, _metrics_hook
from rattle.config import (
    generate_config,
)
from rattle.config.models import Config
from rattle.diagnostics import FileContent, Result
from rattle.engine import Metrics
from rattle.rendering.console import AsyncConsole, echo, getchar
from rattle.util import capture

MAX_AUTOFIX_PASSES = 10


def _validate_fix_options(
    paths: tuple[Path, ...],
    *,
    quiet: bool,
    diff: bool,
    stats: bool,
    interactive: bool,
) -> bool:
    if quiet and diff:
        usage_error("--quiet and --diff cannot be used together")
    if quiet and stats:
        usage_error("--quiet and --stats cannot be used together")
    if quiet and interactive:
        usage_error("--quiet and --interactive cannot be used together")

    is_stdin = bool(paths[0] and str(paths[0]) == "-")
    if is_stdin and interactive:
        usage_error("--interactive cannot be used with stdin")

    return is_stdin


def _prompt_for_fix() -> tuple[bool, bool]:
    prompt = "Apply autofix? [Y]es, [n]o, [q]uit: "
    while True:
        echo(prompt, nl=False, err=True)
        answer = getchar(echo_input=True, err=True).lower()
        echo(err=True)
        if answer in {"\n", "\r", ""}:
            answer = "y"
        if answer in {"y", "n", "q"}:
            break
        echo("Press y to apply, n to skip, or q to quit fixing.", err=True)

    return answer == "y", answer == "q"


def _changed_result_paths(results: list[Result]) -> set[Path]:
    changed: set[Path] = set()
    for result in results:
        if result.source is None:
            continue
        try:
            current = result.path.read_bytes()
        except OSError:
            continue
        if current != result.source:
            changed.add(result.path)
    return changed


def _autofixable_result_count(
    results: list[Result],
    *,
    changed_paths: set[Path] | None = None,
) -> int:
    return sum(
        1
        for result in results
        if result.violation is not None
        and result.violation.autofixable
        and (changed_paths is None or result.path in changed_paths)
    )


def _submit_applied_fix_results(
    report: FixReport,
    results: list[Result],
    *,
    changed_paths: set[Path] | None,
    show_diff: bool,
) -> None:
    if not show_diff:
        return

    for result in results:
        if changed_paths is not None and result.path not in changed_paths:
            continue
        report.submit_applied_fix(result, show_diff=True)


def _collect_rattle_bytes(
    path: Path,
    content: FileContent,
    *,
    config: Config,
    autofix: bool,
    include_diff: bool,
    metrics_hook: Callable[[Metrics], None] | None,
) -> tuple[list[Result], FileContent | None]:
    runner = capture(
        rattle_bytes(
            path,
            content,
            config=config,
            autofix=autofix,
            include_diff=include_diff,
            metrics_hook=metrics_hook,
        )
    )
    results = list(runner)
    return results, runner.result


def _run_automatic_fix_path_pass(
    paths: tuple[Path, ...],
    report: FixReport,
    *,
    diff: bool,
) -> bool:
    results = list(
        rattle_paths(
            paths,
            autofix=True,
            include_diff=diff,
            options=report.options,
            parallel=True,
            metrics_hook=_metrics_hook(report.console, enabled=report.options.print_metrics),
        )
    )
    changed_paths = _changed_result_paths(results)
    fixed = _autofixable_result_count(results, changed_paths=changed_paths)
    if not fixed or not changed_paths:
        return False

    report.state.fixed += fixed
    _submit_applied_fix_results(report, results, changed_paths=changed_paths, show_diff=diff)
    return True


def _verify_fix_paths(paths: tuple[Path, ...], report: FixReport) -> None:
    for result in rattle_paths(
        paths,
        include_diff=False,
        allow_cached_dirty_results=False,
        options=report.options,
        metrics_hook=_metrics_hook(report.console, enabled=report.options.print_metrics),
    ):
        report.record_verified(result)


def _run_automatic_fix_paths(
    paths: tuple[Path, ...],
    report: FixReport,
    *,
    diff: bool,
) -> None:
    for _ in range(MAX_AUTOFIX_PASSES):
        if not _run_automatic_fix_path_pass(paths, report, diff=diff):
            break

    _verify_fix_paths(paths, report)


def _run_interactive_fix_paths(paths: tuple[Path, ...], report: FixReport) -> None:
    generator = capture(
        rattle_paths(
            paths,
            autofix=False,
            include_diff=True,
            options=report.options,
            parallel=False,
            metrics_hook=_metrics_hook(report.console, enabled=report.options.print_metrics),
        )
    )
    for result in generator:
        report.visited.add(result.path)
        violation = result.violation
        if violation is None or not violation.autofixable:
            continue

        report.submit_applied_fix(result, show_diff=True)
        report.console.flush()
        apply_fix, quit_fixing = _prompt_for_fix()
        if quit_fixing:
            report.violation_files.add(result.path)
            report.state.violations += 1
            report.state.autofixes += 1
            report.state.exit_code |= 1
            return
        if apply_fix:
            generator.respond(answer=True)
            report.state.fixed += 1

    _verify_fix_paths(paths, report)


def _run_automatic_fix_stdin(
    paths: tuple[Path, ...],
    report: FixReport,
    *,
    diff: bool,
) -> None:
    path = paths[1].resolve()
    content = sys.stdin.buffer.read()
    config = generate_config(path, options=report.options, explicit_path=True)
    if config.excluded:
        sys.stdout.buffer.write(content)
        return

    for _ in range(MAX_AUTOFIX_PASSES):
        results, updated = _collect_rattle_bytes(
            path,
            content,
            config=config,
            autofix=True,
            include_diff=diff,
            metrics_hook=_metrics_hook(report.console, enabled=report.options.print_metrics),
        )
        if updated is None or updated == content:
            break

        fixed = _autofixable_result_count(results)
        if not fixed:
            break

        report.state.fixed += fixed
        _submit_applied_fix_results(report, results, changed_paths=None, show_diff=diff)
        content = updated

    results, _ = _collect_rattle_bytes(
        path,
        content,
        config=config,
        autofix=False,
        include_diff=False,
        metrics_hook=_metrics_hook(report.console, enabled=report.options.print_metrics),
    )
    for result in results:
        report.record_verified(result)

    sys.stdout.buffer.write(content)


def fix(
    *paths: Path,
    rules: str | None = None,
    quiet: bool = False,
    jobs: int | None = None,
    config: Path | None = None,
    exclude: list[str] | None = None,
    extend_exclude: list[str] | None = None,
    diff: bool = False,
    interactive: bool = False,
    compact: bool = False,
    stats: bool = False,
) -> None:
    """
    Apply available autofixes to files.

    Args:
        paths: Files or directories to fix. Use "- PATH" to fix code from stdin as PATH and write to stdout.
        quiet: Print only the final summary.
        config: Use this config file instead of discovered configuration.
        exclude: Replace configured exclude patterns.
        extend_exclude: Add exclude patterns.
        jobs: Number of worker processes to use when linting multiple files.
        rules: Override configured rules with comma-separated selectors.
        interactive: Prompt before applying each autofix.
        compact: Print compact diagnostics.
        diff: Show applied fixes as unified diffs.
        stats: Print violation counts by rule.

    pass "- PATH" to read stdin, treat it as PATH, and write fixed code to stdout
    """
    paths = _resolve_input_paths(paths)
    is_stdin = _validate_fix_options(
        paths,
        quiet=quiet,
        diff=diff,
        stats=stats,
        interactive=interactive,
    )

    runtime_options = build_options(
        config=config,
        exclude=exclude,
        extend_exclude=extend_exclude,
        jobs=jobs,
        rules=rules,
    )

    console = AsyncConsole()
    report = FixReport(
        console=console,
        options=runtime_options,
        is_stdin=is_stdin,
        quiet=quiet,
        compact=compact,
        stats=stats,
    )
    try:
        if is_stdin:
            _run_automatic_fix_stdin(paths, report, diff=diff)
        elif interactive:
            _run_interactive_fix_paths(paths, report)
        else:
            _run_automatic_fix_paths(paths, report, diff=diff)

        report.submit()
    finally:
        console.close()
    if report.state.exit_code:
        raise SystemExit(report.state.exit_code)


__all__ = ["fix"]
