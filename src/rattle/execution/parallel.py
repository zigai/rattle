from __future__ import annotations

import multiprocessing
import os
from collections.abc import Callable, Collection, Iterable
from dataclasses import dataclass, field
from multiprocessing.context import BaseContext
from pathlib import Path

import trailrunner

from rattle.config.models import Config, Options
from rattle.diagnostics import Result
from rattle.engine import Metrics
from rattle.execution.files import rattle_configured_file
from rattle.rule_loading import collect_rules

ConfiguredPath = tuple[Path, Config, bool]
ConfiguredPathBatch = list[ConfiguredPath]


@dataclass(frozen=True)
class ConfiguredPathBatchResult:
    results: list[Result]
    deferred_format_paths: list[Path]
    metrics: list[Metrics] = field(default_factory=list)


def _run_configured_batches(
    runner: trailrunner.Trailrunner,
    batches: Iterable[ConfiguredPathBatch],
    run_batch: Callable[[ConfiguredPathBatch], ConfiguredPathBatchResult],
) -> Iterable[tuple[ConfiguredPathBatch, ConfiguredPathBatchResult]]:
    # Trailrunner is runtime-generic, but its published annotations restrict items to Path.
    return runner.run_iter(batches, run_batch)  # type: ignore[arg-type, return-value]


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
    for path, config, explicit_path in batch:
        results.extend(
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


__all__ = ["ConfiguredPath", "ConfiguredPathBatch", "ConfiguredPathBatchResult"]
