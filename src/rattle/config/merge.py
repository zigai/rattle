from __future__ import annotations

import logging
import platform
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from packaging.version import InvalidVersion, Version

from rattle.config.discovery import locate_configs, read_configs
from rattle.config.errors import ConfigError
from rattle.config.matching import (
    _excluded_by_options_without_configs,
    _get_string_sequence_from_mapping,
    _path_matches_glob,
    _read_ruff_file_selection,
    _relative_path_str,
    get_options,
    get_rule_pattern_table,
    get_sequence,
)
from rattle.config.models import Config, Options, RawConfig
from rattle.config.parsing import parse_exact_rule_target, parse_rule
from rattle.formatting import FORMAT_STYLES
from rattle.rendering.models import OutputFormat
from rattle.rule_loading import BUILTIN_RULE_COLLECTIONS, _builtin_rule_types
from rattle.selectors import (
    QualifiedRule,
    RuleNameSelector,
    RuleOptionsTable,
    RuleSelector,
)

LOG = logging.getLogger(__name__)


def _needs_configured_rule_imports(selectors: Sequence[RuleSelector]) -> bool:
    return any(
        isinstance(selector, RuleNameSelector)
        and selector.value not in BUILTIN_RULE_COLLECTIONS
        and not any(rule_type.name == selector.value for rule_type in _builtin_rule_types())
        for selector in selectors
    )


def _configured_rule_imports(*selector_groups: Iterable[RuleSelector]) -> list[RuleSelector]:
    selectors = {
        selector
        for selector_group in selector_groups
        for selector in selector_group
        if isinstance(selector, QualifiedRule)
    }
    return sorted(selectors, key=str)


def _apply_runtime_options(
    config: Config,
    options: Options,
    raw_configs: list[RawConfig],
    *,
    explicit_path: bool,
) -> None:
    if not raw_configs and _excluded_by_options_without_configs(
        config.path,
        options,
        explicit_path=explicit_path,
    ):
        config.excluded = True

    if options.tags:
        config.tags = options.tags

    if options.rules:
        if _needs_configured_rule_imports(options.rules):
            config.rule_imports = _configured_rule_imports(config.enable)
        config.enable = list(options.rules)
        config.disable = []

    if options.output_format:
        config.output_format = options.output_format

    if options.output_template:
        config.output_template = options.output_template

    if options.no_format:
        config.formatter = None


