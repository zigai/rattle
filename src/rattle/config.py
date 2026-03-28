# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import importlib
import inspect
import logging
import pkgutil
import platform
import sys
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from functools import cache
from importlib.machinery import ModuleSpec
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import (
    Any,
)

from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

from .format import FORMAT_STYLES
from .ftypes import (
    AliasSelector,
    AliasSelectorRegex,
    CodeSelector,
    CodeSelectorRegex,
    Config,
    Options,
    OutputFormat,
    QualifiedRule,
    QualifiedRuleRegex,
    RawConfig,
    RuleOptionsTable,
    RuleSelector,
    T,
    is_rule_option_value,
    is_sequence,
)
from .rule import LintRule
from .util import append_sys_path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

RATTLE_CONFIG_FILENAMES = ("pyproject.toml",)
RATTLE_LOCAL_MODULE = "rattle.local"
BUILTIN_RULE_MODULES = ("rattle.rules", "rattle.rules.extra")


log = logging.getLogger(__name__)
GLOB_META_CHARS = frozenset("*?[")
_logged_rule_load_failures: set[tuple[Path, Path | None, str, str, str]] = set()


class ConfigError(ValueError):
    def __init__(self, msg: str, config: RawConfig | None = None) -> None:
        super().__init__(msg)
        self.config = config


class CollectionError(RuntimeError):
    def __init__(self, msg: str, rule: RuleSelector) -> None:
        super().__init__(msg)
        self.rule = rule

    def __reduce__(self) -> tuple[type[RuntimeError], Any]:
        return type(self), (*self.args, self.rule)


@dataclass(frozen=True)
class RuleResolution:
    selector: RuleSelector
    rules: tuple[type[LintRule], ...]
    concrete: bool


@dataclass
class RuleRegistry:
    imported_rules: dict[QualifiedRule, tuple[type[LintRule], ...]] = field(default_factory=dict)
    import_errors: dict[QualifiedRule, Exception] = field(default_factory=dict)
    rules_by_key: dict[str, type[LintRule]] = field(default_factory=dict)
    rules_by_code: dict[str, type[LintRule]] = field(default_factory=dict)
    rules_by_alias: dict[str, type[LintRule]] = field(default_factory=dict)

    def register(self, rule_type: type[LintRule], *, builtin: bool) -> None:
        key = _rule_key_for_type(rule_type)
        existing = self.rules_by_key.get(key)
        if existing is None:
            self.rules_by_key[key] = rule_type
        elif existing is not rule_type:
            raise CollectionError(
                f"duplicate rule registration for {key}",
                QualifiedRule(rule_type.__module__, rule_type.__name__),
            )

        code = rule_type.CODE
        if code is not None:
            if not CodeSelectorRegex.fullmatch(code):
                raise CollectionError(
                    f"{key} declares invalid CODE {code!r}",
                    QualifiedRule(rule_type.__module__, rule_type.__name__),
                )
            self._register_unique_selector(
                self.rules_by_code,
                code,
                rule_type,
                selector_kind="CODE",
            )

        for alias in _selector_aliases_for_rule_type(rule_type, builtin=builtin):
            if CodeSelectorRegex.fullmatch(alias):
                raise CollectionError(
                    f"{key} declares alias {alias!r} that collides with code syntax",
                    QualifiedRule(rule_type.__module__, rule_type.__name__),
                )
            if not AliasSelectorRegex.fullmatch(alias):
                raise CollectionError(
                    f"{key} declares invalid alias {alias!r}",
                    QualifiedRule(rule_type.__module__, rule_type.__name__),
                )
            self._register_unique_selector(
                self.rules_by_alias,
                alias,
                rule_type,
                selector_kind="alias",
            )

    def _register_unique_selector(
        self,
        mapping: dict[str, type[LintRule]],
        selector: str,
        rule_type: type[LintRule],
        *,
        selector_kind: str,
    ) -> None:
        existing = mapping.get(selector)
        if existing is None:
            mapping[selector] = rule_type
            return
        if existing is rule_type:
            return

        raise CollectionError(
            (
                f"duplicate rule {selector_kind} {selector!r} for "
                f"{_rule_key_for_type(existing)} and {_rule_key_for_type(rule_type)}"
            ),
            QualifiedRule(rule_type.__module__, rule_type.__name__),
        )


def is_rule(obj: type[T]) -> bool:
    """Returns True if class is a concrete subclass of LintRule."""
    return inspect.isclass(obj) and issubclass(obj, LintRule) and obj is not LintRule


