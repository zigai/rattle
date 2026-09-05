from __future__ import annotations

import base64
import binascii
import hashlib
import inspect
import json
import os
import platform
from collections.abc import Collection
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from rattle.cache.models import CACHE_VERSION, ResultCacheEntry
from rattle.config.discovery import locate_configs
from rattle.config.models import Config, Options
from rattle.diagnostics import FileContent
from rattle.rule import LintRule


def _jsonable_option_value(value: object) -> object:
    if isinstance(value, list):
        return tuple(value)
    return value


def _path_stat_fingerprint(path: Path | None) -> tuple[str, int, int] | None:
    if path is None:
        return None

    try:
        stat = path.stat()
    except OSError:
        return (path.as_posix(), -1, -1)
    return (path.as_posix(), stat.st_mtime_ns, stat.st_size)


def _package_version(package_name: str) -> str | None:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return None


def _runtime_fingerprint() -> tuple[tuple[str, str | None], ...]:
    return (
        ("python", platform.python_version()),
        ("rattle-lint", _package_version("rattle-lint")),
        ("libcst", _package_version("libcst")),
    )


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
        _sibling_python_file_fingerprints(resolved_source_path),
        tuple(
            sorted((name, _jsonable_option_value(value)) for name, value in rule.settings.items())
        ),
    )


def _sibling_python_file_fingerprints(
    source_path: Path | None,
) -> tuple[tuple[str, int, int], ...]:
    if source_path is None:
        return ()
    try:
        paths = sorted(source_path.parent.glob("*.py"))
    except OSError:
        return ()
    return tuple(
        fingerprint
        for path in paths
        if (fingerprint := _path_stat_fingerprint(path.resolve())) is not None
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
        "runtime": _runtime_fingerprint(),
        "path": path.as_posix(),
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
        "include_diff": include_diff,
        "root": config.root.as_posix(),
        "enable_root_import": config.enable_root_import.as_posix()
        if isinstance(config.enable_root_import, Path)
        else config.enable_root_import,
        "rule_imports": [str(selector) for selector in config.rule_imports],
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
        tuple(options.exclude),
        tuple(options.extend_exclude),
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
        "runtime": _runtime_fingerprint(),
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
        if not _path_stat_fingerprint_matches(raw_path_stat):
            return False

    if len(raw_fingerprint) >= 6:
        raw_sibling_stats = raw_fingerprint[4]
        if not isinstance(raw_sibling_stats, list | tuple):
            return False
        for raw_path_stat in raw_sibling_stats:
            if not _path_stat_fingerprint_matches(raw_path_stat):
                return False

    return True


def _path_stat_fingerprint_matches(raw_path_stat: object) -> bool:
    if (
        not isinstance(raw_path_stat, list | tuple)
        or len(raw_path_stat) != 3
        or not isinstance(raw_path_stat[0], str)
    ):
        return False
    path = Path(raw_path_stat[0])
    current = _path_stat_fingerprint(path)
    return current == tuple(raw_path_stat)


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
    del raw_fingerprint_hash
    if not isinstance(raw_fingerprints, list):
        return False
    return _rule_fingerprints_match(raw_fingerprints)


def _cached_result_entry_matches_current_rules(
    entry: ResultCacheEntry,
    rules: Collection[LintRule],
) -> bool:
    return _cached_rule_fingerprints_match(
        entry.rule_fingerprints,
        entry.rule_fingerprint_hash,
    ) and _cached_rule_set_matches_current(entry, rules)


def _cached_rule_set_matches_current(
    entry: ResultCacheEntry,
    rules: Collection[LintRule],
) -> bool:
    current_rule_fingerprints: list[object] = [rule_cache_fingerprint(rule) for rule in rules]
    current_rule_fingerprint_hash = _rule_fingerprint_hash(current_rule_fingerprints)
    entry_rule_fingerprint_hash = entry.rule_fingerprint_hash
    if entry_rule_fingerprint_hash is None:
        entry_rule_fingerprint_hash = _rule_fingerprint_hash(entry.rule_fingerprints)
    return (
        current_rule_fingerprint_hash is not None
        and entry_rule_fingerprint_hash == current_rule_fingerprint_hash
    )


def _decode_cached_source(entry: ResultCacheEntry) -> FileContent | None:
    if entry.source is None:
        return None

    try:
        return base64.b64decode(entry.source, validate=True)
    except (ValueError, binascii.Error):
        return None


__all__ = ["rule_cache_fingerprint"]
