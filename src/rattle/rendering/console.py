from __future__ import annotations

import queue
import sys
import threading
from dataclasses import dataclass
from typing import TextIO

from stdl import st


def echo(
    message: str = "",
    *,
    color: str | None = None,
    bold: bool = False,
    nl: bool = True,
    err: bool = False,
    file: TextIO | None = None,
) -> None:
    stream = file or (sys.stderr if err else sys.stdout)
    stream.write(st.colored(message, color=color, style="bold" if bold else None))
    if nl:
        stream.write("\n")
    stream.flush()


def getchar(*, echo_input: bool = False, err: bool = False) -> str:
    char = sys.stdin.read(1)
    if echo_input and char:
        echo(char, nl=False, err=err)
    return char


def echo_color_precomputed_diff(diff: str, *, err: bool = False) -> None:
    echo(color_precomputed_diff(diff), nl=False, err=err)


def color_precomputed_diff(diff: str) -> str:
    lines: list[str] = []
    for line in diff.splitlines(keepends=True):
        if line.startswith(("---", "+++")):
            lines.append(st.colored(line, style="bold"))
        elif line.startswith("@@"):
            lines.append(st.colored(line, color="cyan"))
        elif line.startswith("-"):
            lines.append(st.colored(line, color="red"))
        elif line.startswith("+"):
            lines.append(st.colored(line, color="green"))
        else:
            lines.append(line)
    return "".join(lines)


@dataclass(frozen=True)
class ConsoleMessage:
    text: str
    err: bool
    nl: bool


class AsyncConsole:
    def __init__(
        self,
        *,
        stdout: TextIO | None = None,
        stderr: TextIO | None = None,
        maxsize: int = 512,
    ) -> None:
        self._stdout = stdout or sys.stdout
        self._stderr = stderr or sys.stderr
        self._queue: queue.Queue[ConsoleMessage | None] = queue.Queue(maxsize=maxsize)
        self._error: Exception | None = None
        self._closed = False
        self._thread: threading.Thread | None = None

    def submit(self, message: str = "", *, err: bool = False, nl: bool = True) -> None:
        if self._closed:
            raise RuntimeError("console is closed")
        self._raise_if_failed()
        self._start()
        self._queue.put(ConsoleMessage(message, err, nl))
        self._raise_if_failed()

    def flush(self) -> None:
        if self._thread is None:
            return
        self._queue.join()
        self._raise_if_failed()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._thread is None:
            return
        self._queue.put(None)
        self._thread.join()
        self._raise_if_failed()

    def _start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._write_messages, name="rattle-console")
        self._thread.start()

    def _write_messages(self) -> None:
        while True:
            message = self._queue.get()
            try:
                if message is None:
                    return
                stream = self._stderr if message.err else self._stdout
                stream.write(message.text)
                if message.nl:
                    stream.write("\n")
                stream.flush()
            except (OSError, UnicodeError) as e:
                self._error = e
            finally:
                self._queue.task_done()

    def _raise_if_failed(self) -> None:
        if self._error is not None:
            raise self._error


__all__ = [
    "AsyncConsole",
    "ConsoleMessage",
    "color_precomputed_diff",
    "echo",
    "echo_color_precomputed_diff",
    "getchar",
]