@contextmanager
def local_rule_loader(rule: QualifiedRule) -> Iterator[None]:
    """
    Allows importing local rules from arbitrary paths as submodules of rattle.local.

    Imports ``rattle.local``, a "reserved" package within the rattle namespace, and
    overrides the module's path and import spec to come from the root of the specified
    local rule. Relative imports within the local namespace should work correctly,
    though may cause collisions if parent-relative imports (``..foo``) are used.

    When the context exits, this removes all members of the ``rattle.local`` namespace
    from the global ``sys.modules`` dictionary, allowing subsequent imports of further
    local rules.

    This allows importlib to find local names within the fake ``rattle.local`` namespace,
    even if they come from arbitrary places on disk, or would otherwise have namespace
    conflicts if loaded normally using a munged ``sys.path``.
    """
    try:
        import rattle.local

        assert hasattr(rattle.local, "__path__")
        assert rattle.local.__spec__ is not None
        assert rule.root is not None

        orig_spec = rattle.local.__spec__
        rattle.local.__path__ = [rule.root.as_posix()]
        rattle.local.__spec__ = ModuleSpec(
            name=RATTLE_LOCAL_MODULE,
            loader=orig_spec.loader,
            origin=(rule.root / "__init__.py").as_posix(),
            is_package=True,
        )

        yield

    finally:
        for key in list(sys.modules):
            if key.startswith("rattle.local"):
                sys.modules.pop(key, None)


def find_rules(rule: QualifiedRule) -> Iterable[type[LintRule]]:
    """
    Import the rule's qualified module name and return a list of collected rule classes.

    Imports the module by qualified name (eg ``foo.bar`` or ``.local.rules``), and
    then walks that module to find all lint rules.

    If a specific rule name is given, returns only the lint rule matching that name;
    otherwise returns the entire list of found rules.
    """
    try:
        if rule.local:
            with local_rule_loader(rule):
                module = importlib.import_module(rule.module, "rattle.local")
                module_rules = walk_module(module)
        else:
            module = importlib.import_module(rule.module)
            module_rules = walk_module(module)

        if rule.name:
            if value := module_rules.get(rule.name, None):
                if issubclass(value, LintRule):
                    yield value
                else:
                    log.warning("don't know what to do with {value!r}")
            elif rule.local:
                raise CollectionError(f"could not find rule {rule} in {rule.root}", rule)
            else:
                raise CollectionError(f"could not find rule {rule}", rule)

        else:
            for name in sorted(module_rules.keys()):
                yield module_rules[name]

    except ImportError as e:
        if rule.local:
            raise CollectionError(f"could not import rule(s) {rule} from {rule.root}", rule) from e
        else:
            raise CollectionError(f"could not import rule(s) {rule}", rule) from e


def walk_module(module: ModuleType) -> dict[str, type[LintRule]]:
    """
    Given a module object, return a mapping of all rule names to classes.

    Looks at all objects of the module, and collects lint rules that match the
    :func:`is_rule` predicate.

    If the original module is a package (eg, ``foo.__init__``), also loads all
    modules from that package (ignoring sub-packages), and includes their rules in
    the final results.
    """
    rules: dict[str, type[LintRule]] = {}

    members = inspect.getmembers(module, is_rule)
    rules.update(members)

    if hasattr(module, "__path__"):
        for _, module_name, is_pkg in pkgutil.iter_modules(module.__path__):
            if not is_pkg:  # do not recurse to sub-packages
                mod = importlib.import_module(f".{module_name}", module.__name__)
                rules.update(walk_module(mod))

    return rules


def _rule_key_for_type(rule_type: type[LintRule]) -> str:
    return f"{rule_type.__module__}:{rule_type.__name__}"


@cache
def _builtin_rule_types() -> tuple[type[LintRule], ...]:
    builtin_rules: list[type[LintRule]] = []
    for module_name in BUILTIN_RULE_MODULES:
        builtin_rules.extend(find_rules(QualifiedRule(module_name)))
    return tuple(builtin_rules)


def _selector_aliases_for_rule_type(rule_type: type[LintRule], *, builtin: bool) -> set[str]:
    aliases = set(rule_type.ALIASES)
    if builtin:
        aliases.add(rule_type.__name__)
    return aliases


def _option_key_aliases_for_rule_type(rule_type: type[LintRule]) -> set[str]:
    module_parts = rule_type.__module__.split(".")
    aliases: set[str] = set()
    for idx in range(len(module_parts), 0, -1):
        module_name = ".".join(module_parts[:idx])
        aliases.add(f"{module_name}:{rule_type.__name__}")

    local_prefix = f"{RATTLE_LOCAL_MODULE}."
    if rule_type.__module__.startswith(local_prefix):
        local_module = rule_type.__module__.removeprefix(local_prefix)
        local_parts = local_module.split(".")
        for idx in range(len(local_parts), 0, -1):
            module_name = ".".join(local_parts[:idx])
            aliases.add(f".{module_name}:{rule_type.__name__}")

    builtin_rule_types = set(_builtin_rule_types())
    aliases.update(
        _selector_aliases_for_rule_type(rule_type, builtin=rule_type in builtin_rule_types)
    )
    if rule_type.CODE is not None:
        aliases.add(rule_type.CODE)

    return aliases


