from __future__ import annotations

import sys

from interfacy import ExecutableFlag, Interfacy, Param
from interfacy.naming import NoAbbreviations

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

CONFIG_PARAM = Param(short="c")
LINT_PARAMS = {
    "config": CONFIG_PARAM,
    "diff": Param(short="d"),
    "exclude": Param(short="e"),
    "extend_exclude": Param(short="ee"),
    "jobs": Param(short="j"),
    "quiet": Param(short="q"),
    "rules": Param(short="r"),
}
FIX_PARAMS = {
    **LINT_PARAMS,
    "interactive": Param(short="i"),
}


def build_app(*, sys_exit_enabled: bool = True) -> Interfacy:
    app = Interfacy(
        sys_exit_enabled=sys_exit_enabled,
        abbreviation_gen=NoAbbreviations(),
        bool_negative_prefix=None,
        help_flags=("-h", "--help"),
        executable_flags=[
            ExecutableFlag(
                ("-V", "--version"),
                _version,
                help="Show the version and exit.",
            )
        ],
    )
    app.add_command(lint, parameter_settings=LINT_PARAMS)
    app.add_command(fix, parameter_settings=FIX_PARAMS)
    app.add_command(lsp, parameter_settings={"config": CONFIG_PARAM})
    app.add_command(
        explain_command,
        name="explain",
        parameter_settings={"config": CONFIG_PARAM},
    )
    app.add_command(
        rules_command,
        name="rules",
        parameter_settings={"config": CONFIG_PARAM},
    )
    app.add_command(
        validate_command,
        name="validate",
        parameter_settings={"config": Param(kind="positional", metavar="CONFIG")},
    )
    return app


def _coalesce_repeated_list_options(args: list[str]) -> list[str]:
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


__all__ = ["build_app", "main"]
