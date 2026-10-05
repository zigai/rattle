from __future__ import annotations

import os
import sys
from collections.abc import Callable

from interfacy import ExecutableFlag, Interfacy, Param
from interfacy.naming import NoAbbreviations
from interfacy.plugins import InterfacyPlugin, PluginContext

from rattle.cli.commands.explain import explain_command
from rattle.cli.commands.fix import fix
from rattle.cli.commands.lint import lint
from rattle.cli.commands.lsp import lsp
from rattle.cli.commands.rules import rules_command
from rattle.cli.commands.validate import validate_command
from rattle.cli.environment import (
    _reexec_with_uv,
    _should_reexec_with_uv,
    _version,
)
from rattle.cli.options import usage_error
from rattle.config import CollectionError, ConfigError

CONFIG_PARAM = Param(short="c", metavar="<path>")
LINT_PARAMS = {
    "config": CONFIG_PARAM,
    "diff": Param(short="d"),
    "exclude": Param(short="e", metavar="<pattern>"),
    "extend_exclude": Param(metavar="<pattern>"),
    "jobs": Param(short="j", metavar="<n>"),
    "quiet": Param(short="q"),
    "rules": Param(short="r", metavar="<selectors>"),
    "stats": Param(short="s"),
    "output_format": Param(metavar="<rattle|vscode|custom>"),
    "output_template": Param(metavar="<template>"),
}
FIX_PARAMS = {
    **LINT_PARAMS,
    "interactive": Param(short="i"),
}
SIGPIPE_EXIT_CODE = 141
DOCS_URL = "https://rattle.readthedocs.io/en/latest"


class CommandErrorPlugin(InterfacyPlugin):
    def wrap_execute(self, _context: PluginContext, call_next: Callable[[], object]) -> object:
        try:
            return call_next()
        except BrokenPipeError:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
            raise SystemExit(SIGPIPE_EXIT_CODE) from None
        except CollectionError as e:
            usage_error(
                f"{e}\nRun `rattle rules` to list the rules enabled for a path, "
                f"or see {DOCS_URL}/guide/builtins.html"
            )
        except ConfigError as e:
            usage_error(f"{e}\nSee {DOCS_URL}/guide/configuration.html")


def build_app() -> Interfacy:
    app = Interfacy(
        abbreviation_gen=NoAbbreviations(),
        help_flags=("--help",),
        allow_args_from_file=False,
        executable_flags=[
            ExecutableFlag(
                ("-V", "--version"),
                _version,
                help="Show the version and exit.",
            )
        ],
        plugins=[CommandErrorPlugin()],
    )
    app.add_command(lint, parameter_settings=LINT_PARAMS)
    app.add_command(fix, parameter_settings=FIX_PARAMS)
    app.add_command(
        lsp,
        parameter_settings={
            "config": CONFIG_PARAM,
            "tcp": Param(metavar="<port>"),
            "ws": Param(metavar="<port>"),
            "debounce_interval": Param(metavar="<seconds>"),
        },
    )
    app.add_command(
        explain_command,
        name="explain",
        parameter_settings={"config": CONFIG_PARAM},
    )
    app.add_command(
        rules_command,
        name="rules",
        parameter_settings={"config": CONFIG_PARAM, "test": Param(short="t")},
    )
    app.add_command(
        validate_command,
        name="validate",
        parameter_settings={"config": Param(kind="positional", metavar="CONFIG")},
    )
    return app


def _coalesce_repeated_list_options(args: list[str]) -> list[str]:
    options = {
        "--exclude": "--exclude",
        "-e": "--exclude",
        "--extend-exclude": "--extend-exclude",
    }
    patterns: dict[str, list[str]] = {"--exclude": [], "--extend-exclude": []}
    output: list[str] = []
    index = 0
    while index < len(args) and args[index] != "--":
        name, separator, value = args[index].partition("=")
        option = options.get(name)
        if option is None or (not separator and index + 1 == len(args)):
            output.append(args[index])
            index += 1
        elif separator:
            patterns[option].append(value)
            index += 1
        else:
            patterns[option].append(args[index + 1])
            index += 2

    for option, values in patterns.items():
        if values:
            output.extend((option, *values))
    return output + args[index:]


def main(args: list[str] | None = None) -> object:
    """Run the rattle CLI."""
    if args is None:
        args = sys.argv[1:]
        if _should_reexec_with_uv(args):
            _reexec_with_uv(args)

    return build_app().run(args=_coalesce_repeated_list_options(args))


__all__ = ["build_app", "main"]