def _enable_root_import_path(enable_root_import: bool | Path, root: Path) -> Path | None:
    if not enable_root_import:
        return None
    if isinstance(enable_root_import, Path):
        return root / enable_root_import
    return root


def _log_rule_load_failure_once(
    selector: RuleSelector,
    error: Exception,
    *,
    root: Path,
    enable_root_import: bool | Path,
) -> None:
    import_root = _enable_root_import_path(enable_root_import, root)
    key = (
        root.resolve(),
        import_root.resolve() if import_root is not None else None,
        str(selector),
        error.__class__.__name__,
        str(error),
    )
    if key in _logged_rule_load_failures:
        return

    _logged_rule_load_failures.add(key)
    log.warning(
        "Failed to load rules '%s': %s: %s",
        selector,
        error.__class__.__name__,
        error,
    )


def _build_rule_registry(
    selectors: Iterable[RuleSelector],
    *,
    root: Path,
    enable_root_import: bool | Path = False,
    strict: bool,
    log_failures: bool = True,
) -> RuleRegistry:
    registry = RuleRegistry()
    builtin_rule_types = set(_builtin_rule_types())
    for rule_type in builtin_rule_types:
        registry.register(rule_type, builtin=True)

    import_selectors = sorted(
        {selector for selector in selectors if isinstance(selector, QualifiedRule)},
        key=str,
    )
    with ExitStack() as stack:
        path = _enable_root_import_path(enable_root_import, root)
        if path is not None:
            stack.enter_context(append_sys_path(path))

        for selector in import_selectors:
            try:
                rules = tuple(find_rules(selector))
            except Exception as error:
                if strict:
                    raise
                registry.import_errors[selector] = error
                if log_failures:
                    _log_rule_load_failure_once(
                        selector,
                        error,
                        root=root,
                        enable_root_import=enable_root_import,
                    )
                rules = ()

            registry.imported_rules[selector] = rules
            for rule_type in rules:
                registry.register(rule_type, builtin=rule_type in builtin_rule_types)

    return registry


def _resolve_selector(selector: RuleSelector, registry: RuleRegistry) -> RuleResolution:
    if isinstance(selector, QualifiedRule):
        if error := registry.import_errors.get(selector):
            raise error
        rules = registry.imported_rules.get(selector, ())
        if selector.name is not None and not rules:
            raise CollectionError(f"could not find rule {selector}", selector)
        return RuleResolution(selector, rules, concrete=selector.name is not None)

    if isinstance(selector, CodeSelector):
        if rule_type := registry.rules_by_code.get(selector.value):
            return RuleResolution(selector, (rule_type,), concrete=True)

        rules = tuple(
            sorted(
                {
                    rule_type
                    for code, rule_type in registry.rules_by_code.items()
                    if code.startswith(selector.value)
                },
                key=_rule_key_for_type,
            )
        )
        if not rules:
            raise CollectionError(f"could not find rule {selector}", selector)
        return RuleResolution(selector, rules, concrete=False)

    if rule_type := registry.rules_by_alias.get(selector.value):
        return RuleResolution(selector, (rule_type,), concrete=True)

    raise CollectionError(f"could not find rule {selector}", selector)


def _resolve_selector_or_log(
    selector: RuleSelector,
    registry: RuleRegistry,
    *,
    root: Path,
    enable_root_import: bool | Path,
) -> RuleResolution | None:
    try:
        return _resolve_selector(selector, registry)
    except Exception as error:  # noqa: BLE001 - import boundary
        _log_rule_load_failure_once(
            selector,
            error,
            root=root,
            enable_root_import=enable_root_import,
        )
        return None


def collect_rule_types(
    config: Config,
    *,
    # out-param to capture reasons when disabling rules for debugging
    debug_reasons: dict[type[LintRule], str] | None = None,
) -> Collection[type[LintRule]]:
    """Import and return rule types specified by `enables` and `disables`."""
    all_rules: set[type[LintRule]] = set()
    named_enables: set[type[LintRule]] = set()
    disabled_rules = debug_reasons if debug_reasons is not None else {}

    registry = _build_rule_registry(
        (*config.enable, *config.disable),
        root=config.root,
        enable_root_import=config.enable_root_import,
        strict=False,
    )

    for selector in config.enable:
        resolution = _resolve_selector_or_log(
            selector,
            registry,
            root=config.root,
            enable_root_import=config.enable_root_import,
        )
        if resolution is None:
            continue
        if resolution.concrete:
            named_enables |= set(resolution.rules)
        all_rules |= set(resolution.rules)

    for selector in config.disable:
        resolution = _resolve_selector_or_log(
            selector,
            registry,
            root=config.root,
            enable_root_import=config.enable_root_import,
        )
        if resolution is None:
            continue
        disabled_rules.update(
            {
                rule_type: "disabled"
                for rule_type in resolution.rules
                if rule_type not in named_enables
            }
        )
        all_rules -= set(disabled_rules)

    if config.tags:
        disabled_rules.update({R: "tags" for R in all_rules if R.TAGS not in config.tags})
        all_rules -= set(disabled_rules)

    if config.python_version is not None:
        disabled_rules.update(
            {
                R: "python-version"
                for R in all_rules
                if R.PYTHON_VERSION
                and config.python_version not in SpecifierSet(R.PYTHON_VERSION, prereleases=True)
            }
        )
        all_rules -= set(disabled_rules)

    return all_rules


