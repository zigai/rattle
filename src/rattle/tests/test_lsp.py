# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os
import threading
from pathlib import Path

import pytest
from lsprotocol.types import PublishDiagnosticsParams

from rattle.errors import RattleExecutionError
from rattle.ftypes import LSPOptions, Options, QualifiedRule
from rattle.lsp import LSP, Debouncer


def test_lsp_config_cache_invalidation(tmp_path: Path) -> None:
    config_path = tmp_path / "pyproject.toml"
    target_path = tmp_path / "sample.py"
    target_path.write_text("x = 1\n")

    config_path.write_text(
        """
[tool.rattle]
root = true
disable = ["fixit"]
"""
    )

    lsp = LSP(Options(), LSPOptions(tcp=None, ws=None, stdio=False, debounce_interval=0))

    first = lsp.load_config(target_path)
    assert QualifiedRule("rattle.rules.fixit") in first.disable

    first_stat = config_path.stat()
    config_path.write_text(
        """
[tool.rattle]
root = true
"""
    )
    os.utime(
        config_path,
        ns=(first_stat.st_atime_ns, first_stat.st_mtime_ns + 1_000_000_000),
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


def test_lsp_validate_clears_diagnostics_when_file_is_excluded() -> None:
    class ExcludedLSP(LSP):
        def diagnostic_generator(self, uri: str, *, autofix: bool = False) -> None:
            del autofix, uri
            return None

    lsp = ExcludedLSP(
        Options(),
        LSPOptions(tcp=None, ws=None, stdio=False, debounce_interval=0),
    )
    published: list[PublishDiagnosticsParams] = []

    def publish(params: PublishDiagnosticsParams) -> None:
        published.append(params)

    lsp.lsp.text_document_publish_diagnostics = publish

    lsp.validate("file:///tmp/example.py", 7)
    lsp.close()

    assert len(published) == 1
    assert published[0].diagnostics == []
    assert published[0].version == 7


def test_debouncer_surfaces_sanitized_background_failures() -> None:
    callback_started = threading.Event()

    def fail() -> None:
        callback_started.set()
        raise ValueError("api_token=TOP-SECRET")

    debouncer = Debouncer(fail, interval=0.001)
    debouncer()
    assert callback_started.wait(timeout=1)

    with pytest.raises(RattleExecutionError, match=r"Debounced callback failed \(ValueError\)"):
        debouncer.close()
