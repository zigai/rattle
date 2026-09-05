from __future__ import annotations

import logging
from collections.abc import Generator, Iterable
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path

import trailrunner

from rattle.cache import ResultCache
from rattle.config.merge import generate_config
from rattle.config.models import Config, Options
from rattle.diagnostics import Result
from rattle.engine import MetricsHook
from rattle.execution.files import rattle_configured_file, rattle_stdin
from rattle.execution.parallel import (
    ConfiguredPath,
    _configured_path_batches,
    _configured_path_total_bytes,
    _default_worker_count,
    _preload_rules_for_fork,
    _process_context,
    _rattle_configured_file_batch_wrapper,
    _run_configured_batches,
)
from rattle.formatting import format_paths

STDIN = Path("-")
LOG = logging.getLogger(__name__)


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
        batch_results = _run_configured_batches(runner, batches, fn)
        for _, batch_result in batch_results:
            self.deferred_format_paths.extend(batch_result.deferred_format_paths)
            if self.metrics_hook is not None:
                for metrics in batch_result.metrics:
                    self.metrics_hook(metrics)
            yield from batch_result.results

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


__all__ = ["STDIN", "rattle_paths"]
