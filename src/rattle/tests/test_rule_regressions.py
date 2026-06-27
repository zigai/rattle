from pathlib import Path
from textwrap import dedent

import pytest

from rattle.engine import LintRunner
from rattle.ftypes import Config, LintViolation
from rattle.rule import LintRule
from rattle.rules.exports.no_underscore_all_exports import NoUnderscoreAllExports
from rattle.rules.fixit.no_namedtuple import NoNamedTuple
from rattle.rules.fixit_extra.cls_in_classmethod import UseClsInClassmethod
from rattle.rules.fixit_extra.deprecated_abc_import import DeprecatedABCImport
from rattle.rules.fixit_extra.no_assert_true_for_comparison import (
    NoAssertTrueForComparisons,
)
from rattle.rules.fixit_extra.rewrite_to_comprehension import RewriteToComprehension
from rattle.rules.fixit_extra.use_assert_in import UseAssertIn
from rattle.rules.fixit_extra.use_assert_is_not_none import UseAssertIsNotNone
from rattle.rules.fixit_extra.use_async_sleep_in_async_def import (
    UseAsyncSleepInAsyncDef,
)
from rattle.rules.fixit_extra.use_fstring import UseFstring
from rattle.rules.style.no_str_exception_translation import NoStrExceptionTranslation
from rattle.rules.style.public_method_order import PublicMethodOrder
from rattle.rules.typing.no_bare_object_annotations import NoBareObjectAnnotations


def _reports(rule: LintRule, source: str) -> tuple[LintRunner, list[LintViolation]]:
    path = Path("sample.py")
    runner = LintRunner(path, dedent(source).encode())
    return runner, list(runner.collect_violations([rule], Config(path=path)))


@pytest.mark.parametrize(
    ("rule", "source"),
    [
        (
            NoUnderscoreAllExports(),
            """
            EXPORTS, OTHER = ["_private"], []
            __all__ = EXPORTS
            """,
        ),
        (
            UseClsInClassmethod(),
            """
            from builtins import classmethod as cm

            class C:
                @cm
                def make(kls):
                    return kls()
            """,
        ),
        (
            UseAsyncSleepInAsyncDef(),
            """
            import time
            nap = time.sleep

            async def f():
                nap(1)
            """,
        ),
        (
            UseAsyncSleepInAsyncDef(),
            """
            from time import *

            async def f():
                sleep(1)
            """,
        ),
        (
            NoBareObjectAnnotations(),
            """
            from typing import Annotated

            value: Annotated[object, "meta"]
            """,
        ),
        (
            NoBareObjectAnnotations(),
            """
            from typing_extensions import Annotated

            value: Annotated[object, "meta"]
            """,
        ),
        (
            NoBareObjectAnnotations(),
            """
            from typing import TypeAlias

            Object: TypeAlias = object
            value: Object = payload
            """,
        ),
        (
            NoStrExceptionTranslation(),
            """
            try:
                run()
            except ValueError as exc:
                error = exc
                raise RuntimeError(str(error)) from exc
            """,
        ),
        (
            PublicMethodOrder(),
            """
            from typing import *

            def overload(func):
                return func

            class Workflow:
                @overload
                def build(self, value: str) -> str: ...

                def _normalize(self, value: str) -> str:
                    return value

                def build(self, value: str) -> str:
                    return self._normalize(value)
            """,
        ),
        (
            DeprecatedABCImport(),
            """
            try:
                work()
            except ValueError:
                from collections import Mapping
            """,
        ),
        (
            NoNamedTuple(),
            """
            from dataclasses import field
            from typing import NamedTuple

            class Foo(NamedTuple):
                x: int
            result = Foo(1).x
            """,
        ),
    ],
)
def test_alias_and_scope_false_negative_regressions(rule: LintRule, source: str) -> None:
    _runner, reports = _reports(rule, source)

    assert len(reports) == 1


