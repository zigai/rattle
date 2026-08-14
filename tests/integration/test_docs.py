import re
from pathlib import Path

from rattle.rule_loading import _builtin_rule_types

RULE_COUNT_PATTERN = re.compile(r"(?m)^- (?P<count>\d+) built-in lint rules$")


def _public_rule_count(path: Path) -> int:
    match = RULE_COUNT_PATTERN.search(path.read_text())
    assert match is not None, f"missing built-in rule count in {path}"
    return int(match.group("count"))


def test_public_builtin_rule_counts_are_current(project_root: Path) -> None:
    expected = len(_builtin_rule_types())
    assert _public_rule_count(project_root / "README.md") == expected
    assert _public_rule_count(project_root / "docs" / "index.md") == expected
