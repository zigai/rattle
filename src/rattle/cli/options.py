from __future__ import annotations

from pathlib import Path
from typing import NoReturn

from rattle.cli.environment import DEBUG_ENV, METRICS_ENV, _configure_logging, _env_flag
from rattle.config import (
    RuleRegistry,
    generate_config,
    parse_rule,
)
from rattle.config.models import Options
from rattle.rendering.console import echo
from rattle.rendering.models import OutputFormat
from rattle.selectors import RuleSelector

STDIN = Path("-")


def usage_error(message: str) -> NoReturn:
    echo(message, err=True)
    raise SystemExit(2)


def require_existing_file(path: Path, *, option: str) -> Path:
    if not path.is_file():
        usage_error(f"{option}: no such file: {path}")
    return path


def require_existing_path(path: Path, *, argument: str) -> Path:
    if not path.exists():
        usage_error(f"{argument}: no such file or directory: {path}")
    return path


def _resolve_input_paths(paths: tuple[Path, ...]) -> tuple[Path, ...]:
    if not paths:
        return (Path.cwd(),)
    if paths[0] == STDIN:
        if len(paths) != 2:
            usage_error(
                'Reading from stdin needs exactly one path after "-" to name the code, '
                "for example: rattle lint - src/module.py"
            )
        return paths
    return tuple(require_existing_path(path, argument="path") for path in paths)


def require_known_rules(paths: tuple[Path, ...], options: Options) -> None:
    if not options.rules:
        return

    targets = paths[1:] if paths[0] == STDIN else paths
    for path in targets:
        config = generate_config(path.resolve(), options=options)
        registry = RuleRegistry.load(
            (*config.rule_imports, *config.enable, *config.disable),
            root=config.root,
            enable_root_import=config.enable_root_import,
            strict=True,
        )
        for selector in options.rules:
            registry.resolve(selector)


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
    output_format: OutputFormat | None = None,
    output_template: str | None = None,
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
        output_format=output_format,
        output_template=output_template,
        print_metrics=_env_flag(METRICS_ENV),
    )


__all__ = [
    "build_options",
    "parse_rules",
    "require_existing_file",
    "require_existing_path",
    "require_known_rules",
]
