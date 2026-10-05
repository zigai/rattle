from __future__ import annotations

import json as json_module
from pathlib import Path

from rattle.cli.options import build_options
from rattle.config import (
    collect_rule_types,
    generate_config,
    parse_rule,
    resolve_rule_type,
)
from rattle.rendering.console import echo
from rattle.rendering.rule_info import RuleInfo, render_console_rule_info


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
    parsed_selector = parse_rule(rule, materialized_config.root)
    rule_type = resolve_rule_type(materialized_config, parsed_selector)
    enabled_rule_types = set(collect_rule_types(materialized_config))

    info = RuleInfo.from_rule(rule_type, enabled=rule_type in enabled_rule_types)
    if json:
        echo(json_module.dumps(info.to_json_data(), ensure_ascii=False, indent=2))
        return

    render_console_rule_info(info)


__all__ = ["explain_command"]
