from pathlib import Path
from textwrap import dedent

import pytest

from rattle.engine import LintRunner
from rattle.ftypes import Config, LintViolation
from rattle.rule import LintRule
from rattle.rules.exports.module_all_at_bottom import ModuleAllAtBottom
from rattle.rules.exports.no_underscore_all_exports import NoUnderscoreAllExports
from rattle.rules.style.no_annotated_self import NoAnnotatedSelf
from rattle.rules.style.no_exception_message_variables import NoExceptionMessageVariables
from rattle.rules.style.no_str_exception_translation import NoStrExceptionTranslation
from rattle.rules.style.no_underscore_class import NoUnderscoreClass
from rattle.rules.style.public_method_order import PublicMethodOrder
from rattle.rules.typing.no_bare_object_annotations import NoBareObjectAnnotations


def _reports(
    rule: LintRule,
    source: str,
    *,
    path: Path = Path("sample.py"),
) -> tuple[LintRunner, list[LintViolation]]:
    runner = LintRunner(path, dedent(source).encode())
    return runner, list(runner.collect_violations([rule], Config(path=path)))


def _fixed(rule: LintRule, source: str) -> tuple[list[LintViolation], str]:
    runner, reports = _reports(rule, source)
    return reports, runner.apply_replacements(reports).code


def test_module_all_allows_a_trailing_construction_block() -> None:
    _runner, reports = _reports(
        ModuleAllAtBottom(),
        """
        def public() -> None:
            pass

        __all__ = []
        __all__.append("public")
        __all__ += ["other"]
        """,
    )

    assert reports == []


def test_module_all_reports_a_conditional_declaration_before_a_definition() -> None:
    _runner, reports = _reports(
        ModuleAllAtBottom(),
        """
        if enabled:
            __all__ = ["public"]

        def public() -> None:
            pass
        """,
    )

    assert len(reports) == 1


def test_module_all_ignores_function_local_all() -> None:
    _runner, reports = _reports(
        ModuleAllAtBottom(),
        """
        def build() -> list[str]:
            __all__ = ["local"]
            return __all__

        value = build()
        """,
    )

    assert reports == []


@pytest.mark.parametrize(
    "source",
    [
        """
        EXPORTS = ["_private"]
        from provider import EXPORTS
        __all__ = EXPORTS
        """,
        """
        EXPORTS = ["_private"]

        def list(values):
            return []

        __all__ = list(EXPORTS)
        """,
    ],
)
def test_no_underscore_all_exports_does_not_use_stale_or_shadowed_alias_facts(
    source: str,
) -> None:
    _runner, reports = _reports(NoUnderscoreAllExports(), source)

    assert reports == []


def test_no_underscore_all_exports_tracks_static_alias_mutations() -> None:
    _runner, reports = _reports(
        NoUnderscoreAllExports(),
        """
        EXPORTS = ["public"]
        EXPORTS.append("_private")
        __all__ = EXPORTS
        """,
    )

    assert len(reports) == 1


def test_no_underscore_all_exports_recognizes_imported_builtin_constructor() -> None:
    _runner, reports = _reports(
        NoUnderscoreAllExports(),
        """
        from builtins import list

        EXPORTS = ["_private"]
        __all__ = list(EXPORTS)
        """,
    )

    assert len(reports) == 1


def test_no_underscore_all_exports_tracks_augmented_mutable_alias() -> None:
    _runner, reports = _reports(
        NoUnderscoreAllExports(),
        """
        EXPORTS = ["public"]
        ALIAS = EXPORTS
        ALIAS += ["_private"]
        __all__ = EXPORTS
        """,
    )

    assert len(reports) == 1


def test_no_underscore_all_exports_does_not_mutate_augmented_tuple_alias() -> None:
    _runner, reports = _reports(
        NoUnderscoreAllExports(),
        """
        EXPORTS = ("public",)
        ALIAS = EXPORTS
        ALIAS += ("_private",)
        __all__ = EXPORTS
        """,
    )

    assert reports == []


