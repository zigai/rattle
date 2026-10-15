from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from rattle.__version__ import __version__
from rattle.pyproject import TOMLDecodeError, load_pyproject

UV_REEXEC_ENV = "RATTLE_UV_RUN_REEXEC"
UV_REEXEC_DISABLE_ENV = "RATTLE_NO_UV_RUN_REEXEC"
DEBUG_ENV = "RATTLE_DEBUG"
METRICS_ENV = "RATTLE_METRICS"
UV_PROJECT_MARKERS = ("uv.lock",)
UV_REEXEC_COMMANDS = frozenset({"check", "rules", "validate", "lsp", "explain"})
TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "on"})


def _version() -> str:
    return f"rattle {__version__}"


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").lower() in TRUTHY_ENV_VALUES


def _configure_logging() -> None:
    level = logging.DEBUG if _env_flag(DEBUG_ENV) else logging.WARNING
    logging.basicConfig(level=level, stream=sys.stderr, format="%(levelname)s: %(message)s")


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

        dependency_groups = data.get("dependency-groups")
        if isinstance(dependency_groups, dict):
            return directory

    return None


def _project_environment(root: Path) -> Path:
    configured = os.environ.get("UV_PROJECT_ENVIRONMENT")
    if not configured:
        return root / ".venv"

    environment = Path(configured)
    return environment if environment.is_absolute() else root / environment


def _project_rattle(root: Path) -> Path | None:
    environment = _project_environment(root)
    if environment.resolve() == Path(sys.prefix).resolve():
        return None

    executable = environment / ("Scripts/rattle.exe" if os.name == "nt" else "bin/rattle")
    return executable if executable.is_file() else None


def _project_rattle_for_reexec(args: list[str]) -> Path | None:
    if os.environ.get(UV_REEXEC_ENV) or os.environ.get(UV_REEXEC_DISABLE_ENV):
        return None

    command = next((arg for arg in args if not arg.startswith("-")), None)
    if command not in UV_REEXEC_COMMANDS:
        return None

    root = _find_uv_project_root(Path.cwd())
    if root is None:
        return None

    return _project_rattle(root)


def _reexec_project_rattle(executable: Path, args: list[str]) -> None:
    env = os.environ.copy()
    env[UV_REEXEC_ENV] = "1"
    os.execve(executable, [str(executable), *args], env)  # noqa: S606
