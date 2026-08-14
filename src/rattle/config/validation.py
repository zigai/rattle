from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from rattle.config.discovery import read_configs
from rattle.config.errors import ConfigError
from rattle.config.matching import (
    _get_string_sequence_from_mapping,
    _read_ruff_file_selection,
    get_options,
    get_rule_pattern_table,
)
from rattle.config.merge import parse_exact_rule_target, parse_rule
from rattle.config.models import RawConfig
from rattle.pyproject import TOMLDecodeError
from rattle.rule import RuleConfigurationError
from rattle.rule_loading import CollectionError, RuleRegistry, _build_rule_registry
from rattle.selectors import RuleOptionsTable, RuleSelector


@dataclass
class ConfigValidator:
    path: Path
    exceptions: list[str] = field(default_factory=list)
    selectors_to_validate: list[tuple[str, RuleSelector, str]] = field(default_factory=list)
    option_targets_to_validate: list[tuple[str, RuleSelector, Mapping[str, object], str]] = field(
        default_factory=list
    )
    root: Path = field(init=False)
    config: RawConfig = field(init=False)
    data: dict[str, object] = field(init=False)
    enable_root_import: bool | Path = field(init=False)

    def validate(self) -> list[str]:
        try:
            self.root = self.path.parent
            configs = read_configs([self.path])
            if not configs:
                return self.exceptions
            self.config = configs[0]
            self.data = self.config.data
            self.enable_root_import = self._enable_root_import()

            self._collect_global_rules()
            self._collect_global_options()
            self._collect_per_file_rules()
            self._validate_file_selection()
            self._validate_inherited_ruff_files()
            self._collect_overrides()
            self._resolve_collected_rules()
        except (CollectionError, ConfigError, OSError, TOMLDecodeError) as e:
            self.exceptions.append(f"Invalid config: {type(e).__name__}: {e}")

        return self.exceptions

    def _enable_root_import(self) -> bool | Path:
        raw_enable_root_import = self.data.get("enable-root-import", False)
        if not raw_enable_root_import:
            return False
        return Path(raw_enable_root_import) if isinstance(raw_enable_root_import, str) else True

    def _collect_global_rules(self) -> None:
        self._collect_rule_selectors(
            _get_string_sequence_from_mapping(self.config, self.data, "enable"),
            "global enable",
        )
        self._collect_rule_selectors(
            _get_string_sequence_from_mapping(self.config, self.data, "disable"),
            "global disable",
        )

    def _collect_global_options(self) -> None:
        try:
            global_options = get_options(self.config, "options")
        except ConfigError as e:
            self.exceptions.append(
                f"Failed to parse options for global options: {type(e).__name__}: {e}"
            )
        else:
            self._collect_rule_option_targets(global_options, "global options")

    def _collect_per_file_rules(self) -> None:
        try:
            per_file_enable = get_rule_pattern_table(self.config, "per-file-enable")
        except ConfigError as e:
            self.exceptions.append(f"Failed to parse per-file-enable: {type(e).__name__}: {e}")
        else:
            self._collect_rule_patterns(per_file_enable, "per-file-enable")

        try:
            per_file_disable = get_rule_pattern_table(self.config, "per-file-disable")
        except ConfigError as e:
            self.exceptions.append(f"Failed to parse per-file-disable: {type(e).__name__}: {e}")
        else:
            self._collect_rule_patterns(per_file_disable, "per-file-disable")

    def _validate_file_selection(self) -> None:
        try:
            _get_string_sequence_from_mapping(self.config, self.data, "exclude")
        except ConfigError as e:
            self.exceptions.append(f"Failed to parse exclude: {type(e).__name__}: {e}")

    def _validate_inherited_ruff_files(self) -> None:
        inherit_ruff_files = self.data.get("inherit-ruff-files", False)
        if inherit_ruff_files and not isinstance(inherit_ruff_files, bool):
            self.exceptions.append(
                "Failed to parse inherit-ruff-files: ConfigError: 'inherit-ruff-files' must be a boolean"
            )
        elif inherit_ruff_files:
            try:
                _read_ruff_file_selection(self.config)
            except (ConfigError, OSError, TOMLDecodeError) as e:
                self.exceptions.append(
                    f"Failed to parse inherited Ruff file settings: {type(e).__name__}: {e}"
                )

    def _collect_overrides(self) -> None:
        overrides = self.data.get("overrides", [])
        if not isinstance(overrides, list):
            self.exceptions.append(
                "Failed to parse overrides: ConfigError: 'overrides' requires array of tables"
            )
            return

        for override in overrides:
            if not isinstance(override, dict):
                self.exceptions.append(
                    "Failed to parse overrides: ConfigError: 'overrides' requires array of tables"
                )
                continue

            raw_override_path = override.get("path", self.path.as_posix())
            if not isinstance(raw_override_path, str):
                self.exceptions.append(
                    "Failed to parse overrides: ConfigError: override path must be a string"
                )
                continue
            override_path = Path(raw_override_path)
            self._collect_rule_selectors(
                _get_string_sequence_from_mapping(self.config, override, "enable"),
                f"override enable: `{override_path}`",
            )
            self._collect_rule_selectors(
                _get_string_sequence_from_mapping(self.config, override, "disable"),
                f"override disable: `{override_path}`",
            )

            try:
                override_options = get_options(self.config, "options", data=override)
            except ConfigError as e:
                self.exceptions.append(
                    f"Failed to parse options for override options: `{override_path}`: "
                    f"{type(e).__name__}: {e}"
                )
            else:
                self._collect_rule_option_targets(
                    override_options, f"override options: `{override_path}`"
                )

    def _collect_rule_selectors(self, rules: Sequence[str], context: str) -> None:
        for rule in rules:
            try:
                selector = parse_rule(rule, self.root, self.config)
            except ConfigError as e:
                self.exceptions.append(
                    f"Failed to parse rule `{rule}` for {context}: {type(e).__name__}: {e}"
                )
                continue
            self.selectors_to_validate.append((rule, selector, context))

    def _collect_rule_option_targets(
        self,
        rule_options: RuleOptionsTable,
        context: str,
    ) -> None:
        for option_key, settings in rule_options.items():
            try:
                selector = parse_exact_rule_target(option_key, self.root, self.config)
            except ConfigError as e:
                self.exceptions.append(
                    f"Failed to validate options for `{option_key}` in {context}: "
                    f"{type(e).__name__}: {e}"
                )
                continue
            self.option_targets_to_validate.append((option_key, selector, settings, context))

    def _collect_rule_patterns(
        self,
        rule_patterns: Mapping[str, Sequence[str]],
        context: str,
    ) -> None:
        for pattern, rules in rule_patterns.items():
            self._collect_rule_selectors(rules, f"{context}: `{pattern}`")

    def _resolve_collected_rules(self) -> None:
        registry = _build_rule_registry(
            [
                *[selector for _raw, selector, _context in self.selectors_to_validate],
                *[
                    selector
                    for _raw_rule_name, selector, _settings, _context in self.option_targets_to_validate
                ],
            ],
            root=self.root,
            enable_root_import=self.enable_root_import,
            strict=False,
            log_failures=False,
        )

        for raw_rule, selector, context in self.selectors_to_validate:
            if error := self._resolve_rule_validation_error(registry, raw_rule, selector, context):
                self.exceptions.append(error)

        for raw_rule_name, selector, settings, context in self.option_targets_to_validate:
            self._validate_rule_options(registry, raw_rule_name, selector, settings, context)

    def _resolve_rule_validation_error(
        self,
        registry: RuleRegistry,
        raw_rule: str,
        selector: RuleSelector,
        context: str,
    ) -> str | None:
        try:
            registry.resolve(selector)
        except CollectionError as e:
            return f"Failed to import rule `{raw_rule}` for {context}: {type(e).__name__}: {e}"
        return None

    def _validate_rule_options(
        self,
        registry: RuleRegistry,
        raw_rule_name: str,
        selector: RuleSelector,
        settings: Mapping[str, object],
        context: str,
    ) -> None:
        try:
            resolution = registry.resolve(selector)
        except CollectionError as e:
            self.exceptions.append(
                f"Failed to validate options for `{raw_rule_name}` in {context}: "
                f"{type(e).__name__}: {e}"
            )
            return

        if len(resolution.rules) != 1:
            self.exceptions.append(
                f"Failed to validate options for `{raw_rule_name}` in {context}: ConfigError: rule target must resolve to exactly one rule class"
            )
            return

        try:
            rule = resolution.rules[0]()
            rule.configure(settings)
        except RuleConfigurationError as e:
            self.exceptions.append(
                f"Failed to validate options for `{raw_rule_name}` in {context}: "
                f"{type(e).__name__}: {e}"
            )


def validate_config(path: Path) -> list[str]:
    """
    Validate the config provided. The provided path is expected to be a valid toml
    config file. Any exception found while parsing or importing will be added to a list
    of exceptions that are returned.
    """
    return ConfigValidator(path).validate()


__all__ = ["ConfigValidator", "validate_config"]
