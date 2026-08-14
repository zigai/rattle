from __future__ import annotations

import contextlib
import io
import sys
from dataclasses import dataclass
from types import TracebackType
from typing import Protocol, TextIO


class Cli(Protocol):
    def __call__(self, args: list[str], *, sys_exit_enabled: bool) -> object: ...


@dataclass(frozen=True)
class CliResult:
    exit_code: int
    stdout: str
    stderr: str
    exception: Exception | SystemExit | None = None

    @property
    def output(self) -> str:
        return self.stdout + self.stderr


class InputStream(io.StringIO):
    def __init__(self, value: str) -> None:
        super().__init__(value)
        self._buffer = io.BytesIO(value.encode())

    @property
    def buffer(self) -> io.BytesIO:
        return self._buffer


class OutputBuffer:
    def __init__(self, stream: OutputStream) -> None:
        self._stream = stream

    def write(self, value: bytes) -> int:
        text = value.decode()
        self._stream.write(text)
        return len(value)

    def flush(self) -> None:
        self._stream.flush()


class OutputStream:
    def __init__(self) -> None:
        self._stream = io.StringIO()
        self._buffer = OutputBuffer(self)

    @property
    def buffer(self) -> OutputBuffer:
        return self._buffer

    def write(self, value: str) -> int:
        return self._stream.write(value)

    def flush(self) -> None:
        self._stream.flush()

    def getvalue(self) -> str:
        return self._stream.getvalue()


class Stdin(contextlib.AbstractContextManager[None]):
    def __init__(self, value: str | None) -> None:
        self._value = value
        self._previous: TextIO = sys.stdin

    def __enter__(self) -> None:
        self._previous = sys.stdin
        sys.stdin = InputStream(self._value or "")

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        sys.stdin = self._previous


class CliRunner:
    def invoke(
        self,
        cli: Cli,
        args: list[str] | tuple[str, ...] | None = None,
        input: str | None = None,
        *,
        catch_exceptions: bool = True,
    ) -> CliResult:
        stdout = OutputStream()
        stderr = OutputStream()
        exit_code = 0
        exception: Exception | SystemExit | None = None
        with (
            Stdin(input),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            try:
                result = cli(list(args or ()), sys_exit_enabled=False)
                if isinstance(result, int):
                    exit_code = result
                elif isinstance(result, SystemExit):
                    exception = result
                    if isinstance(result.code, int):
                        exit_code = result.code
                    elif result.code is None:
                        exit_code = 0
                    else:
                        exit_code = 1
            except SystemExit as e:
                exception = e
                if isinstance(e.code, int):
                    exit_code = e.code
                elif e.code is None:
                    exit_code = 0
                else:
                    exit_code = 1
            except Exception as e:
                exception = e
                exit_code = 1
                if not catch_exceptions:
                    raise

        return CliResult(
            exit_code=exit_code,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
            exception=exception,
        )
