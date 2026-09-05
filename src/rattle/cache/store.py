from __future__ import annotations

import base64
import logging
import os
import uuid
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

from msgspec import DecodeError, Struct
from msgspec.json import encode as encode_json
from platformdirs import user_cache_path

from rattle.cache.keys import (
    _cached_result_entry_matches_current_rules,
    _cached_rule_fingerprints_match,
    _clean_cache_key,
    _clean_status_cache_key,
    _config_path_fingerprints,
    _decode_cached_source,
    _rule_fingerprint_hash,
    rule_cache_fingerprint,
)
from rattle.cache.models import (
    CACHE_VERSION,
    CLEAN_STATUS_CACHE_DECODER,
    RESULT_CACHE_DECODER,
    CleanStatusCacheEntry,
    PendingPathCollection,
    ResultCacheEntry,
    SerializedViolationCacheEntry,
)
from rattle.config.models import Config, Options
from rattle.diagnostics import FileContent, LintViolation, Result
from rattle.rule import LintRule

LOG = logging.getLogger(__name__)
CLEAN_STATUS_PRECHECK_MIN_PATHS = 20
CACHE_MAX_BYTES = 250 * 1024 * 1024
CACHE_PRUNE_TARGET_BYTES = 200 * 1024 * 1024


@dataclass(frozen=True)
class ResultCache:
    root: Path

    @classmethod
    def from_environment(cls) -> ResultCache | None:
        if os.environ.get("RATTLE_DISABLE_CACHE"):
            return None

        if raw_cache_dir := os.environ.get("RATTLE_CACHE_DIR"):
            return cls(Path(raw_cache_dir) / CACHE_VERSION)

        return cls(user_cache_path("rattle-lint", appauthor=False, version=CACHE_VERSION))

    def result_key(
        self,
        path: Path,
        stat: os.stat_result,
        config: Config,
        *,
        include_diff: bool,
    ) -> str:
        return _clean_cache_key(path, stat, config, include_diff=include_diff)

    def read_configured_file(
        self,
        cache_key: str,
        stat: os.stat_result,
        *,
        path: Path,
        config: Config,
        rules: Collection[LintRule],
        autofix: bool,
        allow_cached_dirty_results: bool = False,
    ) -> tuple[list[Result] | None, set[str], bool]:
        cached_results = self._read_result(
            cache_key,
            stat,
            path=path,
            config=config,
            rules=rules,
        )
        if cached_results is None:
            return None, set(), False

        if all(result.violation is None for result in cached_results):
            return cached_results, set(), True

        if not autofix and allow_cached_dirty_results:
            return cached_results, set(), True

        if not autofix:
            return None, set(), False

        autofix_rule_names = {
            violation.rule_name
            for result in cached_results
            if (violation := result.violation) is not None and violation.autofixable
        }
        if not autofix_rule_names:
            return None, set(), False

        return cached_results, autofix_rule_names, False

    def write_result(
        self,
        cache_key: str,
        stat: os.stat_result,
        *,
        source: FileContent | None = None,
        violations: list[LintViolation] | None = None,
        rules: Collection[LintRule] = (),
    ) -> None:
        entry_path = self._result_entry_path(cache_key)
        rule_fingerprints: list[object] = [rule_cache_fingerprint(rule) for rule in rules]
        if violations:
            assert source is not None
            entry = ResultCacheEntry(
                version=CACHE_VERSION,
                mtime_ns=stat.st_mtime_ns,
                size=stat.st_size,
                status="violations",
                rule_fingerprints=rule_fingerprints,
                rule_fingerprint_hash=_rule_fingerprint_hash(rule_fingerprints),
                source=base64.b64encode(source).decode("ascii"),
                violations=[SerializedViolationCacheEntry.from_violation(v) for v in violations],
            )
        else:
            entry = ResultCacheEntry(
                version=CACHE_VERSION,
                mtime_ns=stat.st_mtime_ns,
                size=stat.st_size,
                status="clean",
                rule_fingerprints=rule_fingerprints,
                rule_fingerprint_hash=_rule_fingerprint_hash(rule_fingerprints),
            )

        self._write_json(entry_path, entry, error_message="Failed to write clean cache")

    def write_clean_status(
        self,
        path: Path,
        stat: os.stat_result,
        *,
        options: Options | None,
        explicit_path: bool,
        include_diff: bool,
        rules: Collection[LintRule],
    ) -> None:
        config_fingerprints = _config_path_fingerprints(path, options=options)
        cache_key = _clean_status_cache_key(
            path,
            stat,
            options=options,
            explicit_path=explicit_path,
            include_diff=include_diff,
            config_fingerprints=config_fingerprints,
        )
        entry_path = self._clean_status_entry_path(cache_key)
        rule_fingerprints: list[object] = [rule_cache_fingerprint(rule) for rule in rules]
        entry = CleanStatusCacheEntry(
            version=CACHE_VERSION,
            status="clean",
            mtime_ns=stat.st_mtime_ns,
            size=stat.st_size,
            rule_fingerprints=rule_fingerprints,
            rule_fingerprint_hash=_rule_fingerprint_hash(rule_fingerprints),
        )
        self._write_json(entry_path, entry, error_message="Failed to write clean status cache")

    def collect_pending_paths(
        self,
        expanded_paths: list[tuple[Path, bool]],
        *,
        include_diff: bool,
        options: Options | None,
    ) -> PendingPathCollection:
        pending_paths = [(path.resolve(), explicit_path) for path, explicit_path in expanded_paths]
        if len(pending_paths) < CLEAN_STATUS_PRECHECK_MIN_PATHS:
            return PendingPathCollection(pending_paths, [])

        cached_results: list[Result] = []
        remaining_paths: list[tuple[Path, bool]] = []
        for path, explicit_path in pending_paths:
            result = self._read_clean_status(
                path,
                options=options,
                explicit_path=explicit_path,
                include_diff=include_diff,
            )
            if result is None:
                remaining_paths.append((path, explicit_path))
            else:
                cached_results.append(result)
        return PendingPathCollection(remaining_paths, cached_results)

    def _result_entry_path(self, cache_key: str) -> Path:
        return self.root / cache_key[:2] / f"{cache_key}.json"

    def _clean_status_entry_path(self, cache_key: str) -> Path:
        return self.root / "clean" / cache_key[:2] / f"{cache_key}.json"

    def _read_result(
        self,
        cache_key: str,
        stat: os.stat_result,
        *,
        path: Path,
        config: Config,
        rules: Collection[LintRule],
    ) -> list[Result] | None:
        try:
            raw = self._result_entry_path(cache_key).read_bytes()
            entry = RESULT_CACHE_DECODER.decode(raw)
        except (OSError, DecodeError):
            return None

        if (
            entry.mtime_ns != stat.st_mtime_ns
            or entry.size != stat.st_size
            or not _cached_result_entry_matches_current_rules(entry, rules)
        ):
            return None
        if entry.status == "clean":
            return [Result(path, violation=None, config=config)]

        source = _decode_cached_source(entry)
        if source is None:
            return None

        return [
            Result(path, violation=violation.to_violation(), source=source, config=config)
            for violation in entry.violations
        ]

    def _read_clean_status(
        self,
        path: Path,
        *,
        options: Options | None,
        explicit_path: bool,
        include_diff: bool,
        config_fingerprints: tuple[tuple[str, int, int], ...] | None = None,
    ) -> Result | None:
        path = path.resolve()
        try:
            stat = path.stat()
        except OSError:
            return None

        if config_fingerprints is None:
            config_fingerprints = _config_path_fingerprints(path, options=options)
        cache_key = _clean_status_cache_key(
            path,
            stat,
            options=options,
            explicit_path=explicit_path,
            include_diff=include_diff,
            config_fingerprints=config_fingerprints,
        )
        try:
            raw = self._clean_status_entry_path(cache_key).read_bytes()
            entry = CLEAN_STATUS_CACHE_DECODER.decode(raw)
        except (OSError, DecodeError):
            return None

        if entry.mtime_ns != stat.st_mtime_ns or entry.size != stat.st_size:
            return None
        if not _cached_rule_fingerprints_match(
            entry.rule_fingerprints,
            entry.rule_fingerprint_hash,
        ):
            return None

        return Result(path, violation=None)

    def _write_json(
        self,
        entry_path: Path,
        entry: Struct,
        *,
        error_message: str,
    ) -> None:
        try:
            entry_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = entry_path.with_name(f"{entry_path.name}.{os.getpid()}.{uuid.uuid4()}.tmp")
            tmp_path.write_bytes(encode_json(entry, order="sorted"))
            tmp_path.replace(entry_path)
            _prune_cache(self.root)
        except OSError:
            LOG.debug(error_message, exc_info=True)


def _prune_cache(
    root: Path,
    *,
    max_bytes: int = CACHE_MAX_BYTES,
    target_bytes: int = CACHE_PRUNE_TARGET_BYTES,
) -> None:
    entries: list[tuple[int, int, Path]] = []
    total_bytes = 0
    try:
        paths = list(root.rglob("*.json"))
        for path in paths:
            try:
                stat = path.stat()
            except OSError:
                continue
            total_bytes += stat.st_size
            entries.append((stat.st_mtime_ns, stat.st_size, path))
    except OSError:
        return

    if total_bytes <= max_bytes:
        return

    for _, size, path in sorted(entries):
        try:
            path.unlink()
        except OSError:
            continue
        total_bytes -= size
        if total_bytes <= target_bytes:
            return


__all__ = ["ResultCache"]
