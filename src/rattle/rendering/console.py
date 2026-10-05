from __future__ import annotations

import os
import queue
import re
import sys
import threading
from dataclasses import dataclass
from typing import Literal, TextIO

Color = Literal["red", "green", "yellow", "cyan", "gray", "light_red", "light_blue", "light_cyan"]

COLOR_CODES: dict[Color, int] = {
    "red": 31,
    "green": 32,
    "yellow": 33,
    "cyan": 36,
    "gray": 90,
    "light_red": 91,
    "light_blue": 94,
    "light_cyan": 96,
}
BOLD_CODE = 1
ANSI_STYLE_RE = re.compile(r"\x1b\[[0-9;]*m")


def colored(text: str, color: Color | None = None, *, bold: bool = False) -> str:
    codes = [
        str(code) for code in (BOLD_CODE if bold else None, color and COLOR_CODES[color]) if code
    ]
    if not codes:
        return text
    return f"\x1b[{';'.join(codes)}m{text}\x1b[0m"


def color_enabled(stream: TextIO) -> bool:
    if os.environ.get("NO_COLOR") or os.environ.get("NOCOLOR") or os.environ.get("TERM") == "dumb":
        return False
    return stream.isatty()


def for_stream(text: str, stream: TextIO) -> str:
    return text if color_enabled(stream) else ANSI_STYLE_RE.sub("", text)


def echo(
    message: str = "",
    *,
    color: Color | None = None,
    bold: bool = False,
    nl: bool = True,
    err: bool = False,
    file: TextIO | None = None,
) -> None:
    stream = file or (sys.stderr if err else sys.stdout)
    stream.write(for_stream(colored(message, color, bold=bold), stream))
    if nl:
        stream.write("\n")
    stream.flush()


def echo_color_precomputed_diff(diff: str, *, err: bool = False) -> None:
    echo(color_precomputed_diff(diff), nl=False, err=err)


def color_precomputed_diff(diff: str) -> str:
    lines: list[str] = []
    for line in diff.splitlines(keepends=True):
        if line.startswith(("---", "+++")):
            lines.append(colored(line, bold=True))
        elif line.startswith("@@"):
            lines.append(colored(line, "cyan"))
        elif line.startswith("-"):
            lines.append(colored(line, "red"))
        elif line.startswith("+"):
            lines.append(colored(line, "green"))
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
                stream.write(for_stream(message.text, stream))
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
    "ANSI_STYLE_RE",
    "AsyncConsole",
    "Color",
    "ConsoleMessage",
    "color_enabled",
    "color_precomputed_diff",
    "colored",
    "echo",
    "echo_color_precomputed_diff",
    "for_stream",
]
