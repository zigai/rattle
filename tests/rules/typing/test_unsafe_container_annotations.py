from pathlib import Path
from textwrap import dedent

import pytest

from rattle.config.models import Config
from rattle.diagnostics import LintViolation
from rattle.engine import LintRunner
from rattle.rule import LintRule
from rattle.rules.typing.no_any_container_annotations import NoAnyContainerAnnotations
from rattle.rules.typing.no_object_mapping_values import NoObjectMappingValues

ANY_MESSAGE = (
    "Replace `Any` in this container annotation with concrete element, key, or value types."
)
OBJECT_MESSAGE = (
    "Replace this broad `object` mapping value with a concrete value type or parsed owner type."
)


def _reports(
    rule: LintRule,
    source: str,
    *,
    path: Path = Path("sample.py"),
) -> tuple[LintRunner, list[LintViolation]]:
    runner = LintRunner(path, dedent(source).encode())
    return runner, list(runner.collect_violations([rule], Config(path=path)))


def test_public_rule_names_match_the_documented_selectors() -> None:
    assert NoAnyContainerAnnotations.name == "no-any-container-annotations"
    assert NoObjectMappingValues.name == "no-object-mapping-values"


@pytest.mark.parametrize(
    "annotation",
    [
        "list[Any]",
        "set[Any]",
        "frozenset[Any]",
        "typing.List[Any]",
        "t.Set[Any]",
        "deque[Any]",
        "collections.deque[Any]",
        "Sequence[Any]",
        "cabc.MutableSequence[Any]",
        "cabc.Iterable[Any]",
        "cabc.Iterator[Any]",
    ],
)
def test_any_rule_reports_standard_element_container_spellings(annotation: str) -> None:
    _runner, reports = _reports(
        NoAnyContainerAnnotations(),
        f"""
        import collections
        import collections.abc as cabc
        import typing
        import typing as t
        from collections import deque
        from collections.abc import Sequence
        from typing import Any

        value: {annotation}
        """,
    )

    assert [report.message for report in reports] == [ANY_MESSAGE]


@pytest.mark.parametrize(
    "annotation",
    [
        "dict[Any, int]",
        "dict[str, Any]",
        "typing.Dict[Any, int]",
        "Mapping[str, Any]",
        "cabc.MutableMapping[Any, str]",
        "collections.defaultdict[str, Any]",
        "collections.OrderedDict[Any, str]",
        "collections.Counter[Any]",
        "collections.ChainMap[str, Any]",
    ],
)
def test_any_rule_reports_mapping_key_and_value_positions(annotation: str) -> None:
    _runner, reports = _reports(
        NoAnyContainerAnnotations(),
        f"""
        import collections
        import collections.abc as cabc
        import typing
        from collections.abc import Mapping
        from typing import Any

        value: {annotation}
        """,
    )

    assert [report.message for report in reports] == [ANY_MESSAGE]


@pytest.mark.parametrize(
    "annotation",
    [
        "tuple[int, Any]",
        "typing.Tuple[Any, ...]",
        "Generator[Any, None, None]",
        "Generator[int, Any, None]",
        "Generator[int, None, Any]",
        "cabc.AsyncGenerator[Any, None]",
        "KeysView[Any]",
        "cabc.ValuesView[Any]",
        "ItemsView[str, Any]",
        "cabc.ItemsView[Any, str]",
    ],
)
def test_any_rule_reports_tuple_generator_and_mapping_view_positions(
    annotation: str,
) -> None:
    _runner, reports = _reports(
        NoAnyContainerAnnotations(),
        f"""
        import collections.abc as cabc
        import typing
        from collections.abc import Generator, ItemsView, KeysView
        from typing import Any

        value: {annotation}
        """,
    )

    assert [report.message for report in reports] == [ANY_MESSAGE]


@pytest.mark.parametrize(
    "annotation",
    [
        "Annotated[list[Any], 'metadata']",
        "Required[dict[str, Any]]",
        "NotRequired[set[Any]]",
        "ReadOnly[Mapping[str, Any]]",
        "Optional[list[Any]]",
        "Union[None, tuple[Any, ...]]",
        "list[Any] | None",
    ],
)
def test_any_rule_looks_through_transparent_wrappers_and_unions(annotation: str) -> None:
    _runner, reports = _reports(
        NoAnyContainerAnnotations(),
        f"""
        from collections.abc import Mapping
        from typing import Annotated, Any, NotRequired, Optional, Required, Union
        from typing_extensions import ReadOnly

        value: {annotation}
        """,
    )

    assert [report.message for report in reports] == [ANY_MESSAGE]