@pytest.mark.parametrize(
    "source",
    [
        """
        EXPORTS = ["_private"]
        EXPORTS[0] = "public"
        __all__ = EXPORTS
        """,
        """
        EXPORTS = ["_private"]
        ALIAS = EXPORTS
        ALIAS.clear()
        __all__ = EXPORTS
        """,
    ],
)
def test_no_underscore_all_exports_invalidates_mutated_alias_facts(source: str) -> None:
    _runner, reports = _reports(NoUnderscoreAllExports(), source)

    assert reports == []


def test_no_underscore_all_exports_does_not_expand_an_appended_collection() -> None:
    _runner, reports = _reports(
        NoUnderscoreAllExports(),
        '__all__.append(["_private"])',
    )

    assert reports == []


def test_exception_message_variable_used_by_handler_is_not_throwaway() -> None:
    _runner, reports = _reports(
        NoExceptionMessageVariables(),
        """
        try:
            message = "invalid"
            raise ValueError(message)
        except ValueError:
            log(message)
        """,
    )

    assert reports == []


def test_exception_message_variable_ignores_uses_of_an_earlier_binding() -> None:
    _runner, reports = _reports(
        NoExceptionMessageVariables(),
        """
        message = "earlier"
        log(message)
        message = "invalid"
        raise ValueError(message)
        """,
    )

    assert len(reports) == 1


@pytest.mark.parametrize(
    "expression",
    ["(lambda: formatter)().format(exc)", "formatter % exc"],
)
def test_no_str_exception_translation_ignores_non_string_format_operations(
    expression: str,
) -> None:
    _runner, reports = _reports(
        NoStrExceptionTranslation(),
        f"""
        try:
            run()
        except ValueError as exc:
            raise RuntimeError({expression}) from exc
        """,
    )

    assert reports == []


def test_no_str_exception_translation_honors_annotated_rebinding() -> None:
    _runner, reports = _reports(
        NoStrExceptionTranslation(),
        """
        try:
            run()
        except ValueError as exc:
            exc: str = "stable"
            raise RuntimeError(str(exc))
        """,
    )

    assert reports == []


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


@pytest.mark.parametrize(
    ("rule", "source"),
    [
        (
            NoAnnotatedSelf(),
            """
            class Service:
                @custom
                def run(self: "Service") -> None:
                    pass
            """,
        ),
        (
            NoUnderscoreClass(),
            """
            def factory():
                class _Private:
                    pass
                return _Private
            """,
        ),
        (
            PublicMethodOrder(),
            """
            class Service:
                def __init__(self) -> None:
                    pass

                async def run(self) -> None:
                    pass

                def _helper(self) -> None:
                    pass
            """,
        ),
    ],
)
def test_rules_cover_adversarial_but_unambiguous_cases(
    rule: LintRule,
    source: str,
) -> None:
    _runner, reports = _reports(rule, source)

    assert len(reports) == (0 if isinstance(rule, PublicMethodOrder) else 1)


def test_module_all_dynamic_value_is_reported_without_reordering_fix() -> None:
    _runner, reports = _reports(
        ModuleAllAtBottom(),
        """
        def public():
            return "old"

        __all__ = [public]

        def public():
            return "new"
        """,
    )

    assert len(reports) == 1
    assert reports[0].replacement is None


def test_module_all_fix_does_not_move_past_binding_named_all() -> None:
    _runner, reports = _reports(
        ModuleAllAtBottom(),
        """
        __all__ = ["public"]

        def __all__():
            return "runtime binding"
        """,
    )

    assert len(reports) == 1
    assert reports[0].replacement is None


def test_exception_message_global_assignment_is_not_treated_as_local() -> None:
    _runner, reports = _reports(
        NoExceptionMessageVariables(),
        """
        message = "original"

        def fail():
            global message
            message = "invalid"
            raise ValueError(message)
        """,
    )

    assert reports == []


def test_underscore_class_range_targets_class_name() -> None:
    _runner, reports = _reports(NoUnderscoreClass(), "class _Private:\n    pass")

    assert len(reports) == 1
    assert reports[0].range is not None
    assert reports[0].range.start.column == 6
    assert reports[0].range.end.column == 14


def test_annotated_self_in_conditional_class_body_is_reported() -> None:
    reports, fixed = _fixed(
        NoAnnotatedSelf(),
        """
        class Service:
            if enabled:
                def run(self: "Service") -> None:
                    pass
        """,
    )

    assert len(reports) == 1
    assert "def run(self) -> None:" in fixed
