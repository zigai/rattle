from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, time
from typing import TypeVar

from msgspec import Struct, ValidationError, convert, field, to_builtins

ModelT = TypeVar("ModelT", bound=Struct)


class ConfigModelError(ValueError):
    """Raised when structured configuration does not match its boundary model."""


class OverrideConfigModel(Struct, kw_only=True, omit_defaults=True):
    path: str
    enable: list[str] = field(default_factory=list)
    disable: list[str] = field(default_factory=list)
    options: dict[str, object] | list[dict[str, object]] = field(default_factory=dict)
    python_version: str | None = field(default=None, name="python-version")
    formatter: str | None = None


class RattleConfigModel(Struct, kw_only=True, omit_defaults=True):
    root: bool = False
    enable_root_import: bool | str = field(default=False, name="enable-root-import")
    enable: list[str] = field(default_factory=list)
    disable: list[str] = field(default_factory=list)
    options: dict[str, object] | list[dict[str, object]] = field(default_factory=dict)
    python_version: str | None = field(default=None, name="python-version")
    formatter: str | None = None
    output_format: str | None = field(default=None, name="output-format")
    output_template: str | None = field(default=None, name="output-template")
    exclude: list[str] = field(default_factory=list)
    inherit_ruff_files: bool = field(default=False, name="inherit-ruff-files")
    per_file_enable: dict[str, list[str]] = field(
        default_factory=dict,
        name="per-file-enable",
    )
    per_file_disable: dict[str, list[str]] = field(
        default_factory=dict,
        name="per-file-disable",
    )
    overrides: list[OverrideConfigModel] = field(default_factory=list)


class RuffConfigModel(Struct, kw_only=True, omit_defaults=True):
    include: list[str] = field(default_factory=list)
    extend_include: list[str] = field(default_factory=list, name="extend-include")
    exclude: list[str] = field(default_factory=list)
    extend_exclude: list[str] = field(default_factory=list, name="extend-exclude")
    force_exclude: bool = field(default=False, name="force-exclude")


RATTLE_CONFIG_KEYS = frozenset(
    {
        "root",
        "enable-root-import",
        "enable",
        "disable",
        "options",
        "python-version",
        "formatter",
        "output-format",
        "output-template",
        "exclude",
        "inherit-ruff-files",
        "per-file-enable",
        "per-file-disable",
        "overrides",
    }
)
OVERRIDE_CONFIG_KEYS = frozenset(
    {"path", "enable", "disable", "options", "python-version", "formatter"}
)


def _convert_config(value: object, model_type: type[ModelT]) -> ModelT:
    try:
        return convert(value, type=model_type, strict=True)
    except ValidationError as e:
        raise ConfigModelError(str(e)) from None


def parse_rattle_config(value: object) -> dict[str, object]:
    model = _convert_config(value, RattleConfigModel)
    parsed = to_builtins(
        model,
        builtin_types=(date, datetime, time),
    )
    assert isinstance(parsed, dict)

    if isinstance(value, Mapping):
        for key, unknown_value in value.items():
            if isinstance(key, str) and key not in RATTLE_CONFIG_KEYS:
                parsed[key] = unknown_value

        raw_overrides = value.get("overrides", ())
        parsed_overrides = parsed.get("overrides", [])
        if isinstance(raw_overrides, list) and isinstance(parsed_overrides, list):
            for raw_override, parsed_override in zip(
                raw_overrides,
                parsed_overrides,
                strict=True,
            ):
                if not isinstance(raw_override, Mapping) or not isinstance(parsed_override, dict):
                    continue
                for key, unknown_value in raw_override.items():
                    if isinstance(key, str) and key not in OVERRIDE_CONFIG_KEYS:
                        parsed_override[key] = unknown_value

    return parsed


def parse_ruff_config(value: object) -> RuffConfigModel:
    model = _convert_config(value, RuffConfigModel)
    return model


__all__ = [
    "ConfigModelError",
    "RattleConfigModel",
    "RuffConfigModel",
    "parse_rattle_config",
    "parse_ruff_config",
]
