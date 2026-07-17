from pathlib import Path
from textwrap import dedent

import pytest

from rattle.engine import LintRunner
from rattle.ftypes import Config, LintViolation
from rattle.rule import LintRule
from rattle.rules.exports.no_underscore_all_exports import NoUnderscoreAllExports
from rattle.rules.fixit.no_namedtuple import NoNamedTuple
from rattle.rules.fixit_extra.avoid_or_in_except import AvoidOrInExcept
from rattle.rules.fixit_extra.chained_instance_check import CollapseIsinstanceChecks
from rattle.rules.fixit_extra.cls_in_classmethod import UseClsInClassmethod
from rattle.rules.fixit_extra.compare_singleton_primitives_by_is import (
    CompareSingletonPrimitivesByIs,
)
from rattle.rules.fixit_extra.deprecated_abc_import import DeprecatedABCImport
from rattle.rules.fixit_extra.no_assert_true_for_comparison import (
    NoAssertTrueForComparisons,
)
from rattle.rules.fixit_extra.no_inherit_from_object import NoInheritFromObject
from rattle.rules.fixit_extra.no_redundant_arguments_super import NoRedundantArgumentsSuper
from rattle.rules.fixit_extra.no_redundant_fstring import NoRedundantFString
from rattle.rules.fixit_extra.no_redundant_lambda import NoRedundantLambda
from rattle.rules.fixit_extra.no_redundant_list_comprehension import (
    NoRedundantListComprehension,
)
from rattle.rules.fixit_extra.no_string_type_annotation import NoStringTypeAnnotation
from rattle.rules.fixit_extra.replace_union_with_optional import ReplaceUnionWithOptional
from rattle.rules.fixit_extra.rewrite_to_comprehension import RewriteToComprehension
from rattle.rules.fixit_extra.rewrite_to_literal import RewriteToLiteral
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


def _fixed(rule: LintRule, source: str) -> tuple[list[LintViolation], str]:
    runner, reports = _reports(rule, source)
    return reports, runner.apply_replacements(reports).code


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


def test_no_named_tuple_does_not_autofix_to_dataclass() -> None:
    source = """
    from dataclasses import field
    from typing import NamedTuple

    class Foo(NamedTuple):
        x: int
    result = Foo(1).x
    """

    _runner, reports = _reports(NoNamedTuple(), source)

    assert len(reports) == 1
    assert reports[0].replacement is None


def test_no_redundant_list_comprehension_does_not_autofix_to_generator() -> None:
    source = """
    result = any([f(x) for x in xs])
    """

    _runner, reports = _reports(NoRedundantListComprehension(), source)

    assert len(reports) == 1
    assert reports[0].replacement is None


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


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("value==True", "value is True"),
        ("value ==True", "value is True"),
        ("value== True", "value is True"),
        ("value!=None", "value is not None"),
    ],
)
def test_singleton_comparison_fix_adds_required_whitespace(
    source: str,
    expected: str,
) -> None:
    reports, fixed = _fixed(CompareSingletonPrimitivesByIs(), source)

    assert len(reports) == 1
    assert fixed == expected


@pytest.mark.parametrize(
    "source",
    ["False == -0", "False != -0", "True == +1", "True != +1"],
)
def test_singleton_comparison_allows_signed_boolean_number_comparisons(source: str) -> None:
    _runner, reports = _reports(CompareSingletonPrimitivesByIs(), source)

    assert reports == []


@pytest.mark.parametrize("parameters", ["*, cls", "*cls", "**cls", "*args, cls=None"])
def test_classmethod_missing_positional_parameter_does_not_duplicate_cls(
    parameters: str,
) -> None:
    _runner, reports = _reports(
        UseClsInClassmethod(),
        f"""
        class Example:
            @classmethod
            def build({parameters}):
                pass
        """,
    )

    assert len(reports) == 1
    assert reports[0].replacement is None


@pytest.mark.parametrize(
    "source",
    [
        """
        class Example:
            @classmethod
            def build(receiver):
                global cls
                return receiver
        """,
        """
        class Example:
            @classmethod
            def build(receiver):
                import math as receiver
                return receiver.pi
        """,
        """
        class Example:
            @classmethod
            def build(receiver):
                def receiver():
                    return 17
                return receiver()
        """,
    ],
)
def test_classmethod_unsafe_binding_renames_have_no_fix(source: str) -> None:
    _runner, reports = _reports(UseClsInClassmethod(), source)

    assert len(reports) == 1
    assert reports[0].replacement is None


def test_concatenated_string_annotation_is_fixed_as_one_expression() -> None:
    reports, fixed = _fixed(
        NoStringTypeAnnotation(),
        """
        from __future__ import annotations

        def create() -> "Lat" "er":
            pass
        """,
    )

    assert len(reports) == 1
    assert "def create() -> Later:" in fixed


def test_late_typing_import_protects_literal_values() -> None:
    _runner, reports = _reports(
        NoStringTypeAnnotation(),
        """
        from __future__ import annotations

        def create() -> typing.Literal["unit"]:
            pass

        import typing
        """,
    )

    assert reports == []


def test_nested_annotated_metadata_string_is_not_unquoted() -> None:
    _runner, reports = _reports(
        NoStringTypeAnnotation(),
        """
        from __future__ import annotations
        from typing import Annotated

        value: Annotated[int, Metadata["unit"]]
        """,
    )

    assert reports == []


def test_multiline_future_import_enables_string_annotation_rule() -> None:
    reports, fixed = _fixed(
        NoStringTypeAnnotation(),
        """
        from __future__ import (
            annotations,
        )

        def create() -> "Later":
            pass
        """,
    )

    assert len(reports) == 1
    assert "def create() -> Later:" in fixed


