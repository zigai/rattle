# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import json
import os
import subprocess
import sys
import threading
import time
import traceback
from contextlib import suppress
from pathlib import Path
from textwrap import dedent

import pytest
from lsprotocol.types import (
    DocumentFormattingParams,
    FormattingOptions,
    PublishDiagnosticsParams,
    TextDocumentContentChangePartial,
    TextDocumentIdentifier,
    TextDocumentItem,
)
from pygls.workspace import Workspace

from rattle.config.models import LSPOptions, Options
from rattle.errors import RattleExecutionError
from rattle.lsp import LSP, Debouncer
from rattle.selectors import QualifiedRule, RuleNameSelector


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


def test_lsp_reschedules_validation_while_previous_callback_completes(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[tool.rattle]\nroot=true\nenable=["use-literal"]\n')
    script = dedent(
        """
        import json
        import sys
        import threading
        from pathlib import Path
        from lsprotocol.types import (
            DidChangeTextDocumentParams, DidOpenTextDocumentParams,
            TextDocumentItem, VersionedTextDocumentIdentifier,
        )
        from pygls.workspace import Workspace
        from rattle.config.models import LSPOptions, Options
        from rattle.lsp import LSP

        started = threading.Event()
        release = threading.Event()
        latest = threading.Event()
        messages = []

        class ControlledLSP(LSP):
            def diagnostic_generator(self, uri, *, autofix=False):
                generator = super().diagnostic_generator(uri, autofix=autofix)
                if not started.is_set():
                    started.set()
                    assert release.wait(2)
                return generator

        root = Path(sys.argv[1])
        uri = (root / 'sample.py').as_uri()
        lsp = ControlledLSP(
            Options(), LSPOptions(tcp=None, ws=None, stdio=False, debounce_interval=0.001)
        )
        lsp.lsp.protocol._workspace = Workspace(root.as_uri())
        def publish(params):
            messages.append([params.version, [item.code for item in params.diagnostics]])
            if params.version == 2:
                latest.set()
        lsp.lsp.text_document_publish_diagnostics = publish

        original_join = threading.Timer.join
        def release_on_join(timer, *args, **kwargs):
            release.set()
            return original_join(timer, *args, **kwargs)
        threading.Timer.join = release_on_join
        try:
            item = TextDocumentItem(uri=uri, language_id='python', version=1, text='value = 0\\n')
            lsp.lsp.workspace.put_text_document(item)
            lsp.on_did_open(DidOpenTextDocumentParams(text_document=item))
            assert started.wait(2)
            lsp.lsp.workspace.put_text_document(TextDocumentItem(
                uri=uri, language_id='python', version=2, text='value = list([0])\\n'
            ))
            lsp.on_did_change(DidChangeTextDocumentParams(
                text_document=VersionedTextDocumentIdentifier(uri=uri, version=2),
                content_changes=[],
            ))
            release.set()
            assert latest.wait(2)
            lsp.close()
            print(json.dumps(messages[-1]))
        finally:
            release.set()
            threading.Timer.join = original_join
            lsp.close()
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script, tmp_path.as_posix()],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [2, ["use-literal"]]


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


def test_debouncer_clears_error_on_subsequent_call() -> None:
    runs: list[bool] = []

    def task(fail: bool = False) -> None:
        if fail:
            raise ValueError("boom")
        runs.append(True)

    d = Debouncer(task, interval=0.01)
    d(fail=True)
    time.sleep(0.05)

    d(fail=False)
    time.sleep(0.05)
    assert runs == [True]


def test_lsp_publishes_syntax_error_diagnostics() -> None:
    lsp = LSP(
        Options(rules=[RuleNameSelector("no-annotated-self")]),
        LSPOptions(tcp=None, ws=None, stdio=False, debounce_interval=0),
    )
    lsp.lsp.protocol._workspace = Workspace("/tmp")
    item = TextDocumentItem(
        uri="file:///tmp/syntax_err.py", language_id="python", version=1, text="def foo("
    )
    lsp.lsp.workspace.put_text_document(item)

    published: list[PublishDiagnosticsParams] = []

    def publish(params: PublishDiagnosticsParams) -> None:
        published.append(params)

    lsp.lsp.text_document_publish_diagnostics = publish
    lsp.validate("file:///tmp/syntax_err.py", 1)

    assert len(published) == 1
    assert len(published[0].diagnostics) == 1
    diag = published[0].diagnostics[0]
    assert diag.code == "syntax-error"
    assert diag.range.start.line == 0


def test_lsp_format_empty_document() -> None:
    lsp = LSP(
        Options(),
        LSPOptions(tcp=None, ws=None, stdio=False, debounce_interval=0),
    )
    lsp.lsp.protocol._workspace = Workspace("/tmp")
    item = TextDocumentItem(uri="file:///tmp/empty.py", language_id="python", version=1, text="")
    lsp.lsp.workspace.put_text_document(item)

    params = DocumentFormattingParams(
        text_document=TextDocumentIdentifier(uri="file:///tmp/empty.py"),
        options=FormattingOptions(tab_size=4, insert_spaces=True),
    )
    edits = lsp.format(params)
    assert edits is None


@pytest.mark.parametrize(
    "last_line",
    [
        pytest.param("tail = 'a'", id="ascii-no-newline"),
        pytest.param("tail = '\U00010000'", id="astral-no-newline"),
        pytest.param("tail = ''\r\n", id="crlf"),
        pytest.param("tail = ''\n", id="lf"),
    ],
)
def test_lsp_format_replaces_entire_utf16_document(tmp_path: Path, last_line: str) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.rattle]\nroot=true\nformatter="none"\nenable=["use-literal"]\n'
    )
    uri = (tmp_path / "sample.py").as_uri()
    lsp = LSP(Options(), LSPOptions(tcp=None, ws=None, stdio=False, debounce_interval=0))
    lsp.lsp.protocol._workspace = Workspace(tmp_path.as_uri())
    lsp.lsp.workspace.put_text_document(
        TextDocumentItem(
            uri=uri, language_id="python", version=1, text="value = list([0])\n" + last_line
        )
    )
    params = DocumentFormattingParams(
        text_document=TextDocumentIdentifier(uri=uri),
        options=FormattingOptions(tab_size=4, insert_spaces=True),
    )

    try:
        edits = lsp.format(params)
        assert edits is not None
        document = lsp.lsp.workspace.get_text_document(uri)
        for edit in sorted(
            edits,
            key=lambda edit: (edit.range.start.line, edit.range.start.character),
            reverse=True,
        ):
            document.apply_change(
                TextDocumentContentChangePartial(range=edit.range, text=edit.new_text)
            )
        assert document.source == "value = [0]\n" + last_line
    finally:
        lsp.close()


def test_lsp_format_applies_empty_module_replacement(empty_module_project: Path) -> None:
    uri = (empty_module_project / "sample.py").as_uri()
    lsp = LSP(Options(), LSPOptions(tcp=None, ws=None, stdio=False, debounce_interval=0))
    lsp.lsp.protocol._workspace = Workspace(empty_module_project.as_uri())
    lsp.lsp.workspace.put_text_document(
        TextDocumentItem(uri=uri, language_id="python", version=1, text="pass\n")
    )
    params = DocumentFormattingParams(
        text_document=TextDocumentIdentifier(uri=uri),
        options=FormattingOptions(tab_size=4, insert_spaces=True),
    )

    try:
        edits = lsp.format(params)
        assert edits is not None
        document = lsp.lsp.workspace.get_text_document(uri)
        for edit in sorted(
            edits,
            key=lambda edit: (edit.range.start.line, edit.range.start.character),
            reverse=True,
        ):
            document.apply_change(
                TextDocumentContentChangePartial(range=edit.range, text=edit.new_text)
            )
        assert document.source == ""
    finally:
        lsp.close()


def test_lsp_config_detects_metadata_preserving_edit(tmp_path: Path) -> None:
    config_path = tmp_path / "pyproject.toml"
    config_path.write_text(
        '[tool.rattle]\nroot=true\nenable=["forbidden-call"]\n'
        '[tool.rattle.options."forbidden-call"]\nforbidden_calls=["os.getenv"]\n'
    )
    uri = (tmp_path / "sample.py").as_uri()
    lsp = LSP(Options(), LSPOptions(tcp=None, ws=None, stdio=False, debounce_interval=0))
    lsp.lsp.protocol._workspace = Workspace(tmp_path.as_uri())
    lsp.lsp.workspace.put_text_document(
        TextDocumentItem(
            uri=uri, language_id="python", version=1, text="import os\nos.system('x')\n"
        )
    )
    published: list[PublishDiagnosticsParams] = []
    lsp.lsp.text_document_publish_diagnostics = published.append

    try:
        lsp.validate(uri, 1)
        original_stat = config_path.stat()
        config_path.write_text(config_path.read_text().replace("os.getenv", "os.system"))
        os.utime(config_path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
        lsp.validate(uri, 2)
        assert config_path.stat().st_size == original_stat.st_size
        assert config_path.stat().st_mtime_ns == original_stat.st_mtime_ns
        assert [
            [diagnostic.code for diagnostic in message.diagnostics] for message in published
        ] == [
            [],
            ["forbidden-call"],
        ]
    finally:
        lsp.close()
