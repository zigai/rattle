# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import logging
import time
from collections import defaultdict
from collections.abc import Callable, Collection, Generator, Iterator, Mapping
from contextlib import ExitStack, contextmanager
from dataclasses import replace
from functools import partial
from pathlib import Path
from types import MappingProxyType

from libcst import CSTNode, CSTTransformer, CSTVisitor, Module, parse_module
from libcst._metadata_dependent import LazyValue
from libcst.metadata import (
    BatchableMetadataProvider,
    FilePathProvider,
    FullRepoManager,
    MetadataWrapper,
    ParentNodeProvider,
    PositionProvider,
    ProviderT,
    QualifiedNameProvider,
    Scope,
    ScopeProvider,
)
from moreorless import unified_diff

from rattle.ast import AstParseError
from rattle.config.models import Config
from rattle.diagnostics import CodeRange, FileContent, LintViolation, NodeReplacement
from rattle.errors import RattleRuleExecutionError
from rattle.rule import LintRule, VisitorMethod

Metrics = dict[str, int]
MetricsHook = Callable[[Metrics], None]

LOG = logging.getLogger(__name__)
_RULE_SOURCE_FILTERS: dict[type[LintRule], tuple[bytes, ...] | None] = {}
_MODULE_ONLY_PROVIDERS: dict[type[BatchableMetadataProvider[object]], bool] = {}

_VISITOR_SOURCE_PATTERNS = {
    "AnnAssign": (b":",),
    "Assign": (b"=",),
    "AssignTarget": (b"=",),
    "Call": (b"(",),
    "ClassDef": (b"class",),
    "FunctionDef": (b"def",),
    "Import": (b"import",),
    "ImportAlias": (b"import",),
    "ImportFrom": (b"from",),
}


def _ensure_parent_metadata(rule: LintRule) -> None:
    if ParentNodeProvider in rule.get_inherited_dependencies():
        return

    dependencies: Collection[ProviderT] = frozenset(
        (*type(rule).get_inherited_dependencies(), ParentNodeProvider)
    )

    def get_inherited_dependencies() -> Collection[ProviderT]:
        return dependencies

    rule.get_inherited_dependencies = get_inherited_dependencies


def diff_violation(path: Path, module: Module, violation: LintViolation) -> str:
    """Generate string diff representation of a violation."""
    orig = module.code
    replacement = violation.replacement
    assert replacement is not None

    class ReplacementTransformer(CSTTransformer):
        def on_visit(self, node: CSTNode) -> bool:
            return node is not violation.node

        def on_leave(
            self, original_node: CSTNode, updated_node: CSTNode
        ) -> NodeReplacement[CSTNode]:
            if original_node is violation.node:
                return replacement
            return updated_node

    mod = module.visit(ReplacementTransformer())
    assert isinstance(mod, Module)
    change = mod.code

    return unified_diff(
        orig,
        change,
        path.name,
        n=1,
    )


def diff_module(path: Path, before: Module, after: Module) -> str:
    """Generate string diff representation between two module versions."""
    return unified_diff(
        before.code,
        after.code,
        path.name,
        n=1,
    )


def _resolve_violation_position(
    position_metadata: Mapping[CSTNode, CodeRange],
    violation: LintViolation,
) -> LintViolation:
    if violation.range is not None:
        return violation

    position = position_metadata.get(violation.position_node or violation.node)
    if position is None:
        raise ValueError(f"Unable to determine violation position for {violation.rule_name}")

    return replace(violation, range=position)


def _gather_providers(providers: Collection[ProviderT]) -> set[ProviderT]:
    gathered: set[ProviderT] = set()
    pending = list(providers)
    while pending:
        provider = pending.pop()
        if provider not in gathered:
            gathered.add(provider)
            pending.extend(provider.METADATA_DEPENDENCIES)
    return gathered


