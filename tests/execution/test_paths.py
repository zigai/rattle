import os
from collections.abc import Callable, Generator
from pathlib import Path
from unittest.mock import patch

from rattle.api import rattle_paths
from rattle.config.models import Config
from rattle.diagnostics import FileContent, Result
from rattle.execution.parallel import (
    ConfiguredPathBatch,
    ConfiguredPathBatchResult,
)
from rattle.rule import LintRule


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
    def test_rattle_paths_clean_status_cache_skips_source_read(self, tmp_path: Path) -> None:
        root = tmp_path
        paths = []
        for index in range(20):
            path = root / f"clean_{index}.py"
            path.write_bytes(f"value = {index}\n".encode())
            paths.append(path)
        cache_dir = root / "cache"
        (root / "pyproject.toml").write_text(
            "[tool.rattle]\nroot = true\nenable = ['modernization']\n"
        )

        with patch.dict(os.environ, {"RATTLE_CACHE_DIR": cache_dir.as_posix()}):
            list(rattle_paths(paths, parallel=False))
            with (
                patch("rattle.execution.paths.generate_config") as generate_config,
                patch("rattle.execution.content.LintRunner") as lint_runner,
            ):
                results = list(rattle_paths(paths, parallel=False))

        assert [result.source for result in results] == [None for _ in range(20)]
        generate_config.assert_not_called()
        lint_runner.assert_not_called()

    def test_rattle_paths_result_cache_lookup_is_single_owner(self, tmp_path: Path) -> None:
        root = tmp_path
        path = root / "clean.py"
        path.write_bytes(b"pass\n")
        cache_dir = root / "cache"
        config = Config(path=path, root=root)

        with (
            patch.dict(os.environ, {"RATTLE_CACHE_DIR": cache_dir.as_posix()}),
            patch("rattle.execution.paths.generate_config", return_value=config),
            patch("rattle.cache.ResultCache._read_result", return_value=None) as read_result,
        ):
            list(rattle_paths([path], parallel=False))

        read_result.assert_called_once()

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
            patch("rattle.execution.paths.generate_config", return_value=config),
            patch(
                "rattle.execution.files.collect_rules",
                return_value=(FixRule(),),
            ),
            patch("rattle.execution.files.rattle_bytes", side_effect=rattle_bytes_stub),
            patch("rattle.execution.paths.format_paths") as format_paths,
        ):
            list(rattle_paths([first, second], autofix=True, parallel=False))

        assert first.read_text() == "y\n"
        assert second.read_text() == "y\n"
        assert seen_formatters == [None, None]
        format_paths.assert_called_once()
        formatted_paths, batch_config = format_paths.call_args.args
        assert formatted_paths == [first.resolve(), second.resolve()]
        assert batch_config.formatter == "ruff"