def resolve_rule_settings(
    config: Config,
    rule_types: Collection[type[LintRule]],
) -> dict[type[LintRule], dict[str, object]]:
    rules_by_key: dict[str, type[LintRule]] = {}
    for rule_type in rule_types:
        for alias in _option_key_aliases_for_rule_type(rule_type):
            rules_by_key[alias] = rule_type

    resolved_settings: dict[type[LintRule], dict[str, object]] = {}
    for rule_name, settings in config.options.items():
        rule_type = rules_by_key.get(rule_name)
        if rule_type is None:
            continue

        target_settings = resolved_settings.setdefault(rule_type, {})
        target_settings.update(settings)

    return resolved_settings


def materialize_rules(
    rule_types: Collection[type[LintRule]],
    resolved_settings: Mapping[type[LintRule], Mapping[str, object]],
) -> list[LintRule]:
    materialized_rules: list[LintRule] = []
    for rule_type in sorted(rule_types, key=_rule_key_for_type):
        rule = rule_type()
        rule.configure(resolved_settings.get(rule_type, {}))
        materialized_rules.append(rule)

    return materialized_rules


def collect_rules(
    config: Config,
    *,
    # out-param to capture reasons when disabling rules for debugging
    debug_reasons: dict[type[LintRule], str] | None = None,
) -> Collection[LintRule]:
    """Import, configure, and return rules specified by `enables` and `disables`."""
    rule_types = collect_rule_types(config, debug_reasons=debug_reasons)
    resolved_settings = resolve_rule_settings(config, rule_types)
    return materialize_rules(rule_types, resolved_settings)


def locate_configs(path: Path, root: Path | None = None) -> list[Path]:
    """
    Given a file path, locate all relevant config files in priority order.

    Walking upward from target path, creates a list of candidate paths that exist
    on disk, ordered from nearest/highest priority to further/lowest priority.

    If root is given, only return configs between path and root (inclusive), ignoring
    any paths outside of root, even if they would contain relevant configs.
    If given, root must contain path.

    Returns a list of config paths in priority order, from highest priority to lowest.
    """
    results: list[Path] = []

    if not path.is_dir():
        path = path.parent

    root = root.resolve() if root is not None else Path(path.anchor)
    path.relative_to(root)  # enforce path being inside root

    while True:
        candidates = (path / filename for filename in RATTLE_CONFIG_FILENAMES)
        results.extend(candidate for candidate in candidates if candidate.is_file())

        if path in (root, path.parent):
            break

        path = path.parent

    return results


def read_configs(paths: list[Path]) -> list[RawConfig]:
    """
    Read config data for each path given, and return their raw toml config values.

    Skips any path with no — or empty — `tool.rattle` section.
    Stops early at any config with `root = true`.

    Maintains the same order as given in paths, minus any skipped files.
    """
    configs: list[RawConfig] = []

    for path in paths:
        path = path.resolve()
        if path.name != "pyproject.toml":
            raise ConfigError(
                "Rattle only reads configuration from `pyproject.toml`",
            )
        content = path.read_text()
        data = tomllib.loads(content)
        rattle_data = data.get("tool", {}).get("rattle", {})

        if rattle_data:
            config = RawConfig(path=path, data=rattle_data)
            configs.append(config)

            if config.data.get("root", False):
                break

    return configs


def get_rule_pattern_table(
    config: RawConfig, key: str, *, data: dict[str, Any] | None = None
) -> dict[str, list[str]]:
    mapping = data.pop(key, {}) if data else config.data.pop(key, {})

    if not isinstance(mapping, Mapping):
        raise ConfigError(f"{key!r} must be mapping of values, got {type(mapping)}", config=config)

    result: dict[str, list[str]] = {}
    for raw_pattern, rules in mapping.items():
        if not isinstance(raw_pattern, str):
            raise ConfigError(
                f"{key!r} pattern must be a string, got {type(raw_pattern)}",
                config=config,
            )
        if not raw_pattern:
            raise ConfigError(f"{key!r} pattern may not be empty", config=config)
        if not is_sequence(rules):
            raise ConfigError(
                f"{key!r} value for {raw_pattern!r} must be array of values, got {type(rules)}",
                config=config,
            )

        pattern_rules: list[str] = []
        for rule in rules:
            if not isinstance(rule, str):
                raise ConfigError(
                    f"{key!r} value for {raw_pattern!r} must contain strings, got {type(rule)}",
                    config=config,
                )
            pattern_rules.append(rule)

        result[raw_pattern] = pattern_rules

    return result