def test_any_rule_handles_qualified_alias_imports_and_string_annotations() -> None:
    _runner, reports = _reports(
        NoAnyContainerAnnotations(),
        """
        import collections.abc as containers
        import typing as types
        from typing import Any as Dynamic

        first: "types.List[Dynamic]"
        second: "containers.Mapping[str, types.Any]"
        """,
    )

    assert [report.message for report in reports] == [ANY_MESSAGE, ANY_MESSAGE]


@pytest.mark.parametrize(
    "source",
    [
        """
        from typing import Any, TypeAlias

        UnsafeList: TypeAlias = list[Any]
        Alias: TypeAlias = UnsafeList
        value: Alias
        """,
        """
        from typing import Any

        type UnsafeList = list[Any]
        type Alias = UnsafeList
        value: Alias
        """,
        """
        from typing import Any

        type Bucket[T] = list[T]
        value: Bucket[Any]
        """,
        """
        from typing import Any, TypeAlias, TypeVar

        T = TypeVar("T")
        Bag: TypeAlias = list[T]
        value: Bag[Any]
        """,
    ],
)
def test_any_rule_follows_direct_generic_and_chained_type_aliases(source: str) -> None:
    _runner, reports = _reports(NoAnyContainerAnnotations(), source)

    assert [report.message for report in reports] == [ANY_MESSAGE]


def test_any_rule_uses_a_pep_695_type_parameter_default() -> None:
    _runner, reports = _reports(
        NoAnyContainerAnnotations(),
        """
        from typing import Any

        type Bag[T = Any] = list[T]
        value: Bag
        """,
    )

    assert [report.message for report in reports] == [ANY_MESSAGE]


def test_any_rule_allows_an_explicit_safe_argument_over_a_pep_695_default() -> None:
    _runner, reports = _reports(
        NoAnyContainerAnnotations(),
        """
        from typing import Any

        type Bag[T = Any] = list[T]
        value: Bag[int]
        """,
    )

    assert reports == []


def test_any_rule_reports_an_inherently_unsafe_generic_alias_only_once() -> None:
    _runner, reports = _reports(
        NoAnyContainerAnnotations(),
        """
        from typing import Any

        type Bag[T] = list[Any]
        value: Bag[int]
        """,
    )

    assert [report.message for report in reports] == [ANY_MESSAGE]


def test_any_rule_reports_only_the_innermost_unsafe_container() -> None:
    _runner, reports = _reports(
        NoAnyContainerAnnotations(),
        """
        from typing import Any

        value: list[tuple[int, dict[str, Any]]]
        """,
    )

    assert [report.message for report in reports] == [ANY_MESSAGE]


@pytest.mark.parametrize(
    "source",
    [
        """
        from typing import Any

        class list:
            pass

        value: list[Any]
        """,
        """
        class Any:
            pass

        value: list[Any]
        """,
        """
        import typing

        class LocalTyping:
            List = list
            Any = object

        typing = LocalTyping()
        value: typing.List[typing.Any]
        """,
        """
        from typing import Any, Generic, TypeVar

        T = TypeVar("T")

        class Box(Generic[T]):
            pass

        value: Box[Any]
        """,
    ],
)
def test_any_rule_respects_shadowing_and_does_not_unwrap_domain_generics(
    source: str,
) -> None:
    _runner, reports = _reports(NoAnyContainerAnnotations(), source)

    assert reports == []


@pytest.mark.parametrize(
    "annotation",
    [
        "dict[str, object]",
        "typing.Dict[str, object]",
        "Mapping[str, object]",
        "cabc.MutableMapping[str, object]",
        "collections.defaultdict[str, object]",
        "collections.OrderedDict[str, object]",
        "collections.ChainMap[str, object]",
    ],
)
def test_object_rule_reports_only_standard_mapping_value_positions(
    annotation: str,
) -> None:
    _runner, reports = _reports(
        NoObjectMappingValues(),
        f"""
        import collections
        import collections.abc as cabc
        import typing
        from collections.abc import Mapping

        value: {annotation}
        """,
    )

    assert [report.message for report in reports] == [OBJECT_MESSAGE]


@pytest.mark.parametrize(
    "annotation",
    [
        "dict[object, int]",
        "list[object]",
        "tuple[object, str]",
        "cabc.KeysView[object]",
        "cabc.ItemsView[object, int]",
        "cabc.ItemsView[str, object]",
        "cabc.ValuesView[object]",
        "cabc.Generator[object, None, None]",
        "Box[object]",
    ],
)
def test_object_rule_allows_non_mapping_value_positions(annotation: str) -> None:
    _runner, reports = _reports(
        NoObjectMappingValues(),
        f"""
        import collections.abc as cabc
        from typing import Generic, TypeVar

        T = TypeVar("T")

        class Box(Generic[T]):
            pass

        value: {annotation}
        """,
    )

    assert reports == []


