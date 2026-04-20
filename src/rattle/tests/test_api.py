from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from rattle.api import _default_worker_count, rattle_paths


class RecordingTrailrunner:
    calls: list[tuple[int, list[Path]]] = []

    def __init__(self, *, concurrency: int = 0, **_: object) -> None:
        self.concurrency = concurrency

    def run_iter(self, paths: list[Path], func: object) -> object:
        group = list(paths)
        type(self).calls.append((self.concurrency, group))
        for path in group:
            yield path, func(path)


class ApiTest(TestCase):
    def test_default_worker_count_preserves_headroom(self) -> None:
        for cpu_count, expected in (
            (1, 1),
            (2, 1),
            (3, 2),
            (4, 3),
            (6, 4),
            (8, 6),
            (12, 9),
            (16, 12),
        ):
            with self.subTest(cpu_count=cpu_count):
                assert _default_worker_count(cpu_count) == expected

    def test_rattle_paths_caps_parallel_worker_count(self) -> None:
        RecordingTrailrunner.calls.clear()
        paths = [Path("a.py"), Path("b.py"), Path("c.py")]

        with (
            patch(
                "rattle.api._expand_paths",
                return_value=([(path, True) for path in paths], False, Path("stdin")),
            ),
            patch(
                "rattle.api.generate_config",
                side_effect=lambda *args, **kwargs: SimpleNamespace(excluded=False),
            ),
            patch(
                "rattle.api._rattle_file_wrapper",
                side_effect=lambda path, **kwargs: [path.name],
            ),
            patch("rattle.api._default_worker_count", return_value=2),
            patch("rattle.api.trailrunner.Trailrunner", RecordingTrailrunner),
        ):
            results = list(rattle_paths([Path("target")]))

        assert results == ["a.py", "b.py", "c.py"]
        assert RecordingTrailrunner.calls == [(2, paths)]

    def test_rattle_paths_falls_back_to_serial_when_parallel_cap_is_one(self) -> None:
        paths = [Path("a.py"), Path("b.py")]

        with (
            patch(
                "rattle.api._expand_paths",
                return_value=([(path, True) for path in paths], False, Path("stdin")),
            ),
            patch(
                "rattle.api.generate_config",
                side_effect=lambda *args, **kwargs: SimpleNamespace(excluded=False),
            ),
            patch(
                "rattle.api.rattle_file",
                side_effect=lambda path, **kwargs: iter([path.name]),
            ) as rattle_file,
            patch("rattle.api._default_worker_count", return_value=1),
            patch(
                "rattle.api.trailrunner.Trailrunner",
                side_effect=AssertionError("process pool should not be used"),
            ),
        ):
            results = list(rattle_paths([Path("target")]))

        assert results == ["a.py", "b.py"]
        assert rattle_file.call_count == 2
