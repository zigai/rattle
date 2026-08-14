from __future__ import annotations

from rattle.config.models import RawConfig


class ConfigError(ValueError):
    def __init__(self, msg: str, config: RawConfig | None = None) -> None:
        super().__init__(msg)
        self.config = config


__all__ = ["ConfigError"]
