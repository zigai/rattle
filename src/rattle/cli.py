# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import logging
import sys
import unittest
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import click

from rattle import __version__

from .api import print_result, rattle_paths
from .config import collect_rules, generate_config, parse_rule, validate_config
from .ftypes import Config, LSPOptions, Options, OutputFormat, Tags
from .rule import LintRule
from .testing import generate_lint_rule_test_cases
from .util import capture


def splash(visited: set[Path], dirty: set[Path], autofixes: int = 0, fixed: int = 0) -> None:
    def f(v: int) -> str:
        return "file" if v == 1 else "files"

    if dirty:
        reports = [
            click.style(f"{len(visited)} {f(len(visited))} checked"),
            click.style(f"{len(dirty)} {f(len(dirty))} with errors", fg="yellow", bold=True),
        ]
        if autofixes:
            word = "fix" if autofixes == 1 else "fixes"
            reports += [click.style(f"{autofixes} auto-{word} available", bold=True)]
        if fixed:
            word = "fix" if fixed == 1 else "fixes"
            reports += [click.style(f"{fixed} {word} applied", bold=True)]

        message = ", ".join(reports)
        click.secho(message, err=True)
    else:
        click.secho(f"{len(visited)} {f(len(visited))} clean", err=True)


def _output_config_for_path(path: Path, options: Options) -> Config:
    return generate_config(path, options=options)


@dataclass
class _FixState:
    exit_code: int = 0
    autofixes: int = 0
    fixed: int = 0


def _prompt_for_fix(generator: capture, state: _FixState) -> bool:
    answer = click.prompt(
        "Apply autofix?",
        default="y",
        type=click.Choice("ynq", case_sensitive=False),
    )
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
    state: _FixState,
) -> bool:
    error = getattr(result, "error", None)
    if error:
        state.exit_code |= 2
        return False

    violation = getattr(result, "violation", None)
    if not violation:
        return False

    if interactive and violation.autofixable:
        state.autofixes += 1
        return _prompt_for_fix(generator, state)

    if autofix and violation.autofixable:
        state.autofixes += 1
        state.fixed += 1
        return False

    state.exit_code |= 1
    return False


@click.group()
@click.pass_context
@click.version_option(__version__, "--version", "-V", prog_name="rattle")
@click.option("--debug/--quiet", is_flag=True, default=None, help="Increase decrease verbosity")
@click.option(
    "--config-file",
    "-c",
    type=click.Path(dir_okay=False, exists=True, path_type=Path),
    default=None,
    help="Override default config file search behavior",
)
@click.option(
    "--tags",
    type=str,
    default="",
    help="Select or filter rules by tags",
)
@click.option(
    "--rules",
    type=str,
    default="",
    help="Override configured rules",
)
@click.option(
    "--output-format",
    "-o",
    type=click.Choice([o.name for o in OutputFormat], case_sensitive=False),
    show_choices=True,
    default=None,
    help="Select output format type",
)
@click.option(
    "--output-template",
    type=str,
    default="",
    help="Python format template to use with output format 'custom'",
)
@click.option("--print-metrics", is_flag=True, help="Print metrics of this run")
def main(
    ctx: click.Context,
    debug: bool | None,
    config_file: Path | None,
    tags: str,
    rules: str,
    output_format: OutputFormat | None,
    output_template: str,
    print_metrics: bool,
) -> None:
    level = logging.WARNING
    if debug is not None:
        level = logging.DEBUG if debug else logging.ERROR
    logging.basicConfig(level=level, stream=sys.stderr)

    ctx.obj = Options(
        debug=debug,
        config_file=config_file,
        tags=Tags.parse(tags),
        rules=sorted(
            {parse_rule(r, Path.cwd()) for r in (rs.strip() for rs in rules.split(",")) if r},
            key=str,
        ),
        output_format=output_format,
        output_template=output_template,
        print_metrics=print_metrics,
    )


@main.command()
@click.pass_context
@click.option("--diff", "-d", is_flag=True, help="Show diff of suggested changes")
@click.argument("paths", nargs=-1, type=click.Path(path_type=Path))
def lint(
    ctx: click.Context,
    diff: bool,
    paths: Sequence[Path],
) -> None:
    """
    Lint one or more paths and return suggestions.

    pass "- <FILENAME>" for STDIN representing <FILENAME>
    """
    options: Options = ctx.obj

    if not paths:
        paths = [Path.cwd()]

    exit_code = 0
    visited: set[Path] = set()
    dirty: set[Path] = set()
    autofixes = 0
    for result in rattle_paths(
        paths, options=options, metrics_hook=print if options.print_metrics else None
    ):
        visited.add(result.path)
        config = _output_config_for_path(result.path, options)
        if print_result(
            result,
            show_diff=diff,
            output_format=config.output_format,
            output_template=config.output_template,
        ):
            dirty.add(result.path)
            if result.violation:
                exit_code |= 1
                if result.violation.autofixable:
                    autofixes += 1
            if result.error:
                exit_code |= 2

    splash(visited, dirty, autofixes)
    ctx.exit(exit_code)


