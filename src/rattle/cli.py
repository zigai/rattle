# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import json as json_module
import logging
import os
import shutil
import sys
import unittest
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from interfacy import ExecutableFlag, Interfacy
from interfacy.naming import AbbreviationGenerator
from interfacy.plugins import InterfacyPlugin, PluginContext
from interfacy.schema.schema import ArgumentKind, ParserSchema
from stdl.st import colored

from rattle.__version__ import __version__

from .api import rattle_paths
from .config import (
    CollectionError,
    collect_rule_types,
    collect_rules,
    generate_config,
    parse_rule,
    resolve_rule_type,
    validate_config,
)
from .console import AsyncConsole, echo, getchar
from .explain import RuleInfo, render_console_rule_info
from .ftypes import (
    STDIN,
    Config,
    LSPOptions,
    Metrics,
    Options,
    OutputFormat,
    Result,
    RuleSelector,
)
from .output import render_console_result
from .rule import LintRule
from .testing import generate_lint_rule_test_cases
from .util import capture

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


UV_REEXEC_ENV = "RATTLE_UV_RUN_REEXEC"
UV_REEXEC_DISABLE_ENV = "RATTLE_NO_UV_RUN_REEXEC"
DEBUG_ENV = "RATTLE_DEBUG"
METRICS_ENV = "RATTLE_METRICS"
UV_PROJECT_MARKERS = ("uv.lock",)
UV_REEXEC_COMMANDS = frozenset({"lint", "fix", "rules", "validate", "lsp", "explain"})
TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "on"})


class RattleAbbreviationGenerator(AbbreviationGenerator):
    SHORT_FLAGS = {
        "config": "c",
        "diff": "d",
        "exclude": "e",
        "extend-exclude": "ee",
        "interactive": "i",
        "jobs": "j",
        "quiet": "q",
        "rules": "r",
    }

    def generate(self, value: str, taken: list[str]) -> str | None:
        flag = self.SHORT_FLAGS.get(value)
        if flag is None or flag in taken:
            return None
        taken.append(flag)
        return flag


class ValidateConfigPositionalPlugin(InterfacyPlugin):
    def transform_schema(
        self,
        _context: PluginContext,
        schema: ParserSchema,
    ) -> ParserSchema:
        validate_command = schema.commands.get("validate")
        if validate_command is None or not validate_command.parameters:
            return schema

        config_argument = validate_command.parameters[0]
        if config_argument.name != "config":
            return schema

        config_argument.kind = ArgumentKind.POSITIONAL
        config_argument.flags = ("CONFIG",)
        config_argument.required = False
        config_argument.nargs = "?"
        config_argument.metavar = "CONFIG"
        return schema


def _display_path(path: Path) -> Path:
    try:
        return path.relative_to(Path.cwd())
    except ValueError:
        return path


def splash(
    visited: set[Path],
    violation_files: set[Path],
    error_files: set[Path],
    violations: int = 0,
    autofixes: int = 0,
    fixed: int = 0,
) -> str:
    def f(v: int) -> str:
        return "file" if v == 1 else "files"

    if violation_files or error_files:
        reports = [colored(f"{len(visited)} {f(len(visited))} checked")]
        if violations:
            reports.append(
                colored(
                    f"{violations} violation{'s' if violations != 1 else ''} "
                    f"in {len(violation_files)} {f(len(violation_files))}",
                    color="yellow",
                    style="bold",
                )
            )
        if error_files:
            reports.append(
                colored(
                    f"{len(error_files)} {f(len(error_files))} with errors",
                    color="yellow",
                    style="bold",
                )
            )
        if autofixes:
            reports.append(colored(f"{autofixes} autofixable", style="bold"))
        if fixed:
            word = "fix" if fixed == 1 else "fixes"
            reports.append(colored(f"{fixed} {word} applied", style="bold"))

        return ", ".join(reports)

    return f"{len(visited)} {f(len(visited))} clean"


def _submit_result(
    console: AsyncConsole,
    result: Result,
    *,
    show_diff: bool,
    stderr: bool = False,
    output_format: OutputFormat,
    output_template: str,
    brief: bool,
    brief_rule_width: int | None = None,
) -> bool:
    rendered = render_console_result(
        result,
        path=_display_path(result.path),
        show_diff=show_diff,
        output_format=output_format,
        output_template=output_template,
        brief=brief,
        brief_rule_width=brief_rule_width,
    )
    if rendered is None:
        return False
    console.submit(rendered, err=stderr)
    return True


