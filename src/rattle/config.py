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
from collections import defaultdict
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from contextlib import ExitStack, contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from functools import cache
from importlib.machinery import ModuleSpec
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import (
    Any,
    cast,
)

from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

from .format import FORMAT_STYLES
from .ftypes import (
    Config,
    Options,
    OutputFormat,
    QualifiedRule,
    QualifiedRuleRegex,
    RawConfig,
    RuleNameSelector,
    RuleNameSelectorRegex,
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
BUILTIN_RULE_PACKS = {
    "blank_lines": "rattle.rules.blank_lines",
    "fixit": "rattle.rules.fixit",
    "fixit_extra": "rattle.rules.fixit_extra",
}
BUILTIN_RULE_MODULES = tuple(BUILTIN_RULE_PACKS.values())


log = logging.getLogger(__name__)
GLOB_META_CHARS = frozenset("*?[")
_logged_rule_load_failures: set[tuple[Path, Path | None, str, str, str]] = set()
_rule_plan_cache: dict[tuple[object, ...], tuple["RulePlanEntry", ...]] = {}


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


@dataclass(frozen=True)
class RulePlanEntry:
    rule_type: type[LintRule]
    settings: Mapping[str, object]


@dataclass
class RuleRegistry:
    imported_rules: dict[QualifiedRule, tuple[type[LintRule], ...]] = field(default_factory=dict)
    import_errors: dict[QualifiedRule, Exception] = field(default_factory=dict)
    rules_by_key: dict[str, type[LintRule]] = field(default_factory=dict)
    rules_by_name: dict[str, list[type[LintRule]]] = field(default_factory=dict)

    def register(self, rule_type: type[LintRule]) -> None:
        key = _rule_key_for_type(rule_type)
        existing = self.rules_by_key.get(key)
        if existing is None:
            self.rules_by_key[key] = rule_type
        elif existing is not rule_type:
            raise CollectionError(
                f"duplicate rule registration for {key}",
                QualifiedRule(rule_type.__module__, rule_type.__name__),
            )

        self._register_name(rule_type)

    def resolve(self, selector: RuleSelector) -> RuleResolution:
        if isinstance(selector, QualifiedRule):
            if error := self.import_errors.get(selector):
                raise error
            rules = self.imported_rules.get(selector, ())
            if selector.name is not None and not rules:
                raise CollectionError(f"could not find rule {selector}", selector)
            return RuleResolution(selector, rules, concrete=selector.name is not None)

        if rules := self.rules_by_name.get(selector.value):
            if len(rules) == 1:
                return RuleResolution(selector, (rules[0],), concrete=True)
            options = ", ".join(
                _rule_key_for_type(rule_type) for rule_type in sorted(rules, key=_rule_key_for_type)
            )
            raise CollectionError(
                f"ambiguous rule name {selector.value!r}; use one of: {options}",
                selector,
            )

        raise CollectionError(f"could not find rule {selector}", selector)

    def resolve_or_log(
        self,
        selector: RuleSelector,
        *,
        root: Path,
        enable_root_import: bool | Path,
    ) -> RuleResolution | None:
        try:
            return self.resolve(selector)
        except Exception as error:  # noqa: BLE001 - import boundary
            _log_rule_load_failure_once(
                selector,
                error,
                root=root,
                enable_root_import=enable_root_import,
            )
            return None

    def iter_resolved(
        self,
        selectors: Iterable[RuleSelector],
        *,
        root: Path,
        enable_root_import: bool | Path,
    ) -> Iterator[RuleResolution]:
        for selector in selectors:
            resolution = self.resolve_or_log(
                selector,
                root=root,
                enable_root_import=enable_root_import,
            )
            if resolution is not None:
                yield resolution

    def _register_name(self, rule_type: type[LintRule]) -> None:
        for name in _rule_name_aliases(rule_type.__name__):
            rules = self.rules_by_name.setdefault(name, [])
            if rule_type in rules:
                continue
            rules.append(rule_type)


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

    if getattr(module, "__rattle_collect__", True) is False:
        return rules

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


def _rule_name_aliases(name: str) -> set[str]:
    aliases = {name}
    if name.endswith("Rule"):
        aliases.add(name.removesuffix("Rule"))
    else:
        aliases.add(f"{name}Rule")
    return aliases


@cache
def _builtin_rule_types() -> tuple[type[LintRule], ...]:
    builtin_rules: list[type[LintRule]] = []
    for module_name in BUILTIN_RULE_MODULES:
        builtin_rules.extend(find_rules(QualifiedRule(module_name)))
    return tuple(builtin_rules)


def _option_key_aliases_for_rule_type(rule_type: type[LintRule]) -> set[str]:
    module_parts = rule_type.__module__.split(".")
    aliases: set[str] = set()
    rule_names = _rule_name_aliases(rule_type.__name__)
    for idx in range(len(module_parts), 0, -1):
        module_name = ".".join(module_parts[:idx])
        aliases.update(f"{module_name}:{rule_name}" for rule_name in rule_names)

    local_prefix = f"{RATTLE_LOCAL_MODULE}."
    if rule_type.__module__.startswith(local_prefix):
        local_module = rule_type.__module__.removeprefix(local_prefix)
        local_parts = local_module.split(".")
        for idx in range(len(local_parts), 0, -1):
            module_name = ".".join(local_parts[:idx])
            aliases.update(f".{module_name}:{rule_name}" for rule_name in rule_names)

    if rule_type in set(_builtin_rule_types()):
        aliases.update(rule_names)
        for module_name in BUILTIN_RULE_MODULES:
            if rule_type in set(find_rules(QualifiedRule(module_name))):
                aliases.update(f"{module_name}:{rule_name}" for rule_name in rule_names)

    return aliases


def _option_key_aliases_for_rule_types(
    rule_types: Collection[type[LintRule]],
) -> dict[str, type[LintRule]]:
    aliases: dict[str, type[LintRule]] = {}
    rules_by_name: dict[str, list[type[LintRule]]] = defaultdict(list)

    for rule_type in rule_types:
        for alias in _option_key_aliases_for_rule_type(rule_type):
            aliases[alias] = rule_type
        for rule_name in _rule_name_aliases(rule_type.__name__):
            rules_by_name[rule_name].append(rule_type)

    for name, named_rules in rules_by_name.items():
        if len(named_rules) == 1:
            aliases[name] = named_rules[0]

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
        registry.register(rule_type)

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
                registry.register(rule_type)

    return registry


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

    for resolution in registry.iter_resolved(
        config.enable,
        root=config.root,
        enable_root_import=config.enable_root_import,
    ):
        if resolution.concrete:
            named_enables |= set(resolution.rules)
        all_rules |= set(resolution.rules)

    for resolution in registry.iter_resolved(
        config.disable,
        root=config.root,
        enable_root_import=config.enable_root_import,
    ):
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
    rules_by_key = _option_key_aliases_for_rule_types(rule_types)

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


def materialize_rule_plan(plan: Collection[RulePlanEntry]) -> list[LintRule]:
    materialized_rules: list[LintRule] = []
    for entry in plan:
        rule = entry.rule_type()
        rule.configure(deepcopy(dict(entry.settings)))
        materialized_rules.append(rule)

    return materialized_rules


def _config_rule_plan_key(config: Config) -> tuple[object, ...]:
    return (
        config.root,
        config.enable_root_import,
        tuple(str(selector) for selector in config.enable),
        tuple(str(selector) for selector in config.disable),
        (
            config.tags.include,
            config.tags.exclude,
        ),
        str(config.python_version) if config.python_version is not None else None,
        tuple(
            sorted(
                (
                    rule_name,
                    tuple(
                        sorted(
                            (option_name, repr(option_value))
                            for option_name, option_value in settings.items()
                        )
                    ),
                )
                for rule_name, settings in config.options.items()
            )
        ),
    )


def resolve_rule_plan(config: Config) -> tuple[RulePlanEntry, ...]:
    key = _config_rule_plan_key(config)
    plan = _rule_plan_cache.get(key)
    if plan is not None:
        return plan

    rule_types = collect_rule_types(config)
    resolved_settings = resolve_rule_settings(config, rule_types)
    plan = tuple(
        RulePlanEntry(rule_type, deepcopy(resolved_settings.get(rule_type, {})))
        for rule_type in sorted(rule_types, key=_rule_key_for_type)
    )
    _rule_plan_cache[key] = plan
    return plan


def collect_rules(
    config: Config,
    *,
    # out-param to capture reasons when disabling rules for debugging
    debug_reasons: dict[type[LintRule], str] | None = None,
) -> Collection[LintRule]:
    """Import, configure, and return rules specified by `enables` and `disables`."""
    if debug_reasons is None:
        return materialize_rule_plan(resolve_rule_plan(config))

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
    if not path.is_dir():
        path = path.parent

    root = root.resolve() if root is not None else Path(path.anchor)
    path = path.resolve()
    return list(
        _locate_configs_for_directory(
            path,
            root,
            _directory_fingerprints(path, root),
        )
    )


@cache
def _locate_configs_for_directory(
    path: Path,
    root: Path,
    directory_fingerprints: tuple[tuple[str, int, int], ...],
) -> tuple[Path, ...]:
    del directory_fingerprints
    path.relative_to(root)  # enforce path being inside root
    results: list[Path] = []
    while True:
        candidates = (path / filename for filename in RATTLE_CONFIG_FILENAMES)
        results.extend(candidate for candidate in candidates if candidate.is_file())

        if path in (root, path.parent):
            break

        path = path.parent

    return tuple(results)


def _directory_fingerprints(path: Path, root: Path) -> tuple[tuple[str, int, int], ...]:
    path.relative_to(root)  # enforce path being inside root
    fingerprints: list[tuple[str, int, int]] = []
    while True:
        try:
            stat = path.stat()
        except OSError:
            fingerprints.append((path.as_posix(), -1, -1))
        else:
            fingerprints.append((path.as_posix(), stat.st_mtime_ns, stat.st_size))

        if path in (root, path.parent):
            break
        path = path.parent

    return tuple(fingerprints)


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
        try:
            stat = path.stat()
        except OSError as error:
            raise ConfigError(f"Failed to stat configuration file {path}") from error
        data = _read_pyproject_data(path, stat.st_mtime_ns, stat.st_size)
        tool_data = data.get("tool", {})
        if not isinstance(tool_data, Mapping):
            continue
        rattle_data = tool_data.get("rattle", {})

        if rattle_data:
            if not isinstance(rattle_data, dict):
                raise ConfigError("'tool.rattle' must be mapping of values")
            config = RawConfig(path=path, data=deepcopy(rattle_data))
            configs.append(config)

            if config.data.get("root", False):
                break

    return configs


@cache
def _read_pyproject_data(path: Path, mtime_ns: int, size: int) -> dict[str, Any]:
    del mtime_ns, size
    content = path.read_text()
    data = tomllib.loads(content)
    if not isinstance(data, dict):
        return {}
    return data


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
    for item in cast(Sequence[object], value):
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


def _path_matches_current_dir_glob(path: Path, pattern: str) -> bool:
    relative_path = _relative_path_str(path, Path.cwd())
    if relative_path is None:
        relative_path = path.as_posix()
    return _path_matches_glob(relative_path, pattern)


def _excluded_by_options_without_configs(path: Path, options: Options, explicit_path: bool) -> bool:
    patterns = options.exclude or options.extend_exclude
    return bool(
        patterns
        and any(_path_matches_current_dir_glob(path, pattern) for pattern in patterns)
        and (options.exclude or not explicit_path)
    )


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
                    f"{option_name!r} must be a TOML scalar, array, or table, got {type(value)}",
                    config=config,
                )

            rule_configs[rule_name][option_name] = list(value) if is_sequence(value) else value

    return rule_configs


