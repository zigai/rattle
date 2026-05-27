import base64
import hashlib
import inspect
import json
import logging
import os
from collections.abc import Collection, Generator
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from libcst import Name
from platformdirs import user_cache_path

from .config import locate_configs
from .ftypes import (
    CodePosition,
    CodeRange,
    Config,
    FileContent,
    LintViolation,
    Options,
    Result,
)
from .rule import LintRule

LOG = logging.getLogger(__name__)
CACHE_VERSION = "results-v1"
CLEAN_STATUS_PRECHECK_MIN_PATHS = 20
_rule_fingerprint_validation_cache: dict[str, bool] = {}


@dataclass(frozen=True)
class SerializedViolationCacheEntry:
    rule_name: str
    range: CodeRange
    message: str
    autofixable: bool
    diff: str

    @classmethod
    def from_violation(cls, violation: LintViolation) -> "SerializedViolationCacheEntry":
        assert violation.range is not None
        return cls(
            rule_name=violation.rule_name,
            range=violation.range,
            message=violation.message,
            autofixable=violation.autofixable,
            diff=violation.diff,
        )

    def to_json(self) -> dict[str, object]:
        return {
            "rule_name": self.rule_name,
            "range": {
                "start": {
                    "line": self.range.start.line,
                    "column": self.range.start.column,
                },
                "end": {
                    "line": self.range.end.line,
                    "column": self.range.end.column,
                },
            },
            "message": self.message,
            "autofixable": self.autofixable,
            "diff": self.diff,
        }

    def to_violation(self) -> LintViolation:
        return LintViolation(
            rule_name=self.rule_name,
            range=self.range,
            message=self.message,
            node=Name("__rattle_cached_violation__"),
            replacement=Name("__rattle_cached_replacement__") if self.autofixable else None,
            diff=self.diff,
        )


@dataclass(frozen=True)
class ResultCacheEntry:
    mtime_ns: int
    size: int
    status: str
    rule_fingerprints: list[object]
    rule_fingerprint_hash: str | None
    source: str | None
    violations: list[SerializedViolationCacheEntry]


@dataclass(frozen=True)
class CleanStatusCacheEntry:
    mtime_ns: int
    size: int
    rule_fingerprints: list[object]
    rule_fingerprint_hash: str | None


