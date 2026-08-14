from __future__ import annotations

from pathlib import Path

from rattle.api import rattle_paths
from rattle.cli.options import _resolve_input_paths, build_options, usage_error
from rattle.cli.reporting import LintReport, _metrics_hook
from rattle.rendering.console import AsyncConsole


def lint(
    *paths: Path,
    rules: str | None = None,
    jobs: int | None = None,
    config: Path | None = None,
    exclude: list[str] | None = None,
    extend_exclude: list[str] | None = None,
    diff: bool = False,
    compact: bool = False,
    stats: bool = False,
    quiet: bool = False,
) -> None:
    """
    Check files for Rattle violations.

    Args:
        paths: Files or directories to check. Use "- PATH" to check code from stdin as PATH.
        quiet: Print only the final summary.
        config: Use this config file instead of discovered configuration.
        exclude: Replace configured exclude patterns.
        extend_exclude: Add exclude patterns.
        jobs: Number of worker processes to use when linting multiple files.
        rules: Override configured rules with comma-separated selectors.
        compact: Print compact diagnostics.
        diff: Show available fixes as unified diffs.
        stats: Print violation counts by rule.

    pass "- PATH" to read stdin and treat it as PATH
    """
    if quiet and diff:
        usage_error("--quiet and --diff cannot be used together")
    if quiet and stats:
        usage_error("--quiet and --stats cannot be used together")

    paths = _resolve_input_paths(paths)

    runtime_options = build_options(
        config=config,
        exclude=exclude,
        extend_exclude=extend_exclude,
        jobs=jobs,
        rules=rules,
    )
    console = AsyncConsole()
    report = LintReport(
        console=console,
        options=runtime_options,
        diff=diff,
        compact=compact,
        quiet=quiet,
        stats=stats,
    )
    try:
        for result in rattle_paths(
            paths,
            include_diff=diff,
            allow_cached_dirty_results=True,
            options=runtime_options,
            metrics_hook=_metrics_hook(console, enabled=runtime_options.print_metrics),
        ):
            report.record(result)

        report.submit()
    finally:
        console.close()
    if report.state.exit_code:
        raise SystemExit(report.state.exit_code)


__all__ = ["lint"]
