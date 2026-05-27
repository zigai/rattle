import os
from collections.abc import Callable, Collection, Generator
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from libcst import Name, Pass

from rattle.api import (
    ConfiguredPath,
    _default_worker_count,
    rattle_configured_file,
    rattle_paths,
)
from rattle.cache import (
    ResultCache,
    ResultCacheEntry,
    _cached_rule_fingerprints_match,
    _clean_status_cache_key,
    _decode_cached_source,
    _path_stat_fingerprint,
    _prune_cache,
    rule_cache_fingerprint,
)
from rattle.engine import LintRunner
from rattle.ftypes import CodePosition, CodeRange, Config, FileContent, LintViolation, Result
from rattle.rule import LintRule


class RecordingTrailrunner:
    calls: list[tuple[int, list[ConfiguredPath]]] = []

    def __init__(self, *, concurrency: int = 0, **_: object) -> None:
        self.concurrency = concurrency

    def run_iter(
        self,
        paths: list[ConfiguredPath],
        func: Callable[[ConfiguredPath], object],
    ) -> object:
        group: list[ConfiguredPath] = list(paths)
        type(self).calls.append((self.concurrency, group))
        for item in group:
            yield item, func(item)


class TestApi:
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
            assert _default_worker_count(cpu_count) == expected

    def test_rattle_paths_caps_parallel_worker_count(self) -> None:
        RecordingTrailrunner.calls.clear()
        paths: list[Path] = [Path("a.py"), Path("b.py"), Path("c.py")]

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
                "rattle.api._rattle_configured_file_wrapper",
                side_effect=lambda item, **kwargs: [item[0].name],
            ),
            patch("rattle.api._default_worker_count", return_value=2),
            patch("rattle.api.trailrunner.Trailrunner", RecordingTrailrunner),
        ):
            results = list(rattle_paths([Path("target")]))

        assert results == ["a.py", "b.py", "c.py"]
        assert RecordingTrailrunner.calls == [
            (2, [(path.resolve(), Config(path=path), True) for path in paths])
        ]

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
        assert second_results[0].source == b"pass\n"
        lint_runner.assert_not_called()

    def test_rattle_paths_clean_status_cache_preserves_source(self, tmp_path: Path) -> None:
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

        assert [result.source for result in results] == [
            f"value = {index}\n".encode() for index in range(20)
        ]
        lint_runner.assert_not_called()

    def test_path_stat_fingerprint_reflects_same_process_file_edits(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "rule_helpers.py"
        path.write_text("VALUE = 1\n")
        first = _path_stat_fingerprint(path)

        path.write_text("VALUE = 200\n")

        assert _path_stat_fingerprint(path) != first

    def test_rule_fingerprint_validation_rechecks_old_hash(
        self,
        tmp_path: Path,
    ) -> None:
        source = tmp_path / "custom_rules.py"
        source.write_text("VALUE = 1\n")
        source_fingerprint = _path_stat_fingerprint(source)
        parent_fingerprint = _path_stat_fingerprint(source.parent)
        raw_fingerprints: list[object] = [
            ["custom_rules", "CustomRule", source_fingerprint, parent_fingerprint, ()]
        ]

        assert _cached_rule_fingerprints_match(raw_fingerprints, None)

        source.write_text("VALUE = 200\n")

        assert not _cached_rule_fingerprints_match(raw_fingerprints, None)

    def test_rule_fingerprint_tracks_sibling_python_modules(self, tmp_path: Path) -> None:
        class PackageRule(LintRule):
            pass

        rule_module = tmp_path / "rules.py"
        helper_module = tmp_path / "helpers.py"
        rule_module.write_text("class PackageRule: pass\n")
        helper_module.write_text("VALUE = 1\n")

        with patch("rattle.cache.inspect.getsourcefile", return_value=rule_module.as_posix()):
            first = rule_cache_fingerprint(PackageRule())

            helper_module.write_text("VALUE = 200\n")

            assert rule_cache_fingerprint(PackageRule()) != first

    def test_clean_status_cache_key_includes_interpreter_version(self, tmp_path: Path) -> None:
        path = tmp_path / "clean.py"
        path.write_text("pass\n")
        stat = path.stat()
        config_fingerprints: tuple[tuple[str, int, int], ...] = ()

        with patch("rattle.cache.platform.python_version", return_value="3.10.0"):
            py310_key = _clean_status_cache_key(
                path,
                stat,
                options=None,
                explicit_path=True,
                include_diff=False,
                config_fingerprints=config_fingerprints,
            )
        with patch("rattle.cache.platform.python_version", return_value="3.13.0"):
            py313_key = _clean_status_cache_key(
                path,
                stat,
                options=None,
                explicit_path=True,
                include_diff=False,
                config_fingerprints=config_fingerprints,
            )

        assert py310_key != py313_key

    def test_corrupted_cache_files_are_misses(self, tmp_path: Path) -> None:
        path = tmp_path / "clean.py"
        path.write_text("pass\n")
        stat = path.stat()
        config = Config(path=path, root=tmp_path)
        cache = ResultCache(tmp_path / "cache")
        cache_key = cache.result_key(path.resolve(), stat, config, include_diff=False)
        cache.write_result(cache_key, stat)
        cache._result_entry_path(cache_key).write_bytes(b"\xff")

        assert cache._read_result(cache_key, stat, path=path, config=config, rules=()) is None

        cache.write_clean_status(
            path,
            stat,
            options=None,
            explicit_path=True,
            include_diff=False,
            rules=(),
        )
        clean_cache_files = list((cache.root / "clean").rglob("*.json"))
        assert len(clean_cache_files) == 1
        clean_cache_files[0].write_bytes(b"\xff")

        assert (
            cache._read_clean_status(
                path,
                options=None,
                explicit_path=True,
                include_diff=False,
            )
            is None
        )

    def test_invalid_base64_cached_source_is_rejected(self) -> None:
        entry = ResultCacheEntry(
            mtime_ns=0,
            size=0,
            status="violations",
            rule_fingerprints=[],
            rule_fingerprint_hash=None,
            source="!!!!",
            violations=[],
        )

        assert _decode_cached_source(entry) is None

    def test_cache_pruning_deletes_oldest_entries(self, tmp_path: Path) -> None:
        cache_root = tmp_path / "cache"
        cache_root.mkdir()
        old_entry = cache_root / "old.json"
        new_entry = cache_root / "new.json"
        old_entry.write_bytes(b"x" * 7)
        new_entry.write_bytes(b"x" * 7)

        _prune_cache(cache_root, max_bytes=10, target_bytes=7)

        assert not old_entry.exists()
        assert new_entry.exists()

    def test_clean_cache_misses_when_current_rule_set_changes(self, tmp_path: Path) -> None:
        class ExistingRule(LintRule):
            pass

        class AddedRule(LintRule):
            pass

        path = tmp_path / "clean.py"
        path.write_text("pass\n")
        stat = path.stat()
        config = Config(path=path, root=tmp_path)
        cache = ResultCache(tmp_path / "cache")
        cache_key = cache.result_key(path.resolve(), stat, config, include_diff=False)
        cache.write_result(cache_key, stat, rules=[ExistingRule()])

        assert (
            cache._read_result(
                cache_key,
                stat,
                path=path,
                config=config,
                rules=[ExistingRule()],
            )
            is not None
        )
        assert (
            cache._read_result(
                cache_key,
                stat,
                path=path,
                config=config,
                rules=[ExistingRule(), AddedRule()],
            )
            is None
        )

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
            patch("rattle.cache.ResultCache.write_result") as write_result,
            patch("rattle.cache.ResultCache.write_clean_status") as write_clean_status,
        ):
            results = list(rattle_configured_file(path, config=config, autofix=True))

        assert seen_rules == [["AutoFix"]]
        assert [result.violation.rule_name for result in results if result.violation] == ["Other"]
        write_result.assert_not_called()
        write_clean_status.assert_not_called()

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