def _get_string_sequence_from_mapping(
    config: RawConfig, mapping: Mapping[str, object], key: str
) -> list[str]:
    value = mapping.get(key, ())

    if not is_sequence(value):
        raise ConfigError(f"{key!r} must be array of values, got {type(value)}", config=config)

    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ConfigError(f"{key!r} values must be strings, got {type(item)}", config=config)
        result.append(item)

    return result


def _read_ruff_file_selection(config: RawConfig) -> tuple[list[str], list[str], bool]:
    pyproject_path = (
        config.path
        if config.path.name == "pyproject.toml"
        else config.path.parent / "pyproject.toml"
    )
    if not pyproject_path.is_file():
        return [], [], False

    content = pyproject_path.read_text()
    data = tomllib.loads(content)
    ruff_data = data.get("tool", {}).get("ruff", {})

    if not ruff_data:
        return [], [], False
    if not isinstance(ruff_data, Mapping):
        raise ConfigError("'tool.ruff' must be mapping of values", config=config)

    includes = _get_string_sequence_from_mapping(config, ruff_data, "include")
    includes.extend(_get_string_sequence_from_mapping(config, ruff_data, "extend-include"))

    excludes = _get_string_sequence_from_mapping(config, ruff_data, "exclude")
    excludes.extend(_get_string_sequence_from_mapping(config, ruff_data, "extend-exclude"))

    force_exclude = ruff_data.get("force-exclude", False)
    if not isinstance(force_exclude, bool):
        raise ConfigError("'force-exclude' must be a boolean", config=config)

    return includes, excludes, force_exclude


def _relative_path_str(path: Path, base: Path) -> str | None:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return None


def _path_matches_glob(relative_path: str, pattern: str) -> bool:
    has_glob = any(char in pattern for char in GLOB_META_CHARS)

    if "/" not in pattern:
        parts = relative_path.split("/")
        if has_glob:
            path = PurePosixPath()
            return any(path.joinpath(part).match(pattern) for part in parts)
        return pattern in parts

    if not has_glob:
        return relative_path == pattern or relative_path.startswith(f"{pattern}/")

    return PurePosixPath(relative_path).match(pattern)


def get_sequence(
    config: RawConfig, key: str, *, data: dict[str, Any] | None = None
) -> Sequence[str]:
    value: Sequence[str]
    value = data.pop(key, ()) if data else config.data.pop(key, ())

    if not is_sequence(value):
        raise ConfigError(f"{key!r} must be array of values, got {type(value)}", config=config)

    return value


def get_options(  # noqa: C901 - option parsing and normalization
    config: RawConfig, key: str, *, data: dict[str, Any] | None = None
) -> RuleOptionsTable:
    mapping = data.pop(key, {}) if data else config.data.pop(key, {})

    if is_sequence(mapping):
        merged_mapping: dict[object, object] = {}
        for item in mapping:
            if not isinstance(item, Mapping):
                raise ConfigError(
                    f"{key!r} sequence values must be mappings, got {type(item)}",
                    config=config,
                )
            merged_mapping.update(item)
        mapping = merged_mapping

    if not isinstance(mapping, Mapping):
        raise ConfigError(f"{key!r} must be mapping of values, got {type(mapping)}", config=config)

    rule_configs: RuleOptionsTable = {}
    for raw_rule_name, rule_config in mapping.items():
        if not isinstance(raw_rule_name, str):
            raise ConfigError(
                f"{key!r} rule name must be a string, got {type(raw_rule_name)}",
                config=config,
            )

        try:
            rule_target = parse_exact_rule_target(raw_rule_name, config.path.parent, config)
        except ConfigError as error:
            raise ConfigError(f"{key!r} {error}", config=config) from error

        if not isinstance(rule_config, Mapping):
            raise ConfigError(
                f"{key!r} rule config for {raw_rule_name!r} must be a mapping, got {type(rule_config)}",
                config=config,
            )

        rule_name = str(rule_target)
        rule_configs[rule_name] = {}
        for option_name, value in rule_config.items():
            if not isinstance(option_name, str):
                raise ConfigError(
                    f"{key!r} option names must be strings, got {type(option_name)}",
                    config=config,
                )

            if not is_rule_option_value(value):
                raise ConfigError(
                    f"{option_name!r} must be a TOML scalar or array of scalars, got {type(value)}",
                    config=config,
                )

            rule_configs[rule_name][option_name] = list(value) if is_sequence(value) else value

    return rule_configs


