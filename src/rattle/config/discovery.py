from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from functools import cache
from pathlib import Path

from rattle.config.errors import ConfigError
from rattle.config.models import RawConfig
from rattle.config.parsing import ConfigModelError, parse_rattle_config
from rattle.pyproject import load_pyproject

RATTLE_CONFIG_FILENAMES = ("pyproject.toml",)


def locate_configs(path: Path, root: Path | None = None) -> list[Path]:
    """
    Given a file path, locate all relevant config files in priority order.

    Walking upward from target path, creates a list of candidate paths that exist
    on disk, ordered from nearest/highest priority to further/lowest priority.

    If root is given, only return configs between path and root (inclusive), ignoring
    any paths outside of root, even if they would contain relevant configs.
    If given, root must contain path.

    Returns a list of config paths in priority order, from highest priority to lowest.
    """
    if not path.is_dir():
        path = path.parent

    root = root.resolve() if root is not None else Path(path.anchor)
    path = path.resolve()
    return list(
        _locate_configs_for_directory(
            path,
            root,
            _directory_fingerprints(path, root),
        )
    )


@cache
def _locate_configs_for_directory(
    path: Path,
    root: Path,
    directory_fingerprints: tuple[tuple[str, int, int], ...],
) -> tuple[Path, ...]:
    del directory_fingerprints
    path.relative_to(root)  # enforce path being inside root
    results: list[Path] = []
    while True:
        candidates = (path / filename for filename in RATTLE_CONFIG_FILENAMES)
        results.extend(candidate for candidate in candidates if candidate.is_file())

        if path in (root, path.parent):
            break

        path = path.parent

    return tuple(results)


def _directory_fingerprints(path: Path, root: Path) -> tuple[tuple[str, int, int], ...]:
    path.relative_to(root)  # enforce path being inside root
    fingerprints: list[tuple[str, int, int]] = []
    while True:
        try:
            stat = path.stat()
        except OSError:
            fingerprints.append((path.as_posix(), -1, -1))
        else:
            fingerprints.append((path.as_posix(), stat.st_mtime_ns, stat.st_size))

        if path in (root, path.parent):
            break
        path = path.parent

    return tuple(fingerprints)


def read_configs(paths: list[Path]) -> list[RawConfig]:
    """
    Read config data for each path given, and return their raw toml config values.

    Skips any path with no — or empty — `tool.rattle` section.
    Stops early at any config with `root = true`.

    Maintains the same order as given in paths, minus any skipped files.
    """
    configs: list[RawConfig] = []

    for path in paths:
        path = path.resolve()
        if path.name != "pyproject.toml":
            raise ConfigError(
                "Rattle only reads configuration from `pyproject.toml`",
            )
        try:
            stat = path.stat()
        except OSError as e:
            raise ConfigError(f"Failed to stat configuration file {path}") from e
        data = load_pyproject(path, stat=stat)
        tool_data = data.get("tool", {})
        if not isinstance(tool_data, Mapping):
            continue
        rattle_data = tool_data.get("rattle", {})

        if rattle_data:
            try:
                parsed_rattle_data = parse_rattle_config(rattle_data)
            except ConfigModelError as e:
                raise ConfigError(f"Invalid 'tool.rattle' configuration: {e}") from None
            config = RawConfig(path=path, data=deepcopy(parsed_rattle_data))
            configs.append(config)

            if config.data.get("root", False):
                break

    return configs


__all__ = ["locate_configs", "read_configs"]