@pytest.mark.parametrize(
    ("rule", "source"),
    [
        (
            UseAsyncSleepInAsyncDef(),
            """
            from time import *

            async def f():
                sleep = something_else
                sleep(1)
            """,
        ),
        (
            UseAssertIn(),
            """
            class Checker:
                def assertTrue(self, expr):
                    print(expr)

                def check(self, a, b):
                    self.assertTrue(a in b)
            """,
        ),
        (
            UseAssertIn(),
            """
            class Checker:
                def assertFalse(self, expr):
                    print(expr)

                def check(self, a, b):
                    self.assertFalse(a in b)
            """,
        ),
        (
            UseAssertIsNotNone(),
            """
            class Checker:
                def assertFalse(self, expr):
                    print(expr)

                def check(self, x):
                    self.assertFalse(x is None)
            """,
        ),
        (
            NoAssertTrueForComparisons(),
            """
            class Checker:
                def assertTrue(self, expr):
                    print(expr)

                def check(self, a, b):
                    self.assertTrue(a == b)
            """,
        ),
        (
            PublicMethodOrder(),
            """
            def property(func):
                return func

            class Workflow:
                def _normalize(self) -> str:
                    return "ok"

                @property
                def value(self) -> str:
                    return self._normalize()
            """,
        ),
        (
            PublicMethodOrder(),
            """
            def singledispatchmethod(func):
                return func

            class Workflow:
                def _helper(self):
                    pass

                @singledispatchmethod
                def run(self, value):
                    return value
            """,
        ),
        (
            NoStrExceptionTranslation(),
            """
            error = "fixed"

            try:
                run()
            except ValueError as exc:
                def capture() -> None:
                    error = exc

                raise RuntimeError(str(error)) from exc
            """,
        ),
        (
            NoStrExceptionTranslation(),
            """
            error = "fixed"

            try:
                run()
            except ValueError as exc:
                class Capture:
                    error = exc

                raise RuntimeError(str(error)) from exc
            """,
        ),
        (
            PublicMethodOrder(),
            """
            from typing import *

            class Workflow:
                @overload
                def build(self, value: str) -> str: ...

                def _normalize(self, value: str) -> str:
                    return value

                def build(self, value: str) -> str:
                    return self._normalize(value)
            """,
        ),
        (
            PublicMethodOrder(),
            """
            from typing_extensions import *

            class Workflow:
                @overload
                def build(self, value: str) -> str: ...

                def _normalize(self, value: str) -> str:
                    return value

                def build(self, value: str) -> str:
                    return self._normalize(value)
            """,
        ),
    ],
)
def test_false_positive_regressions_do_not_report(
    rule: LintRule,
    source: str,
) -> None:
    _runner, reports = _reports(rule, source)

    assert reports == []


def test_use_comprehension_does_not_autofix_set_listcomp_order() -> None:
    source = """
    events = []
    class Key:
        def __init__(self, name): self.name = name
        def __hash__(self):
            events.append(f"hash {self.name}")
            return hash(self.name)
    def make(name):
        events.append(f"make {name}")
        return Key(name)
    result = set([make(name) for name in ["a", "b"]])
    """

    _runner, reports = _reports(RewriteToComprehension(), source)

    assert len(reports) == 1
    assert reports[0].replacement is None


def test_no_named_tuple_adds_dataclasses_import_when_only_field_is_imported() -> None:
    source = """
    from dataclasses import field
    from typing import NamedTuple

    class Foo(NamedTuple):
        x: int
    result = Foo(1).x
    """

    runner, reports = _reports(NoNamedTuple(), source)
    fixed = runner.apply_replacements(reports).code

    assert len(reports) == 1
    assert fixed == dedent("""
    import dataclasses
    from dataclasses import field

    @dataclasses.dataclass(frozen=True)
    class Foo:
        x: int
    result = Foo(1).x
    """)


def test_use_f_string_percent_s_autofix_uses_str_conversion() -> None:
    source = """
    events = []
    class Value:
        def __str__(self):
            events.append("str")
            return "S"
        def __format__(self, spec):
            events.append("format")
            return "F"
    result = "%s" % Value()
    """

    runner, reports = _reports(UseFstring(), source)
    fixed = runner.apply_replacements(reports).code

    assert len(reports) == 1
    assert "{Value()!s}" in fixed

    original_namespace: dict[str, object] = {}
    fixed_namespace: dict[str, object] = {}
    exec(dedent(source), original_namespace)
    exec(fixed, fixed_namespace)

    assert original_namespace["result"] == fixed_namespace["result"] == "S"
    assert original_namespace["events"] == fixed_namespace["events"] == ["str"]