@dataclass(frozen=True)
class ResultCache:
    root: Path

    @classmethod
    def from_environment(cls) -> "ResultCache | None":
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
        autofix: bool,
    ) -> tuple[list[Result] | None, set[str], bool]:
        cached_results = self._read_result(
            cache_key,
            stat,
            path=path,
            config=config,
        )
        if cached_results is None:
            return None, set(), False

        if all(result.violation is None for result in cached_results):
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
        data: dict[str, object] = {
            "version": CACHE_VERSION,
            "mtime_ns": stat.st_mtime_ns,
            "size": stat.st_size,
        }
        rule_fingerprints: list[object] = [rule_cache_fingerprint(rule) for rule in rules]
        data["rule_fingerprints"] = rule_fingerprints
        data["rule_fingerprint_hash"] = _rule_fingerprint_hash(rule_fingerprints)
        if violations:
            assert source is not None
            data["status"] = "violations"
            data["source"] = base64.b64encode(source).decode("ascii")
            data["violations"] = [_serialize_violation(violation) for violation in violations]
        else:
            data["status"] = "clean"

        self._write_json(entry_path, data, error_message="Failed to write clean cache")

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
        data: dict[str, object] = {
            "version": CACHE_VERSION,
            "status": "clean",
            "mtime_ns": stat.st_mtime_ns,
            "size": stat.st_size,
        }
        rule_fingerprints: list[object] = [rule_cache_fingerprint(rule) for rule in rules]
        data["rule_fingerprints"] = rule_fingerprints
        data["rule_fingerprint_hash"] = _rule_fingerprint_hash(rule_fingerprints)
        self._write_json(entry_path, data, error_message="Failed to write clean status cache")

    def collect_pending_paths(
        self,
        expanded_paths: list[tuple[Path, bool]],
        *,
        include_diff: bool,
        options: Options | None,
    ) -> Generator[Result, None, list[tuple[Path, bool]]]:
        clean_precheck = len(expanded_paths) >= CLEAN_STATUS_PRECHECK_MIN_PATHS
        config_fingerprint_cache: dict[Path, tuple[tuple[str, int, int], ...]] = {}
        pending_paths: list[tuple[Path, bool]] = []
        for path, explicit_path in expanded_paths:
            path = path.resolve()
            if clean_precheck:
                parent = path.parent
                config_fingerprints = config_fingerprint_cache.get(parent)
                if config_fingerprints is None:
                    config_fingerprints = _config_path_fingerprints(path, options=options)
                    config_fingerprint_cache[parent] = config_fingerprints
                cached_clean = self._read_clean_status(
                    path,
                    options=options,
                    explicit_path=explicit_path,
                    include_diff=include_diff,
                    config_fingerprints=config_fingerprints,
                )
                if cached_clean is not None:
                    yield cached_clean
                    continue
            pending_paths.append((path, explicit_path))
        return pending_paths

    def collect_uncached_paths(
        self,
        included_paths: list[tuple[Path, Config, bool]],
        *,
        include_diff: bool,
    ) -> Generator[Result, None, list[tuple[Path, Config, bool]]]:
        uncached_paths: list[tuple[Path, Config, bool]] = []
        for path, config, explicit_path in included_paths:
            cached_results = self._read_usable_result(
                path,
                config,
                include_diff=include_diff,
            )
            if cached_results is None:
                uncached_paths.append((path, config, explicit_path))
            else:
                yield from cached_results
        return uncached_paths

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
    ) -> list[Result] | None:
        try:
            raw = self._result_entry_path(cache_key).read_text()
            raw_data: object = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return None

        entry = _decode_result_cache_entry(raw_data, stat)
        if entry is None:
            return None
        if not _cached_rule_fingerprints_match(
            entry.rule_fingerprints,
            entry.rule_fingerprint_hash,
        ):
            return None

        if entry.status == "clean":
            return _cached_clean_results(path, config)

        source = _decode_cached_source(entry)
        if source is None:
            return None

        return [
            Result(path, violation=violation.to_violation(), source=source, config=config)
            for violation in entry.violations
        ]

    def _read_usable_result(
        self,
        path: Path,
        config: Config,
        *,
        include_diff: bool,
    ) -> list[Result] | None:
        path = path.resolve()
        try:
            stat = path.stat()
        except OSError:
            return None

        cache_key = self.result_key(path, stat, config, include_diff=include_diff)
        cached_results = self._read_result(
            cache_key,
            stat,
            path=path,
            config=config,
        )
        if cached_results is None:
            return None
        if any(result.violation is not None for result in cached_results):
            return None
        return cached_results

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
            raw = self._clean_status_entry_path(cache_key).read_text()
            raw_data: object = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return None

        entry = _decode_clean_status_cache_entry(raw_data, stat)
        if entry is None:
            return None
        if not _cached_rule_fingerprints_match(
            entry.rule_fingerprints,
            entry.rule_fingerprint_hash,
        ):
            return None

        try:
            source = path.read_bytes()
        except OSError:
            return None
        return Result(path, violation=None, source=source)

    def _write_json(
        self,
        entry_path: Path,
        data: dict[str, object],
        *,
        error_message: str,
    ) -> None:
        try:
            entry_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = entry_path.with_name(f"{entry_path.name}.{os.getpid()}.tmp")
            tmp_path.write_text(json.dumps(data, sort_keys=True))
            tmp_path.replace(entry_path)
        except OSError:
            LOG.debug(error_message, exc_info=True)


def _jsonable_option_value(value: object) -> object:
    if isinstance(value, list):
        return tuple(value)
    return value


@cache
def _path_stat_fingerprint(path: Path | None) -> tuple[str, int, int] | None:
    if path is None:
        return None

    try:
        stat = path.stat()
    except OSError:
        return (path.as_posix(), -1, -1)
    return (path.as_posix(), stat.st_mtime_ns, stat.st_size)


def rule_cache_fingerprint(rule: LintRule) -> tuple[object, ...]:
    rule_type = type(rule)
    try:
        source_path = inspect.getsourcefile(rule_type)
    except TypeError:
        source_path = None

    if source_path is None:
        for value in rule_type.__dict__.values():
            if inspect.isfunction(value):
                source_path = value.__code__.co_filename
                break

    resolved_source_path = Path(source_path).resolve() if source_path else None
    return (
        rule_type.__module__,
        rule_type.__qualname__,
        _path_stat_fingerprint(resolved_source_path),
        _path_stat_fingerprint(resolved_source_path.parent if resolved_source_path else None),
        tuple(
            sorted((name, _jsonable_option_value(value)) for name, value in rule.settings.items())
        ),
    )


