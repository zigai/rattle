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
from pathlib import Path

from libcst import Module

from .ftypes import Config, FileContent

FORMAT_STYLES: dict[str | None, type["Formatter"]] = {}


def _resolve_required_executable(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise RuntimeError(f"{name} formatter is not installed")
    return executable


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
        import ufmt.util

        mode = ufmt.util.make_black_config(path)
        content = black.format_file_contents(module.bytes.decode("utf-8"), fast=False, mode=mode)
        return content.encode("utf-8")


class UfmtFormatter(Formatter):
    STYLE = "ufmt"

    def format(self, module: Module, path: Path) -> FileContent:
        import ufmt
        import ufmt.util

        black_config = ufmt.util.make_black_config(path)
        usort_config = ufmt.UsortConfig.find(path)

        return ufmt.ufmt_bytes(
            path, module.bytes, black_config=black_config, usort_config=usort_config
        )


class RuffFormatter(Formatter):
    STYLE = "ruff"

    def format(self, module: Module, path: Path) -> FileContent:
        proc = subprocess.run(  # noqa: S603 - fixed executable and args
            [
                _resolve_required_executable("ruff"),
                "format",
                "--stdin-filename",
                path.as_posix(),
                "-",
            ],
            input=module.bytes,
            capture_output=True,
            check=False,
        )

        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace").strip()
            message = stderr or "ruff format failed"
            raise RuntimeError(message)

        return proc.stdout


def format_module(module: Module, path: Path, config: Config) -> FileContent:
    """
    Format the given source module, and return its final content in bytes.

    Uses the ``config`` object to instantiate the correct :class:`Formatter` style.
    """
    formatter = FORMAT_STYLES[config.formatter]()
    return formatter.format(module, path)


FORMAT_STYLES[None] = Formatter
