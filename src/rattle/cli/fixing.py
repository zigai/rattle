from __future__ import annotations

import sys
from pathlib import Path

from rattle.api import rattle_bytes, rattle_paths
from rattle.cli.reporting import FixReport, _metrics_hook
from rattle.config import (
    generate_config,
)
from rattle.config.models import Config
from rattle.diagnostics import FileContent, Result
from rattle.rendering.console import echo
from rattle.util import capture

MAX_AUTOFIX_PASSES = 10


def _prompt_for_fix() -> tuple[bool, bool]:
    while True:
        echo("Apply autofix? [y/N/q] ", nl=False, err=True)
        line = sys.stdin.readline()
        if not line:
            echo(err=True)
            return False, True

        answer = line.strip().lower()
        if answer in {"", "n", "no"}:
            return False, False
        if answer in {"y", "yes"}:
            return True, False
        if answer in {"q", "quit"}:
            return False, True
        echo("Answer y to apply, n to skip, or q to stop fixing.", err=True)


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


class FixRun:
    def __init__(self, paths: tuple[Path, ...], report: FixReport, *, diff: bool) -> None:
        self.paths = paths
        self.report = report
        self.diff = diff
        self.metrics_hook = _metrics_hook(report.console, enabled=report.options.print_metrics)

    def run_automatic(self) -> None:
        for _ in range(MAX_AUTOFIX_PASSES):
            if not self._run_automatic_pass():
                break

        self._verify_paths()

    def run_interactive(self) -> None:
        generator = capture(
            rattle_paths(
                self.paths,
                autofix=False,
                include_diff=True,
                options=self.report.options,
                parallel=False,
                metrics_hook=self.metrics_hook,
            )
        )
        accepted_fixes: dict[Path, int] = {}
        for result in generator:
            self.report.visited.add(result.path)
            if result.error:
                self.report.state.fixed -= accepted_fixes.pop(result.path, 0)
                self.report.record_verified(result)
                continue
            violation = result.violation
            if violation is None or not violation.autofixable:
                continue

            self.report.submit_applied_fix(result, show_diff=True)
            self.report.console.flush()
            apply_fix, quit_fixing = _prompt_for_fix()
            if quit_fixing:
                self.report.violation_files.add(result.path)
                self.report.state.violations += 1
                self.report.state.autofixes += 1
                self.report.state.exit_code |= 1
                return
            if apply_fix:
                generator.respond(answer=True)
                self.report.state.fixed += 1
                accepted_fixes[result.path] = accepted_fixes.get(result.path, 0) + 1

        self._verify_paths()

    def run_stdin(self) -> None:
        path = self.paths[1].resolve()
        content = sys.stdin.buffer.read()
        config = generate_config(path, options=self.report.options, explicit_path=True)
        if config.excluded:
            sys.stdout.buffer.write(content)
            return

        for _ in range(MAX_AUTOFIX_PASSES):
            results, updated = self._collect_bytes(
                path,
                content,
                config=config,
                autofix=True,
                include_diff=self.diff,
            )
            if updated is None or updated == content:
                break

            fixed = _autofixable_result_count(results)
            if not fixed:
                break

            self.report.state.fixed += fixed
            self._submit_applied_fixes(results, changed_paths=None)
            content = updated

        results, _ = self._collect_bytes(
            path,
            content,
            config=config,
            autofix=False,
            include_diff=False,
        )
        for result in results:
            self.report.record_verified(result)

        sys.stdout.buffer.write(content)

    def _run_automatic_pass(self) -> bool:
        results = list(
            rattle_paths(
                self.paths,
                autofix=True,
                include_diff=self.diff,
                options=self.report.options,
                parallel=True,
                metrics_hook=self.metrics_hook,
            )
        )
        changed_paths = _changed_result_paths(results)
        fixed = _autofixable_result_count(results, changed_paths=changed_paths)
        if not fixed or not changed_paths:
            return False

        self.report.state.fixed += fixed
        self._submit_applied_fixes(results, changed_paths=changed_paths)
        return True

    def _verify_paths(self) -> None:
        for result in rattle_paths(
            self.paths,
            include_diff=False,
            allow_cached_dirty_results=False,
            options=self.report.options,
            metrics_hook=self.metrics_hook,
        ):
            self.report.record_verified(result)

    def _collect_bytes(
        self,
        path: Path,
        content: FileContent,
        *,
        config: Config,
        autofix: bool,
        include_diff: bool,
    ) -> tuple[list[Result], FileContent | None]:
        runner = capture(
            rattle_bytes(
                path,
                content,
                config=config,
                autofix=autofix,
                include_diff=include_diff,
                metrics_hook=self.metrics_hook,
            )
        )
        results = list(runner)
        return results, runner.result

    def _submit_applied_fixes(
        self,
        results: list[Result],
        *,
        changed_paths: set[Path] | None,
    ) -> None:
        if not self.diff:
            return

        for result in results:
            if changed_paths is not None and result.path not in changed_paths:
                continue
            self.report.submit_applied_fix(result, show_diff=True)


__all__ = ["FixRun"]