def _metrics_hook(console: AsyncConsole, enabled: bool) -> Callable[[Metrics], None] | None:
    if not enabled:
        return None
    return lambda metrics: console.submit(str(metrics))


def _output_config_for_path(path: Path, options: Options) -> Config:
    return generate_config(path, options=options)


def _print_stats(console: AsyncConsole, stats: Counter[str]) -> None:
    if not stats:
        return

    console.submit("Violation stats by rule:", err=True)
    width = max(len(rule_name) for rule_name in stats)
    for rule_name, count in sorted(stats.items()):
        console.submit(f"  {rule_name:<{width}}  {count}", err=True)


@dataclass
class LintState:
    exit_code: int = 0
    violations: int = 0
    autofixes: int = 0
    visited: set[Path] = field(default_factory=set)
    violation_files: set[Path] = field(default_factory=set)
    error_files: set[Path] = field(default_factory=set)
    violation_stats: Counter[str] = field(default_factory=Counter)
    diagnostics: list[tuple[Result, Config]] = field(default_factory=list)


@dataclass
class FixState:
    exit_code: int = 0
    violations: int = 0
    autofixes: int = 0
    fixed: int = 0
    violation_stats: Counter[str] = field(default_factory=Counter)


@dataclass
class LintReport:
    console: AsyncConsole
    options: Options
    diff: bool
    compact: bool
    quiet: bool
    stats: bool
    state: LintState = field(default_factory=LintState)

    @property
    def exit_code(self) -> int:
        return self.state.exit_code

    def record(self, result: Result) -> None:
        self.state.visited.add(result.path)
        if not result.violation and not result.error:
            return

        config = result.config or _output_config_for_path(result.path, self.options)
        _record_lint_result(result, config, state=self.state, stats=self.stats)

    def submit(self) -> None:
        if not self.quiet:
            _submit_lint_diagnostics(
                self.console,
                self.state.diagnostics,
                diff=self.diff,
                compact=self.compact,
            )
        self.console.submit(
            splash(
                self.state.visited,
                self.state.violation_files,
                self.state.error_files,
                self.state.violations,
                self.state.autofixes,
            ),
            err=True,
        )
        if self.stats:
            _print_stats(self.console, self.state.violation_stats)


def _record_lint_result(
    result: Result,
    config: Config,
    *,
    state: LintState,
    stats: bool,
) -> None:
    state.diagnostics.append((result, config))
    if result.violation:
        state.violation_files.add(result.path)
        state.violations += 1
        if stats:
            state.violation_stats[result.violation.rule_name] += 1
        state.exit_code |= 1
        if result.violation.autofixable:
            state.autofixes += 1
    if result.error:
        state.error_files.add(result.path)
        state.exit_code |= 2


def _compact_rule_width(diagnostics: list[tuple[Result, Config]], *, compact: bool) -> int | None:
    if not compact:
        return None

    rule_names = [
        result.violation.rule_name
        for result, config in diagnostics
        if result.violation and config.output_format == OutputFormat.rattle
    ]
    if not rule_names:
        return None

    return max(len(rule_name) for rule_name in rule_names)


def _submit_lint_diagnostics(
    console: AsyncConsole,
    diagnostics: list[tuple[Result, Config]],
    *,
    diff: bool,
    compact: bool,
) -> None:
    compact_rule_width = _compact_rule_width(diagnostics, compact=compact)
    for result, config in diagnostics:
        _submit_result(
            console,
            result,
            show_diff=diff,
            output_format=config.output_format,
            output_template=config.output_template,
            brief=compact,
            brief_rule_width=compact_rule_width,
        )


def _validate_fix_options(
    paths: tuple[Path, ...],
    *,
    quiet: bool,
    diff: bool,
    stats: bool,
    interactive: bool,
) -> bool:
    if quiet and diff:
        usage_error("--quiet and --diff cannot be used together")
    if quiet and stats:
        usage_error("--quiet and --stats cannot be used together")
    if quiet and interactive:
        usage_error("--quiet and --interactive cannot be used together")

    is_stdin = bool(paths[0] and str(paths[0]) == "-")
    if is_stdin and interactive:
        usage_error("--interactive cannot be used with stdin")

    return is_stdin


