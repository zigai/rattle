import pytest

from rattle.rules.exports.module_all_at_bottom import ModuleAllAtBottom
from rattle.rules.exports.no_underscore_all_exports import NoUnderscoreAllExports
from tests.support import run_rule


def test_module_all_allows_a_trailing_construction_block() -> None:
    _runner, reports = run_rule(
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
    _runner, reports = run_rule(
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
    _runner, reports = run_rule(
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
    _runner, reports = run_rule(NoUnderscoreAllExports(), source)

    assert reports == []


def test_no_underscore_all_exports_tracks_static_alias_mutations() -> None:
    _runner, reports = run_rule(
        NoUnderscoreAllExports(),
        """
        EXPORTS = ["public"]
        EXPORTS.append("_private")
        __all__ = EXPORTS
        """,
    )

    assert len(reports) == 1


def test_no_underscore_all_exports_recognizes_imported_builtin_constructor() -> None:
    _runner, reports = run_rule(
        NoUnderscoreAllExports(),
        """
        from builtins import list

        EXPORTS = ["_private"]
        __all__ = list(EXPORTS)
        """,
    )

    assert len(reports) == 1


def test_no_underscore_all_exports_tracks_augmented_mutable_alias() -> None:
    _runner, reports = run_rule(
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
    _runner, reports = run_rule(
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
    _runner, reports = run_rule(NoUnderscoreAllExports(), source)

    assert reports == []


def test_no_underscore_all_exports_does_not_expand_an_appended_collection() -> None:
    _runner, reports = run_rule(
        NoUnderscoreAllExports(),
        '__all__.append(["_private"])',
    )

    assert reports == []


def test_module_all_dynamic_value_is_reported_without_reordering_fix() -> None:
    _runner, reports = run_rule(
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
    _runner, reports = run_rule(
        ModuleAllAtBottom(),
        """
        __all__ = ["public"]

        def __all__():
            return "runtime binding"
        """,
    )

    assert len(reports) == 1
    assert reports[0].replacement is None
