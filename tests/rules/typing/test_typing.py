import pytest

from rattle.rules.typing.no_bare_object_annotations import NoBareObjectAnnotations
from tests.support import run_rule


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
    _runner, reports = run_rule(NoBareObjectAnnotations(), source)

    assert len(reports) == 1


def test_no_bare_object_annotations_respects_string_annotation_shadowing() -> None:
    _runner, reports = run_rule(
        NoBareObjectAnnotations(),
        """
        class object:
            pass

        value: "object"
        """,
    )

    assert reports == []


def test_no_bare_object_annotations_follows_forward_alias_annotation() -> None:
    _runner, reports = run_rule(
        NoBareObjectAnnotations(),
        """
        from typing import TypeAlias

        Object: TypeAlias = object
        value: "Object"
        """,
    )

    assert len(reports) == 1


def test_no_bare_object_annotations_exempts_dunder_eq_other() -> None:
    code = """class Item:
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Item)
    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)
"""
    _runner, reports = run_rule(NoBareObjectAnnotations(), code)
    assert reports == []