def parse_rule(rule: str, root: Path, config: RawConfig | None = None) -> RuleSelector:
    """Given a raw rule string, parse and return a rule selector object."""
    if module := BUILTIN_RULE_PACKS.get(rule):
        return QualifiedRule(module)

    if "." not in rule and ":" not in rule and RuleNameSelectorRegex.fullmatch(rule):
        return RuleNameSelector(rule)

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

    return selector


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

        self._process_subpath(
            self.config.path.parent,
            enable=get_sequence(self.config, "enable"),
            disable=get_sequence(self.config, "disable"),
            options=get_options(self.config, "options"),
            python_version=self.config.data.pop("python-version", None),
            formatter=self.config.data.pop("formatter", None),
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
            log.warning("unknown configuration option %r", key)

    def _apply_root_import(self, data: dict[str, Any]) -> None:
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

    def _apply_output_options(self, data: dict[str, Any]) -> None:
        if value := data.pop("output-format", ""):
            try:
                self.output_format = OutputFormat(value)
            except ValueError as e:
                raise ConfigError(
                    f"output-format: unknown value {value!r}", config=self.config
                ) from e

        if value := data.pop("output-template", ""):
            self.output_template = value

    def _update_target_python_version(self, python_version: str | None) -> None:
        if python_version is None:
            return
        if not isinstance(python_version, str):
            raise ConfigError("'python-version' must be a string", config=self.config)
        if python_version:
            try:
                self.target_python_version = Version(python_version)
            except InvalidVersion as error:
                raise ConfigError(
                    f"'python-version' {python_version!r} is not valid",
                    config=self.config,
                ) from error
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
        for override in get_sequence(self.config, "overrides"):
            if not isinstance(override, dict):
                raise ConfigError("'overrides' requires array of tables", config=self.config)

            subpath = override.get("path", None)
            if not subpath:
                raise ConfigError("'overrides' table requires 'path' value", config=self.config)

            self._process_subpath(
                self.config.path.parent / subpath,
                enable=get_sequence(self.config, "enable", data=override),
                disable=get_sequence(self.config, "disable", data=override),
                options=get_options(self.config, "options", data=override),
                python_version=override.pop("python-version", None),
                formatter=override.pop("formatter", None),
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
        if not raw_configs and _excluded_by_options_without_configs(path, options, explicit_path):
            config.excluded = True

        if options.tags:
            config.tags = options.tags

        if options.rules:
            config.enable = list(options.rules)
            config.disable = []

        if options.output_format:
            config.output_format = options.output_format

        if options.output_template:
            config.output_template = options.output_template

        if options.no_format:
            config.formatter = None

    return config


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
    data: dict[str, Any] = field(init=False)
    enable_root_import: bool | Path = field(init=False)

    def validate(self) -> list[str]:
        try:
            self.root = self.path.parent
            self.config = read_configs([self.path])[0]
            self.data = self.config.data
            self.enable_root_import = self._enable_root_import()

            self._collect_global_rules()
            self._collect_global_options()
            self._collect_per_file_rules()
            self._validate_file_selection()
            self._validate_inherited_ruff_files()
            self._collect_overrides()
            self._resolve_collected_rules()
        except Exception as error:  # noqa: BLE001 - validation boundary
            self.exceptions.append(f"Invalid config: {error.__class__.__name__}: {error}")

        return self.exceptions

    def _enable_root_import(self) -> bool | Path:
        raw_enable_root_import = self.data.get("enable-root-import", False)
        if not raw_enable_root_import:
            return False
        return Path(raw_enable_root_import) if isinstance(raw_enable_root_import, str) else True

    def _collect_global_rules(self) -> None:
        self._collect_rule_selectors(self.data.get("enable", []), "global enable")
        self._collect_rule_selectors(self.data.get("disable", []), "global disable")

    def _collect_global_options(self) -> None:
        try:
            global_options = get_options(self.config, "options")
        except Exception as error:  # noqa: BLE001 - validation boundary
            self.exceptions.append(
                f"Failed to parse options for global options: {error.__class__.__name__}: {error}"
            )
        else:
            self._collect_rule_option_targets(global_options, "global options")

    def _collect_per_file_rules(self) -> None:
        try:
            per_file_enable = get_rule_pattern_table(self.config, "per-file-enable")
        except Exception as error:  # noqa: BLE001 - validation boundary
            self.exceptions.append(
                f"Failed to parse per-file-enable: {error.__class__.__name__}: {error}"
            )
        else:
            self._collect_rule_patterns(per_file_enable, "per-file-enable")

        try:
            per_file_disable = get_rule_pattern_table(self.config, "per-file-disable")
        except Exception as error:  # noqa: BLE001 - validation boundary
            self.exceptions.append(
                f"Failed to parse per-file-disable: {error.__class__.__name__}: {error}"
            )
        else:
            self._collect_rule_patterns(per_file_disable, "per-file-disable")

    def _validate_file_selection(self) -> None:
        try:
            _get_string_sequence_from_mapping(self.config, self.data, "exclude")
        except Exception as error:  # noqa: BLE001 - validation boundary
            self.exceptions.append(f"Failed to parse exclude: {error.__class__.__name__}: {error}")

    def _validate_inherited_ruff_files(self) -> None:
        inherit_ruff_files = self.data.get("inherit-ruff-files", False)
        if inherit_ruff_files and not isinstance(inherit_ruff_files, bool):
            self.exceptions.append(
                "Failed to parse inherit-ruff-files: ConfigError: 'inherit-ruff-files' must be a boolean"
            )
        elif inherit_ruff_files:
            try:
                _read_ruff_file_selection(self.config)
            except Exception as error:  # noqa: BLE001 - validation boundary
                self.exceptions.append(
                    f"Failed to parse inherited Ruff file settings: {error.__class__.__name__}: {error}"
                )

    def _collect_overrides(self) -> None:
        for override in self.data.get("overrides", []):
            if not isinstance(override, dict):
                self.exceptions.append(
                    "Failed to parse overrides: ConfigError: 'overrides' requires array of tables"
                )
                continue

            override_path = Path(override.get("path", self.path))
            self._collect_rule_selectors(
                override.get("enable", []),
                f"override enable: `{override_path}`",
            )
            self._collect_rule_selectors(
                override.get("disable", []),
                f"override disable: `{override_path}`",
            )

            try:
                override_options = get_options(self.config, "options", data=override)
            except Exception as error:  # noqa: BLE001 - validation boundary
                self.exceptions.append(
                    f"Failed to parse options for override options: `{override_path}`: {error.__class__.__name__}: {error}"
                )
            else:
                self._collect_rule_option_targets(
                    override_options, f"override options: `{override_path}`"
                )

    def _collect_rule_selectors(self, rules: Sequence[str], context: str) -> None:
        for rule in rules:
            try:
                selector = parse_rule(rule, self.root, self.config)
            except Exception as error:  # noqa: BLE001 - validation boundary
                self.exceptions.append(
                    f"Failed to parse rule `{rule}` for {context}: {error.__class__.__name__}: {error}"
                )
                continue
            self.selectors_to_validate.append((rule, selector, context))

    def _collect_rule_option_targets(
        self,
        rule_options: RuleOptionsTable,
        context: str,
    ) -> None:
        for rule_name, settings in rule_options.items():
            try:
                selector = parse_exact_rule_target(rule_name, self.root, self.config)
            except Exception as error:  # noqa: BLE001 - validation boundary
                self.exceptions.append(
                    f"Failed to validate options for `{rule_name}` in {context}: {error.__class__.__name__}: {error}"
                )
                continue
            self.option_targets_to_validate.append((rule_name, selector, settings, context))

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
        except Exception as error:  # noqa: BLE001 - validation boundary
            return (
                f"Failed to import rule `{raw_rule}` for {context}: "
                f"{error.__class__.__name__}: {error}"
            )
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
        except Exception as error:  # noqa: BLE001 - validation boundary
            self.exceptions.append(
                f"Failed to validate options for `{raw_rule_name}` in {context}: {error.__class__.__name__}: {error}"
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
        except Exception as error:  # noqa: BLE001 - validation boundary
            self.exceptions.append(
                f"Failed to validate options for `{raw_rule_name}` in {context}: {error.__class__.__name__}: {error}"
            )


def validate_config(path: Path) -> list[str]:
    """
    Validate the config provided. The provided path is expected to be a valid toml
    config file. Any exception found while parsing or importing will be added to a list
    of exceptions that are returned.
    """
    return ConfigValidator(path).validate()


__all__ = [
    "BUILTIN_RULE_MODULES",
    "BUILTIN_RULE_PACKS",
    "GLOB_META_CHARS",
    "RATTLE_CONFIG_FILENAMES",
    "RATTLE_LOCAL_MODULE",
    "CollectionError",
    "ConfigError",
    "ConfigMerger",
    "RuleRegistry",
    "RuleResolution",
    "collect_rule_types",
    "collect_rules",
    "find_rules",
    "generate_config",
    "get_options",
    "get_rule_pattern_table",
    "get_sequence",
    "is_rule",
    "local_rule_loader",
    "locate_configs",
    "materialize_rules",
    "parse_exact_rule_target",
    "parse_rule",
    "read_configs",
    "resolve_rule_settings",
    "validate_config",
    "walk_module",
]
