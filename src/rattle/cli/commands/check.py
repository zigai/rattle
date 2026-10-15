from __future__ import annotations

import sys
from pathlib import Path

from rattle.api import rattle_paths
from rattle.cli.fixing import FixRun
from rattle.cli.options import (
    STDIN,
    _resolve_input_paths,
    build_options,
    require_known_rules,
    usage_error,
)
from rattle.cli.reporting import FixReport, LintReport, _metrics_hook
from rattle.rendering.console import AsyncConsole
from rattle.rendering.models import OutputFormat


def _validate_check_options(
    *,
    fix: bool,
    interactive: bool,
    quiet: bool,
    diff: bool,
    stats: bool,
    compact: bool,
    json: bool,
    output_format: OutputFormat | None,
    output_template: str | None,
) -> None:
    if interactive and not fix:
        usage_error("--interactive requires --fix")
    if quiet and diff:
        usage_error("--quiet and --diff cannot be used together")
    if quiet and stats:
        usage_error("--quiet and --stats cannot be used together")
    if quiet and interactive:
        usage_error("--quiet and --interactive cannot be used together")
    for enabled, option in (
        (fix, "--fix"),
        (quiet, "--quiet"),
        (diff, "--diff"),
        (compact, "--compact"),
        (output_format, "--output-format"),
        (output_template, "--output-template"),
    ):
        if json and enabled:
            usage_error(f"--json and {option} cannot be used together")


def check(
    *paths: Path,
    fix: bool = False,
    rules: str | None = None,
    jobs: int | None = None,
    config: Path | None = None,
    exclude: list[str] | None = None,
    extend_exclude: list[str] | None = None,
    output_format: OutputFormat | None = None,
    output_template: str | None = None,
    diff: bool = False,
    interactive: bool = False,
    compact: bool = False,
    stats: bool = False,
    quiet: bool = False,
    json: bool = False,
) -> None:
    """
    Check files for Rattle violations and optionally apply autofixes.

    Args:
        paths: Files or directories to check. Use "- PATH" to check code from stdin as PATH; with --fix, write fixed code to stdout.
        fix: Apply available autofixes, then report remaining violations.
        quiet: Print only the final summary.
        config: Use this config file instead of discovered configuration.
        exclude: Replace configured exclude patterns.
        extend_exclude: Add exclude patterns.
        jobs: Number of worker processes to use when checking multiple files, at least 1.
        rules: Override configured rules with comma-separated selectors.
        output_format: Override the configured output format.
        output_template: Override the configured template for the custom output format.
        interactive: Prompt before applying each autofix. Requires --fix and a terminal on stdin.
        compact: Print compact diagnostics.
        diff: Show available fixes as unified diffs, or applied changes with --fix.
        stats: Print violation counts by rule.
        json: Print diagnostics as JSON. Cannot be combined with --fix.

    pass "- PATH" to read stdin and treat it as PATH
    """
    _validate_check_options(
        fix=fix,
        interactive=interactive,
        quiet=quiet,
        diff=diff,
        stats=stats,
        compact=compact,
        json=json,
        output_format=output_format,
        output_template=output_template,
    )
    paths = _resolve_input_paths(paths)
    is_stdin = paths[0] == STDIN
    if is_stdin and interactive:
        usage_error("--interactive cannot be used with stdin")
    if interactive and not sys.stdin.isatty():
        usage_error(
            "--interactive requires a terminal on stdin; "
            "run without --interactive to apply all fixes"
        )

    runtime_options = build_options(
        config=config,
        exclude=exclude,
        extend_exclude=extend_exclude,
        jobs=jobs,
        rules=rules,
        output_format=output_format,
        output_template=output_template,
    )
    require_known_rules(paths, runtime_options)
    console = AsyncConsole()
    report: FixReport | LintReport
    try:
        if fix:
            report = FixReport(
                console=console,
                options=runtime_options,
                is_stdin=is_stdin,
                quiet=quiet,
                compact=compact,
                stats=stats,
            )
            run = FixRun(paths, report, diff=diff)
            if is_stdin:
                run.run_stdin()
            elif interactive:
                run.run_interactive()
            else:
                run.run_automatic()
        else:
            report = LintReport(
                console=console,
                options=runtime_options,
                diff=diff,
                compact=compact,
                quiet=quiet,
                stats=stats,
                json=json,
            )
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


__all__ = ["check"]
