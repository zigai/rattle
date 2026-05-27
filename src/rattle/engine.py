# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import logging
import time
from collections import defaultdict
from collections.abc import Collection, Generator, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

from libcst import CSTNode, CSTTransformer, Module, parse_module, visit_batched
from libcst.metadata import (
    FilePathProvider,
    FullRepoManager,
    MetadataWrapper,
    ParentNodeProvider,
    PositionProvider,
    ProviderT,
)
from moreorless import unified_diff

from .ftypes import (
    CodeRange,
    Config,
    FileContent,
    LintViolation,
    Metrics,
    MetricsHook,
    NodeReplacement,
)
from .rule import LintRule

LOG = logging.getLogger(__name__)
_RULE_SOURCE_FILTERS: dict[type[LintRule], tuple[bytes, ...] | None] = {}

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
    if source_filter is None:
        return True

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

        lint_ignore_enabled = b"lint-ignore" in self.source or b"lint-fixme" in self.source

        visit_timing_enabled = metrics_hook is not None or LOG.isEnabledFor(logging.DEBUG)

        for rule in rules:
            if rule.SETTINGS and not rule.settings:
                rule.configure({})
            if not rule.should_lint_file(self.source, config.path):
                continue
            if not _rule_may_match_source(rule, self.source):
                continue
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
        if metadata_rules:
            wrapper.visit_batched(active_rules)
        elif plain_rules:
            visit_batched(self.module, plain_rules)
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

    def apply_replacements(self, violations: Collection[LintViolation]) -> Module:
        """Apply any autofixes to the module, and return the resulting source code."""
        replacements = {v.node: v.replacement for v in violations if v.replacement}

        class ReplacementTransformer(CSTTransformer):
            def on_visit(self, node: CSTNode) -> bool:
                # don't visit children if we're going to replace the parent anyways
                return node not in replacements

            def on_leave(self, node: CSTNode, updated: CSTNode) -> NodeReplacement:  # type: ignore[type-arg]
                if node in replacements:
                    new = replacements[node]
                    return new
                return updated

        updated: Module = self.module.visit(ReplacementTransformer())
        return updated


__all__ = (
    "LintRunner",
    "diff_violation",
)
