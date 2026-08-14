from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
import sys
from collections import defaultdict
from collections.abc import Collection, Iterable, Iterator, Mapping
from contextlib import ExitStack, contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from functools import cache
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from typing import TypeVar

from packaging.specifiers import SpecifierSet

from rattle.config.models import Config
from rattle.rule import LintRule
from rattle.selectors import QualifiedRule, RuleSelector
from rattle.util import append_sys_path

T = TypeVar("T")
BUILTIN_RULE_COLLECTIONS = {
    "blank-lines": "rattle.rules.blank_lines",
    "exports": "rattle.rules.exports",
    "modernization": "rattle.rules.modernization",
    "legacy": "rattle.rules.legacy",
    "policy": "rattle.rules.policy",
    "style": "rattle.rules.style",
    "typing": "rattle.rules.typing",
}
BUILTIN_RULE_COLLECTION_MODULES = tuple(BUILTIN_RULE_COLLECTIONS.values())
RATTLE_LOCAL_MODULE = "rattle.local"
LOG = logging.getLogger(__name__)
_logged_rule_load_failures: set[tuple[Path, Path | None, str, str, str]] = set()
_rule_plan_cache: dict[tuple[object, ...], tuple[RulePlanEntry, ...]] = {}


class CollectionError(RuntimeError):
    def __init__(self, msg: str, rule: RuleSelector) -> None:
        super().__init__(msg)
        self.message = msg
        self.rule = rule

    def __reduce__(self) -> tuple[type[CollectionError], tuple[str, RuleSelector]]:
        return type(self), (self.message, self.rule)


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
                QualifiedRule(rule_type.__module__, rule_type.name),
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
        except CollectionError as e:
            _log_rule_load_failure_once(
                selector,
                e,
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
        name = rule_type.name
        rules = self.rules_by_name.setdefault(name, [])
        if rule_type not in rules:
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
                    LOG.warning("don't know what to do with {value!r}")
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
    rules.update((rule_type.name, rule_type) for _, rule_type in members)

    if hasattr(module, "__path__"):
        for _, module_name, is_pkg in pkgutil.iter_modules(module.__path__):
            if not is_pkg:  # do not recurse to sub-packages
                mod = importlib.import_module(f".{module_name}", module.__name__)
                rules.update(walk_module(mod))

    return rules


def _rule_key_for_type(rule_type: type[LintRule]) -> str:
    return f"{rule_type.__module__}:{rule_type.name}"


@cache
def _builtin_rule_types() -> tuple[type[LintRule], ...]:
    builtin_rules: list[type[LintRule]] = []
    for module_name in BUILTIN_RULE_COLLECTION_MODULES:
        builtin_rules.extend(find_rules(QualifiedRule(module_name)))
    return tuple(builtin_rules)


def _option_key_aliases_for_rule_type(rule_type: type[LintRule]) -> set[str]:
    module_parts = rule_type.__module__.split(".")
    aliases: set[str] = set()
    name = rule_type.name
    for idx in range(len(module_parts), 0, -1):
        module_name = ".".join(module_parts[:idx])
        aliases.add(f"{module_name}:{name}")

    local_prefix = f"{RATTLE_LOCAL_MODULE}."
    if rule_type.__module__.startswith(local_prefix):
        local_module = rule_type.__module__.removeprefix(local_prefix)
        local_parts = local_module.split(".")
        for idx in range(len(local_parts), 0, -1):
            module_name = ".".join(local_parts[:idx])
            aliases.add(f".{module_name}:{name}")

    if rule_type in set(_builtin_rule_types()):
        aliases.add(name)
        for module_name in BUILTIN_RULE_COLLECTION_MODULES:
            if rule_type in set(find_rules(QualifiedRule(module_name))):
                aliases.add(f"{module_name}:{name}")

    return aliases


def _option_key_aliases_for_rule_types(
    rule_types: Collection[type[LintRule]],
) -> dict[str, type[LintRule]]:
    aliases: dict[str, type[LintRule]] = {}
    rules_by_name: dict[str, list[type[LintRule]]] = defaultdict(list)

    for rule_type in rule_types:
        for alias in _option_key_aliases_for_rule_type(rule_type):
            aliases[alias] = rule_type
        rules_by_name[rule_type.name].append(rule_type)

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
        "",
    )
    if key in _logged_rule_load_failures:
        return

    _logged_rule_load_failures.add(key)
    LOG.warning(
        "Failed to load rules '%s': %s",
        selector,
        error.__class__.__name__,
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
            except CollectionError as e:
                if strict:
                    raise
                registry.import_errors[selector] = e
                if log_failures:
                    _log_rule_load_failure_once(
                        selector,
                        e,
                        root=root,
                        enable_root_import=enable_root_import,
                    )
                rules = ()

            registry.imported_rules[selector] = rules
            for rule_type in rules:
                registry.register(rule_type)

    return registry


def resolve_rule_type(config: Config, selector: RuleSelector) -> type[LintRule]:
    """Resolve one rule selector against built-ins and configured/imported rules."""
    registry = _build_rule_registry(
        (*config.rule_imports, *config.enable, *config.disable, selector),
        root=config.root,
        enable_root_import=config.enable_root_import,
        strict=False,
    )
    resolution = registry.resolve(selector)
    rules = resolution.rules
    if resolution.concrete and len(rules) == 1:
        return rules[0]

    if not rules:
        raise CollectionError(f"could not find rule {selector}", selector)

    options = ", ".join(
        _rule_key_for_type(rule_type) for rule_type in sorted(rules, key=_rule_key_for_type)
    )
    raise CollectionError(
        f"rule selector {selector!s} matched {len(rules)} rules; use one of: {options}",
        selector,
    )


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
        (*config.rule_imports, *config.enable, *config.disable),
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
    for option_key, settings in config.options.items():
        rule_type = rules_by_key.get(option_key)
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
        tuple(str(selector) for selector in config.rule_imports),
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


__all__ = [
    "BUILTIN_RULE_COLLECTIONS",
    "CollectionError",
    "RulePlanEntry",
    "RuleRegistry",
    "collect_rule_types",
    "collect_rules",
    "find_rules",
    "materialize_rule_plan",
    "materialize_rules",
    "resolve_rule_plan",
    "resolve_rule_settings",
    "resolve_rule_type",
    "walk_module",
]
