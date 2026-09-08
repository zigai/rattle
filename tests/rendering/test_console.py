from __future__ import annotations

import io
from contextlib import suppress
from threading import Event

import pytest

from rattle.rendering.console import AsyncConsole


class BrokenStream(io.StringIO):
    def __init__(self) -> None:
        super().__init__()
        self.write_started = Event()
        self.fail_write = Event()

    def write(self, value: str) -> int:
        self.write_started.set()
        if not self.fail_write.wait(timeout=5):
            raise OSError("timed out waiting to release stream failure")
        raise OSError("stream is broken")


def test_async_console_writes_messages_in_order() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    console = AsyncConsole(stdout=stdout, stderr=stderr)

    console.submit("one")
    console.submit("two", nl=False)
    console.submit("err", err=True)
    console.close()

    assert stdout.getvalue() == "one\ntwo"
    assert stderr.getvalue() == "err\n"


def test_async_console_flushes_without_closing() -> None:
    stdout = io.StringIO()
    console = AsyncConsole(stdout=stdout, stderr=io.StringIO(), maxsize=1)

    for index in range(5):
        console.submit(str(index), nl=False)
    console.flush()

    assert stdout.getvalue() == "01234"
    console.close()


def test_async_console_close_surfaces_writer_errors() -> None:
    stream = BrokenStream()
    console = AsyncConsole(stdout=stream, stderr=io.StringIO())

    try:
        console.submit("broken")
        assert stream.write_started.wait(timeout=5), "writer did not start"
        stream.fail_write.set()

        with pytest.raises(OSError, match="stream is broken"):
            console.close()
    finally:
        stream.fail_write.set()
        with suppress(OSError):
            console.close()
