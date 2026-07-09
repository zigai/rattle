# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import logging
import multiprocessing
import os
import sys
from collections.abc import Collection, Generator, Iterable
from dataclasses import dataclass, field, replace
from functools import partial
from multiprocessing.context import BaseContext
from pathlib import Path
from typing import Any, cast

import trailrunner
from libcst import ParserSyntaxError

from .ast import AstParseError
from .cache import ResultCache
from .config import collect_rules, generate_config
from .console import echo, echo_color_precomputed_diff
from .engine import LintRunner, diff_module
from .format import format_module, format_paths
from .ftypes import (
    STDIN,
    Config,
    FileContent,
    LintViolation,
    Metrics,
    MetricsHook,
    Options,
    OutputFormat,
    Result,
)
from .output import render_rattle_result
from .rule import LintRule

LOG = logging.getLogger(__name__)
ConfiguredPath = tuple[Path, Config, bool]
ConfiguredPathBatch = list[ConfiguredPath]


@dataclass(frozen=True)
class ConfiguredPathBatchResult:
    results: list[Result]
    deferred_format_paths: list[Path]
    metrics: list[Metrics] = field(default_factory=list)


@dataclass
class ConfiguredFileCacheSession:
    path: Path
    config: Config
    stat: os.stat_result
    rules: Collection[LintRule]
    autofix: bool = False
    include_diff: bool = False
    allow_cached_dirty_results: bool = False
    options: Options | None = None
    explicit_path: bool = False
    cache: ResultCache | None = None
    cache_key: str = ""
    cached_results: list[Result] | None = None
    cached_autofix_rule_names: set[str] = field(default_factory=set)
    cached_passthrough: list[Result] = field(default_factory=list)

    @classmethod
    def from_environment(
        cls,
        *,
        path: Path,
        config: Config,
        stat: os.stat_result,
        rules: Collection[LintRule],
        autofix: bool,
        include_diff: bool,
        allow_cached_dirty_results: bool,
        options: Options | None,
        explicit_path: bool,
    ) -> "ConfiguredFileCacheSession":
        return cls(
            path=path,
            config=config,
            stat=stat,
            rules=rules,
            autofix=autofix,
            include_diff=include_diff,
            allow_cached_dirty_results=allow_cached_dirty_results,
            options=options,
            explicit_path=explicit_path,
            cache=ResultCache.from_environment(),
        )

    def read_complete_entry(self) -> bool:
        if self.cache is None:
            return False

        self.cache_key = self.cache.result_key(
            self.path,
            self.stat,
            self.config,
            include_diff=self.include_diff,
        )
        self.cached_results, self.cached_autofix_rule_names, cached_result_is_complete = (
            self.cache.read_configured_file(
                self.cache_key,
                self.stat,
                path=self.path,
                config=self.config,
                rules=self.rules,
                autofix=self.autofix,
                allow_cached_dirty_results=self.allow_cached_dirty_results,
            )
        )
        return cached_result_is_complete

    def prepare_autofix_passthrough(self) -> list[Result]:
        if not self.cached_autofix_rule_names:
            return []

        self.cached_passthrough = [
            result
            for result in self.cached_results or ()
            if result.violation is not None
            and result.violation.rule_name not in self.cached_autofix_rule_names
        ]
        self.rules = [rule for rule in self.rules if rule.name in self.cached_autofix_rule_names]
        return self.cached_passthrough

    def write_result(
        self,
        content: FileContent,
        clean: bool,
        cacheable: bool,
        cache_violations: list[LintViolation],
    ) -> None:
        if self.cache is None:
            return

        if clean and not self.cached_passthrough:
            self.cache.write_result(self.cache_key, self.stat, rules=self.rules)
            self.cache.write_clean_status(
                self.path,
                self.stat,
                options=self.options,
                explicit_path=self.explicit_path,
                include_diff=self.include_diff,
                rules=self.rules,
            )
            return

        if cacheable and cache_violations:
            self.cache.write_result(
                self.cache_key,
                self.stat,
                source=content,
                violations=cache_violations,
                rules=self.rules,
            )