def _record_fix_output(
    console: AsyncConsole,
    result: Result,
    *,
    config: Config,
    is_stdin: bool,
    quiet: bool,
    interactive: bool,
    diff: bool,
    compact: bool,
    stats: bool,
    state: FixState,
    violation_files: set[Path],
    error_files: set[Path],
) -> None:
    if result.violation:
        violation_files.add(result.path)
        if stats:
            state.violation_stats[result.violation.rule_name] += 1
    if result.error:
        error_files.add(result.path)

    if quiet:
        return

    _submit_result(
        console,
        result,
        show_diff=interactive or diff,
        stderr=is_stdin,
        output_format=config.output_format,
        output_template=config.output_template,
        brief=compact,
    )


def _prompt_for_fix(generator: capture, state: FixState) -> bool:
    prompt = "Apply autofix? [Y]es, [n]o, [q]uit: "
    while True:
        echo(prompt, nl=False, err=True)
        answer = getchar(echo_input=True, err=True).lower()
        echo(err=True)
        if answer in {"\n", "\r", ""}:
            answer = "y"
        if answer in {"y", "n", "q"}:
            break
        echo("Press y to apply, n to skip, or q to quit fixing.", err=True)

    if answer == "y":
        generator.respond(answer=True)
        state.fixed += 1
        return False

    state.exit_code |= 1
    return answer == "q"


def _update_fix_state(
    result: object,
    *,
    autofix: bool,
    interactive: bool,
    generator: capture,
    state: FixState,
) -> bool:
    error = getattr(result, "error", None)
    if error:
        state.exit_code |= 2
        return False

    violation = getattr(result, "violation", None)
    if not violation:
        return False

    state.violations += 1

    if interactive and violation.autofixable:
        state.autofixes += 1
        return _prompt_for_fix(generator, state)

    if autofix and violation.autofixable:
        state.autofixes += 1
        state.fixed += 1
        return False

    state.exit_code |= 1
    return False


def _version() -> str:
    return f"rattle {__version__}"


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").lower() in TRUTHY_ENV_VALUES


def _configure_logging() -> None:
    level = logging.DEBUG if _env_flag(DEBUG_ENV) else logging.WARNING
    logging.basicConfig(level=level, stream=sys.stderr)


def _find_uv_project_root(path: Path) -> Path | None:
    for directory in (path, *path.parents):
        if any((directory / marker).is_file() for marker in UV_PROJECT_MARKERS):
            return directory

        pyproject = directory / "pyproject.toml"
        if not pyproject.is_file():
            continue

        try:
            data = tomllib.loads(pyproject.read_text())
        except Exception:  # noqa: BLE001, S112 - bootstrap should not block normal CLI handling
            continue

        tool = data.get("tool", {})
        if isinstance(tool, dict) and "uv" in tool:
            return directory

        dependency_groups = data.get("dependency-groups", {})
        if isinstance(dependency_groups, dict):
            return directory

    return None


def _should_reexec_with_uv(args: list[str]) -> bool:
    if os.environ.get(UV_REEXEC_ENV) or os.environ.get(UV_REEXEC_DISABLE_ENV):
        return False
    if shutil.which("uv") is None:
        return False

    command = next((arg for arg in args if not arg.startswith("-")), None)
    if command not in UV_REEXEC_COMMANDS:
        return False

    return _find_uv_project_root(Path.cwd()) is not None


def _reexec_with_uv(args: list[str]) -> None:
    uv_path = shutil.which("uv")
    if uv_path is None:
        return

    env = os.environ.copy()
    env[UV_REEXEC_ENV] = "1"
    os.execve(uv_path, [uv_path, "run", "rattle", *args], env)  # noqa: S606


def usage_error(message: str) -> None:
    echo(message, err=True)
    raise SystemExit(2)


def require_existing_file(path: Path, *, option: str) -> Path:
    if not path.exists() or not path.is_file():
        usage_error(f"{option} must be an existing file: {path}")
    return path


def require_existing_path(path: Path, *, argument: str) -> Path:
    if not path.exists():
        usage_error(f"{argument} must be an existing path: {path}")
    return path


def _resolve_input_paths(paths: tuple[Path, ...]) -> tuple[Path, ...]:
    if not paths:
        return (Path.cwd(),)
    if paths[0] == STDIN:
        if len(paths) != 2:
            usage_error('stdin mode requires exactly "- PATH"')
        return paths
    return tuple(require_existing_path(path, argument="path") for path in paths)


def parse_rules(rules: str | None) -> list[RuleSelector]:
    selectors = (selector.strip() for selector in (rules or "").split(","))
    return sorted({parse_rule(selector, Path.cwd()) for selector in selectors if selector}, key=str)


