# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import time
from pathlib import Path

from rattle.ftypes import LSPOptions, Options, QualifiedRule
from rattle.lsp import LSP


def test_lsp_config_cache_invalidation(tmp_path: Path) -> None:
    config_path = tmp_path / "pyproject.toml"
    target_path = tmp_path / "sample.py"
    target_path.write_text("x = 1\n")

    config_path.write_text(
        """
[tool.rattle]
root = true
disable = ["rattle.rules"]
"""
    )

    lsp = LSP(Options(), LSPOptions(tcp=None, ws=None, stdio=False, debounce_interval=0))

    first = lsp.load_config(target_path)
    assert QualifiedRule("rattle.rules") in first.disable

    time.sleep(0.01)
    config_path.write_text(
        """
[tool.rattle]
root = true
"""
    )

    second = lsp.load_config(target_path)
    assert first is not second
    assert second.disable == []


def test_lsp_load_config_marks_excluded_files(tmp_path: Path) -> None:
    config_path = tmp_path / "pyproject.toml"
    target_path = tmp_path / "ignored.py"
    target_path.write_text("x = 1\n")

    config_path.write_text(
        """
[tool.rattle]
root = true
inherit-ruff-files = true
[tool.ruff]
exclude = ["ignored.py"]
"""
    )

    lsp = LSP(Options(), LSPOptions(tcp=None, ws=None, stdio=False, debounce_interval=0))

    resolved = lsp.load_config(target_path)
    assert resolved.excluded is True