@dataclass
class ConfiguredFileRun:
    path: Path
    config: Config
    autofix: bool = False
    include_diff: bool = False
    allow_cached_dirty_results: bool = False
    deferred_format_paths: list[Path] | None = None
    options: Options | None = None
    explicit_path: bool = False
    metrics_hook: MetricsHook | None = None
    content: FileContent | None = None
    stat: os.stat_result | None = None
    rules: Collection[LintRule] = ()
    cache_session: ConfiguredFileCacheSession | None = None

    def run(self) -> Generator[Result, bool, None]:
        self.path = self.path.resolve()

        try:
            self.stat = self.path.stat()
            self.rules = collect_rules(self.config)
            if self.metrics_hook is None:
                self.cache_session = ConfiguredFileCacheSession.from_environment(
                    path=self.path,
                    config=self.config,
                    stat=self.stat,
                    rules=self.rules,
                    autofix=self.autofix,
                    include_diff=self.include_diff,
                    allow_cached_dirty_results=self.allow_cached_dirty_results,
                    options=self.options,
                    explicit_path=self.explicit_path,
                )
                if self.cache_session.read_complete_entry():
                    yield from (self.cache_session.cached_results or [])
                    return

                yield from self.cache_session.prepare_autofix_passthrough()
                self.rules = self.cache_session.rules

            if not self.rules:
                self.content = self.path.read_bytes()
                yield Result(
                    self.path,
                    violation=None,
                    source=self.content,
                    config=self.config,
                )
                return

            self.content = self.path.read_bytes()
            lint_config = replace(self.config, formatter=None) if self.defer_format else self.config
            runner = rattle_bytes(
                self.path,
                self.content,
                config=lint_config,
                autofix=self.autofix,
                include_diff=self.include_diff,
                rules=self.rules,
                metrics_hook=self.metrics_hook,
            )
            updated, clean, cacheable, cache_violations = yield from _drive_rattle_bytes(
                runner,
                cacheable=not self.autofix,
            )
            self._store_result(updated, clean, cacheable, cache_violations)

        except Exception as error:  # noqa: BLE001 - file boundary
            LOG.debug("Exception while rattle_configured_file", exc_info=error)
            yield Result.from_exception(
                self.path,
                error,
                source=self.content,
                config=self.config,
            )

    @property
    def defer_format(self) -> bool:
        return (
            self.deferred_format_paths is not None
            and self.autofix
            and self.config.formatter == "ruff"
        )

    def _store_result(
        self,
        updated: FileContent | None,
        clean: bool,
        cacheable: bool,
        cache_violations: list[LintViolation],
    ) -> None:
        assert self.stat is not None
        if updated and updated != self.content:
            LOG.info("%s: writing changes to file", self.path)
            self.path.write_bytes(updated)
            if self.defer_format and self.deferred_format_paths is not None:
                self.deferred_format_paths.append(self.path)
            return

        if self.content is not None and self.cache_session is not None:
            self.cache_session.write_result(
                self.content,
                clean=clean,
                cacheable=cacheable,
                cache_violations=cache_violations,
            )


