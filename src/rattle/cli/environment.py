from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path

from rattle.__version__ import __version__
from rattle.pyproject import TOMLDecodeError, load_pyproject

UV_REEXEC_ENV = "RATTLE_UV_RUN_REEXEC"
UV_REEXEC_DISABLE_ENV = "RATTLE_NO_UV_RUN_REEXEC"
DEBUG_ENV = "RATTLE_DEBUG"
METRICS_ENV = "RATTLE_METRICS"
UV_PROJECT_MARKERS = ("uv.lock",)
UV_REEXEC_COMMANDS = frozenset({"lint", "fix", "rules", "validate", "lsp", "explain"})
TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "on"})


def _version() -> str:
    return f"rattle {__version__}"


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").lower() in TRUTHY_ENV_VALUES


def _configure_logging() -> None:
    level = logging.DEBUG if _env_flag(DEBUG_ENV) else logging.WARNING
    logging.basicConfig(level=level, stream=sys.stderr)


def _find_uv_project_root(path: Path) -> Path | None:
    for directory in (path, *path.parents):
        if any((directory / marker).is_file() for marker in UV_PROJECT_MARKERS):
            return directory

        pyproject = directory / "pyproject.toml"
        if not pyproject.is_file():
            continue

        try:
            data = load_pyproject(pyproject)
        except (OSError, UnicodeDecodeError, TOMLDecodeError):
            continue

        tool = data.get("tool", {})
        if isinstance(tool, dict) and "uv" in tool:
            return directory

        dependency_groups = data.get("dependency-groups", {})
        if isinstance(dependency_groups, dict):
            return directory

    return None


def _should_reexec_with_uv(args: list[str]) -> bool:
    if os.environ.get(UV_REEXEC_ENV) or os.environ.get(UV_REEXEC_DISABLE_ENV):
        return False
    if shutil.which("uv") is None:
        return False

    command = next((arg for arg in args if not arg.startswith("-")), None)
    if command not in UV_REEXEC_COMMANDS:
        return False

    return _find_uv_project_root(Path.cwd()) is not None


def _reexec_with_uv(args: list[str]) -> None:
    uv_path = shutil.which("uv")
    if uv_path is None:
        return

    env = os.environ.copy()
    env[UV_REEXEC_ENV] = "1"
    os.execve(uv_path, [uv_path, "run", "rattle", *args], env)  # noqa: S606


__all__ = []
