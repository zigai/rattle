# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""
Post-transform file formatters.

NOTE: be sure to update docs/guide/configuration.rst to include any new formatters.
"""

import shutil
import subprocess
import sys
from collections.abc import Collection, Mapping
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, cast

from libcst import Module

from .ftypes import Config, FileContent

if TYPE_CHECKING:
    import black
    import ufmt

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

FORMAT_STYLES: dict[str | None, type["Formatter"]] = {}


def _resolve_required_executable(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise RuntimeError(f"{name} formatter is not installed")
    return executable


def _run_ruff_format(args: list[str], *, input_bytes: bytes | None = None) -> bytes:
    proc = subprocess.run(  # noqa: S603 - fixed executable and args
        [_resolve_required_executable("ruff"), "format", *args],
        input=input_bytes,
        capture_output=True,
        check=False,
    )

    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        message = stderr or "ruff format failed"
        raise RuntimeError(message)

    return proc.stdout


class Formatter:
    """Rattle post-transform code style and formatting interface."""

    STYLE: str
    """
    Short name to identify this formatting style in user configuration.
    For example: ``"black"``.
    """

    def __init_subclass__(cls) -> None:
        FORMAT_STYLES[cls.STYLE] = cls

    def format(self, module: Module, _path: Path) -> FileContent:
        """Format the given :class:`~libcst.Module` and return it as UTF-8 encoded bytes."""
        return module.bytes


class BlackFormatter(Formatter):
    STYLE = "black"

    def format(self, module: Module, path: Path) -> FileContent:
        import black

        mode = cast("black.Mode", _black_config(path.resolve()))
        content = black.format_file_contents(module.bytes.decode("utf-8"), fast=False, mode=mode)
        return content.encode("utf-8")


class UfmtFormatter(Formatter):
    STYLE = "ufmt"

    def format(self, module: Module, path: Path) -> FileContent:
        import ufmt

        resolved_path = path.resolve()
        black_config = cast("black.Mode", _black_config(resolved_path))
        usort_config = cast("ufmt.UsortConfig", _usort_config(resolved_path))

        return ufmt.ufmt_bytes(
            path, module.bytes, black_config=black_config, usort_config=usort_config
        )


class RuffFormatter(Formatter):
    STYLE = "ruff"

    def format(self, module: Module, path: Path) -> FileContent:
        return _run_ruff_format(
            [
                "--stdin-filename",
                path.as_posix(),
                "-",
            ],
            input_bytes=module.bytes,
        )


class AutoFormatter(Formatter):
    STYLE = "auto"

    def format(self, module: Module, path: Path) -> FileContent:
        style = _detect_formatter_style(path)
        if style is None:
            return module.bytes

        formatter = FORMAT_STYLES[style]()
        return formatter.format(module, path)


def _detect_formatter_style(path: Path) -> str | None:
    for pyproject_path in _iter_pyproject_paths(path):
        try:
            data = tomllib.loads(pyproject_path.read_text())
        except tomllib.TOMLDecodeError:
            data = {}

        tool_data = data.get("tool", {})
        if not isinstance(tool_data, Mapping):
            continue

        ruff_data = tool_data.get("ruff", {})
        if isinstance(ruff_data, Mapping) and isinstance(ruff_data.get("format"), Mapping):
            return "ruff"

        if isinstance(tool_data.get("ufmt"), Mapping) or isinstance(
            tool_data.get("usort"), Mapping
        ):
            return "ufmt"

        if isinstance(tool_data.get("black"), Mapping):
            return "black"

    return None


def _iter_pyproject_paths(path: Path) -> list[Path]:
    base = path if path.is_dir() else path.parent
    base = base.resolve()
    paths: list[Path] = []
    while True:
        pyproject_path = base / "pyproject.toml"
        if pyproject_path.is_file():
            paths.append(pyproject_path)
        if base == base.parent:
            return paths
        base = base.parent


def format_module(module: Module, path: Path, config: Config) -> FileContent:
    """
    Format the given source module, and return its final content in bytes.

    Uses the ``config`` object to instantiate the correct :class:`Formatter` style.
    """
    formatter = FORMAT_STYLES[config.formatter]()
    return formatter.format(module, path)


def format_paths(paths: Collection[Path], config: Config) -> None:
    if not paths or config.formatter is None:
        return

    if config.formatter != "ruff":
        raise NotImplementedError(f"batch formatting is not supported for {config.formatter!r}")

    _run_ruff_format([path.as_posix() for path in sorted(set(paths))])


FORMAT_STYLES[None] = Formatter
FORMAT_STYLES["none"] = Formatter


@cache
def _black_config(path: Path) -> object:
    import ufmt.util

    return ufmt.util.make_black_config(path)


@cache
def _usort_config(path: Path) -> object:
    import ufmt

    return ufmt.UsortConfig.find(path)


__all__ = (
    "FORMAT_STYLES",
    "AutoFormatter",
    "BlackFormatter",
    "Formatter",
    "RuffFormatter",
    "UfmtFormatter",
    "format_module",
)
