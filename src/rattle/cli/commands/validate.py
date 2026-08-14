from __future__ import annotations

from pathlib import Path

from rattle.cli.options import require_existing_file
from rattle.config import (
    validate_config,
)
from rattle.rendering.console import echo


def validate_command(config: Path | None = None) -> None:
    """Validate Rattle configuration.

    Args:
        config: Config file to validate. Defaults to pyproject.toml.
    """
    config_path = config or Path("pyproject.toml")
    exceptions = validate_config(require_existing_file(config_path, option="path"))

    if exceptions:
        for e in exceptions:
            echo(e, err=True)
        raise SystemExit(1)


__all__ = ["validate_command"]
