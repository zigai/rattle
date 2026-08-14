from __future__ import annotations

import logging
import os
import sys
from collections.abc import Collection, Generator
from dataclasses import dataclass, field, replace
from pathlib import Path

from rattle.cache import ResultCache
from rattle.config.errors import ConfigError
from rattle.config.merge import generate_config
from rattle.config.models import Config, Options
from rattle.diagnostics import FileContent, LintViolation, Result
from rattle.engine import MetricsHook
from rattle.execution.content import _drive_rattle_bytes, rattle_bytes
from rattle.rule import LintRule
from rattle.rule_loading import CollectionError, collect_rules

LOG = logging.getLogger(__name__)


@dataclass
class ConfiguredFileCacheSession:
    path: Path
    config: Config
    stat: os.stat_result
    rules: Collection[LintRule]
    autofix: bool = False
    include_diff: bool = False
    allow_cached_dirty_results: bool = False
    options: Options | None = None
    explicit_path: bool = False
    cache: ResultCache | None = None
    cache_key: str = ""
    cached_results: list[Result] | None = None
    cached_autofix_rule_names: set[str] = field(default_factory=set)
    cached_passthrough: list[Result] = field(default_factory=list)

    @classmethod
    def from_environment(
        cls,
        *,
        path: Path,
        config: Config,
        stat: os.stat_result,
        rules: Collection[LintRule],
        autofix: bool,
        include_diff: bool,
        allow_cached_dirty_results: bool,
        options: Options | None,
        explicit_path: bool,
    ) -> ConfiguredFileCacheSession:
        return cls(
            path=path,
            config=config,
            stat=stat,
            rules=rules,
            autofix=autofix,
            include_diff=include_diff,
            allow_cached_dirty_results=allow_cached_dirty_results,
            options=options,
            explicit_path=explicit_path,
            cache=ResultCache.from_environment(),
        )

    def read_complete_entry(self) -> bool:
        if self.cache is None:
            return False

        self.cache_key = self.cache.result_key(
            self.path,
            self.stat,
            self.config,
            include_diff=self.include_diff,
        )
        self.cached_results, self.cached_autofix_rule_names, cached_result_is_complete = (
            self.cache.read_configured_file(
                self.cache_key,
                self.stat,
                path=self.path,
                config=self.config,
                rules=self.rules,
                autofix=self.autofix,
                allow_cached_dirty_results=self.allow_cached_dirty_results,
            )
        )
        return cached_result_is_complete

    def prepare_autofix_passthrough(self) -> list[Result]:
        if not self.cached_autofix_rule_names:
            return []

        self.cached_passthrough = [
            result
            for result in self.cached_results or ()
            if result.violation is not None
            and result.violation.rule_name not in self.cached_autofix_rule_names
        ]
        self.rules = [rule for rule in self.rules if rule.name in self.cached_autofix_rule_names]
        return self.cached_passthrough

    def write_result(
        self,
        content: FileContent,
        *,
        clean: bool,
        cacheable: bool,
        cache_violations: list[LintViolation],
    ) -> None:
        if self.cache is None:
            return

        if clean and not self.cached_passthrough:
            self.cache.write_result(self.cache_key, self.stat, rules=self.rules)
            self.cache.write_clean_status(
                self.path,
                self.stat,
                options=self.options,
                explicit_path=self.explicit_path,
                include_diff=self.include_diff,
                rules=self.rules,
            )
            return

        if cacheable and cache_violations:
            self.cache.write_result(
                self.cache_key,
                self.stat,
                source=content,
                violations=cache_violations,
                rules=self.rules,
            )


