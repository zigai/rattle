from __future__ import annotations

import sys
import unittest
from pathlib import Path

from stdl.st import colored

from rattle.cli.options import build_options, require_existing_path
from rattle.config import (
    collect_rules,
    generate_config,
)
from rattle.rendering.console import echo
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
    return f"  {colored(rule.name, color='light_cyan', style='bold')}{description_text}"


def _rule_description(rule: LintRule) -> str:
    description = " ".join(rule.MESSAGE.split())
    description = description.split(" Learn more:", maxsplit=1)[0]
    description = description.split(" See ", maxsplit=1)[0]
    return description


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


__all__ = ["rules_command"]