@dataclass
class PathLintRun:
    paths: Iterable[Path]
    autofix: bool = False
    include_diff: bool = False
    allow_cached_dirty_results: bool = False
    options: Options | None = None
    parallel: bool = True
    metrics_hook: MetricsHook | None = None
    expanded_paths: list[tuple[Path, bool]] = field(default_factory=list)
    included_paths: list[ConfiguredPath] = field(default_factory=list)
    cached_clean_results: list[Result] = field(default_factory=list)
    deferred_format_paths: list[Path] = field(default_factory=list)

    def run(self) -> Generator[Result, bool, None]:
        paths = tuple(self.paths)
        if not paths:
            return

        self.expanded_paths, is_stdin, stdin_path = _expand_paths(paths)
        if is_stdin:
            yield from rattle_stdin(
                stdin_path,
                autofix=self.autofix,
                include_diff=self.include_diff,
                options=self.options,
                metrics_hook=self.metrics_hook,
            )
            return

        self.included_paths = _configured_paths(
            self._pending_paths(),
            options=self.options,
        )
        yield from self.cached_clean_results
        if not self.included_paths:
            return
        if len(self.included_paths) == 1 or not self.parallel:
            yield from self.run_serial()
            return

        yield from self.run_parallel()

    def run_configured_group(self, group: list[ConfiguredPath]) -> Generator[Result, bool, None]:
        self.included_paths = group
        yield from self.run_parallel()

    def run_serial(self) -> Generator[Result, bool, None]:
        for path, config, explicit_path in self.included_paths:
            yield from rattle_configured_file(
                path,
                config=config,
                autofix=self.autofix,
                include_diff=self.include_diff,
                allow_cached_dirty_results=self.allow_cached_dirty_results,
                deferred_format_paths=self.deferred_format_paths,
                options=self.options,
                explicit_path=explicit_path,
                metrics_hook=self.metrics_hook,
            )
        if self.deferred_format_paths:
            format_paths(self.deferred_format_paths, Config(formatter="ruff"))

    def run_parallel(self) -> Generator[Result, bool, None]:
        concurrency = self._concurrency()
        if concurrency <= 1:
            yield from self.run_serial()
            return

        fn = partial(
            _rattle_configured_file_batch_wrapper,
            autofix=self.autofix,
            include_diff=self.include_diff,
            allow_cached_dirty_results=self.allow_cached_dirty_results,
            options=self.options,
            collect_metrics=self.metrics_hook is not None,
        )
        context = _process_context()
        if context is not None:
            _preload_rules_for_fork(self.included_paths)
        batches = _configured_path_batches(self.included_paths, concurrency=concurrency)
        runner = trailrunner.Trailrunner(concurrency=concurrency, context=context)
        batch_results = cast(
            Iterable[tuple[ConfiguredPathBatch, ConfiguredPathBatchResult | list[Result]]],
            cast(Any, runner).run_iter(batches, fn),
        )
        for _, batch_result in batch_results:
            if isinstance(batch_result, ConfiguredPathBatchResult):
                self.deferred_format_paths.extend(batch_result.deferred_format_paths)
                if self.metrics_hook is not None:
                    for metrics in batch_result.metrics:
                        self.metrics_hook(metrics)
                yield from batch_result.results
            else:
                yield from batch_result

        if self.deferred_format_paths:
            format_paths(self.deferred_format_paths, Config(formatter="ruff"))

    def _pending_paths(self) -> list[tuple[Path, bool]]:
        cache = ResultCache.from_environment() if self.metrics_hook is None else None
        if cache is None:
            self.cached_clean_results = []
            return [(path.resolve(), explicit_path) for path, explicit_path in self.expanded_paths]

        collection = cache.collect_pending_paths(
            self.expanded_paths,
            include_diff=self.include_diff,
            options=self.options,
        )
        self.cached_clean_results = collection.cached_results
        return collection.pending_paths

    def _concurrency(self) -> int:
        configured_jobs = self.options.jobs if self.options is not None else None
        worker_count = (
            configured_jobs
            if configured_jobs is not None
            else _default_worker_count(
                file_count=len(self.included_paths),
                total_bytes=_configured_path_total_bytes(self.included_paths),
            )
        )
        return min(len(self.included_paths), worker_count)


def _available_cpu_count() -> int:
    try:
        return len(os.sched_getaffinity(0))
    except AttributeError:
        return os.cpu_count() or 1