@pytest.mark.parametrize(
    "source",
    [
        "value = dict(foo=[])",
        "value = tuple(*[[1, 2]])",
        "value = set(*[[1, 2]])",
        "value = dict(*[[(1, 2), (3, 4)]])",
        "value = dict([(1, *items)])",
    ],
)
def test_collection_literal_rule_skips_keyword_and_starred_arguments(source: str) -> None:
    _runner, reports = _reports(RewriteToLiteral(), source)

    assert reports == []


def test_dict_literal_fix_preserves_pair_comment() -> None:
    reports, fixed = _fixed(
        RewriteToLiteral(),
        """
        value = dict([
            (1, 2),  # preserve this comment
            (3, 4),
        ])
        """,
    )

    assert len(reports) == 1
    assert "# preserve this comment" in fixed


@pytest.mark.parametrize(
    "source",
    [
        'f"module runtime expression"',
        """
        class Example:
            f"class runtime expression"
        """,
        """
        def function():
            f"function runtime expression"
        """,
    ],
)
def test_redundant_fstring_does_not_create_docstring(source: str) -> None:
    _runner, reports = _reports(NoRedundantFString(), source)

    assert reports == []


def test_empty_redundant_fstring_is_fixed() -> None:
    reports, fixed = _fixed(NoRedundantFString(), 'value = f""')

    assert len(reports) == 1
    assert fixed == 'value = ""'


def test_collapsed_isinstance_diagnostic_has_no_eager_evaluation_fix() -> None:
    _runner, reports = _reports(
        CollapseIsinstanceChecks(),
        "isinstance(value, Expected) or isinstance(value, build_type())",
    )

    assert len(reports) == 1
    assert reports[0].replacement is None


def test_redundant_lambda_diagnostic_preserves_late_binding() -> None:
    _runner, reports = _reports(
        NoRedundantLambda(),
        """
        callback = lambda value: target(value)
        target = lambda value: value
        """,
    )

    assert len(reports) == 1
    assert reports[0].replacement is None


def test_redundant_super_diagnostic_does_not_change_execution_frame() -> None:
    _runner, reports = _reports(
        NoRedundantArgumentsSuper(),
        """
        class Child(Parent):
            def method(self):
                return lambda: super(Child, self).method()
        """,
    )

    assert len(reports) == 1
    assert reports[0].replacement is None


def test_percent_format_unknown_expression_has_no_tuple_unsafe_fix() -> None:
    _runner, reports = _reports(
        UseFstring(),
        """
        values = ("hello",)
        result = "%s" % values
        """,
    )

    assert len(reports) == 1
    assert reports[0].replacement is None


def test_percent_format_literal_keeps_safe_fstring_fix() -> None:
    reports, fixed = _fixed(UseFstring(), 'result = "%s" % "hello"')

    assert len(reports) == 1
    assert fixed == '''result = f"{'hello'!s}"'''


@pytest.mark.parametrize(
    "expression",
    ['"line\\nbreak"', 'f"{value}"', "function(\n    value,\n)"],
)
def test_percent_format_avoids_pre_312_invalid_fstring_fix(expression: str) -> None:
    _runner, reports = _reports(UseFstring(), f'result = "%s" % {expression}')

    assert len(reports) == 1
    assert reports[0].replacement is None


def test_comprehension_rewrite_does_not_change_generator_exception_semantics() -> None:
    _runner, reports = _reports(
        RewriteToComprehension(),
        "value = list(stop() for _ in range(1))",
    )

    assert len(reports) == 1
    assert reports[0].replacement is None


def test_explicit_object_base_with_metaclass_has_no_fix() -> None:
    _runner, reports = _reports(
        NoInheritFromObject(),
        """
        class Example(object, metaclass=Meta):
            pass
        """,
    )

    assert len(reports) == 1
    assert reports[0].replacement is None


def test_imported_builtin_object_base_is_detected() -> None:
    reports, fixed = _fixed(
        NoInheritFromObject(),
        """
        from builtins import object

        class Example(object):
            pass
        """,
    )

    assert len(reports) == 1
    assert "class Example:" in fixed


def test_negated_equality_assertion_has_no_semantics_changing_fix() -> None:
    _runner, reports = _reports(
        NoAssertTrueForComparisons(),
        "self.assertTrue(not left == right)",
    )

    assert len(reports) == 1
    assert reports[0].replacement is None


def test_custom_assertion_destination_is_not_recommended() -> None:
    _runner, reports = _reports(
        NoAssertTrueForComparisons(),
        """
        class Example:
            def assertEqual(self, left, right):
                raise RuntimeError

            def check(self, left, right):
                self.assertTrue(left == right)
        """,
    )

    assert reports == []


def test_comparison_comment_prevents_assertion_autofix() -> None:
    _runner, reports = _reports(
        NoAssertTrueForComparisons(),
        """
        self.assertTrue(
            left  # preserve comparison context
            == right,
        )
        """,
    )

    assert len(reports) == 1
    assert reports[0].replacement is None


def test_custom_union_and_optional_have_no_typing_rewrite() -> None:
    _runner, reports = _reports(
        ReplaceUnionWithOptional(),
        """
        class Union:
            pass

        class Optional:
            pass

        value: Union[str, None]
        """,
    )

    assert len(reports) == 1
    assert reports[0].replacement is None


@pytest.mark.parametrize(
    "source",
    [
        """
        try:
            pass
        except* ValueError or TypeError:
            pass
        """,
        """
        try:
            pass
        except (ValueError, TypeError or OSError):
            pass
        """,
    ],
)
def test_or_in_except_detects_star_and_nested_forms(source: str) -> None:
    _runner, reports = _reports(AvoidOrInExcept(), source)

    assert len(reports) == 1
