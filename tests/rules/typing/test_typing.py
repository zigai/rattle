from pathlib import Path
from textwrap import dedent

import pytest

from rattle.config.models import Config
from rattle.diagnostics import LintViolation
from rattle.engine import LintRunner
from rattle.rule import LintRule
from rattle.rules.typing.no_bare_object_annotations import NoBareObjectAnnotations


def _reports(
    rule: LintRule,
    source: str,
    *,
    path: Path = Path("sample.py"),
) -> tuple[LintRunner, list[LintViolation]]:
    runner = LintRunner(path, dedent(source).encode())
    return runner, list(runner.collect_violations([rule], Config(path=path)))


@pytest.mark.parametrize(
    "source",
    [
        """
        from typing import TypeAlias

        Object: TypeAlias = object
        OtherObject: TypeAlias = Object
        value: OtherObject
        """,
        """
        type Object = object
        value: Object
        """,
        """
        from typing import TypeAlias

        MaybeObject: TypeAlias = object | None
        value: MaybeObject
        """,
    ],
)
def test_no_bare_object_annotations_follows_explicit_type_aliases(source: str) -> None:
    _runner, reports = _reports(NoBareObjectAnnotations(), source)

    assert len(reports) == 1


def test_no_bare_object_annotations_respects_string_annotation_shadowing() -> None:
    _runner, reports = _reports(
        NoBareObjectAnnotations(),
        """
        class object:
            pass

        value: "object"
        """,
    )

    assert reports == []


def test_no_bare_object_annotations_follows_forward_alias_annotation() -> None:
    _runner, reports = _reports(
        NoBareObjectAnnotations(),
        """
        from typing import TypeAlias

        Object: TypeAlias = object
        value: "Object"
        """,
    )

    assert len(reports) == 1
