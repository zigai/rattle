import re
import textwrap
from pathlib import Path

from rattle.config import collect_rules
from rattle.ftypes import Config, Invalid, QualifiedRule


def _dedent(source: str) -> str:
    return textwrap.dedent(re.sub(r"\A\n", "", source))


def _invalid_case(value: str | Invalid) -> Invalid:
    if isinstance(value, str):
        return Invalid(code=value)
    return value


def test_source_patterns_match_all_invalid_builtin_fixtures() -> None:
    rules = collect_rules(
        Config(
            enable=[
                QualifiedRule("rattle.rules.blank_lines"),
                QualifiedRule("rattle.rules.fixit"),
                QualifiedRule("rattle.rules.fixit_extra"),
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
            case = _invalid_case(raw_case)
            source = _dedent(case.code).encode()
            if not rule.should_lint_file(source, Path("invalid.py")):
                failures.append(f"{rule.name}.INVALID[{index}]")

    assert failures == []