def parse_rule(rule: str, root: Path, config: RawConfig | None = None) -> RuleSelector:
    """Given a raw rule string, parse and return a rule selector object."""
    if CodeSelectorRegex.fullmatch(rule):
        return CodeSelector(rule)

    if "." not in rule and ":" not in rule and AliasSelectorRegex.fullmatch(rule):
        return AliasSelector(rule)

    if not (match := QualifiedRuleRegex.match(rule)):
        raise ConfigError(f"invalid rule name {rule!r}", config=config)

    group = match.groupdict()
    module = group["module"]
    name = group["name"]
    local = group["local"]

    if local:
        return QualifiedRule(module, name, local, root)
    return QualifiedRule(module, name)


def parse_exact_rule_target(
    rule: str,
    root: Path,
    config: RawConfig | None = None,
) -> RuleSelector:
    selector = parse_rule(rule, root, config)

    if isinstance(selector, QualifiedRule):
        if selector.name is None:
            raise ConfigError(
                f"rule target {rule!r} must reference one concrete rule (`module:ClassName`)",
                config=config,
            )
        return selector

    if isinstance(selector, CodeSelector) and not any(char.isdigit() for char in selector.value):
        raise ConfigError(
            f"rule target {rule!r} must reference one concrete rule (exact code or alias)",
            config=config,
        )

    return selector


def merge_configs(  # noqa: C901 - config merge orchestration
    path: Path,
    raw_configs: list[RawConfig],
    root: Path | None = None,
    *,
    explicit_path: bool = False,
) -> Config:
    """
    Given multiple raw configs, merge them in priority order.

    Assumes raw_configs are given in order from highest to lowest priority.
    """
    config: RawConfig
    enable_root_import: bool | Path = Config.enable_root_import
    enable_rules: set[RuleSelector] = {QualifiedRule("rattle.rules")}
    disable_rules: set[RuleSelector] = set()
    rule_options: RuleOptionsTable = {}
    target_python_version: Version | None = Version(platform.python_version())
    target_formatter: str | None = None
    output_format: OutputFormat = OutputFormat.rattle
    output_template: str = ""
    excluded = False

    def update_target_python_version(python_version: str | None) -> None:
        nonlocal target_python_version

        if python_version is None:
            return
        if not isinstance(python_version, str):
            raise ConfigError("'python-version' must be a string", config=config)
        if python_version:
            try:
                target_python_version = Version(python_version)
            except InvalidVersion as error:
                raise ConfigError(
                    f"'python-version' {python_version!r} is not valid",
                    config=config,
                ) from error
            return

        # disable versioning, aka python-version = ""
        target_python_version = None

    def apply_rule_selection(
        *,
        config_dir: Path,
        enable: Sequence[str] = (),
        disable: Sequence[str] = (),
    ) -> None:
        for rule in enable:
            selector = parse_rule(rule, config_dir, config)
            enable_rules.add(selector)
            disable_rules.discard(selector)

        for rule in disable:
            selector = parse_rule(rule, config_dir, config)
            enable_rules.discard(selector)
            disable_rules.add(selector)

    def process_subpath(
        subpath: Path,
        *,
        enable: Sequence[str] = (),
        disable: Sequence[str] = (),
        options: RuleOptionsTable | None = None,
        python_version: str | None = None,
        formatter: str | None = None,
    ) -> None:
        nonlocal target_python_version
        nonlocal target_formatter

        subpath = subpath.resolve()
        try:
            path.relative_to(subpath)
        except ValueError:  # not relative to subpath
            return

        apply_rule_selection(config_dir=config.path.parent, enable=enable, disable=disable)

        if options:
            for rule_name, option_values in options.items():
                existing_options = rule_options.setdefault(rule_name, {})
                existing_options.update(option_values)

        update_target_python_version(python_version)

        if formatter:
            if formatter not in FORMAT_STYLES:
                raise ConfigError(f"'formatter' {formatter!r} not supported", config=config)

            target_formatter = formatter

    def process_rule_patterns(
        config_dir: Path,
        *,
        enable: Mapping[str, Sequence[str]] | None = None,
        disable: Mapping[str, Sequence[str]] | None = None,
    ) -> None:
        relative_path = _relative_path_str(path, config_dir)
        if relative_path is None:
            return

        for pattern, rules in (enable or {}).items():
            if _path_matches_glob(relative_path, pattern):
                apply_rule_selection(config_dir=config_dir, enable=rules)

        for pattern, rules in (disable or {}).items():
            if _path_matches_glob(relative_path, pattern):
                apply_rule_selection(config_dir=config_dir, disable=rules)

    def process_ruff_file_selection(config_dir: Path, *, inherited: bool) -> None:
        nonlocal excluded

        if not inherited:
            return

        relative_path = _relative_path_str(path, config_dir)
        if relative_path is None:
            return

        includes, excludes, force_exclude = _read_ruff_file_selection(config)
        if includes and not any(_path_matches_glob(relative_path, pattern) for pattern in includes):
            excluded = True

        if (
            excludes
            and any(_path_matches_glob(relative_path, pattern) for pattern in excludes)
            and (force_exclude or not explicit_path)
        ):
            excluded = True

    for config in reversed(raw_configs):
        if root is None:
            root = config.path.parent

        data = config.data
        if data.pop("root", False):
            root = config.path.parent

        if value := data.pop("enable-root-import", False):
            if root != config.path.parent:
                raise ConfigError(
                    "enable-root-import not allowed in non-root configs", config=config
                )
            if isinstance(value, str):
                value_path = Path(value)
                if value_path.is_absolute():
                    raise ConfigError(
                        "enable-root-import: absolute paths not allowed", config=config
                    )
                if ".." in value_path.parts:
                    raise ConfigError(
                        "enable-root-import: '..' components not allowed", config=config
                    )
                enable_root_import = value_path
            else:
                enable_root_import = True

        if value := data.pop("output-format", ""):
            try:
                output_format = OutputFormat(value)
            except ValueError as e:
                raise ConfigError(f"output-format: unknown value {value!r}", config=config) from e

        if value := data.pop("output-template", ""):
            output_template = value

        inherit_ruff_files = data.pop("inherit-ruff-files", False)
        if not isinstance(inherit_ruff_files, bool):
            raise ConfigError("'inherit-ruff-files' must be a boolean", config=config)

        process_subpath(
            config.path.parent,
            enable=get_sequence(config, "enable"),
            disable=get_sequence(config, "disable"),
            options=get_options(config, "options"),
            python_version=config.data.pop("python-version", None),
            formatter=config.data.pop("formatter", None),
        )

        for override in get_sequence(config, "overrides"):
            if not isinstance(override, dict):
                raise ConfigError("'overrides' requires array of tables", config=config)

            subpath = override.get("path", None)
            if not subpath:
                raise ConfigError("'overrides' table requires 'path' value", config=config)

            subpath = config.path.parent / subpath
            process_subpath(
                subpath,
                enable=get_sequence(config, "enable", data=override),
                disable=get_sequence(config, "disable", data=override),
                options=get_options(config, "options", data=override),
                python_version=override.pop("python-version", None),
                formatter=override.pop("formatter", None),
            )

        process_rule_patterns(
            config.path.parent,
            enable=get_rule_pattern_table(config, "per-file-enable"),
            disable=get_rule_pattern_table(config, "per-file-disable"),
        )
        process_ruff_file_selection(config.path.parent, inherited=inherit_ruff_files)

        for key in data:
            log.warning("unknown configuration option %r", key)

    return Config(
        path=path,
        root=root or Path(path.anchor),
        excluded=excluded,
        enable_root_import=enable_root_import,
        enable=sorted(enable_rules, key=str),
        disable=sorted(disable_rules, key=str),
        options=rule_options,
        python_version=target_python_version,
        formatter=target_formatter,
        output_format=output_format,
        output_template=output_template,
    )


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
    config = merge_configs(path, raw_configs, root=root, explicit_path=explicit_path)

    if options:
        if options.tags:
            config.tags = options.tags

        if options.rules:
            config.enable = list(options.rules)
            config.disable = []

        if options.output_format:
            config.output_format = options.output_format

        if options.output_template:
            config.output_template = options.output_template

    return config


