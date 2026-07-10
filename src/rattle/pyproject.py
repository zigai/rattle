import os
import sys
from dataclasses import dataclass
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

TOMLDecodeError = tomllib.TOMLDecodeError


@dataclass(frozen=True)
class PyprojectCacheEntry:
    mtime_ns: int
    size: int
    document: dict[str, object]


_pyproject_cache: dict[Path, PyprojectCacheEntry] = {}


def load_pyproject(
    path: Path,
    *,
    stat: os.stat_result | None = None,
) -> dict[str, object]:
    """Load a pyproject document, caching it until its file metadata changes."""
    file_stat = stat or path.stat()
    cached_entry = _pyproject_cache.get(path)
    if (
        cached_entry is not None
        and cached_entry.mtime_ns == file_stat.st_mtime_ns
        and cached_entry.size == file_stat.st_size
    ):
        return cached_entry.document

    document = tomllib.loads(path.read_text())
    _pyproject_cache[path] = PyprojectCacheEntry(
        mtime_ns=file_stat.st_mtime_ns,
        size=file_stat.st_size,
        document=document,
    )
    return document


__all__ = ["TOMLDecodeError", "load_pyproject"]
