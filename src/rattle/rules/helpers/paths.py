from __future__ import annotations

import fnmatch
from pathlib import Path


def matches_any_pattern(patterns: list[str], value: str) -> bool:
    return any(fnmatch.fnmatchcase(value, pattern) for pattern in patterns)


def path_candidates(path: Path) -> tuple[str, ...]:
    candidates = [path.as_posix(), path.name]
    try:
        candidates.append(path.relative_to(Path.cwd()).as_posix())
    except ValueError:
        pass

    return tuple(dict.fromkeys(candidates))


def matches_path(pattern: str, path: Path) -> bool:
    return any(fnmatch.fnmatchcase(candidate, pattern) for candidate in path_candidates(path))


def matches_exact_path(expected_path: str, path: Path) -> bool:
    return expected_path in path_candidates(path)


def is_excluded_path(path: Path, excluded_path_parts: list[str]) -> bool:
    if path.name.startswith("test_") or path.name.endswith("_test.py"):
        return True

    return any(part in excluded_path_parts for part in path.parts)
