from __future__ import annotations

import io

import pytest

from rattle.console import AsyncConsole


class BrokenStream(io.StringIO):
    def write(self, value: str) -> int:
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
    console = AsyncConsole(stdout=BrokenStream(), stderr=io.StringIO())

    console.submit("broken")

    with pytest.raises(OSError, match="stream is broken"):
        console.close()
