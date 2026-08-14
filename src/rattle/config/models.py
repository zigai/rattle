from __future__ import annotations

import platform
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from packaging.version import Version

from rattle.rendering.models import OutputFormat
from rattle.selectors import RuleOptionsTable, RuleSelector, Tags


@dataclass
class Options:
    """Command-line options that affect runtime behavior."""

    debug: bool | None = None
    config_file: Path | None = None
    exclude: Sequence[str] = ()
    extend_exclude: Sequence[str] = ()
    jobs: int | None = None
    tags: Tags | None = None
    rules: Sequence[RuleSelector] = ()
    output_format: OutputFormat | None = None
    output_template: str | None = None
    print_metrics: bool = False
    no_format: bool = False


@dataclass
class LSPOptions:
    """Language-server transport and scheduling options."""

    tcp: int | None
    ws: int | None
    stdio: bool = True
    debounce_interval: float = 0.5


@dataclass
class Config:
    """Materialized configuration valid for processing a single file."""

    path: Path = field(default_factory=Path)
    root: Path = field(default_factory=Path.cwd)
    excluded: bool = False
    enable_root_import: bool | Path = False
    enable: list[RuleSelector] = field(default_factory=list)
    disable: list[RuleSelector] = field(default_factory=list)
    rule_imports: list[RuleSelector] = field(default_factory=list)
    options: RuleOptionsTable = field(default_factory=dict)
    python_version: Version | None = field(
        default_factory=lambda: Version(platform.python_version())
    )
    tags: Tags = field(default_factory=Tags)
    formatter: str | None = "auto"
    output_format: OutputFormat = OutputFormat.rattle
    output_template: str = ""

    def __post_init__(self) -> None:
        self.path = self.path.resolve()
        self.root = self.root.resolve()


@dataclass
class RawConfig:
    path: Path
    data: dict[str, object]

    def __post_init__(self) -> None:
        self.path = self.path.resolve()


__all__ = ["Config", "LSPOptions", "Options", "RawConfig"]
