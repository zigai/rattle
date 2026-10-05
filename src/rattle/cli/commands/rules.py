from __future__ import annotations

import json as json_module
import unittest
from pathlib import Path

from rattle.cli.options import build_options, require_existing_path, usage_error
from rattle.config import (
    collect_rules,
    generate_config,
)
from rattle.config.models import Options
from rattle.rendering.console import colored, echo
from rattle.rule import LintRule
from rattle.testing import generate_lint_rule_test_cases


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
    return f"  {colored(rule.name, 'light_cyan', bold=True)}{description_text}"


def _rule_description(rule: LintRule) -> str:
    description = " ".join(rule.MESSAGE.split())
    description = description.split(" Learn more:", maxsplit=1)[0]
    description = description.split(" See ", maxsplit=1)[0]
    return description


def _test_rules(paths: tuple[Path, ...], options: Options) -> None:
    lint_rules_by_name: dict[str, LintRule] = {}
    for path in paths:
        path_config = generate_config(path.resolve(), options=options)
        for rule in collect_rules(path_config):
            lint_rules_by_name[rule.qualified_name()] = rule
    _run_rule_tests(sorted(lint_rules_by_name.values(), key=lambda rule: rule.name))


def _print_rules(path: Path, options: Options) -> None:
    disabled: dict[type[LintRule], str] = {}
    enabled = collect_rules(generate_config(path, options=options), debug_reasons=disabled)
    echo(colored(f"Rules for {path}", bold=True))
    echo(f"{len(enabled)} enabled" + (f", {len(disabled)} disabled" if disabled else ""))
    for rule in sorted(enabled, key=lambda candidate: candidate.name):
        echo(_rule_line(rule))

    if disabled:
        echo()
        echo(colored("Disabled", bold=True))
        for rule_type, reason in sorted(disabled.items(), key=lambda item: item[0].name):
            echo(f"  {rule_type.name} {colored(f'({reason})', 'gray')}")


def _rules_json_data(path: Path, options: Options) -> dict[str, object]:
    disabled: dict[type[LintRule], str] = {}
    enabled = collect_rules(generate_config(path, options=options), debug_reasons=disabled)
    return {
        "path": path.as_posix(),
        "enabled": [
            {"name": rule.name, "description": _rule_description(rule)}
            for rule in sorted(enabled, key=lambda candidate: candidate.name)
        ],
        "disabled": [
            {"name": rule_type.name, "reason": reason}
            for rule_type, reason in sorted(disabled.items(), key=lambda item: item[0].name)
        ],
    }


def rules_command(
    *paths: Path,
    config: Path | None = None,
    test: bool = False,
    json: bool = False,
) -> None:
    """Display or test currently enabled lint rules.

    Args:
        paths: Files or directories whose rules should be shown.
        config: Use this config file instead of discovered configuration.
        test: Test lint rules and their VALID/INVALID cases.
        json: Print enabled and disabled rules as JSON.
    """
    if test and json:
        usage_error("--test and --json cannot be used together")

    resolved_paths = tuple(require_existing_path(path, argument="path") for path in paths) or (
        Path.cwd(),
    )

    runtime_options = build_options(
        config=config,
    )

    if test:
        _test_rules(resolved_paths, runtime_options)
        return

    if json:
        echo(
            json_module.dumps(
                [_rules_json_data(path.resolve(), runtime_options) for path in resolved_paths],
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    for index, path in enumerate(resolved_paths):
        if index:
            echo()
        _print_rules(path.resolve(), runtime_options)


__all__ = ["rules_command"]