def build_options(
    *,
    rules: str | None = None,
    jobs: int | None = None,
    config: Path | None = None,
    exclude: list[str] | None = None,
    extend_exclude: list[str] | None = None,
) -> Options:
    if jobs is not None and jobs < 1:
        usage_error("--jobs must be an integer greater than or equal to 1")

    _configure_logging()

    return Options(
        debug=True if _env_flag(DEBUG_ENV) else None,
        config_file=(require_existing_file(config, option="--config") if config else None),
        exclude=tuple(exclude or ()),
        extend_exclude=tuple(extend_exclude or ()),
        jobs=jobs,
        rules=parse_rules(rules),
        print_metrics=_env_flag(METRICS_ENV),
    )


def lint(
    *paths: Path,
    rules: str | None = None,
    jobs: int | None = None,
    config: Path | None = None,
    exclude: list[str] | None = None,
    extend_exclude: list[str] | None = None,
    diff: bool = False,
    compact: bool = False,
    stats: bool = False,
    quiet: bool = False,
) -> None:
    """
    Check files for Rattle violations.

    Args:
        paths: Files or directories to check. Use "- PATH" to check code from stdin as PATH.
        quiet: Print only the final summary.
        config: Use this config file instead of discovered configuration.
        exclude: Replace configured exclude patterns.
        extend_exclude: Add exclude patterns.
        jobs: Number of worker processes to use when linting multiple files.
        rules: Override configured rules with comma-separated selectors.
        compact: Print compact diagnostics.
        diff: Show available fixes as unified diffs.
        stats: Print violation counts by rule.

    pass "- PATH" to read stdin and treat it as PATH
    """
    if quiet and diff:
        usage_error("--quiet and --diff cannot be used together")
    if quiet and stats:
        usage_error("--quiet and --stats cannot be used together")

    paths = _resolve_input_paths(paths)

    runtime_options = build_options(
        config=config,
        exclude=exclude,
        extend_exclude=extend_exclude,
        jobs=jobs,
        rules=rules,
    )
    console = AsyncConsole()
    report = LintReport(
        console=console,
        options=runtime_options,
        diff=diff,
        compact=compact,
        quiet=quiet,
        stats=stats,
    )
    try:
        for result in rattle_paths(
            paths,
            include_diff=diff,
            allow_cached_dirty_results=True,
            options=runtime_options,
            metrics_hook=_metrics_hook(console, runtime_options.print_metrics),
        ):
            report.record(result)

        report.submit()
    finally:
        console.close()
    if report.exit_code:
        raise SystemExit(report.exit_code)


def fix(
    *paths: Path,
    rules: str | None = None,
    quiet: bool = False,
    jobs: int | None = None,
    config: Path | None = None,
    exclude: list[str] | None = None,
    extend_exclude: list[str] | None = None,
    diff: bool = False,
    interactive: bool = False,
    compact: bool = False,
    stats: bool = False,
) -> None:
    """
    Apply available autofixes to files.

    Args:
        paths: Files or directories to fix. Use "- PATH" to fix code from stdin as PATH and write to stdout.
        quiet: Print only the final summary.
        config: Use this config file instead of discovered configuration.
        exclude: Replace configured exclude patterns.
        extend_exclude: Add exclude patterns.
        jobs: Number of worker processes to use when linting multiple files.
        rules: Override configured rules with comma-separated selectors.
        interactive: Prompt before applying each autofix.
        compact: Print compact diagnostics.
        diff: Show applied fixes as unified diffs.
        stats: Print violation counts by rule.

    pass "- PATH" to read stdin, treat it as PATH, and write fixed code to stdout
    """
    paths = _resolve_input_paths(paths)
    is_stdin = _validate_fix_options(
        paths,
        quiet=quiet,
        diff=diff,
        stats=stats,
        interactive=interactive,
    )

    runtime_options = build_options(
        config=config,
        exclude=exclude,
        extend_exclude=extend_exclude,
        jobs=jobs,
        rules=rules,
    )
    autofix = not interactive
    state = FixState()

    visited: set[Path] = set()
    violation_files: set[Path] = set()
    error_files: set[Path] = set()

    console = AsyncConsole()
    try:
        generator = capture(
            rattle_paths(
                paths,
                autofix=autofix,
                include_diff=interactive or diff,
                options=runtime_options,
                parallel=autofix,
                metrics_hook=_metrics_hook(console, runtime_options.print_metrics),
            )
        )
        for result in generator:
            visited.add(result.path)
            if not result.violation and not result.error:
                continue
            result_config = result.config or _output_config_for_path(result.path, runtime_options)
            # for STDIN, we need STDOUT to equal the fixed content, so
            # move everything else to STDERR
            _record_fix_output(
                console,
                result,
                config=result_config,
                is_stdin=is_stdin,
                quiet=quiet,
                interactive=interactive,
                diff=diff,
                compact=compact,
                stats=stats,
                state=state,
                violation_files=violation_files,
                error_files=error_files,
            )
            if interactive:
                console.flush()
            if _update_fix_state(
                result,
                autofix=autofix,
                interactive=interactive,
                generator=generator,
                state=state,
            ):
                break

        console.submit(
            splash(
                visited,
                violation_files,
                error_files,
                state.violations,
                state.autofixes,
                state.fixed,
            ),
            err=True,
        )
        if stats:
            _print_stats(console, state.violation_stats)
    finally:
        console.close()
    if state.exit_code:
        raise SystemExit(state.exit_code)


