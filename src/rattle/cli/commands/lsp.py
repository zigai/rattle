from __future__ import annotations

from pathlib import Path

from rattle.cli.options import build_options, usage_error
from rattle.config.models import LSPOptions


def lsp(
    *,
    config: Path | None = None,
    ws: int | None = None,
    tcp: int | None = None,
    debounce_interval: float = LSPOptions.debounce_interval,
    no_stdio: bool = False,
) -> None:
    """Start the language server.

    https://microsoft.github.io/language-server-protocol/.

    Args:
        config: Use this config file instead of discovered configuration.
        no_stdio: Disable stdio transport when using TCP or WebSocket.
        tcp: Port to serve LSP over TCP.
        ws: Port to serve LSP over WebSocket.
        debounce_interval: Delay diagnostics after document changes, in seconds.
    """
    if tcp is not None and ws is not None:
        usage_error("--tcp and --ws cannot be used together")
    if no_stdio and tcp is None and ws is None:
        usage_error("--no-stdio requires --tcp or --ws")
    if debounce_interval < 0:
        usage_error("--debounce-interval must be greater than or equal to 0")

    from rattle.lsp import LSP

    lsp_options = LSPOptions(
        tcp=tcp,
        ws=ws,
        stdio=not no_stdio,
        debounce_interval=debounce_interval,
    )
    LSP(
        build_options(
            config=config,
        ),
        lsp_options,
    ).start()


__all__ = ["lsp"]
