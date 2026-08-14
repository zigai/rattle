from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

from rattle.api import rattle_paths
from rattle.config.models import Config, Options
from rattle.diagnostics import Result
from rattle.execution.parallel import (
    ConfiguredPathBatch,
    ConfiguredPathBatchResult,
    _default_worker_count,
)


class RecordingTrailrunner:
    calls: list[tuple[int, list[ConfiguredPathBatch]]] = []

    def __init__(self, *, concurrency: int = 0, **_: object) -> None:
        self.concurrency = concurrency

    def run_iter(
        self,
        paths: list[ConfiguredPathBatch],
        func: Callable[[ConfiguredPathBatch], object],
    ) -> object:
        batches: list[ConfiguredPathBatch] = list(paths)
        type(self).calls.append((self.concurrency, batches))
        for batch in batches:
            yield batch, func(batch)


def clean_batch_result(batch: ConfiguredPathBatch) -> ConfiguredPathBatchResult:
    return ConfiguredPathBatchResult(
        results=[Result(path, violation=None) for path, _config, _explicit in batch],
        deferred_format_paths=[],
    )


class TestApi:
    def test_default_worker_count_preserves_headroom(self) -> None:
        for cpu_count, expected in (
            (1, 1),
            (2, 2),
            (3, 3),
            (4, 4),
            (6, 6),
            (8, 8),
            (12, 12),
            (16, 16),
        ):
            assert (
                _default_worker_count(file_count=100, total_bytes=100_000, cpu_count=cpu_count)
                == expected
            )

    def test_default_worker_count_scales_for_large_workloads(self) -> None:
        assert _default_worker_count(file_count=7, total_bytes=50_000_000, cpu_count=16) == 1
        assert _default_worker_count(file_count=64, total_bytes=50_000_000, cpu_count=16) == 8
        assert _default_worker_count(file_count=100, total_bytes=None, cpu_count=16) == 8

    def test_rattle_paths_caps_parallel_worker_count(self) -> None:
        RecordingTrailrunner.calls.clear()
        paths: list[Path] = [Path(f"{index}.py") for index in range(10)]

        with (
            patch(
                "rattle.execution.paths._expand_paths",
                return_value=([(path, True) for path in paths], False, Path("stdin")),
            ),
            patch(
                "rattle.execution.paths.generate_config",
                side_effect=lambda path, *args, **kwargs: Config(path=path),
            ),
            patch(
                "rattle.execution.paths._rattle_configured_file_batch_wrapper",
                side_effect=lambda batch, **_kwargs: clean_batch_result(batch),
            ),
            patch("rattle.execution.paths._default_worker_count", return_value=4),
            patch("rattle.execution.paths._preload_rules_for_fork"),
            patch("rattle.execution.paths.trailrunner.Trailrunner", RecordingTrailrunner),
        ):
            results = list(rattle_paths([Path("target")]))

        assert [result.path.name for result in results] == [path.name for path in paths]
        expected_group = [(path.resolve(), Config(path=path), True) for path in paths]
        assert RecordingTrailrunner.calls == [(4, [[item] for item in expected_group])]

    def test_rattle_paths_uses_configured_jobs(self) -> None:
        RecordingTrailrunner.calls.clear()
        paths: list[Path] = [Path(f"{index}.py") for index in range(10)]

        with (
            patch(
                "rattle.execution.paths._expand_paths",
                return_value=([(path, True) for path in paths], False, Path("stdin")),
            ),
            patch(
                "rattle.execution.paths.generate_config",
                side_effect=lambda path, *args, **kwargs: Config(path=path),
            ),
            patch(
                "rattle.execution.paths._rattle_configured_file_batch_wrapper",
                side_effect=lambda batch, **_kwargs: clean_batch_result(batch),
            ),
            patch("rattle.execution.paths._default_worker_count") as default_worker_count,
            patch("rattle.execution.paths._preload_rules_for_fork"),
            patch("rattle.execution.paths.trailrunner.Trailrunner", RecordingTrailrunner),
        ):
            results = list(rattle_paths([Path("target")], options=Options(jobs=2)))

        assert [result.path.name for result in results] == [path.name for path in paths]
        assert [call[0] for call in RecordingTrailrunner.calls] == [2]
        default_worker_count.assert_not_called()

    def test_rattle_paths_reports_parallel_metrics_in_parent(self) -> None:
        paths: list[Path] = [Path(f"{index}.py") for index in range(10)]
        seen_metrics: list[object] = []
        seen_collect_metrics: list[bool] = []

        def batch_wrapper(
            batch: ConfiguredPathBatch, **kwargs: object
        ) -> ConfiguredPathBatchResult:
            seen_collect_metrics.append(kwargs["collect_metrics"] is True)
            return ConfiguredPathBatchResult(
                [Result(batch[0][0], violation=None)],
                [],
                [{"Count.Total": len(batch)}],
            )

        with (
            patch(
                "rattle.execution.paths._expand_paths",
                return_value=([(path, True) for path in paths], False, Path("stdin")),
            ),
            patch(
                "rattle.execution.paths.generate_config",
                side_effect=lambda path, *args, **kwargs: Config(path=path),
            ),
            patch(
                "rattle.execution.paths._rattle_configured_file_batch_wrapper",
                side_effect=batch_wrapper,
            ),
            patch("rattle.execution.paths._default_worker_count", return_value=4),
            patch("rattle.execution.paths._preload_rules_for_fork"),
            patch("rattle.execution.paths.trailrunner.Trailrunner", RecordingTrailrunner),
        ):
            list(rattle_paths([Path("target")], metrics_hook=seen_metrics.append))

        assert seen_collect_metrics
        assert all(seen_collect_metrics)
        assert seen_metrics == [{"Count.Total": 1} for _ in range(10)]

    def test_rattle_paths_falls_back_to_serial_when_parallel_cap_is_one(self) -> None:
        paths: list[Path] = [Path("a.py"), Path("b.py")]

        with (
            patch(
                "rattle.execution.paths._expand_paths",
                return_value=([(path, True) for path in paths], False, Path("stdin")),
            ),
            patch(
                "rattle.execution.paths.generate_config",
                side_effect=lambda path, *args, **kwargs: Config(path=path),
            ),
            patch(
                "rattle.execution.paths.rattle_configured_file",
                side_effect=lambda path, **kwargs: iter([path.name]),
            ) as rattle_configured_file,
            patch("rattle.execution.paths._default_worker_count", return_value=1),
            patch(
                "rattle.execution.paths.trailrunner.Trailrunner",
                side_effect=AssertionError("process pool should not be used"),
            ),
        ):
            results = list(rattle_paths([Path("target")]))

        assert results == ["a.py", "b.py"]
        assert rattle_configured_file.call_count == 2
