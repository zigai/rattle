import re
import textwrap
from pathlib import Path

from rattle.config import collect_rules
from rattle.config.models import Config
from rattle.rule import Invalid
from rattle.selectors import QualifiedRule


def _dedent(source: str) -> str:
    return textwrap.dedent(re.sub(r"\A\n", "", source))


def test_source_patterns_match_all_invalid_builtin_fixtures() -> None:
    rules = collect_rules(
        Config(
            enable=[
                QualifiedRule("rattle.rules.blank_lines"),
                QualifiedRule("rattle.rules.modernization"),
                QualifiedRule("rattle.rules.legacy"),
                QualifiedRule("rattle.rules.policy"),
                QualifiedRule("rattle.rules.style"),
                QualifiedRule("rattle.rules.typing"),
            ],
            python_version=None,
        )
    )

    failures: list[str] = []
    for rule in rules:
        if not rule.SOURCE_PATTERNS:
            continue

        for index, raw_case in enumerate(rule.INVALID):
            case = Invalid(code=raw_case) if isinstance(raw_case, str) else raw_case
            source = _dedent(case.code).encode()
            if not rule.should_lint_file(source, Path("invalid.py")):
                failures.append(f"{rule.name}.INVALID[{index}]")

    assert failures == []