def lsp(
    *,
    config: Path | None = None,
    ws: int | None = None,
    tcp: int | None = None,
    debounce_interval: float = LSPOptions.debounce_interval,
    no_stdio: bool = False,
) -> None:
    """Start the language server.

    https://microsoft.github.io/language-server-protocol/.

    Args:
        config: Use this config file instead of discovered configuration.
        no_stdio: Disable stdio transport when using TCP or WebSocket.
        tcp: Port to serve LSP over TCP.
        ws: Port to serve LSP over WebSocket.
        debounce_interval: Delay diagnostics after document changes, in seconds.
    """
    if tcp is not None and ws is not None:
        usage_error("--tcp and --ws cannot be used together")
    if no_stdio and tcp is None and ws is None:
        usage_error("--no-stdio requires --tcp or --ws")
    if debounce_interval < 0:
        usage_error("--debounce-interval must be greater than or equal to 0")

    from .lsp import LSP

    lsp_options = LSPOptions(
        tcp=tcp,
        ws=ws,
        stdio=not no_stdio,
        debounce_interval=debounce_interval,
    )
    LSP(
        build_options(
            config=config,
        ),
        lsp_options,
    ).start()


def _run_rule_tests(lint_rules: list[LintRule] | tuple[LintRule, ...]) -> None:
    test_suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for test_case in generate_lint_rule_test_cases(lint_rules):
        test_suite.addTest(loader.loadTestsFromTestCase(test_case))

    test_count = test_suite.countTestCases()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    if test_count == 0 or not result.wasSuccessful():
        raise SystemExit(1)


def _rule_line(rule: LintRule) -> str:
    description = _rule_description(rule)
    description_text = f" - {description}" if description else ""
    return f"  {colored(rule.name, color='light_cyan', style='bold')}{description_text}"


def _rule_description(rule: LintRule) -> str:
    message = getattr(rule, "MESSAGE", "")
    if not isinstance(message, str):
        return ""

    description = " ".join(message.split())
    description = description.split(" Learn more:", maxsplit=1)[0]
    description = description.split(" See ", maxsplit=1)[0]
    return description


def _parse_explain_selector(selector: str, config_path: Path) -> RuleSelector:
    try:
        return parse_rule(selector, config_path)
    except Exception as error:
        usage_error(str(error))
        raise AssertionError("unreachable") from error


def explain_command(
    rule: str,
    *,
    config: Path | None = None,
    json: bool = False,
) -> None:
    """Display detailed information about one lint rule.

    Args:
        rule: Rule name or selector to explain.
        config: Use this config file instead of discovered configuration.
        json: Print rule information as JSON.
    """
    runtime_options = build_options(
        config=config,
    )
    target_path = runtime_options.config_file or Path.cwd()
    materialized_config = generate_config(target_path, options=runtime_options)
    parsed_selector = _parse_explain_selector(rule, materialized_config.root)

    try:
        rule_type = resolve_rule_type(materialized_config, parsed_selector)
        enabled_rule_types = set(collect_rule_types(materialized_config))
    except CollectionError as error:
        echo(str(error), err=True)
        raise SystemExit(2) from error
    except Exception as error:
        echo(str(error), err=True)
        raise SystemExit(2) from error

    info = RuleInfo.from_rule(rule_type, enabled=rule_type in enabled_rule_types)
    if json:
        echo(json_module.dumps(info.to_json_data(), ensure_ascii=False, indent=2))
        return

    render_console_rule_info(info)