@dataclass
class ConfiguredFileRun:
    path: Path
    config: Config
    autofix: bool = False
    include_diff: bool = False
    allow_cached_dirty_results: bool = False
    deferred_format_paths: list[Path] | None = None
    options: Options | None = None
    explicit_path: bool = False
    metrics_hook: MetricsHook | None = None
    content: FileContent | None = None
    stat: os.stat_result | None = None
    rules: Collection[LintRule] = ()
    cache_session: ConfiguredFileCacheSession | None = None

    def run(self) -> Generator[Result, bool, None]:
        self.path = self.path.resolve()

        try:
            self.stat = self.path.stat()
            self.rules = collect_rules(self.config)
            if self.metrics_hook is None:
                self.cache_session = ConfiguredFileCacheSession.from_environment(
                    path=self.path,
                    config=self.config,
                    stat=self.stat,
                    rules=self.rules,
                    autofix=self.autofix,
                    include_diff=self.include_diff,
                    allow_cached_dirty_results=self.allow_cached_dirty_results,
                    options=self.options,
                    explicit_path=self.explicit_path,
                )
                if self.cache_session.read_complete_entry():
                    yield from (self.cache_session.cached_results or [])
                    return

                yield from self.cache_session.prepare_autofix_passthrough()
                self.rules = self.cache_session.rules

            if not self.rules:
                self.content = self.path.read_bytes()
                yield Result(
                    self.path,
                    violation=None,
                    source=self.content,
                    config=self.config,
                )
                return

            self.content = self.path.read_bytes()
            lint_config = replace(self.config, formatter=None) if self.defer_format else self.config
            runner = rattle_bytes(
                self.path,
                self.content,
                config=lint_config,
                autofix=self.autofix,
                include_diff=self.include_diff,
                rules=self.rules,
                metrics_hook=self.metrics_hook,
            )
            updated, clean, cacheable, cache_violations = yield from _drive_rattle_bytes(
                runner,
                cacheable=not self.autofix,
            )
            self._store_result(
                updated,
                clean=clean,
                cacheable=cacheable,
                cache_violations=cache_violations,
            )

        except (CollectionError, ConfigError, OSError) as e:
            LOG.debug(
                "rattle_configured_file failed with %s",
                type(e).__name__,
            )
            yield Result.from_exception(
                self.path,
                e,
                operation="Linting file",
                source=self.content,
                config=self.config,
            )

    @property
    def defer_format(self) -> bool:
        return (
            self.deferred_format_paths is not None
            and self.autofix
            and self.config.formatter == "ruff"
        )

    def _store_result(
        self,
        updated: FileContent | None,
        *,
        clean: bool,
        cacheable: bool,
        cache_violations: list[LintViolation],
    ) -> None:
        assert self.stat is not None
        if updated and updated != self.content:
            LOG.info("%s: writing changes to file", self.path)
            self.path.write_bytes(updated)
            if self.defer_format and self.deferred_format_paths is not None:
                self.deferred_format_paths.append(self.path)
            return

        if self.content is not None and self.cache_session is not None:
            self.cache_session.write_result(
                self.content,
                clean=clean,
                cacheable=cacheable,
                cache_violations=cache_violations,
            )


def rattle_stdin(
    path: Path,
    *,
    autofix: bool = False,
    include_diff: bool = False,
    options: Options | None = None,
    metrics_hook: MetricsHook | None = None,
) -> Generator[Result, bool, None]:
    """
    Wrapper around :func:`rattle_bytes` for formatting content from STDIN.

    The resulting fixed content will be printed to STDOUT.

    Requires passing a path that represents the filesystem location matching the
    contents to be linted. This will be used to resolve the ``pyproject.toml``
    configuration.
    """
    path = path.resolve()
    content: FileContent | None = None
    config: Config | None = None

    try:
        stdin_content = sys.stdin.buffer.read()
        content = stdin_content
        config = generate_config(path, options=options, explicit_path=True)
        if config.excluded:
            return

        updated = yield from rattle_bytes(
            path,
            stdin_content,
            config=config,
            autofix=autofix,
            include_diff=include_diff,
            metrics_hook=metrics_hook,
        )
        if autofix:
            sys.stdout.buffer.write(updated or stdin_content)

    except (CollectionError, ConfigError, OSError, UnicodeError) as e:
        LOG.debug("Linting stdin failed with %s", type(e).__name__)
        yield Result.from_exception(
            path,
            e,
            operation="Linting stdin",
            source=content,
            config=config,
        )


def rattle_file(
    path: Path,
    *,
    autofix: bool = False,
    include_diff: bool = False,
    options: Options | None = None,
    explicit_path: bool = False,
    metrics_hook: MetricsHook | None = None,
) -> Generator[Result, bool, None]:
    """
    Lint a single file on disk, detecting and generating appropriate configuration.

    Generates a merged :ref:`configuration` based on all applicable config files.
    Reads file from disk as raw bytes, and uses :func:`rattle_bytes` to lint and apply
    any fixes to the content. Writes content back to disk if changes are detected.

    Yields :class:`Result` objects for each lint error or exception found, or a single
    empty result if the file is clean.
    See :func:`rattle_bytes` for semantics.
    """
    path = path.resolve()
    config: Config | None = None

    try:
        config = generate_config(path, options=options, explicit_path=explicit_path)
        if config.excluded:
            return

        yield from rattle_configured_file(
            path,
            config=config,
            autofix=autofix,
            include_diff=include_diff,
            options=options,
            explicit_path=explicit_path,
            metrics_hook=metrics_hook,
        )

    except (CollectionError, ConfigError, OSError, UnicodeError) as e:
        LOG.debug("Linting file failed with %s", type(e).__name__)
        yield Result.from_exception(
            path,
            e,
            operation="Linting file",
            config=config,
        )


def rattle_configured_file(
    path: Path,
    *,
    config: Config,
    autofix: bool = False,
    include_diff: bool = False,
    allow_cached_dirty_results: bool = False,
    deferred_format_paths: list[Path] | None = None,
    options: Options | None = None,
    explicit_path: bool = False,
    metrics_hook: MetricsHook | None = None,
) -> Generator[Result, bool, None]:
    yield from ConfiguredFileRun(
        path,
        config,
        autofix=autofix,
        include_diff=include_diff,
        allow_cached_dirty_results=allow_cached_dirty_results,
        deferred_format_paths=deferred_format_paths,
        options=options,
        explicit_path=explicit_path,
        metrics_hook=metrics_hook,
    ).run()


__all__ = ["rattle_configured_file", "rattle_file", "rattle_stdin"]