@dataclass
class ConfigMerger:
    path: Path
    raw_configs: list[RawConfig]
    root: Path | None = None
    options: Options | None = None
    explicit_path: bool = False
    enable_root_import: bool | Path = Config.enable_root_import
    enable_rules: set[RuleSelector] = field(default_factory=set)
    disable_rules: set[RuleSelector] = field(default_factory=set)
    rule_options: RuleOptionsTable = field(default_factory=dict)
    target_python_version: Version | None = field(
        default_factory=lambda: Version(platform.python_version())
    )
    target_formatter: str | None = Config.formatter
    output_format: OutputFormat = OutputFormat.rattle
    output_template: str = ""
    excluded: bool = False
    config: RawConfig = field(init=False)

    def merge(self) -> Config:
        for config in reversed(self.raw_configs):
            self.config = config
            self._merge_config()

        return Config(
            path=self.path,
            root=self.root or Path(self.path.anchor),
            excluded=self.excluded,
            enable_root_import=self.enable_root_import,
            enable=sorted(self.enable_rules, key=str),
            disable=sorted(self.disable_rules, key=str),
            options=self.rule_options,
            python_version=self.target_python_version,
            formatter=self.target_formatter,
            output_format=self.output_format,
            output_template=self.output_template,
        )

    def _merge_config(self) -> None:
        if self.root is None:
            self.root = self.config.path.parent

        data = self.config.data
        if data.pop("root", False):
            self.root = self.config.path.parent

        self._apply_root_import(data)
        self._apply_output_options(data)

        inherit_ruff_files = data.pop("inherit-ruff-files", False)
        if not isinstance(inherit_ruff_files, bool):
            raise ConfigError("'inherit-ruff-files' must be a boolean", config=self.config)
        excludes = _get_string_sequence_from_mapping(self.config, data, "exclude")
        data.pop("exclude", None)

        python_version = self.config.data.pop("python-version", None)
        if python_version is not None and not isinstance(python_version, str):
            raise ConfigError("'python-version' must be a string", config=self.config)
        formatter = self.config.data.pop("formatter", None)
        if formatter is not None and not isinstance(formatter, str):
            raise ConfigError("'formatter' must be a string", config=self.config)

        self._process_subpath(
            self.config.path.parent,
            enable=get_sequence(self.config, "enable"),
            disable=get_sequence(self.config, "disable"),
            options=get_options(self.config, "options"),
            python_version=python_version,
            formatter=formatter,
        )
        self._process_overrides()
        self._process_rule_patterns(
            self.config.path.parent,
            enable=get_rule_pattern_table(self.config, "per-file-enable"),
            disable=get_rule_pattern_table(self.config, "per-file-disable"),
        )
        self._process_file_excludes(self.config.path.parent, excludes=excludes)
        self._process_ruff_file_selection(self.config.path.parent, inherited=inherit_ruff_files)

        for key in data:
            LOG.warning("unknown configuration option %r", key)

    def _apply_root_import(self, data: dict[str, object]) -> None:
        if not (value := data.pop("enable-root-import", False)):
            return

        if self.root != self.config.path.parent:
            raise ConfigError(
                "enable-root-import not allowed in non-root configs", config=self.config
            )
        if isinstance(value, str):
            value_path = Path(value)
            if value_path.is_absolute():
                raise ConfigError(
                    "enable-root-import: absolute paths not allowed", config=self.config
                )
            if ".." in value_path.parts:
                raise ConfigError(
                    "enable-root-import: '..' components not allowed", config=self.config
                )
            self.enable_root_import = value_path
        else:
            self.enable_root_import = True

    def _apply_output_options(self, data: dict[str, object]) -> None:
        if value := data.pop("output-format", ""):
            if not isinstance(value, str):
                raise ConfigError("'output-format' must be a string", config=self.config)
            try:
                self.output_format = OutputFormat(value)
            except ValueError as e:
                raise ConfigError(
                    f"output-format: unknown value {value!r}", config=self.config
                ) from e

        if value := data.pop("output-template", ""):
            if not isinstance(value, str):
                raise ConfigError("'output-template' must be a string", config=self.config)
            self.output_template = value

    def _update_target_python_version(self, python_version: str | None) -> None:
        if python_version is None:
            return
        if not isinstance(python_version, str):
            raise ConfigError("'python-version' must be a string", config=self.config)
        if python_version:
            try:
                self.target_python_version = Version(python_version)
            except InvalidVersion as e:
                raise ConfigError(
                    f"'python-version' {python_version!r} is not valid",
                    config=self.config,
                ) from e
            return

        # disable versioning, aka python-version = ""
        self.target_python_version = None

    def _apply_rule_selection(
        self,
        *,
        config_dir: Path,
        enable: Sequence[str] = (),
        disable: Sequence[str] = (),
    ) -> None:
        for rule in enable:
            selector = parse_rule(rule, config_dir, self.config)
            self.enable_rules.add(selector)
            self.disable_rules.discard(selector)

        for rule in disable:
            selector = parse_rule(rule, config_dir, self.config)
            self.enable_rules.discard(selector)
            self.disable_rules.add(selector)

    def _process_subpath(
        self,
        subpath: Path,
        *,
        enable: Sequence[str] = (),
        disable: Sequence[str] = (),
        options: RuleOptionsTable | None = None,
        python_version: str | None = None,
        formatter: str | None = None,
    ) -> None:
        subpath = subpath.resolve()
        try:
            self.path.relative_to(subpath)
        except ValueError:  # not relative to subpath
            return

        self._apply_rule_selection(
            config_dir=self.config.path.parent,
            enable=enable,
            disable=disable,
        )

        if options:
            for rule_name, option_values in options.items():
                existing_options = self.rule_options.setdefault(rule_name, {})
                existing_options.update(option_values)

        self._update_target_python_version(python_version)

        if formatter:
            if formatter not in FORMAT_STYLES:
                raise ConfigError(f"'formatter' {formatter!r} not supported", config=self.config)

            self.target_formatter = formatter

    def _process_overrides(self) -> None:
        overrides = self.config.data.pop("overrides", [])
        if not isinstance(overrides, list):
            raise ConfigError("'overrides' requires array of tables", config=self.config)

        for override in overrides:
            if not isinstance(override, dict):
                raise ConfigError("'overrides' requires array of tables", config=self.config)

            subpath = override.get("path", None)
            if not isinstance(subpath, str) or not subpath:
                raise ConfigError("'overrides' table requires 'path' value", config=self.config)

            python_version = override.pop("python-version", None)
            if python_version is not None and not isinstance(python_version, str):
                raise ConfigError("'python-version' must be a string", config=self.config)
            formatter = override.pop("formatter", None)
            if formatter is not None and not isinstance(formatter, str):
                raise ConfigError("'formatter' must be a string", config=self.config)

            self._process_subpath(
                self.config.path.parent / subpath,
                enable=get_sequence(self.config, "enable", data=override),
                disable=get_sequence(self.config, "disable", data=override),
                options=get_options(self.config, "options", data=override),
                python_version=python_version,
                formatter=formatter,
            )

    def _process_rule_patterns(
        self,
        config_dir: Path,
        *,
        enable: Mapping[str, Sequence[str]] | None = None,
        disable: Mapping[str, Sequence[str]] | None = None,
    ) -> None:
        relative_path = _relative_path_str(self.path, config_dir)
        if relative_path is None:
            return

        for pattern, rules in (enable or {}).items():
            if _path_matches_glob(relative_path, pattern):
                self._apply_rule_selection(config_dir=config_dir, enable=rules)

        for pattern, rules in (disable or {}).items():
            if _path_matches_glob(relative_path, pattern):
                self._apply_rule_selection(config_dir=config_dir, disable=rules)

    def _process_file_excludes(self, config_dir: Path, *, excludes: Sequence[str]) -> None:
        relative_path = _relative_path_str(self.path, config_dir)
        if relative_path is None:
            return

        if (
            excludes
            and any(_path_matches_glob(relative_path, pattern) for pattern in excludes)
            and not self.explicit_path
        ):
            self.excluded = True

    def _process_ruff_file_selection(self, config_dir: Path, *, inherited: bool) -> None:
        has_cli_file_selection = bool(
            self.options and (self.options.exclude or self.options.extend_exclude)
        )
        if not inherited and not has_cli_file_selection:
            return

        relative_path = _relative_path_str(self.path, config_dir)
        if relative_path is None:
            return

        if inherited:
            includes, excludes, force_exclude = _read_ruff_file_selection(self.config)
        else:
            includes, excludes, force_exclude = [], [], False

        if self.options and self.options.exclude:
            excludes = list(self.options.exclude)
            force_exclude = True
        elif self.options and self.options.extend_exclude:
            excludes.extend(self.options.extend_exclude)

        current_dir_relative_path = _relative_path_str(self.path, Path.cwd())

        def path_matches(pattern: str) -> bool:
            return _path_matches_glob(relative_path, pattern) or (
                current_dir_relative_path is not None
                and _path_matches_glob(current_dir_relative_path, pattern)
            )

        if includes and not any(path_matches(pattern) for pattern in includes):
            self.excluded = True

        if (
            excludes
            and any(path_matches(pattern) for pattern in excludes)
            and (force_exclude or not self.explicit_path)
        ):
            self.excluded = True


def generate_config(
    path: Path | None = None,
    root: Path | None = None,
    *,
    options: Options | None = None,
    explicit_path: bool = False,
) -> Config:
    """Given a file path, walk upwards looking for and applying cascading configs."""
    path = (path or Path.cwd()).resolve()

    if root is not None:
        root = root.resolve()

    if options and options.config_file:
        config_paths = [options.config_file]
    else:
        config_paths = locate_configs(path, root=root)

    raw_configs = read_configs(config_paths)
    config = ConfigMerger(
        path=path,
        raw_configs=raw_configs,
        root=root,
        options=options,
        explicit_path=explicit_path,
    ).merge()

    if options:
        _apply_runtime_options(config, options, raw_configs, explicit_path=explicit_path)

    return config


__all__ = ["ConfigMerger", "generate_config", "parse_exact_rule_target", "parse_rule"]
