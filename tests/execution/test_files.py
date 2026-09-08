import os
from collections.abc import Collection, Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from libcst import Name, Pass

from rattle.api import rattle_configured_file, rattle_paths
from rattle.cache import ResultCache, rule_cache_fingerprint
from rattle.cache.keys import (
    _clean_status_cache_key,
    _decode_cached_source,
    _path_stat_fingerprint,
    _rule_fingerprints_match,
)
from rattle.cache.models import ResultCacheEntry
from rattle.cache.store import _prune_cache
from rattle.config.models import Config
from rattle.diagnostics import CodePosition, CodeRange, FileContent, LintViolation, Result
from rattle.engine import LintRunner
from rattle.rule import LintRule
from rattle.selectors import QualifiedRule


class TestApi:
    def test_rattle_configured_file_uses_clean_cache(self, tmp_path: Path) -> None:
        root = tmp_path
        path = root / "clean.py"
        path.write_bytes(b"pass\n")
        cache_dir = root / "cache"
        config = Config(path=path, root=root, enable=[QualifiedRule("rattle.rules.modernization")])

        with patch.dict(os.environ, {"RATTLE_CACHE_DIR": cache_dir.as_posix()}):
            first_results = list(rattle_configured_file(path, config=config))
            with patch("rattle.execution.content.LintRunner") as lint_runner:
                second_results = list(rattle_configured_file(path, config=config))

        assert len(first_results) == 1
        assert first_results[0].violation is None
        assert first_results[0].source == b"pass\n"
        assert len(second_results) == 1
        assert second_results[0].violation is None
        assert second_results[0].source is None
        lint_runner.assert_not_called()

    def test_rattle_configured_file_serves_dirty_cache_for_lint(self, tmp_path: Path) -> None:
        class DirtyRule(LintRule):
            pass

        def violation() -> LintViolation:
            return LintViolation(
                rule_name="dirty-rule",
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
            patch("rattle.execution.paths.generate_config", return_value=config),
            patch("rattle.cache.ResultCache._read_result", return_value=cached_results),
            patch(
                "rattle.execution.files.collect_rules",
                return_value=(DirtyRule(),),
            ),
            patch("rattle.execution.files.rattle_bytes") as rattle_bytes_stub,
        ):
            results = list(rattle_paths([path], allow_cached_dirty_results=True, parallel=False))

        assert results == cached_results
        rattle_bytes_stub.assert_not_called()

    def test_rattle_paths_does_not_serve_dirty_cache_when_interactive(
        self,
        tmp_path: Path,
    ) -> None:
        class AutoFixRule(LintRule):
            pass

        def violation() -> LintViolation:
            return LintViolation(
                rule_name="auto-fix-rule",
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

        def clean_results(
            *_args: object,
            **_kwargs: object,
        ) -> Generator[Result, bool, FileContent | None]:
            yield Result(path, violation=None, source=b"x\n", config=config)
            return None

        with (
            patch.dict(os.environ, {"RATTLE_CACHE_DIR": cache_dir.as_posix()}),
            patch("rattle.execution.paths.generate_config", return_value=config),
            patch("rattle.cache.ResultCache._read_result", return_value=cached_results),
            patch(
                "rattle.execution.files.collect_rules",
                return_value=(AutoFixRule(),),
            ),
            patch(
                "rattle.execution.files.rattle_bytes",
                side_effect=clean_results,
            ) as rattle_bytes_stub,
        ):
            list(rattle_paths([path], parallel=False))

        rattle_bytes_stub.assert_called_once()

    def test_path_stat_fingerprint_reflects_same_process_file_edits(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "rule_helpers.py"
        path.write_text("VALUE = 1\n")
        first = _path_stat_fingerprint(path)

        path.write_text("VALUE = 200\n")

        assert _path_stat_fingerprint(path) != first

    def test_rule_fingerprint_validation_rechecks_file_metadata(
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

        assert _rule_fingerprints_match(raw_fingerprints)

        source.write_text("VALUE = 200\n")

        assert not _rule_fingerprints_match(raw_fingerprints)

    def test_rule_fingerprint_tracks_sibling_python_modules(self, tmp_path: Path) -> None:
        class PackageRule(LintRule):
            pass

        rule_module = tmp_path / "rules.py"
        helper_module = tmp_path / "helpers.py"
        rule_module.write_text("class PackageRule: pass\n")
        helper_module.write_text("VALUE = 1\n")

        with patch("rattle.cache.keys.inspect.getsourcefile", return_value=rule_module.as_posix()):
            first = rule_cache_fingerprint(PackageRule())

            helper_module.write_text("VALUE = 200\n")

            assert rule_cache_fingerprint(PackageRule()) != first

    def test_clean_status_cache_key_includes_interpreter_version(self, tmp_path: Path) -> None:
        path = tmp_path / "clean.py"
        path.write_text("pass\n")
        stat = path.stat()
        config_fingerprints: tuple[tuple[str, int, int], ...] = ()

        with patch("rattle.cache.keys.platform.python_version", return_value="3.10.0"):
            py310_key = _clean_status_cache_key(
                path,
                stat,
                options=None,
                explicit_path=True,
                include_diff=False,
                config_fingerprints=config_fingerprints,
            )
        with patch("rattle.cache.keys.platform.python_version", return_value="3.13.0"):
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
            version="results-v1",
            mtime_ns=0,
            size=0,
            status="violations",
            rule_fingerprints=[],
            rule_fingerprint_hash=None,
            source="!!!!",
            violations=[],
        )

        assert _decode_cached_source(entry) is None

    def test_cached_violations_are_read_from_cache(self, tmp_path: Path) -> None:
        path = tmp_path / "dirty.py"
        source = b"x = 1\n"
        path.write_bytes(source)
        stat = path.stat()
        config = Config(path=path, root=tmp_path)
        cache = ResultCache(tmp_path / "cache")
        cache_key = cache.result_key(path.resolve(), stat, config, include_diff=False)
        violations = [
            LintViolation(
                rule_name="some-rule",
                range=CodeRange(start=CodePosition(1, 0), end=CodePosition(1, 1)),
                message="bad",
                node=Name("x"),
                replacement=None,
            ),
            LintViolation(
                rule_name="fixable-rule",
                range=CodeRange(start=CodePosition(1, 4), end=CodePosition(1, 5)),
                message="replace me",
                node=Name("y"),
                replacement=Name("z"),
                diff="-y\n+z\n",
            ),
        ]
        cache.write_result(
            cache_key,
            stat,
            source=source,
            violations=violations,
            rules=(),
        )
        cached_results = cache._read_result(cache_key, stat, path=path, config=config, rules=())
        assert cached_results is not None
        assert len(cached_results) == 2
        assert cached_results[0].violation is not None
        assert cached_results[0].violation.rule_name == "some-rule"
        assert not cached_results[0].violation.autofixable
        assert cached_results[0].source == source
        assert cached_results[1].violation is not None
        assert cached_results[1].violation.rule_name == "fixable-rule"
        assert cached_results[1].violation.autofixable
        assert cached_results[1].violation.diff == "-y\n+z\n"
        assert cached_results[1].source == source

    def test_cache_pruning_deletes_entries_until_target(self, tmp_path: Path) -> None:
        cache_root = tmp_path / "cache"
        cache_root.mkdir()
        old_entry = cache_root / "old.json"
        new_entry = cache_root / "new.json"
        old_entry.write_bytes(b"x" * 7)
        new_entry.write_bytes(b"x" * 7)

        _prune_cache(cache_root, max_bytes=10, target_bytes=7)

        remaining_entries = list(cache_root.rglob("*.json"))
        assert len(remaining_entries) == 1
        assert sum(entry.stat().st_size for entry in remaining_entries) == 7

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
        runner = LintRunner(Path("ignored.py"), b"pass  # rattle: ignore\n")

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
            Result(
                path, violation("auto-fix-rule", autofixable=True), source=b"x\n", config=config
            ),
            Result(path, violation("other-rule", autofixable=False), source=b"x\n", config=config),
        ]
        seen_rules: list[list[str]] = []

        with (
            patch.dict(os.environ, {"RATTLE_CACHE_DIR": cache_dir.as_posix()}),
            patch("rattle.cache.ResultCache._read_result", return_value=cached_results),
            patch(
                "rattle.execution.files.collect_rules",
                return_value=(AutoFixRule(), OtherRule()),
            ),
            patch("rattle.execution.files.rattle_bytes", side_effect=rattle_bytes_stub),
            patch("rattle.cache.ResultCache.write_result") as write_result,
            patch("rattle.cache.ResultCache.write_clean_status") as write_clean_status,
        ):
            results = list(rattle_configured_file(path, config=config, autofix=True))

        assert seen_rules == [["auto-fix-rule"]]
        assert [result.violation.rule_name for result in results if result.violation] == [
            "other-rule"
        ]
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
                rule_name="auto-fix-rule",
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
                "rattle.execution.files.collect_rules",
                return_value=(AutoFixRule(),),
            ),
            patch("rattle.execution.files.rattle_bytes", side_effect=rattle_bytes_stub),
        ):
            runner = rattle_configured_file(path, config=config)
            result = next(runner)
            assert result.violation is not None
            accepted = True
            with pytest.raises(StopIteration):
                runner.send(accepted)

        assert accepted_answers == [True]
        assert path.read_text() == "y\n"