class _NodeCollector(CSTVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.nodes: list[CSTNode] = []
        self.parents: dict[CSTNode, CSTNode] = {}
        self._children: list[list[CSTNode]] = [[]]

    def on_visit(self, node: CSTNode) -> bool:
        self.nodes.append(node)
        self._children[-1].append(node)
        self._children.append([])
        return True

    def on_leave(self, original_node: CSTNode) -> None:
        for child in self._children.pop():
            self.parents[child] = original_node

    def on_visit_attribute(self, node: CSTNode, attribute: str) -> None:
        pass

    def on_leave_attribute(self, original_node: CSTNode, attribute: str) -> None:
        pass


def _qualified_name_metadata(
    nodes: Collection[CSTNode],
    scopes: Mapping[CSTNode, object],
) -> dict[CSTNode, object]:
    computed: dict[CSTNode, object] = {}
    for node in nodes:
        scope = scopes.get(node)
        if isinstance(scope, LazyValue):
            scope = scope()
        if isinstance(scope, Scope):
            computed[node] = LazyValue(partial(scope.get_qualified_names_for, node))
        else:
            computed[node] = set()
    return computed


class _BatchedRuleVisitor(CSTVisitor):
    def __init__(self, rules: Collection[LintRule]) -> None:
        super().__init__()
        self._methods: dict[str, list[VisitorMethod]] = {}
        for rule in rules:
            for name, method in rule.get_visitors().items():
                self._methods.setdefault(name, []).append(method)
        self._visit_methods: dict[type[CSTNode], list[VisitorMethod]] = {}
        self._leave_methods: dict[type[CSTNode], list[VisitorMethod]] = {}
        self._attribute_methods: dict[tuple[str, type[CSTNode], str], list[VisitorMethod]] = {}
        self._has_attribute_methods = any("_" in name.partition("_")[2] for name in self._methods)

    def on_visit(self, node: CSTNode) -> bool:
        node_type = type(node)
        methods = self._visit_methods.get(node_type)
        if methods is None:
            methods = self._methods.get(f"visit_{node_type.__name__}", [])
            self._visit_methods[node_type] = methods
        for method in methods:
            method(node)
        return True

    def on_leave(self, original_node: CSTNode) -> None:
        node_type = type(original_node)
        methods = self._leave_methods.get(node_type)
        if methods is None:
            methods = self._methods.get(f"leave_{node_type.__name__}", [])
            self._leave_methods[node_type] = methods
        for method in methods:
            method(original_node)

    def on_visit_attribute(self, node: CSTNode, attribute: str) -> None:
        if self._has_attribute_methods:
            self._call_attribute_methods("visit", node, attribute)

    def on_leave_attribute(self, original_node: CSTNode, attribute: str) -> None:
        if self._has_attribute_methods:
            self._call_attribute_methods("leave", original_node, attribute)

    def _call_attribute_methods(self, prefix: str, node: CSTNode, attribute: str) -> None:
        key = (prefix, type(node), attribute)
        methods = self._attribute_methods.get(key)
        if methods is None:
            methods = self._methods.get(f"{prefix}_{type(node).__name__}_{attribute}", [])
            self._attribute_methods[key] = methods
        for method in methods:
            method(node)


def _is_module_only_provider(provider: BatchableMetadataProvider[object]) -> bool:
    provider_type = type(provider)
    if provider_type not in _MODULE_ONLY_PROVIDERS:
        _MODULE_ONLY_PROVIDERS[provider_type] = provider.get_visitors().keys() == {"visit_Module"}
    return _MODULE_ONLY_PROVIDERS[provider_type]


def _resolve_metadata(
    wrapper: MetadataWrapper,
    providers: Collection[ProviderT],
    cache: Mapping[ProviderT, object],
) -> None:
    resolved = wrapper._metadata
    remaining = _gather_providers(providers) - resolved.keys()
    collector: _NodeCollector | None = None
    while remaining:
        ready = {
            provider
            for provider in remaining
            if resolved.keys() >= set(provider.METADATA_DEPENDENCIES)
        }
        if not ready:
            wrapper.resolve_many(remaining)
            return

        batched: set[ProviderT] = set()
        for provider_type in ready:
            if provider_type is ParentNodeProvider or provider_type is QualifiedNameProvider:
                if collector is None:
                    collector = _NodeCollector()
                    wrapper.module.visit(collector)
                resolved[provider_type] = MappingProxyType(
                    collector.parents
                    if provider_type is ParentNodeProvider
                    else _qualified_name_metadata(collector.nodes, resolved[ScopeProvider])
                )
                continue
            provider = (
                provider_type(cache.get(provider_type))
                if provider_type.gen_cache
                else provider_type()
            )
            if not isinstance(provider, BatchableMetadataProvider):
                resolved[provider_type] = provider._gen(wrapper)
                continue
            if not _is_module_only_provider(provider):
                batched.add(provider_type)
                continue
            with provider.resolve(wrapper):
                provider.visit_Module(wrapper.module)
            resolved[provider_type] = MappingProxyType(dict(provider._computed))

        if batched:
            wrapper.resolve_many(batched)
        remaining -= ready


def _rule_source_filter(rule_type: type[LintRule]) -> tuple[bytes, ...] | None:
    if rule_type in _RULE_SOURCE_FILTERS:
        return _RULE_SOURCE_FILTERS[rule_type]

    patterns: list[bytes] = []
    for visitor_name in rule_type._visitor_names():
        prefix, _, node_name = visitor_name.partition("_")
        if prefix not in {"visit", "leave"}:
            _RULE_SOURCE_FILTERS[rule_type] = None
            return None

        if node_name == "Module":
            _RULE_SOURCE_FILTERS[rule_type] = None
            return None

        visitor_patterns = _VISITOR_SOURCE_PATTERNS.get(node_name)
        if visitor_patterns is None:
            _RULE_SOURCE_FILTERS[rule_type] = None
            return None
        patterns.extend(visitor_patterns)

    result = tuple(frozenset(patterns))
    _RULE_SOURCE_FILTERS[rule_type] = result
    return result


def _rule_may_match_source(rule: LintRule, source: FileContent) -> bool:
    source_filter = _rule_source_filter(type(rule))
    if not source_filter:
        return True

    return any(pattern in source for pattern in source_filter)


class LintRunner:
    def __init__(self, path: Path, source: FileContent) -> None:
        self.path = path
        self.source = source
        self._module: Module | None = None
        self.metrics: Metrics = defaultdict(lambda: 0)

    @property
    def module(self) -> Module:
        if self._module is None:
            self._module = parse_module(self.source)

        return self._module

    def collect_violations(  # noqa: C901 - lint runner orchestration
        self,
        rules: Collection[LintRule],
        config: Config,
        metrics_hook: MetricsHook | None = None,
        *,
        include_diff: bool = False,
    ) -> Generator[LintViolation, None, int]:
        """Run multiple `LintRule`s and yield any lint violations.

        The optional `metrics_hook` parameter will be called (if provided) after all
        lint rules have finished running, passing in a dictionary of
        ``RuleName.visit_function_name`` -> ``duration in microseconds``.
        """

        @contextmanager
        def visit_hook(name: str) -> Iterator[None]:
            start = time.perf_counter()
            try:
                yield
            finally:
                duration_us = int(1000 * 1000 * (time.perf_counter() - start))
                LOG.debug("PERF: %s took %s µs", name, duration_us)
                self.metrics[f"Duration.{name}"] += duration_us

        metadata_cache: dict[ProviderT, object] = {}
        needs_repo_manager: set[ProviderT] = set()
        metadata_rules: list[LintRule] = []
        plain_rules: list[LintRule] = []
        active_rules: list[LintRule] = []
        resolved_config_path: Path | None = None

        lint_ignore_enabled = b"rattle:" in self.source

        visit_timing_enabled = metrics_hook is not None or LOG.isEnabledFor(logging.DEBUG)

        for rule in rules:
            rule._violations = []
            if rule.SETTINGS and not rule.settings:
                rule.configure({})
            if not rule.should_lint_file(self.source, config.path):
                continue
            if not _rule_may_match_source(rule, self.source):
                continue
            rule._config_root = config.root
            rule._lint_ignore_enabled = lint_ignore_enabled
            if lint_ignore_enabled:
                _ensure_parent_metadata(rule)
            rule._visit_hook = visit_hook if visit_timing_enabled else None
            providers = rule.get_inherited_dependencies()
            if providers:
                metadata_rules.append(rule)
            else:
                plain_rules.append(rule)
            active_rules.append(rule)
            for provider in providers:
                if provider is FilePathProvider:
                    if resolved_config_path is None:
                        resolved_config_path = config.path.resolve()
                    metadata_cache[provider] = resolved_config_path
                    continue
                if provider.gen_cache is not None:
                    # TODO: find a better way to declare this requirement in LibCST
                    needs_repo_manager.add(provider)

        if not plain_rules and not metadata_rules:
            _ = self.module
            for rule in rules:
                self.metrics[f"Count.{rule.name}"] = 0
                self.metrics[f"FixCount.{rule.name}"] = 0
            self.metrics["Count.Total"] = 0
            if metrics_hook:
                metrics_hook(self.metrics)
            return 0

        if needs_repo_manager:
            repo_manager = FullRepoManager(
                repo_root_dir=config.root.as_posix(),
                paths=[config.path.as_posix()],
                providers=needs_repo_manager,
            )
            repo_manager.resolve_cache()
            metadata_cache.update(repo_manager.get_cache_for_path(config.path.as_posix()))

        wrapper = MetadataWrapper(self.module, unsafe_skip_copy=True, cache=metadata_cache)
        try:
            if metadata_rules:
                _resolve_metadata(
                    wrapper,
                    {
                        provider
                        for rule in metadata_rules
                        for provider in rule.get_inherited_dependencies()
                    },
                    metadata_cache,
                )
                with ExitStack() as stack:
                    for rule in active_rules:
                        stack.enter_context(rule.resolve(wrapper))
                    self.module.visit(_BatchedRuleVisitor(active_rules))
            elif plain_rules:
                self.module.visit(_BatchedRuleVisitor(plain_rules))
        except AstParseError:
            raise
        except Exception as e:  # noqa: BLE001 - custom rule execution boundary
            raise RattleRuleExecutionError(type(e).__name__) from None
        count = 0
        position_metadata: Mapping[CSTNode, CodeRange] | None = None
        for rule in rules:
            self.metrics[f"Count.{rule.name}"] = len(rule._violations)
            self.metrics[f"FixCount.{rule.name}"] = 0
            for violation in rule._violations:
                count += 1
                if violation.range is None:
                    if position_metadata is None:
                        position_metadata = wrapper.resolve(PositionProvider)
                    violation = _resolve_violation_position(position_metadata, violation)

                if violation.replacement:
                    self.metrics[f"FixCount.{rule.name}"] += 1
                    if include_diff:
                        diff = diff_violation(self.path, self.module, violation)
                        violation = replace(violation, diff=diff)

                yield violation

        self.metrics["Count.Total"] = count

        if metrics_hook:
            metrics_hook(self.metrics)

        return count

    def apply_replacements(  # noqa: C901 - composes nested replacement trees
        self, violations: Collection[LintViolation]
    ) -> Module:
        """Apply any autofixes to the module, and return the resulting source code."""
        replacements = {v.node: v.replacement for v in violations if v.replacement}

        class DescendantCollector(CSTTransformer):
            def __init__(self) -> None:
                self.nodes: set[CSTNode] = set()

            def on_visit(self, node: CSTNode) -> bool:
                self.nodes.add(node)
                return True

        class StructuralReplacementTransformer(CSTTransformer):
            def __init__(
                self,
                nested_replacements: Mapping[CSTNode, NodeReplacement[CSTNode]],
                tree_nodes: set[CSTNode],
            ) -> None:
                self._pending = dict(nested_replacements)
                self._tree_nodes = tree_nodes

            def on_leave(
                self,
                original_node: CSTNode,
                updated_node: CSTNode,
            ) -> NodeReplacement[CSTNode]:
                for source in tuple(self._pending):
                    if original_node is source:
                        return self._pending.pop(source)

                for source, replacement in tuple(self._pending.items()):
                    if source not in self._tree_nodes and original_node.deep_equals(source):
                        del self._pending[source]
                        return replacement
                return updated_node

        class ReplacementTransformer(CSTTransformer):
            def on_leave(
                self,
                original_node: CSTNode,
                updated_node: CSTNode,
            ) -> NodeReplacement[CSTNode]:
                if original_node in replacements:
                    replacement = replacements[original_node]
                    if isinstance(replacement, CSTNode):
                        collector = DescendantCollector()
                        original_node.visit(collector)
                        nested_replacements = {
                            node: nested_replacement
                            for node, nested_replacement in replacements.items()
                            if node is not original_node and node in collector.nodes
                        }
                        if nested_replacements:
                            target_collector = DescendantCollector()
                            replacement.visit(target_collector)
                            replacement = replacement.visit(
                                StructuralReplacementTransformer(
                                    nested_replacements, target_collector.nodes
                                )
                            )
                    replacements[original_node] = replacement
                    return replacement
                return updated_node

        updated: Module = self.module.visit(ReplacementTransformer())
        return updated


__all__ = [
    "LintRunner",
    "diff_module",
    "diff_violation",
]
