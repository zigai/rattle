import os
from collections.abc import Callable, Collection, Generator
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from libcst import Name, Pass

from rattle.api import (
    ConfiguredPathBatch,
    _default_worker_count,
    rattle_bytes,
    rattle_configured_file,
    rattle_paths,
)
from rattle.cache import rule_cache_fingerprint
from rattle.engine import LintRunner
from rattle.ftypes import (
    CodePosition,
    CodeRange,
    Config,
    FileContent,
    LintViolation,
    Options,
    Result,
)
from rattle.rule import LintRule
from rattle.util import capture


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


class TestApi:
    def test_default_worker_count_preserves_headroom(self) -> None:
        for cpu_count, expected in (
            (1, 1),
            (2, 2),
            (3, 3),
            (4, 4),
            (6, 4),
            (8, 4),
            (12, 4),
            (16, 4),
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
                "rattle.api._expand_paths",
                return_value=([(path, True) for path in paths], False, Path("stdin")),
            ),
            patch(
                "rattle.api.generate_config",
                side_effect=lambda path, *args, **kwargs: Config(path=path),
            ),
            patch(
                "rattle.api._rattle_configured_file_batch_wrapper",
                side_effect=lambda batch, **kwargs: [item[0].name for item in batch],
            ),
            patch("rattle.api._default_worker_count", return_value=4),
            patch("rattle.api._preload_rules_for_fork"),
            patch("rattle.api.trailrunner.Trailrunner", RecordingTrailrunner),
        ):
            results = list(rattle_paths([Path("target")]))

        assert results == [path.name for path in paths]
        expected_group = [(path.resolve(), Config(path=path), True) for path in paths]
        assert RecordingTrailrunner.calls == [(4, [[item] for item in expected_group])]

    def test_rattle_paths_uses_configured_jobs(self) -> None:
        RecordingTrailrunner.calls.clear()
        paths: list[Path] = [Path(f"{index}.py") for index in range(10)]

        with (
            patch(
                "rattle.api._expand_paths",
                return_value=([(path, True) for path in paths], False, Path("stdin")),
            ),
            patch(
                "rattle.api.generate_config",
                side_effect=lambda path, *args, **kwargs: Config(path=path),
            ),
            patch(
                "rattle.api._rattle_configured_file_batch_wrapper",
                side_effect=lambda batch, **kwargs: [item[0].name for item in batch],
            ),
            patch("rattle.api._default_worker_count") as default_worker_count,
            patch("rattle.api._preload_rules_for_fork"),
            patch("rattle.api.trailrunner.Trailrunner", RecordingTrailrunner),
        ):
            results = list(rattle_paths([Path("target")], options=Options(jobs=2)))

        assert results == [path.name for path in paths]
        assert [call[0] for call in RecordingTrailrunner.calls] == [2]
        default_worker_count.assert_not_called()

    def test_rattle_paths_falls_back_to_serial_when_parallel_cap_is_one(self) -> None:
        paths: list[Path] = [Path("a.py"), Path("b.py")]

        with (
            patch(
                "rattle.api._expand_paths",
                return_value=([(path, True) for path in paths], False, Path("stdin")),
            ),
            patch(
                "rattle.api.generate_config",
                side_effect=lambda path, *args, **kwargs: Config(path=path),
            ),
            patch(
                "rattle.api.rattle_configured_file",
                side_effect=lambda path, **kwargs: iter([path.name]),
            ) as rattle_configured_file,
            patch("rattle.api._default_worker_count", return_value=1),
            patch(
                "rattle.api.trailrunner.Trailrunner",
                side_effect=AssertionError("process pool should not be used"),
            ),
        ):
            results = list(rattle_paths([Path("target")]))

        assert results == ["a.py", "b.py"]
        assert rattle_configured_file.call_count == 2

    def test_rattle_configured_file_uses_clean_cache(self, tmp_path: Path) -> None:
        root = tmp_path
        path = root / "clean.py"
        path.write_bytes(b"pass\n")
        cache_dir = root / "cache"
        config = Config(path=path, root=root)

        with patch.dict(os.environ, {"RATTLE_CACHE_DIR": cache_dir.as_posix()}):
            first_results = list(rattle_configured_file(path, config=config))
            with patch("rattle.api.LintRunner") as lint_runner:
                second_results = list(rattle_configured_file(path, config=config))

        assert len(first_results) == 1
        assert first_results[0].violation is None
        assert first_results[0].source == b"pass\n"
        assert len(second_results) == 1
        assert second_results[0].violation is None
        assert second_results[0].source is None
        lint_runner.assert_not_called()

    def test_rattle_paths_clean_status_cache_skips_source_read(self, tmp_path: Path) -> None:
        root = tmp_path
        paths = []
        for index in range(20):
            path = root / f"clean_{index}.py"
            path.write_bytes(f"value = {index}\n".encode())
            paths.append(path)
        cache_dir = root / "cache"

        with patch.dict(os.environ, {"RATTLE_CACHE_DIR": cache_dir.as_posix()}):
            list(rattle_paths(paths, parallel=False))
            with patch("rattle.api.LintRunner") as lint_runner:
                results = list(rattle_paths(paths, parallel=False))

        assert [result.source for result in results] == [None for _ in range(20)]
        lint_runner.assert_not_called()

    def test_rattle_configured_file_serves_dirty_cache_for_lint(self, tmp_path: Path) -> None:
        def violation() -> LintViolation:
            return LintViolation(
                rule_name="DirtyRule",
                range=CodeRange(
                    start=CodePosition(line=1, column=0),
                    end=CodePosition(line=1, column=1),
                ),
                message="DirtyRule",
                node=Name("x"),
                replacement=None,
            )

        root = tmp_path
        path = root / "dirty.py"
        path.write_text("x\n")
        cache_dir = root / "cache"
        config = Config(path=path, root=root)
        cached_results: list[Result] = [
            Result(path, violation(), source=b"x\n", config=config),
        ]

        with (
            patch.dict(os.environ, {"RATTLE_CACHE_DIR": cache_dir.as_posix()}),
            patch("rattle.api.generate_config", return_value=config),
            patch("rattle.cache.ResultCache._read_result", return_value=cached_results),
            patch(
                "rattle.api.collect_rules",
                side_effect=AssertionError("cached dirty lint should not collect rules"),
            ),
        ):
            results = list(rattle_paths([path], allow_cached_dirty_results=True, parallel=False))

        assert results == cached_results

    def test_rattle_paths_does_not_serve_dirty_cache_when_interactive(
        self,
        tmp_path: Path,
    ) -> None:
        class AutoFixRule(LintRule):
            pass

        def violation() -> LintViolation:
            return LintViolation(
                rule_name="AutoFix",
                range=CodeRange(
                    start=CodePosition(line=1, column=0),
                    end=CodePosition(line=1, column=1),
                ),
                message="AutoFix",
                node=Name("x"),
                replacement=Name("y"),
            )

        root = tmp_path
        path = root / "dirty.py"
        path.write_text("x\n")
        cache_dir = root / "cache"
        config = Config(path=path, root=root)
        cached_results: list[Result] = [
            Result(path, violation(), source=b"x\n", config=config),
        ]

        with (
            patch.dict(os.environ, {"RATTLE_CACHE_DIR": cache_dir.as_posix()}),
            patch("rattle.api.generate_config", return_value=config),
            patch("rattle.cache.ResultCache._read_result", return_value=cached_results),
            patch(
                "rattle.api.collect_rules",
                return_value=cast(Collection[LintRule], [AutoFixRule()]),
            ),
            patch(
                "rattle.api.rattle_bytes",
                side_effect=lambda *args, **kwargs: iter(
                    [Result(path, violation=None, source=b"x\n", config=config)]
                ),
            ) as rattle_bytes_stub,
        ):
            list(rattle_paths([path], parallel=False))

        rattle_bytes_stub.assert_called_once()

    def test_rattle_paths_result_cache_lookup_is_single_owner(self, tmp_path: Path) -> None:
        root = tmp_path
        path = root / "clean.py"
        path.write_bytes(b"pass\n")
        cache_dir = root / "cache"
        config = Config(path=path, root=root)

        with (
            patch.dict(os.environ, {"RATTLE_CACHE_DIR": cache_dir.as_posix()}),
            patch("rattle.api.generate_config", return_value=config),
            patch("rattle.cache.ResultCache._read_result", return_value=None) as read_result,
        ):
            list(rattle_paths([path], parallel=False))

        read_result.assert_called_once()

    def test_rule_fingerprint_survives_lint_ignore_parent_metadata(self) -> None:
        class CacheRule(LintRule):
            def visit_Pass(self, node: Pass) -> None:
                self.report(node, "pass")

        rule = CacheRule()
        fingerprint = rule_cache_fingerprint(rule)
        runner = LintRunner(Path("ignored.py"), b"pass  # lint-ignore\n")

        assert list(runner.collect_violations([rule], Config(path=Path("ignored.py")))) == []
        assert type(rule) is CacheRule
        assert rule_cache_fingerprint(rule) == fingerprint

    def test_rattle_configured_file_uses_dirty_cache_to_narrow_autofix_rules(
        self,
        tmp_path: Path,
    ) -> None:
        class AutoFixRule(LintRule):
            pass

        class OtherRule(LintRule):
            pass

        def violation(rule_name: str, *, autofixable: bool) -> LintViolation:
            return LintViolation(
                rule_name=rule_name,
                range=CodeRange(
                    start=CodePosition(line=1, column=0),
                    end=CodePosition(line=1, column=1),
                ),
                message=rule_name,
                node=Name("x"),
                replacement=Name("y") if autofixable else None,
            )

        def rattle_bytes_stub(
            path: Path,
            content: FileContent,
            *,
            config: Config,
            rules: Collection[LintRule] | None,
            **_kwargs: object,
        ) -> Generator[Result, bool, FileContent | None]:
            seen_rules.append([rule.name for rule in rules or ()])
            yield Result(path, violation=None, source=content, config=config)
            return None

        root = tmp_path
        path = root / "dirty.py"
        path.write_text("x\n")
        cache_dir = root / "cache"
        config = Config(path=path, root=root)
        cached_results: list[Result] = [
            Result(path, violation("AutoFix", autofixable=True), source=b"x\n", config=config),
            Result(path, violation("Other", autofixable=False), source=b"x\n", config=config),
        ]
        seen_rules: list[list[str]] = []

        with (
            patch.dict(os.environ, {"RATTLE_CACHE_DIR": cache_dir.as_posix()}),
            patch("rattle.cache.ResultCache._read_result", return_value=cached_results),
            patch(
                "rattle.api.collect_rules",
                return_value=cast(Collection[LintRule], [AutoFixRule(), OtherRule()]),
            ),
            patch("rattle.api.rattle_bytes", side_effect=rattle_bytes_stub),
        ):
            results = list(rattle_configured_file(path, config=config, autofix=True))

        assert seen_rules == [["AutoFix"]]
        assert [result.violation.rule_name for result in results if result.violation] == ["Other"]

    def test_rattle_configured_file_does_not_serve_dirty_cache_interactively(
        self,
        tmp_path: Path,
    ) -> None:
        class AutoFixRule(LintRule):
            pass

        def violation() -> LintViolation:
            return LintViolation(
                rule_name="AutoFix",
                range=CodeRange(
                    start=CodePosition(line=1, column=0),
                    end=CodePosition(line=1, column=1),
                ),
                message="AutoFix",
                node=Name("x"),
                replacement=Name("y"),
            )

        def rattle_bytes_stub(
            _path: Path,
            content: FileContent,
            *,
            config: Config,
            **_kwargs: object,
        ) -> Generator[Result, bool, FileContent | None]:
            answer = yield Result(
                config.path,
                violation=violation(),
                source=content,
                config=config,
            )
            accepted_answers.append(answer)
            return b"y\n" if answer else None

        root = tmp_path
        path = root / "dirty.py"
        path.write_text("x\n")
        cache_dir = root / "cache"
        config = Config(path=path, root=root)
        cached_results: list[Result] = [
            Result(path, violation(), source=b"x\n", config=config),
        ]
        accepted_answers: list[bool] = []

        with (
            patch.dict(os.environ, {"RATTLE_CACHE_DIR": cache_dir.as_posix()}),
            patch("rattle.cache.ResultCache._read_result", return_value=cached_results),
            patch(
                "rattle.api.collect_rules",
                return_value=cast(Collection[LintRule], [AutoFixRule()]),
            ),
            patch("rattle.api.rattle_bytes", side_effect=rattle_bytes_stub),
        ):
            runner = rattle_configured_file(path, config=config)
            result = next(runner)
            assert result.violation is not None
            accepted = True
            with pytest.raises(StopIteration):
                runner.send(accepted)

        assert accepted_answers == [True]
        assert path.read_text() == "y\n"

    def test_rattle_bytes_automatic_diff_is_aggregate(self) -> None:
        class RenameXRule(LintRule):
            def visit_Name(self, node: Name) -> None:
                if node.value == "x":
                    self.report(node, "rename x", replacement=Name("y"))

        runner = capture(
            rattle_bytes(
                Path("rename.py"),
                b"x = x\nz = x\n",
                config=Config(path=Path("rename.py")),
                autofix=True,
                include_diff=True,
                rules=[RenameXRule()],
            )
        )

        results = list(runner)

        assert runner.result == b"y = y\nz = y\n"
        diffs = [result.violation.diff for result in results if result.violation]
        assert len(diffs) == 3
        assert diffs[0].count("-x = x") == 1
        assert diffs[0].count("+y = y") == 1
        assert diffs[0].count("-z = x") == 1
        assert diffs[0].count("+z = y") == 1
        assert diffs[1:] == ["", ""]

    def test_rattle_paths_batches_ruff_format_after_automatic_fixes(
        self,
        tmp_path: Path,
    ) -> None:
        class FixRule(LintRule):
            pass

        def rattle_bytes_stub(
            path: Path,
            content: FileContent,
            *,
            config: Config,
            **_kwargs: object,
        ) -> Generator[Result, bool, FileContent | None]:
            seen_formatters.append(config.formatter)
            yield Result(path, violation=None, source=content, config=config)
            return b"y\n"

        first = tmp_path / "first.py"
        second = tmp_path / "second.py"
        first.write_text("x\n")
        second.write_text("x\n")
        config = Config(path=tmp_path, root=tmp_path, formatter="ruff")
        seen_formatters: list[str | None] = []

        with (
            patch("rattle.api.generate_config", return_value=config),
            patch(
                "rattle.api.collect_rules",
                return_value=cast(Collection[LintRule], [FixRule()]),
            ),
            patch("rattle.api.rattle_bytes", side_effect=rattle_bytes_stub),
            patch("rattle.api.format_paths") as format_paths,
        ):
            list(rattle_paths([first, second], autofix=True, parallel=False))

        assert first.read_text() == "y\n"
        assert second.read_text() == "y\n"
        assert seen_formatters == [None, None]
        format_paths.assert_called_once()
        formatted_paths, batch_config = format_paths.call_args.args
        assert formatted_paths == [first.resolve(), second.resolve()]
        assert batch_config.formatter == "ruff"