def validate_config(path: Path) -> list[str]:  # noqa: C901 - config validation orchestration
    """
    Validate the config provided. The provided path is expected to be a valid toml
    config file. Any exception found while parsing or importing will be added to a list
    of exceptions that are returned.
    """
    exceptions: list[str] = []
    try:
        root = path.parent
        configs = read_configs([path])[0]
        data = configs.data
        selectors_to_validate: list[tuple[str, RuleSelector, str]] = []
        option_targets_to_validate: list[tuple[str, RuleSelector, Mapping[str, object], str]] = []

        raw_enable_root_import = data.get("enable-root-import", False)
        enable_root_import: bool | Path = False
        if raw_enable_root_import:
            enable_root_import = (
                Path(raw_enable_root_import) if isinstance(raw_enable_root_import, str) else True
            )

        def collect_rule_selectors(rules: Sequence[str], context: str) -> None:
            for rule in rules:
                try:
                    selector = parse_rule(rule, root, configs)
                except Exception as error:  # noqa: BLE001 - validation boundary
                    exceptions.append(
                        f"Failed to parse rule `{rule}` for {context}: {error.__class__.__name__}: {error}"
                    )
                    continue
                selectors_to_validate.append((rule, selector, context))

        def collect_rule_option_targets(rule_options: RuleOptionsTable, context: str) -> None:
            for rule_name, settings in rule_options.items():
                try:
                    selector = parse_exact_rule_target(rule_name, root, configs)
                except Exception as error:  # noqa: BLE001 - validation boundary
                    exceptions.append(
                        f"Failed to validate options for `{rule_name}` in {context}: {error.__class__.__name__}: {error}"
                    )
                    continue
                option_targets_to_validate.append((rule_name, selector, settings, context))

        def collect_rule_patterns(rule_patterns: Mapping[str, Sequence[str]], context: str) -> None:
            for pattern, rules in rule_patterns.items():
                collect_rule_selectors(rules, f"{context}: `{pattern}`")

        collect_rule_selectors(data.get("enable", []), "global enable")
        collect_rule_selectors(data.get("disable", []), "global disable")

        try:
            global_options = get_options(configs, "options")
        except Exception as error:  # noqa: BLE001 - validation boundary
            exceptions.append(
                f"Failed to parse options for global options: {error.__class__.__name__}: {error}"
            )
        else:
            collect_rule_option_targets(global_options, "global options")

        try:
            per_file_enable = get_rule_pattern_table(configs, "per-file-enable")
        except Exception as error:  # noqa: BLE001 - validation boundary
            exceptions.append(
                f"Failed to parse per-file-enable: {error.__class__.__name__}: {error}"
            )
        else:
            collect_rule_patterns(per_file_enable, "per-file-enable")

        try:
            per_file_disable = get_rule_pattern_table(configs, "per-file-disable")
        except Exception as error:  # noqa: BLE001 - validation boundary
            exceptions.append(
                f"Failed to parse per-file-disable: {error.__class__.__name__}: {error}"
            )
        else:
            collect_rule_patterns(per_file_disable, "per-file-disable")

        inherit_ruff_files = data.get("inherit-ruff-files", False)
        if inherit_ruff_files and not isinstance(inherit_ruff_files, bool):
            exceptions.append(
                "Failed to parse inherit-ruff-files: ConfigError: 'inherit-ruff-files' must be a boolean"
            )
        elif inherit_ruff_files:
            try:
                _read_ruff_file_selection(configs)
            except Exception as error:  # noqa: BLE001 - validation boundary
                exceptions.append(
                    f"Failed to parse inherited Ruff file settings: {error.__class__.__name__}: {error}"
                )

        for override in data.get("overrides", []):
            if not isinstance(override, dict):
                exceptions.append(
                    "Failed to parse overrides: ConfigError: 'overrides' requires array of tables"
                )
                continue

            override_path = Path(override.get("path", path))
            collect_rule_selectors(
                override.get("enable", []),
                f"override enable: `{override_path}`",
            )
            collect_rule_selectors(
                override.get("disable", []),
                f"override disable: `{override_path}`",
            )

            try:
                override_options = get_options(configs, "options", data=override)
            except Exception as error:  # noqa: BLE001 - validation boundary
                exceptions.append(
                    f"Failed to parse options for override options: `{override_path}`: {error.__class__.__name__}: {error}"
                )
            else:
                collect_rule_option_targets(
                    override_options, f"override options: `{override_path}`"
                )

        registry = _build_rule_registry(
            [
                *[selector for _raw, selector, _context in selectors_to_validate],
                *[
                    selector
                    for _raw_rule_name, selector, _settings, _context in option_targets_to_validate
                ],
            ],
            root=root,
            enable_root_import=enable_root_import,
            strict=False,
            log_failures=False,
        )

        def resolve_rule_validation_error(
            raw_rule: str,
            selector: RuleSelector,
            context: str,
        ) -> str | None:
            try:
                _resolve_selector(selector, registry)
            except Exception as error:  # noqa: BLE001 - validation boundary
                return (
                    f"Failed to import rule `{raw_rule}` for {context}: "
                    f"{error.__class__.__name__}: {error}"
                )
            return None

        for raw_rule, selector, context in selectors_to_validate:
            if error := resolve_rule_validation_error(raw_rule, selector, context):
                exceptions.append(error)

        for raw_rule_name, selector, settings, context in option_targets_to_validate:
            try:
                resolution = _resolve_selector(selector, registry)
            except Exception as error:  # noqa: BLE001 - validation boundary
                exceptions.append(
                    f"Failed to validate options for `{raw_rule_name}` in {context}: {error.__class__.__name__}: {error}"
                )
                continue

            if len(resolution.rules) != 1:
                exceptions.append(
                    f"Failed to validate options for `{raw_rule_name}` in {context}: ConfigError: rule target must resolve to exactly one rule class"
                )
                continue

            try:
                rule = resolution.rules[0]()
                rule.configure(settings)
            except Exception as error:  # noqa: BLE001 - validation boundary
                exceptions.append(
                    f"Failed to validate options for `{raw_rule_name}` in {context}: {error.__class__.__name__}: {error}"
                )

    except Exception as error:  # noqa: BLE001 - validation boundary
        exceptions.append(f"Invalid config: {error.__class__.__name__}: {error}")

    return exceptions