@main.command()
@click.pass_context
@click.option(
    "--interactive/--automatic",
    "-i/-a",
    is_flag=True,
    default=True,
    help="how to apply fixes; interactive by default unless STDIN",
)
@click.option("--diff", "-d", is_flag=True, help="show diff even with --automatic")
@click.argument("paths", nargs=-1, type=click.Path(path_type=Path))
def fix(
    ctx: click.Context,
    interactive: bool,
    diff: bool,
    paths: Sequence[Path],
) -> None:
    """
    Lint and autofix one or more files and return results.

    pass "- <FILENAME>" for STDIN representing <FILENAME>;
    this will ignore "--interactive" and always use "--automatic"
    """
    options: Options = ctx.obj

    if not paths:
        paths = [Path.cwd()]

    is_stdin = bool(paths[0] and str(paths[0]) == "-")
    interactive = interactive and not is_stdin
    autofix = not interactive
    state = _FixState()

    visited: set[Path] = set()
    dirty: set[Path] = set()

    # TODO: make this parallel
    generator = capture(
        rattle_paths(
            paths,
            autofix=autofix,
            options=options,
            parallel=False,
            metrics_hook=print if options.print_metrics else None,
        )
    )
    for result in generator:
        visited.add(result.path)
        config = _output_config_for_path(result.path, options)
        # for STDIN, we need STDOUT to equal the fixed content, so
        # move everything else to STDERR
        if print_result(
            result,
            show_diff=interactive or diff,
            stderr=is_stdin,
            output_format=config.output_format,
            output_template=config.output_template,
        ):
            dirty.add(result.path)
        if _update_fix_state(
            result,
            autofix=autofix,
            interactive=interactive,
            generator=generator,
            state=state,
        ):
            break

    splash(visited, dirty, state.autofixes, state.fixed)
    ctx.exit(state.exit_code)


@main.command()
@click.pass_context
@click.option("--stdio", type=bool, default=True, help="Serve LSP over stdio")
@click.option("--tcp", type=int, help="Port to serve LSP over")
@click.option("--ws", type=int, help="Port to serve WS over")
@click.option(
    "--debounce-interval",
    type=float,
    default=LSPOptions.debounce_interval,
    help="Delay in seconds for server-side debounce",
)
def lsp(
    ctx: click.Context,
    stdio: bool,
    tcp: int | None,
    ws: int | None,
    debounce_interval: float,
) -> None:
    """
    Start server for:
    https://microsoft.github.io/language-server-protocol/.
    """
    from .lsp import LSP

    main_options = ctx.obj
    lsp_options = LSPOptions(
        tcp=tcp,
        ws=ws,
        stdio=stdio,
        debounce_interval=debounce_interval,
    )
    LSP(main_options, lsp_options).start()


@main.command()
@click.pass_context
@click.argument("rules", nargs=-1, required=True, type=str)
def test(ctx: click.Context, rules: Sequence[str]) -> None:
    """Test lint rules and their VALID/INVALID cases."""
    qual_rules = [parse_rule(rule, Path.cwd().resolve()) for rule in rules]
    lint_rules = collect_rules(Config(enable=qual_rules, disable=[], python_version=None))
    test_cases = generate_lint_rule_test_cases(lint_rules)

    test_suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for test_case in test_cases:
        test_suite.addTest(loader.loadTestsFromTestCase(test_case))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    if not result.wasSuccessful():
        ctx.exit(1)


@main.command()
@click.pass_context
@click.argument("paths", nargs=-1, type=click.Path(exists=True, path_type=Path))
def debug(ctx: click.Context, paths: Sequence[Path]) -> None:
    """Print materialized configuration for paths."""
    options: Options = ctx.obj

    if not paths:
        paths = [Path.cwd()]

    try:
        from rich import print as pprint
    except ImportError:
        from pprint import pprint

    pprint(options)

    for path in paths:
        path = path.resolve()
        config = generate_config(path, options=options)
        disabled: dict[type[LintRule], str] = {}
        enabled = collect_rules(config, debug_reasons=disabled)
        resolved_settings = {}
        for rule in sorted(enabled, key=str):
            settings = dict(rule.settings)
            if settings:
                resolved_settings[str(rule)] = settings

        print(">>> ", path)
        pprint(config)
        print("enabled:", sorted(str(rule) for rule in enabled))
        print("settings:", resolved_settings)
        print(
            "disabled:",
            sorted(f"{rule()} ({reason})" for rule, reason in disabled.items()),
        )


@main.command(name="validate-config")
@click.pass_context
@click.argument("path", nargs=1, type=click.Path(exists=True, path_type=Path))
def validate_config_command(_ctx: click.Context, path: Path) -> None:
    """Validate the config provided."""
    exceptions = validate_config(path)

    try:
        from rich import print as pprint
    except ImportError:
        from pprint import pprint

    if exceptions:
        for e in exceptions:
            pprint(e)
        sys.exit(-1)
