from __future__ import annotations

import logging
import os
import sys

from rattle.__version__ import __version__

DEBUG_ENV = "RATTLE_DEBUG"
METRICS_ENV = "RATTLE_METRICS"
TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "on"})


def _version() -> str:
    return f"rattle {__version__}"


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").lower() in TRUTHY_ENV_VALUES


def _configure_logging() -> None:
    level = logging.DEBUG if _env_flag(DEBUG_ENV) else logging.WARNING
    logging.basicConfig(level=level, stream=sys.stderr, format="%(levelname)s: %(message)s")
