from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from libcst import Name
from msgspec import Struct, field
from msgspec.json import Decoder as JsonDecoder

from rattle.diagnostics import CodePosition, CodeRange, LintViolation, Result

CACHE_VERSION = "results-v1"


class CachedCodePosition(Struct, frozen=True):
    line: int
    column: int


class CachedCodeRange(Struct, frozen=True):
    start: CachedCodePosition
    end: CachedCodePosition

    @classmethod
    def from_code_range(cls, code_range: CodeRange) -> CachedCodeRange:
        return cls(
            start=CachedCodePosition(code_range.start.line, code_range.start.column),
            end=CachedCodePosition(code_range.end.line, code_range.end.column),
        )

    def to_code_range(self) -> CodeRange:
        return CodeRange(
            start=CodePosition(line=self.start.line, column=self.start.column),
            end=CodePosition(line=self.end.line, column=self.end.column),
        )


class SerializedViolationCacheEntry(Struct, frozen=True):
    rule_name: str
    range: CachedCodeRange
    message: str
    autofixable: bool
    diff: str

    @classmethod
    def from_violation(cls, violation: LintViolation) -> SerializedViolationCacheEntry:
        assert violation.range is not None
        return cls(
            rule_name=violation.rule_name,
            range=CachedCodeRange.from_code_range(violation.range),
            message=violation.message,
            autofixable=violation.autofixable,
            diff=violation.diff,
        )

    def to_violation(self) -> LintViolation:
        return LintViolation(
            rule_name=self.rule_name,
            range=self.range.to_code_range(),
            message=self.message,
            node=Name("__rattle_cached_violation__"),
            replacement=Name("__rattle_cached_replacement__") if self.autofixable else None,
            diff=self.diff,
        )


class ResultCacheEntry(Struct, frozen=True, kw_only=True, omit_defaults=True):
    version: Literal["results-v1"]
    mtime_ns: int
    size: int
    status: Literal["clean", "violations"]
    rule_fingerprints: list[object]
    rule_fingerprint_hash: str | None = None
    source: str | None = None
    violations: list[SerializedViolationCacheEntry] = field(default_factory=list)


class CleanStatusCacheEntry(Struct, frozen=True, kw_only=True, omit_defaults=True):
    version: Literal["results-v1"]
    status: Literal["clean"]
    mtime_ns: int
    size: int
    rule_fingerprints: list[object]
    rule_fingerprint_hash: str | None = None


@dataclass(frozen=True)
class PendingPathCollection:
    pending_paths: list[tuple[Path, bool]]
    cached_results: list[Result]


RESULT_CACHE_DECODER = JsonDecoder(ResultCacheEntry, strict=True)
CLEAN_STATUS_CACHE_DECODER = JsonDecoder(CleanStatusCacheEntry, strict=True)

__all__ = [
    "CleanStatusCacheEntry",
    "PendingPathCollection",
    "ResultCacheEntry",
    "SerializedViolationCacheEntry",
]
