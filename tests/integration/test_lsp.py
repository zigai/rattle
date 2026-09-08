# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os
import threading
import traceback
from contextlib import suppress
from pathlib import Path

import pytest
from lsprotocol.types import PublishDiagnosticsParams

from rattle.config.models import LSPOptions, Options
from rattle.errors import RattleExecutionError
from rattle.lsp import LSP, Debouncer
from rattle.selectors import QualifiedRule


def test_lsp_config_cache_invalidation(tmp_path: Path) -> None:
    config_path = tmp_path / "pyproject.toml"
    target_path = tmp_path / "sample.py"
    target_path.write_text("x = 1\n")

    config_path.write_text(
        """
[tool.rattle]
root = true
disable = ["modernization"]
"""
    )

    lsp = LSP(Options(), LSPOptions(tcp=None, ws=None, stdio=False, debounce_interval=0))

    first = lsp.load_config(target_path)
    assert QualifiedRule("rattle.rules.modernization") in first.disable

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


def test_lsp_close_cleans_all_uris_before_raising_first_callback_failure() -> None:
    first_uri = "file:///tmp/first.py"
    second_uri = "file:///tmp/second.py"
    pending_uri = "file:///tmp/pending.py"
    first_started = threading.Event()
    second_started = threading.Event()
    pending_called = threading.Event()

    class FailingLSP(LSP):
        def _validate(self, uri: str, version: int) -> None:
            del version
            if uri == first_uri:
                first_started.set()
                raise ValueError("api_token=FIRST-SECRET")
            if uri == second_uri:
                second_started.set()
                raise TypeError("api_token=SECOND-SECRET")
            pending_called.set()

    lsp = FailingLSP(Options(), LSPOptions(tcp=None, ws=None, stdio=False, debounce_interval=0.001))
    timers: list[threading.Timer] = []
    try:
        for uri, started in ((first_uri, first_started), (second_uri, second_started)):
            lsp.validate(uri, 1)
            timer = lsp._validate_uri[uri]._timer
            assert timer is not None
            timers.append(timer)
            assert started.wait(timeout=1)
            timer.join(timeout=1)
            assert not timer.is_alive()

        lsp.lsp_options.debounce_interval = 60
        lsp.validate(pending_uri, 1)
        pending_timer = lsp._validate_uri[pending_uri]._timer
        assert pending_timer is not None
        timers.append(pending_timer)
        assert pending_timer.is_alive()
        debouncers = tuple(lsp._validate_uri.values())

        with pytest.raises(RattleExecutionError) as caught:
            lsp.close()

        assert str(caught.value) == "Debounced callback failed (ValueError)"
        diagnostic = "".join(traceback.format_exception(caught.type, caught.value, caught.tb))
        assert "FIRST-SECRET" not in diagnostic
        assert "SECOND-SECRET" not in diagnostic
        assert not pending_called.is_set()
        assert pending_timer.finished.is_set()
        assert all(not timer.is_alive() for timer in timers)
        assert all(debouncer._timer is None for debouncer in debouncers)
        assert lsp._validate_uri == {}
        lsp.close()
    finally:
        with suppress(RattleExecutionError):
            lsp.close()
        for timer in timers:
            timer.cancel()
            timer.join(timeout=1)
