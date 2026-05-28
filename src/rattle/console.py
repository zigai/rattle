from __future__ import annotations

import sys
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
    for line in diff.splitlines(keepends=True):
        if line.startswith(("---", "+++")):
            echo(line, bold=True, nl=False, err=err)
        elif line.startswith("@@"):
            echo(line, color="cyan", nl=False, err=err)
        elif line.startswith("-"):
            echo(line, color="red", nl=False, err=err)
        elif line.startswith("+"):
            echo(line, color="green", nl=False, err=err)
        else:
            echo(line, nl=False, err=err)


__all__ = (
    "echo",
    "echo_color_precomputed_diff",
    "getchar",
)