@pytest.mark.parametrize(
    "annotation",
    [
        "Annotated[dict[str, object], 'metadata']",
        "Required[Mapping[str, object]]",
        "NotRequired[dict[str, object]]",
        "ReadOnly[dict[str, object]]",
        "Optional[dict[str, object]]",
        "Union[None, dict[str, object]]",
        "dict[str, object] | None",
    ],
)
def test_object_rule_looks_through_transparent_wrappers_and_unions(
    annotation: str,
) -> None:
    _runner, reports = _reports(
        NoObjectMappingValues(),
        f"""
        from collections.abc import Mapping
        from typing import Annotated, NotRequired, Optional, Required, Union
        from typing_extensions import ReadOnly

        value: {annotation}
        """,
    )

    assert [report.message for report in reports] == [OBJECT_MESSAGE]


def test_object_rule_handles_qualified_imports_and_string_annotations() -> None:
    _runner, reports = _reports(
        NoObjectMappingValues(),
        """
        import collections.abc as containers
        import typing as types

        first: "types.Dict[str, object]"
        second: "containers.Mapping[str, object]"
        """,
    )

    assert [report.message for report in reports] == [OBJECT_MESSAGE, OBJECT_MESSAGE]


@pytest.mark.parametrize(
    "source",
    [
        """
        from typing import TypeAlias

        ObjectMap: TypeAlias = dict[str, object]
        Alias: TypeAlias = ObjectMap
        value: Alias
        """,
        """
        type ObjectMap = dict[str, object]
        type Alias = ObjectMap
        value: Alias
        """,
        """
        type Index[V] = dict[str, V]
        value: Index[object]
        """,
        """
        from typing import TypeAlias, TypeVar

        V = TypeVar("V")
        Index: TypeAlias = dict[str, V]
        value: Index[object]
        """,
    ],
)
def test_object_rule_follows_direct_generic_and_chained_type_aliases(
    source: str,
) -> None:
    _runner, reports = _reports(NoObjectMappingValues(), source)

    assert [report.message for report in reports] == [OBJECT_MESSAGE]


def test_object_rule_reports_only_the_innermost_unsafe_mapping() -> None:
    _runner, reports = _reports(
        NoObjectMappingValues(),
        "value: dict[str, list[dict[str, object]]]\n",
    )

    assert [report.message for report in reports] == [OBJECT_MESSAGE]


@pytest.mark.parametrize(
    "source",
    [
        """
        class object:
            pass

        value: dict[str, "object"]
        """,
        """
        class dict:
            pass

        value: dict[str, object]
        """,
        """
        import collections.abc as cabc

        class LocalAbc:
            Mapping = dict

        cabc = LocalAbc()
        value: cabc.Mapping[str, object]
        """,
    ],
)
def test_object_rule_respects_shadowing(source: str) -> None:
    _runner, reports = _reports(NoObjectMappingValues(), source)

    assert reports == []


@pytest.mark.parametrize("rule", [NoAnyContainerAnnotations(), NoObjectMappingValues()])
@pytest.mark.parametrize(
    "path",
    [Path("tests/sample.py"), Path("src/test_sample.py")],
)
def test_container_rules_use_the_default_test_path_exclusions(
    rule: LintRule,
    path: Path,
) -> None:
    _runner, reports = _reports(
        rule,
        """
        from typing import Any

        first: list[Any]
        second: dict[str, object]
        """,
        path=path,
    )

    assert reports == []


@pytest.mark.parametrize(
    ("rule", "message"),
    [
        (NoAnyContainerAnnotations(), ANY_MESSAGE),
        (NoObjectMappingValues(), OBJECT_MESSAGE),
    ],
)
def test_container_rule_path_exclusions_are_configurable(
    rule: LintRule,
    message: str,
) -> None:
    rule.configure({"excluded_path_parts": []})
    annotation = "list[Any]" if isinstance(rule, NoAnyContainerAnnotations) else "dict[str, object]"
    _runner, reports = _reports(
        rule,
        f"from typing import Any\nvalue: {annotation}\n",
        path=Path("tests/sample.py"),
    )

    assert [report.message for report in reports] == [message]


@pytest.mark.parametrize(
    ("rule", "source", "message"),
    [
        (
            NoAnyContainerAnnotations(),
            "from typing import Any\nvalue: list[Any]\n",
            ANY_MESSAGE,
        ),
        (
            NoObjectMappingValues(),
            "value: dict[str, object]\n",
            OBJECT_MESSAGE,
        ),
    ],
)
def test_container_diagnostics_have_exact_messages_and_no_replacements(
    rule: LintRule,
    source: str,
    message: str,
) -> None:
    runner, reports = _reports(rule, source)

    assert [report.message for report in reports] == [message]
    assert [report.replacement for report in reports] == [None]
    assert runner.apply_replacements(reports).code == source
