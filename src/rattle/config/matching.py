from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath

from rattle.config.errors import ConfigError
from rattle.config.models import Options, RawConfig
from rattle.config.parsing import (
    ConfigModelError,
    parse_exact_rule_target,
    parse_ruff_config,
)
from rattle.pyproject import load_pyproject
from rattle.selectors import RuleOptionsTable, is_rule_option_value, is_sequence

GLOB_META_CHARS = frozenset("*?[")


def get_rule_pattern_table(
    config: RawConfig, key: str, *, data: dict[str, object] | None = None
) -> dict[str, list[str]]:
    mapping = data.pop(key, {}) if data else config.data.pop(key, {})

    if not isinstance(mapping, Mapping):
        raise ConfigError(f"{key!r} must be mapping of values, got {type(mapping)}", config=config)

    result: dict[str, list[str]] = {}
    for raw_pattern, rules in mapping.items():
        if not isinstance(raw_pattern, str):
            raise ConfigError(
                f"{key!r} pattern must be a string, got {type(raw_pattern)}",
                config=config,
            )
        if not raw_pattern:
            raise ConfigError(f"{key!r} pattern may not be empty", config=config)
        if not is_sequence(rules):
            raise ConfigError(
                f"{key!r} value for {raw_pattern!r} must be array of values, got {type(rules)}",
                config=config,
            )

        pattern_rules: list[str] = []
        for rule in rules:
            if not isinstance(rule, str):
                raise ConfigError(
                    f"{key!r} value for {raw_pattern!r} must contain strings, got {type(rule)}",
                    config=config,
                )
            pattern_rules.append(rule)

        result[raw_pattern] = pattern_rules

    return result


def _get_string_sequence_from_mapping(
    config: RawConfig, mapping: Mapping[str, object], key: str
) -> list[str]:
    value = mapping.get(key, ())

    if not is_sequence(value):
        raise ConfigError(f"{key!r} must be array of values, got {type(value)}", config=config)

    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ConfigError(f"{key!r} values must be strings, got {type(item)}", config=config)
        result.append(item)

    return result


def _read_ruff_file_selection(config: RawConfig) -> tuple[list[str], list[str], bool]:
    pyproject_path = (
        config.path
        if config.path.name == "pyproject.toml"
        else config.path.parent / "pyproject.toml"
    )
    if not pyproject_path.is_file():
        return [], [], False

    data = load_pyproject(pyproject_path)
    tool_data = data.get("tool", {})
    if not isinstance(tool_data, Mapping):
        return [], [], False
    ruff_data = tool_data.get("ruff", {})

    if not ruff_data:
        return [], [], False
    try:
        parsed_ruff = parse_ruff_config(ruff_data)
    except ConfigModelError as e:
        raise ConfigError(f"Invalid 'tool.ruff' configuration: {e}", config=config) from None

    includes = [*parsed_ruff.include, *parsed_ruff.extend_include]
    excludes = [*parsed_ruff.exclude, *parsed_ruff.extend_exclude]
    return includes, excludes, parsed_ruff.force_exclude


def _relative_path_str(path: Path, base: Path) -> str | None:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return None


def _path_matches_glob(relative_path: str, pattern: str) -> bool:
    has_glob = any(char in pattern for char in GLOB_META_CHARS)

    if "/" not in pattern:
        parts = relative_path.split("/")
        if has_glob:
            path = PurePosixPath()
            return any(path.joinpath(part).match(pattern) for part in parts)
        return pattern in parts

    if not has_glob:
        return relative_path == pattern or relative_path.startswith(f"{pattern}/")

    return PurePosixPath(relative_path).match(pattern)


def _path_matches_current_dir_glob(path: Path, pattern: str) -> bool:
    relative_path = _relative_path_str(path, Path.cwd())
    if relative_path is None:
        relative_path = path.as_posix()
    return _path_matches_glob(relative_path, pattern)


def _excluded_by_options_without_configs(
    path: Path,
    options: Options,
    *,
    explicit_path: bool,
) -> bool:
    patterns = options.exclude or options.extend_exclude
    return bool(
        patterns
        and any(_path_matches_current_dir_glob(path, pattern) for pattern in patterns)
        and (options.exclude or not explicit_path)
    )


def get_sequence(
    config: RawConfig, key: str, *, data: dict[str, object] | None = None
) -> Sequence[str]:
    value = data.pop(key, ()) if data else config.data.pop(key, ())

    if not is_sequence(value):
        raise ConfigError(f"{key!r} must be array of values, got {type(value)}", config=config)

    values: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ConfigError(f"{key!r} values must be strings, got {type(item)}", config=config)
        values.append(item)
    return values


def get_options(  # noqa: C901 - option parsing and normalization
    config: RawConfig, key: str, *, data: dict[str, object] | None = None
) -> RuleOptionsTable:

    mapping = data.pop(key, {}) if data else config.data.pop(key, {})

    if is_sequence(mapping):
        merged_mapping: dict[object, object] = {}
        for item in mapping:
            if not isinstance(item, Mapping):
                raise ConfigError(
                    f"{key!r} sequence values must be mappings, got {type(item)}",
                    config=config,
                )
            merged_mapping.update(item)
        mapping = merged_mapping

    if not isinstance(mapping, Mapping):
        raise ConfigError(f"{key!r} must be mapping of values, got {type(mapping)}", config=config)

    rule_configs: RuleOptionsTable = {}
    for raw_rule_name, rule_config in mapping.items():
        if not isinstance(raw_rule_name, str):
            raise ConfigError(
                f"{key!r} rule name must be a string, got {type(raw_rule_name)}",
                config=config,
            )

        try:
            rule_target = parse_exact_rule_target(raw_rule_name, config.path.parent, config)
        except ConfigError as e:
            raise ConfigError(f"{key!r} {e}", config=config) from e

        if not isinstance(rule_config, Mapping):
            raise ConfigError(
                f"{key!r} rule config for {raw_rule_name!r} must be a mapping, got {type(rule_config)}",
                config=config,
            )

        rule_name = str(rule_target)
        rule_configs[rule_name] = {}
        for option_name, value in rule_config.items():
            if not isinstance(option_name, str):
                raise ConfigError(
                    f"{key!r} option names must be strings, got {type(option_name)}",
                    config=config,
                )

            if not is_rule_option_value(value):
                raise ConfigError(
                    f"{option_name!r} must be a TOML scalar, array, or table, got {type(value)}",
                    config=config,
                )

            rule_configs[rule_name][option_name] = value

    return rule_configs


__all__ = ["get_options", "get_rule_pattern_table", "get_sequence"]
