from __future__ import annotations

import logging
from collections.abc import Collection, Generator
from dataclasses import replace
from pathlib import Path

from libcst import ParserSyntaxError

from rattle.ast import AstParseError
from rattle.config.models import Config
from rattle.diagnostics import FileContent, LintViolation, Result
from rattle.engine import LintRunner, MetricsHook, diff_module
from rattle.errors import RattleError
from rattle.formatting import format_module
from rattle.rule import LintRule, RuleConfigurationError
from rattle.rule_loading import collect_rules

LOG = logging.getLogger(__name__)


def _drive_rattle_bytes(
    runner: Generator[Result, bool, FileContent | None],
    *,
    cacheable: bool,
) -> Generator[Result, bool, tuple[FileContent | None, bool, bool, list[LintViolation]]]:
    clean = True
    cache_violations: list[LintViolation] = []

    try:
        result = next(runner)
    except StopIteration as e:
        return e.value, clean, cacheable, cache_violations

    while True:
        if result.violation or result.error:
            clean = False
        if result.error:
            cacheable = False
        if result.violation:
            cache_violations.append(result.violation)
        send_value = yield result
        try:
            result = runner.send(bool(send_value))
        except StopIteration as e:
            return e.value, clean, cacheable, cache_violations


def _rattle_bytes_autofix_with_diff(
    path: Path,
    content: FileContent,
    *,
    config: Config,
    rules: Collection[LintRule],
    metrics_hook: MetricsHook | None,
) -> Generator[Result, bool, FileContent | None]:
    runner = LintRunner(path, content)
    violations = list(
        runner.collect_violations(
            rules,
            config,
            metrics_hook,
            include_diff=False,
        )
    )
    if not violations:
        yield Result(path, violation=None, source=content, config=config)
        return None

    pending_fixes = [violation for violation in violations if violation.replacement]
    updated = runner.apply_replacements(pending_fixes) if pending_fixes else None
    aggregate_diff = diff_module(path, runner.module, updated) if updated else ""
    diff_consumed = False
    for violation in violations:
        if aggregate_diff and violation.replacement and not diff_consumed:
            violation = replace(violation, diff=aggregate_diff)
            diff_consumed = True
        yield Result(path, violation, source=content, config=config)

    if updated:
        return format_module(updated, path, config)
    return None


def rattle_bytes(
    path: Path,
    content: FileContent,
    *,
    config: Config,
    autofix: bool = False,
    include_diff: bool = False,
    rules: Collection[LintRule] | None = None,
    metrics_hook: MetricsHook | None = None,
) -> Generator[Result, bool, FileContent | None]:
    """
    Lint raw bytes content representing a single path, using the given configuration.

    Yields :class:`Result` objects for each lint error or exception found, or a single
    empty result if the file is clean. A file is considered clean if no lint errors or
    no rules are enabled for the given path.
    Returns the final :class:`FileContent` including any fixes applied.

    Use :func:`capture` to more easily capture return value after iterating through
    violations. Use ``generator.send(...)`` with a boolean value to apply individual
    fixes for each violation.

    If ``autofix`` is ``True``, all violations with replacements will be applied
    automatically, even if ``False`` is sent back to the generator.

    """
    try:
        rules = rules if rules is not None else collect_rules(config)

        if not rules:
            yield Result(path, violation=None, source=content, config=config)
            return None

        if autofix and include_diff:
            return (
                yield from _rattle_bytes_autofix_with_diff(
                    path,
                    content,
                    config=config,
                    rules=rules,
                    metrics_hook=metrics_hook,
                )
            )

        runner = LintRunner(path, content)
        pending_fixes: list[LintViolation] = []

        clean = True
        for violation in runner.collect_violations(
            rules, config, metrics_hook, include_diff=include_diff
        ):
            clean = False
            fix = yield Result(path, violation, source=content, config=config)
            if fix or autofix:
                pending_fixes.append(violation)

        if clean:
            yield Result(path, violation=None, source=content, config=config)

        if pending_fixes:
            updated = runner.apply_replacements(pending_fixes)
            return format_module(updated, path, config)

    except (
        AstParseError,
        ParserSyntaxError,
        RattleError,
        RuleConfigurationError,
        UnicodeError,
    ) as e:
        # TODO: this is not the right place to catch errors
        LOG.debug("Linting failed with %s", type(e).__name__)
        yield Result.from_exception(
            path,
            e,
            operation="Linting content",
            source=content,
            config=config,
        )

    return None


__all__ = ["rattle_bytes"]