def _default_worker_count(
    *,
    file_count: int,
    total_bytes: int | None = None,
    cpu_count: int | None = None,
) -> int:
    """
    Pick a fast default worker count without saturating the machine.

    Process startup and rule/config import costs dominate small lint runs, so the
    automatic default intentionally stays conservative unless there is enough
    work to amortize additional workers.
    """
    available = max(1, cpu_count if cpu_count is not None else _available_cpu_count())
    if file_count < 8:
        return 1

    if total_bytes is not None and total_bytes < 2_000_000:
        return min(available, file_count, max(4, file_count // 4))

    return min(8, available, max(1, file_count // 8))


def _configured_path_total_bytes(group: Collection[ConfiguredPath]) -> int | None:
    total = 0
    try:
        for path, _config, _explicit_path in group:
            total += path.stat().st_size
    except OSError:
        return None
    return total


def _configured_path_batches(
    group: list[ConfiguredPath],
    *,
    concurrency: int,
) -> list[ConfiguredPathBatch]:
    chunk_size = max(1, len(group) // max(1, concurrency * 4))
    return [group[index : index + chunk_size] for index in range(0, len(group), chunk_size)]


def _process_context() -> BaseContext | None:
    if os.name != "posix":
        return None
    try:
        return multiprocessing.get_context("fork")
    except ValueError:
        return None


def _display_path(path: Path) -> Path:
    try:
        return path.relative_to(Path.cwd())
    except ValueError:
        return path


def _drive_rattle_bytes(
    runner: Generator[Result, bool, FileContent | None],
    *,
    cacheable: bool,
) -> Generator[Result, bool, tuple[FileContent | None, bool, bool, list[LintViolation]]]:
    clean = True
    cache_violations: list[LintViolation] = []

    while True:
        try:
            result = next(runner)
        except StopIteration as stop:
            return stop.value, clean, cacheable, cache_violations

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
            except StopIteration as stop:
                return stop.value, clean, cacheable, cache_violations


def _print_rattle_result(
    result: Result, *, path: Path, show_diff: bool, stderr: bool, brief: bool
) -> bool:
    rendered = render_rattle_result(result, path=path, color=True, brief=brief)
    if rendered is None:
        return False

    echo(rendered, err=stderr)
    if show_diff and result.violation and result.violation.diff:
        echo_color_precomputed_diff(result.violation.diff, err=stderr)
    if not brief or (show_diff and result.violation and result.violation.diff):
        echo(err=stderr)
    return True


def _print_violation_result(
    result: Result,
    *,
    path: Path,
    show_diff: bool,
    stderr: bool,
    output_format: OutputFormat,
    output_template: str,
    brief: bool,
) -> bool:
    violation = result.violation
    assert violation is not None
    assert violation.range is not None

    rule_name = violation.rule_name
    start_line = violation.range.start.line
    start_col = violation.range.start.column
    message = violation.message
    if violation.autofixable:
        message += " (has autofix)"

    if output_format == OutputFormat.rattle:
        if _print_rattle_result(result, path=path, show_diff=show_diff, stderr=stderr, brief=brief):
            return True
        raise NotImplementedError("missing rattle renderer for lint violation")

    if output_format == OutputFormat.vscode:
        line = f"{path}:{start_line}:{start_col} {rule_name}: {message}"
    elif output_format == OutputFormat.custom:
        line = output_template.format(
            message=message,
            path=path,
            result=result,
            rule_name=rule_name,
            start_col=start_col,
            start_line=start_line,
        )
    else:
        raise NotImplementedError(f"output-format = {output_format!r}")

    echo(line, color="yellow", err=stderr)
    if show_diff and violation.diff:
        echo_color_precomputed_diff(violation.diff, err=stderr)
    return True


def _print_error_result(
    result: Result,
    *,
    path: Path,
    show_diff: bool,
    stderr: bool,
    output_format: OutputFormat,
    brief: bool,
) -> bool:
    error, tb = result.error or (None, "")
    assert error is not None

    if output_format == OutputFormat.rattle and isinstance(
        error, (AstParseError, ParserSyntaxError)
    ):
        if _print_rattle_result(result, path=path, show_diff=show_diff, stderr=stderr, brief=brief):
            return True
        raise NotImplementedError("missing rattle renderer for syntax error")

    echo(f"{path}: EXCEPTION: {error}", color="red", err=stderr)
    echo(tb.strip(), err=stderr)
    return True


def _expand_paths(paths: Iterable[Path]) -> tuple[list[tuple[Path, bool]], bool, Path]:
    expanded_paths: list[tuple[Path, bool]] = []
    is_stdin = False
    stdin_path = Path("stdin")

    for index, path in enumerate(paths):
        if path == STDIN:
            if index == 0:
                is_stdin = True
            else:
                LOG.warning("Cannot mix stdin ('-') with normal paths, ignoring")
        elif is_stdin:
            if index == 1:
                stdin_path = path
            else:
                raise ValueError("too many stdin paths")
        else:
            is_explicit = path.is_file()
            if is_explicit:
                expanded_paths.append((path, True))
            else:
                expanded_paths.extend(
                    (expanded_path, False) for expanded_path in trailrunner.walk(path)
                )

    return expanded_paths, is_stdin, stdin_path


def print_result(
    result: Result,
    *,
    show_diff: bool = False,
    stderr: bool = False,
    output_format: OutputFormat = OutputFormat.rattle,
    output_template: str = "",
    brief: bool = False,
) -> int:
    """
    Print linting results in a simple format designed for human eyes.

    Setting ``show_diff=True`` will output autofixes or suggested changes in unified
    diff format, using ANSI colors when possible.

    Returns ``True`` if the result is "dirty" - either a lint error or exception.
    """
    path = _display_path(result.path)

    if result.violation:
        return _print_violation_result(
            result,
            path=path,
            show_diff=show_diff,
            stderr=stderr,
            output_format=output_format,
            output_template=output_template,
            brief=brief,
        )

    if result.error:
        return _print_error_result(
            result,
            path=path,
            show_diff=show_diff,
            stderr=stderr,
            output_format=output_format,
            brief=brief,
        )

    LOG.debug("%s: clean", path)
    return False


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

    except Exception as error:  # noqa: BLE001 - result conversion boundary
        # TODO: this is not the right place to catch errors
        LOG.debug("Exception while linting", exc_info=error)
        yield Result.from_exception(path, error, source=content, config=config)

    return None


def rattle_stdin(
    path: Path,
    *,
    autofix: bool = False,
    include_diff: bool = False,
    options: Options | None = None,
    metrics_hook: MetricsHook | None = None,
) -> Generator[Result, bool, None]:
    """
    Wrapper around :func:`rattle_bytes` for formatting content from STDIN.

    The resulting fixed content will be printed to STDOUT.

    Requires passing a path that represents the filesystem location matching the
    contents to be linted. This will be used to resolve the ``pyproject.toml``
    configuration.
    """
    path = path.resolve()
    content: FileContent | None = None
    config: Config | None = None

    try:
        stdin_content = sys.stdin.buffer.read()
        content = stdin_content
        config = generate_config(path, options=options, explicit_path=True)
        if config.excluded:
            return

        updated = yield from rattle_bytes(
            path,
            stdin_content,
            config=config,
            autofix=autofix,
            include_diff=include_diff,
            metrics_hook=metrics_hook,
        )
        if autofix:
            sys.stdout.buffer.write(updated or stdin_content)

    except Exception as error:  # noqa: BLE001 - stdin boundary
        LOG.debug("Exception while rattle_stdin", exc_info=error)
        yield Result.from_exception(path, error, source=content, config=config)


def rattle_file(
    path: Path,
    *,
    autofix: bool = False,
    include_diff: bool = False,
    options: Options | None = None,
    explicit_path: bool = False,
    metrics_hook: MetricsHook | None = None,
) -> Generator[Result, bool, None]:
    """
    Lint a single file on disk, detecting and generating appropriate configuration.

    Generates a merged :ref:`configuration` based on all applicable config files.
    Reads file from disk as raw bytes, and uses :func:`rattle_bytes` to lint and apply
    any fixes to the content. Writes content back to disk if changes are detected.

    Yields :class:`Result` objects for each lint error or exception found, or a single
    empty result if the file is clean.
    See :func:`rattle_bytes` for semantics.
    """
    path = path.resolve()
    config: Config | None = None

    try:
        config = generate_config(path, options=options, explicit_path=explicit_path)
        if config.excluded:
            return

        yield from rattle_configured_file(
            path,
            config=config,
            autofix=autofix,
            include_diff=include_diff,
            options=options,
            explicit_path=explicit_path,
            metrics_hook=metrics_hook,
        )

    except Exception as error:  # noqa: BLE001 - file boundary
        LOG.debug("Exception while rattle_file", exc_info=error)
        yield Result.from_exception(
            path,
            error,
            config=config,
        )


def rattle_configured_file(
    path: Path,
    *,
    config: Config,
    autofix: bool = False,
    include_diff: bool = False,
    allow_cached_dirty_results: bool = False,
    deferred_format_paths: list[Path] | None = None,
    options: Options | None = None,
    explicit_path: bool = False,
    metrics_hook: MetricsHook | None = None,
) -> Generator[Result, bool, None]:
    yield from ConfiguredFileRun(
        path,
        config,
        autofix=autofix,
        include_diff=include_diff,
        allow_cached_dirty_results=allow_cached_dirty_results,
        deferred_format_paths=deferred_format_paths,
        options=options,
        explicit_path=explicit_path,
        metrics_hook=metrics_hook,
    ).run()


def _rattle_configured_file_wrapper(
    item: ConfiguredPath,
    *,
    autofix: bool = False,
    include_diff: bool = False,
    allow_cached_dirty_results: bool = False,
    deferred_format_paths: list[Path] | None = None,
    options: Options | None = None,
    metrics_hook: MetricsHook | None = None,
) -> list[Result]:
    path, config, explicit_path = item
    return list(
        rattle_configured_file(
            path,
            config=config,
            autofix=autofix,
            include_diff=include_diff,
            allow_cached_dirty_results=allow_cached_dirty_results,
            deferred_format_paths=deferred_format_paths,
            options=options,
            explicit_path=explicit_path,
            metrics_hook=metrics_hook,
        )
    )


def _rattle_configured_file_batch_wrapper(
    batch: ConfiguredPathBatch,
    *,
    autofix: bool = False,
    include_diff: bool = False,
    allow_cached_dirty_results: bool = False,
    options: Options | None = None,
    collect_metrics: bool = False,
) -> ConfiguredPathBatchResult:
    results: list[Result] = []
    deferred_format_paths: list[Path] = []
    metrics: list[Metrics] = []
    metrics_hook = (lambda value: metrics.append(dict(value))) if collect_metrics else None
    for item in batch:
        results.extend(
            _rattle_configured_file_wrapper(
                item,
                autofix=autofix,
                include_diff=include_diff,
                allow_cached_dirty_results=allow_cached_dirty_results,
                deferred_format_paths=deferred_format_paths,
                options=options,
                metrics_hook=metrics_hook,
            )
        )
    return ConfiguredPathBatchResult(results, deferred_format_paths, metrics)


def _preload_rules_for_fork(group: Collection[ConfiguredPath]) -> None:
    seen: set[tuple[object, ...]] = set()
    for _path, config, _explicit_path in group:
        key = (
            config.root,
            config.enable_root_import,
            tuple(str(selector) for selector in config.enable),
            tuple(str(selector) for selector in config.disable),
            tuple(
                sorted(
                    (
                        rule_name,
                        tuple(
                            sorted(
                                (
                                    option_name,
                                    repr(option_value),
                                )
                                for option_name, option_value in options.items()
                            )
                        ),
                    )
                    for rule_name, options in config.options.items()
                )
            ),
            config.tags,
            config.python_version,
        )
        if key in seen:
            continue
        seen.add(key)
        collect_rules(config)


def _configured_paths(
    pending_paths: list[tuple[Path, bool]],
    *,
    options: Options | None,
) -> list[ConfiguredPath]:
    included_paths: list[ConfiguredPath] = []
    for path, explicit_path in pending_paths:
        config = generate_config(path, options=options, explicit_path=explicit_path)
        if not config.excluded:
            included_paths.append((path, config, explicit_path))
    return included_paths


def rattle_paths(
    paths: Iterable[Path],
    *,
    autofix: bool = False,
    include_diff: bool = False,
    allow_cached_dirty_results: bool = False,
    options: Options | None = None,
    parallel: bool = True,
    metrics_hook: MetricsHook | None = None,
) -> Generator[Result, bool, None]:
    """
    Lint multiple files or directories, recursively expanding each path.

    Walks all paths given, obeying any ``.gitignore`` exclusions, finding Python source
    files. Lints each file found using :func:`rattle_file`, using a process pool when
    more than one file is being linted.

    Yields :class:`Result` objects for each path, lint error, or exception found.
    See :func:`rattle_bytes` for semantics.

    If the first given path is STDIN (``Path("-")``), then content will be linted
    from STDIN using :func:`rattle_stdin`. The fixed content will be written to STDOUT.
    A second path argument may be given, which represents the original content's true
    path name, and will be used:
    - to resolve the ``pyproject.toml`` configuration
    - when printing status messages, diffs, or errors.
    If no second path argument is given, it will default to "stdin" in the current
    working directory.
    Any further path names will result in a runtime error.

    .. note::

        Currently does not support applying individual fixes when ``parallel=True``,
        due to limitations in the multiprocessing method in use.
        Setting ``parallel=False`` will enable interactive fixes.
        Setting ``autofix=True`` will always apply fixes automatically during linting.
    """
    yield from PathLintRun(
        paths,
        autofix=autofix,
        include_diff=include_diff,
        allow_cached_dirty_results=allow_cached_dirty_results,
        options=options,
        parallel=parallel,
        metrics_hook=metrics_hook,
    ).run()


__all__ = [
    "ConfiguredPath",
    "ConfiguredPathBatch",
    "print_result",
    "rattle_bytes",
    "rattle_configured_file",
    "rattle_file",
    "rattle_paths",
    "rattle_stdin",
]
