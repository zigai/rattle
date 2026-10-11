import hashlib
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

TOMLDecodeError = tomllib.TOMLDecodeError


@dataclass(frozen=True)
class PyprojectCacheEntry:
    mtime_ns: int
    size: int
    source_hash: bytes
    document: dict[str, object]


_pyproject_cache: dict[Path, PyprojectCacheEntry] = {}


def load_pyproject(
    path: Path,
    *,
    stat: os.stat_result | None = None,
) -> dict[str, object]:
    """Load a pyproject document, caching it until its contents or metadata change."""
    file_stat = stat or path.stat()
    content = path.read_bytes()
    source_hash = hashlib.sha256(content).digest()
    cached_entry = _pyproject_cache.get(path)
    if (
        cached_entry is not None
        and cached_entry.mtime_ns == file_stat.st_mtime_ns
        and cached_entry.size == file_stat.st_size
        and cached_entry.source_hash == source_hash
    ):
        return cached_entry.document

    document = tomllib.loads(content.decode())
    _pyproject_cache[path] = PyprojectCacheEntry(
        mtime_ns=file_stat.st_mtime_ns,
        size=file_stat.st_size,
        source_hash=source_hash,
        document=document,
    )
    return document


__all__ = ["TOMLDecodeError", "load_pyproject"]
