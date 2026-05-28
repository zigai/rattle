# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import logging
import sys
import unittest
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from interfacy import ExecutableFlag, Interfacy
from stdl.st import colored

from rattle.__version__ import __version__

from .api import rattle_paths
from .config import collect_rules, generate_config, parse_rule, validate_config
from .console import AsyncConsole, echo, getchar
from .ftypes import (
    STDIN,
    Config,
    LSPOptions,
    Metrics,
    Options,
    OutputFormat,
    Result,
    RuleSelector,
    Tags,
)
from .output import render_console_result
from .rule import LintRule
from .testing import generate_lint_rule_test_cases
from .util import capture


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
) -> bool:
    rendered = render_console_result(
        result,
        path=_display_path(result.path),
        show_diff=show_diff,
        output_format=output_format,
        output_template=output_template,
        brief=brief,
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


@dataclass
class FixState:
    exit_code: int = 0
    violations: int = 0
    autofixes: int = 0
    fixed: int = 0


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
    return f"rattle, version {__version__}"


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
        return paths
    return tuple(require_existing_path(path, argument="path") for path in paths)


def parse_rules(rules: str | None) -> list[RuleSelector]:
    selectors = (selector.strip() for selector in (rules or "").split(","))
    return sorted({parse_rule(selector, Path.cwd()) for selector in selectors if selector}, key=str)


def build_options(
    *,
    rules: str | None = None,
    tags: str | None = None,
    jobs: int | None = None,
    config_file: Path | None = None,
    output_format: OutputFormat | None = None,
    output_template: str | None = None,
    print_metrics: bool = False,
    no_format: bool = False,
    quiet: bool = False,
    debug: bool = False,
) -> Options:
    if debug and quiet:
        usage_error("--debug and --quiet cannot be used together")
    if jobs is not None and jobs < 1:
        usage_error("--jobs must be an integer greater than or equal to 1")

    debug_option = True if debug else False if quiet else None
    level = logging.WARNING
    if debug_option is not None:
        level = logging.DEBUG if debug_option else logging.ERROR
    logging.basicConfig(level=level, stream=sys.stderr)

    return Options(
        debug=debug_option,
        config_file=(
            require_existing_file(config_file, option="--config-file") if config_file else None
        ),
        jobs=jobs,
        tags=Tags.parse(tags),
        rules=parse_rules(rules),
        output_format=output_format,
        output_template=output_template,
        print_metrics=print_metrics,
        no_format=no_format,
    )


def lint(
    *paths: Path,
    rules: str | None = None,
    tags: str | None = None,
    jobs: int | None = None,
    config_file: Path | None = None,
    output_format: OutputFormat | None = None,
    output_template: str | None = None,
    diff: bool = False,
    brief: bool = False,
    quiet: bool = False,
    print_metrics: bool = False,
    debug: bool = False,
) -> None:
    """
    Lint one or more paths and return suggestions.

    Args:
        paths: Files or directories to lint. Use "- <FILENAME>" to lint stdin as a file.
        debug: Increase logging verbosity.
        quiet: Decrease logging verbosity.
        config_file: Override default config file search behavior.
        jobs: Number of worker processes to use when linting multiple files.
        tags: Select or filter rules by comma-separated tags.
        rules: Override configured rules with comma-separated selectors.
        output_format: Select output format type.
        output_template: Python format template to use with custom output.
        print_metrics: Print metrics for this run.
        brief: Print each diagnostic on one line.
        diff: Show diffs for suggested changes.

    pass "- <FILENAME>" for STDIN representing <FILENAME>
    """
    paths = _resolve_input_paths(paths)

    runtime_options = build_options(
        debug=debug,
        quiet=quiet,
        config_file=config_file,
        jobs=jobs,
        tags=tags,
        rules=rules,
        output_format=output_format,
        output_template=output_template,
        print_metrics=print_metrics,
    )
    exit_code = 0
    visited: set[Path] = set()
    violation_files: set[Path] = set()
    error_files: set[Path] = set()
    violations = 0
    autofixes = 0
    console = AsyncConsole()
    try:
        for result in rattle_paths(
            paths,
            include_diff=diff,
            allow_cached_dirty_results=True,
            options=runtime_options,
            metrics_hook=_metrics_hook(console, runtime_options.print_metrics),
        ):
            visited.add(result.path)
            if not result.violation and not result.error:
                continue
            config = result.config or _output_config_for_path(result.path, runtime_options)
            if _submit_result(
                console,
                result,
                show_diff=diff,
                output_format=config.output_format,
                output_template=config.output_template,
                brief=brief,
            ):
                if result.violation:
                    violation_files.add(result.path)
                    violations += 1
                    exit_code |= 1
                    if result.violation.autofixable:
                        autofixes += 1
                if result.error:
                    error_files.add(result.path)
                    exit_code |= 2

        console.submit(
            splash(visited, violation_files, error_files, violations, autofixes), err=True
        )
    finally:
        console.close()
    if exit_code:
        raise SystemExit(exit_code)


def fix(
    *paths: Path,
    rules: str | None = None,
    tags: str | None = None,
    quiet: bool = False,
    jobs: int | None = None,
    output_format: OutputFormat | None = None,
    output_template: str | None = None,
    config_file: Path | None = None,
    diff: bool = False,
    automatic: bool = False,
    interactive: bool = False,
    print_metrics: bool = False,
    no_format: bool = False,
    brief: bool = False,
    debug: bool = False,
) -> None:
    """
    Lint and autofix one or more files and return results.

    Args:
        paths: Files or directories to lint and fix. Use "- <FILENAME>" to fix stdin.
        debug: Increase logging verbosity.
        quiet: Decrease logging verbosity.
        config_file: Override default config file search behavior.
        jobs: Number of worker processes to use when linting multiple files.
        tags: Select or filter rules by comma-separated tags.
        rules: Override configured rules with comma-separated selectors.
        output_format: Select output format type.
        output_template: Python format template to use with custom output.
        print_metrics: Print metrics for this run.
        no_format: Skip configured post-fix formatting.
        interactive: Prompt before applying each autofix.
        automatic: Apply autofixes without prompting.
        brief: Print each diagnostic on one line.
        diff: Show diffs even when applying fixes automatically.

    pass "- <FILENAME>" for STDIN representing <FILENAME>;
    this will ignore "--interactive" and always use "--automatic"
    """
    if interactive and automatic:
        usage_error("--interactive and --automatic cannot be used together")

    paths = _resolve_input_paths(paths)

    runtime_options = build_options(
        debug=debug,
        quiet=quiet,
        config_file=config_file,
        jobs=jobs,
        tags=tags,
        rules=rules,
        output_format=output_format,
        output_template=output_template,
        print_metrics=print_metrics,
        no_format=no_format,
    )
    is_stdin = bool(paths[0] and str(paths[0]) == "-")
    interactive = interactive and not is_stdin
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
            config = result.config or _output_config_for_path(result.path, runtime_options)
            # for STDIN, we need STDOUT to equal the fixed content, so
            # move everything else to STDERR
            if _submit_result(
                console,
                result,
                show_diff=interactive or diff,
                stderr=is_stdin,
                output_format=config.output_format,
                output_template=config.output_template,
                brief=brief,
            ):
                if result.violation:
                    violation_files.add(result.path)
                if result.error:
                    error_files.add(result.path)
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
    finally:
        console.close()
    if state.exit_code:
        raise SystemExit(state.exit_code)


def lsp(
    *,
    rules: str | None = None,
    config_file: Path | None = None,
    tags: str | None = None,
    ws: int | None = None,
    tcp: int | None = None,
    debounce_interval: float = LSPOptions.debounce_interval,
    no_stdio: bool = False,
    debug: bool = False,
    quiet: bool = False,
) -> None:
    """Start the language server.

    https://microsoft.github.io/language-server-protocol/.

    Args:
        debug: Increase logging verbosity.
        quiet: Decrease logging verbosity.
        config_file: Override default config file search behavior.
        tags: Select or filter rules by comma-separated tags.
        rules: Override configured rules with comma-separated selectors.
        no_stdio: Disable stdio transport when using TCP or WebSocket.
        tcp: Port to serve LSP over TCP.
        ws: Port to serve LSP over WebSocket.
        debounce_interval: Delay in seconds for server-side debounce.
    """
    from .lsp import LSP

    lsp_options = LSPOptions(
        tcp=tcp,
        ws=ws,
        stdio=not no_stdio,
        debounce_interval=debounce_interval,
    )
    LSP(
        build_options(
            debug=debug,
            quiet=quiet,
            config_file=config_file,
            tags=tags,
            rules=rules,
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
    code = rule.CODE or "-----"
    labels: list[str] = []
    if rule.TAGS:
        labels.append(",".join(sorted(rule.TAGS)))
    labels_text = ", ".join(labels)
    suffix = f" {colored(f'[{labels_text}]', color='gray')}" if labels_text else ""
    description = _rule_description(rule)
    description_text = f" - {colored(description, color='gray')}" if description else ""
    return (
        f"  {colored(code, color='light_cyan', style='bold')} "
        f"{colored(rule.name, style='bold')}{suffix}{description_text}"
    )


def _rule_description(rule: LintRule) -> str:
    message = getattr(rule, "MESSAGE", "")
    if not isinstance(message, str):
        return ""

    description = " ".join(message.split())
    description = description.split(" Learn more:", maxsplit=1)[0]
    description = description.split(" See ", maxsplit=1)[0]
    return description


def rules_command(
    *paths: Path,
    rules: str | None = None,
    tags: str | None = None,
    config_file: Path | None = None,
    test: bool = False,
    debug: bool = False,
    quiet: bool = False,
) -> None:
    """Display or test currently enabled lint rules.

    Args:
        paths: Files or directories whose rules should be shown.
        debug: Increase logging verbosity.
        quiet: Decrease logging verbosity.
        config_file: Override default config file search behavior.
        tags: Select or filter rules by comma-separated tags.
        rules: Override configured rules with comma-separated selectors.
        test: Test lint rules and their VALID/INVALID cases.
    """
    resolved_paths = tuple(require_existing_path(path, argument="path") for path in paths) or (
        Path.cwd(),
    )

    runtime_options = build_options(
        debug=debug,
        quiet=quiet,
        config_file=config_file,
        tags=tags,
        rules=rules,
    )

    if test:
        lint_rules_by_name: dict[str, LintRule] = {}
        for path in resolved_paths:
            config = generate_config(path.resolve(), options=runtime_options)
            for rule in collect_rules(config):
                lint_rules_by_name[rule.qualified_name()] = rule
        _run_rule_tests(
            [
                rule
                for _name, rule in sorted(
                    lint_rules_by_name.items(),
                    key=lambda item: (item[1].CODE or "", item[1].name),
                )
            ]
        )
        return

    for index, path in enumerate(resolved_paths):
        path = path.resolve()
        config = generate_config(path, options=runtime_options)
        disabled: dict[type[LintRule], str] = {}
        enabled = collect_rules(config, debug_reasons=disabled)
        if index:
            echo()

        echo(colored(f"Rules for {path}", style="bold"))
        echo(f"{len(enabled)} enabled" + (f", {len(disabled)} disabled" if disabled else ""))
        for rule in sorted(enabled, key=lambda candidate: (candidate.CODE or "", candidate.name)):
            echo(_rule_line(rule))
            if rule.settings:
                settings = ", ".join(
                    f"{key}={value!r}" for key, value in sorted(rule.settings.items())
                )
                echo(f"      {colored(settings, color='gray')}")

        if disabled:
            echo()
            echo(colored("Disabled", style="bold"))
            for rule_type, reason in sorted(
                disabled.items(),
                key=lambda item: (item[0].CODE or "", item[0].__name__),
            ):
                code = rule_type.CODE or "-----"
                echo(
                    f"  {colored(code, color='gray')} "
                    f"{rule_type.__name__} "
                    f"{colored(f'({reason})', color='gray')}"
                )


def validate_command(*paths: Path) -> None:
    """Validate config.

    Args:
        paths: Config file to validate. Defaults to pyproject.toml.
    """
    if len(paths) > 1:
        usage_error("validate accepts at most one path")
    config_path = paths[0] if paths else Path("pyproject.toml")
    exceptions = validate_config(require_existing_file(config_path, option="path"))

    if exceptions:
        for e in exceptions:
            echo(e, err=True)
        raise SystemExit(255)


def build_app(*, sys_exit_enabled: bool = True) -> Interfacy:
    app = Interfacy(
        sys_exit_enabled=sys_exit_enabled,
        executable_flags=[
            ExecutableFlag(
                ("--version", "-V"),
                _version,
                help="Show the version and exit.",
            )
        ],
    )
    app.add_type_parser(OutputFormat, lambda value: OutputFormat(value.lower()))
    app.add_command(lint)
    app.add_command(fix)
    app.add_command(lsp)
    app.add_command(rules_command, name="rules")
    app.add_command(validate_command, name="validate")
    return app


def main(args: list[str] | None = None, *, sys_exit_enabled: bool = True) -> object:
    """Run the rattle CLI."""
    return build_app(sys_exit_enabled=sys_exit_enabled).run(args=args)


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