def rules_command(
    *paths: Path,
    config: Path | None = None,
    test: bool = False,
) -> None:
    """Display or test currently enabled lint rules.

    Args:
        paths: Files or directories whose rules should be shown.
        config: Use this config file instead of discovered configuration.
        test: Test lint rules and their VALID/INVALID cases.
    """
    resolved_paths = tuple(require_existing_path(path, argument="path") for path in paths) or (
        Path.cwd(),
    )

    runtime_options = build_options(
        config=config,
    )

    if test:
        lint_rules_by_name: dict[str, LintRule] = {}
        for path in resolved_paths:
            path_config = generate_config(path.resolve(), options=runtime_options)
            for rule in collect_rules(path_config):
                lint_rules_by_name[rule.qualified_name()] = rule
        _run_rule_tests(
            [
                rule
                for _name, rule in sorted(
                    lint_rules_by_name.items(),
                    key=lambda item: item[1].name,
                )
            ]
        )
        return

    for index, path in enumerate(resolved_paths):
        path = path.resolve()
        path_config = generate_config(path, options=runtime_options)
        disabled: dict[type[LintRule], str] = {}
        enabled = collect_rules(path_config, debug_reasons=disabled)
        if index:
            echo()

        echo(colored(f"Rules for {path}", style="bold"))
        echo(f"{len(enabled)} enabled" + (f", {len(disabled)} disabled" if disabled else ""))
        for rule in sorted(enabled, key=lambda candidate: candidate.name):
            sys.stdout.write(f"{_rule_line(rule)}\n")
            sys.stdout.flush()

        if disabled:
            echo()
            echo(colored("Disabled", style="bold"))
            for rule_type, reason in sorted(
                disabled.items(),
                key=lambda item: item[0].name,
            ):
                echo(f"  {rule_type.name} {colored(f'({reason})', color='gray')}")


def validate_command(config: Path | None = None) -> None:
    """Validate Rattle configuration.

    Args:
        config: Config file to validate. Defaults to pyproject.toml.
    """
    config_path = config or Path("pyproject.toml")
    exceptions = validate_config(require_existing_file(config_path, option="path"))

    if exceptions:
        for e in exceptions:
            echo(e, err=True)
        raise SystemExit(1)


def build_app(*, sys_exit_enabled: bool = True) -> Interfacy:
    app = Interfacy(
        sys_exit_enabled=sys_exit_enabled,
        abbreviation_gen=RattleAbbreviationGenerator(),
        bool_negative_prefix=None,
        help_flags=("-h", "--help"),
        plugins=[ValidateConfigPositionalPlugin()],
        executable_flags=[
            ExecutableFlag(
                ("-V", "--version"),
                _version,
                help="Show the version and exit.",
            )
        ],
    )
    app.add_command(lint)
    app.add_command(fix)
    app.add_command(lsp)
    app.add_command(explain_command, name="explain")
    app.add_command(rules_command, name="rules")
    app.add_command(validate_command, name="validate")
    return app


def _coalesce_repeated_list_options(args: list[str] | None) -> list[str] | None:
    if args is None:
        return None

    repeated_options = {"--exclude", "-e", "--extend-exclude", "-ee"}
    output: list[str] = []
    pending: dict[str, int] = {}
    index = 0
    while index < len(args):
        arg = args[index]
        if arg not in repeated_options:
            output.append(arg)
            index += 1
            continue

        option = "--exclude" if arg in {"--exclude", "-e"} else "--extend-exclude"
        if option not in pending:
            pending[option] = len(output)
            output.append(arg)

        index += 1
        while index < len(args) and not args[index].startswith("-"):
            output.insert(pending[option] + 1, args[index])
            for pending_option, pending_index in pending.items():
                if pending_option == option or pending_index > pending[option]:
                    pending[pending_option] = pending_index + 1
            index += 1

    return output


def main(args: list[str] | None = None, *, sys_exit_enabled: bool = True) -> object:
    """Run the rattle CLI."""
    if args is None:
        args = sys.argv[1:]
        if _should_reexec_with_uv(args):
            _reexec_with_uv(args)

    return build_app(sys_exit_enabled=sys_exit_enabled).run(
        args=_coalesce_repeated_list_options(args)
    )


__all__ = [
    "FixState",
    "build_app",
    "fix",
    "lint",
    "lsp",
    "main",
    "rules_command",
    "splash",
    "validate_command",
]