def _clean_cache_key(
    path: Path,
    stat: os.stat_result,
    config: Config,
    *,
    include_diff: bool,
) -> str:
    payload: dict[str, object] = {
        "version": CACHE_VERSION,
        "path": path.as_posix(),
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
        "include_diff": include_diff,
        "root": config.root.as_posix(),
        "enable_root_import": config.enable_root_import.as_posix()
        if isinstance(config.enable_root_import, Path)
        else config.enable_root_import,
        "enable": [str(selector) for selector in config.enable],
        "disable": [str(selector) for selector in config.disable],
        "options": [
            (
                rule_name,
                sorted(
                    (option_name, _jsonable_option_value(value))
                    for option_name, value in options.items()
                ),
            )
            for rule_name, options in sorted(config.options.items())
        ],
        "tags": [config.tags.include, config.tags.exclude],
        "python_version": str(config.python_version) if config.python_version is not None else None,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _option_selectors_for_cache(options: Options | None) -> tuple[object, ...]:
    if options is None:
        return ()
    return (
        options.config_file.resolve().as_posix() if options.config_file else None,
        str(options.tags) if options.tags else None,
        tuple(str(rule) for rule in options.rules),
        options.output_format.value if options.output_format else None,
        options.output_template,
    )


def _config_path_fingerprints(
    path: Path,
    *,
    options: Options | None,
) -> tuple[tuple[str, int, int], ...]:
    if options and options.config_file:
        config_paths: list[Path] = [options.config_file]
    else:
        config_paths = locate_configs(path)
    return tuple(
        fingerprint
        for config_path in config_paths
        if (fingerprint := _path_stat_fingerprint(config_path)) is not None
    )


def _clean_status_cache_key(
    path: Path,
    stat: os.stat_result,
    *,
    options: Options | None,
    explicit_path: bool,
    include_diff: bool,
    config_fingerprints: tuple[tuple[str, int, int], ...],
) -> str:
    payload: dict[str, object] = {
        "version": CACHE_VERSION,
        "kind": "clean-status",
        "path": path.as_posix(),
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
        "include_diff": include_diff,
        "explicit_path": explicit_path,
        "options": _option_selectors_for_cache(options),
        "config_fingerprints": config_fingerprints,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _fingerprint_matches(raw_fingerprint: object) -> bool:
    if not isinstance(raw_fingerprint, list | tuple) or len(raw_fingerprint) < 4:
        return False

    for raw_path_stat in (raw_fingerprint[2], raw_fingerprint[3]):
        if (
            not isinstance(raw_path_stat, list | tuple)
            or len(raw_path_stat) != 3
            or not isinstance(raw_path_stat[0], str)
        ):
            return False
        path = Path(raw_path_stat[0])
        current = _path_stat_fingerprint(path)
        if current != tuple(raw_path_stat):
            return False

    return True


def _rule_fingerprints_match(raw_fingerprints: object) -> bool:
    if not isinstance(raw_fingerprints, list):
        return False
    return all(_fingerprint_matches(raw_fingerprint) for raw_fingerprint in raw_fingerprints)


def _rule_fingerprint_hash(raw_fingerprints: object) -> str | None:
    if not isinstance(raw_fingerprints, list):
        return None
    try:
        encoded = json.dumps(raw_fingerprints, sort_keys=True, separators=(",", ":")).encode()
    except TypeError:
        return None
    return hashlib.sha256(encoded).hexdigest()


def _cached_rule_fingerprints_match(
    raw_fingerprints: object,
    raw_fingerprint_hash: object,
) -> bool:
    fingerprint_hash = raw_fingerprint_hash if isinstance(raw_fingerprint_hash, str) else None
    if fingerprint_hash is None:
        fingerprint_hash = _rule_fingerprint_hash(raw_fingerprints)
    if fingerprint_hash is None:
        return False

    cached = _rule_fingerprint_validation_cache.get(fingerprint_hash)
    if cached is not None:
        return cached

    valid = _rule_fingerprints_match(raw_fingerprints)
    _rule_fingerprint_validation_cache[fingerprint_hash] = valid
    return valid


def _decode_code_position(value: object) -> CodePosition | None:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        return None

    line = value.get("line")
    column = value.get("column")
    if type(line) is not int or type(column) is not int:
        return None
    return CodePosition(line=line, column=column)


def _decode_code_range(value: object) -> CodeRange | None:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        return None

    start = _decode_code_position(value.get("start"))
    end = _decode_code_position(value.get("end"))
    if start is None or end is None:
        return None
    return CodeRange(start=start, end=end)


def _decode_serialized_violation(value: object) -> SerializedViolationCacheEntry | None:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        return None

    rule_name = value.get("rule_name")
    range_ = _decode_code_range(value.get("range"))
    message = value.get("message")
    autofixable = value.get("autofixable")
    diff = value.get("diff", "")
    if (
        not isinstance(rule_name, str)
        or range_ is None
        or not isinstance(message, str)
        or not isinstance(autofixable, bool)
        or not isinstance(diff, str)
    ):
        return None

    return SerializedViolationCacheEntry(
        rule_name=rule_name,
        range=range_,
        message=message,
        autofixable=autofixable,
        diff=diff,
    )


def _decode_rule_fingerprints(value: object) -> list[object] | None:
    if not isinstance(value, list):
        return None
    return value


def _decode_cache_entry_header(
    value: object,
    stat: os.stat_result,
    *,
    required_status: str | None = None,
) -> tuple[dict[str, object], list[object], str | None] | None:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        return None
    if value.get("version") != CACHE_VERSION:
        return None
    if value.get("mtime_ns") != stat.st_mtime_ns or value.get("size") != stat.st_size:
        return None
    if required_status is not None and value.get("status") != required_status:
        return None

    rule_fingerprints = _decode_rule_fingerprints(value.get("rule_fingerprints"))
    if rule_fingerprints is None:
        return None

    raw_fingerprint_hash = value.get("rule_fingerprint_hash")
    rule_fingerprint_hash = raw_fingerprint_hash if isinstance(raw_fingerprint_hash, str) else None
    return value, rule_fingerprints, rule_fingerprint_hash


def _decode_result_cache_entry(value: object, stat: os.stat_result) -> ResultCacheEntry | None:
    decoded = _decode_cache_entry_header(value, stat)
    if decoded is None:
        return None

    data, rule_fingerprints, rule_fingerprint_hash = decoded
    status = data.get("status")
    if status == "clean":
        return ResultCacheEntry(
            mtime_ns=stat.st_mtime_ns,
            size=stat.st_size,
            status=status,
            rule_fingerprints=rule_fingerprints,
            rule_fingerprint_hash=rule_fingerprint_hash,
            source=None,
            violations=[],
        )
    if status != "violations":
        return None

    source = data.get("source")
    raw_violations = data.get("violations")
    if not isinstance(source, str) or not isinstance(raw_violations, list):
        return None

    violations: list[SerializedViolationCacheEntry] = []
    for raw_violation in raw_violations:
        violation = _decode_serialized_violation(raw_violation)
        if violation is None:
            return None
        violations.append(violation)

    return ResultCacheEntry(
        mtime_ns=stat.st_mtime_ns,
        size=stat.st_size,
        status=status,
        rule_fingerprints=rule_fingerprints,
        rule_fingerprint_hash=rule_fingerprint_hash,
        source=source,
        violations=violations,
    )


def _decode_clean_status_cache_entry(
    value: object,
    stat: os.stat_result,
) -> CleanStatusCacheEntry | None:
    decoded = _decode_cache_entry_header(value, stat, required_status="clean")
    if decoded is None:
        return None

    _data, rule_fingerprints, rule_fingerprint_hash = decoded
    return CleanStatusCacheEntry(
        mtime_ns=stat.st_mtime_ns,
        size=stat.st_size,
        rule_fingerprints=rule_fingerprints,
        rule_fingerprint_hash=rule_fingerprint_hash,
    )


def _decode_cached_source(entry: ResultCacheEntry) -> FileContent | None:
    if entry.source is None:
        return None

    try:
        return base64.b64decode(entry.source)
    except ValueError:
        return None


def _cached_clean_results(path: Path, config: Config) -> list[Result] | None:
    try:
        source = path.read_bytes()
    except OSError:
        return None
    return [Result(path, violation=None, source=source, config=config)]


def _serialize_violation(violation: LintViolation) -> dict[str, object]:
    return SerializedViolationCacheEntry.from_violation(violation).to_json()


__all__ = (
    "ResultCache",
    "rule_cache_fingerprint",
)
