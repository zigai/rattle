from pathlib import Path
from textwrap import dedent

import pytest

from rattle.config.models import Config
from rattle.diagnostics import LintViolation
from rattle.engine import LintRunner
from rattle.rule import LintRule
from rattle.rules.typing.no_casts_to_never import NoCastsToNever
from rattle.rules.typing.no_chained_casts import NoChainedCasts
from rattle.rules.typing.no_widen_then_cast import NoWidenThenCast
from rattle.rules.typing.require_safety_comment_for_cast import RequireSafetyCommentForCast

CHAINED_MESSAGE = (
    "This cast chain discards type evidence. Keep the original precise type or "
    "validate the value once."
)
NEVER_MESSAGE = (
    "Do not cast a value to `Never` or `NoReturn`; prove exhaustiveness through control flow."
)
WIDEN_MESSAGE = (
    "This value was widened and then cast back to a narrower type. Preserve its "
    "original type evidence."
)
SAFETY_MESSAGE = (
    "This cast has no `SAFETY:` justification. State the invariant immediately "
    "before the cast or its containing statement."
)


def _reports(
    rule: LintRule,
    source: str,
    *,
    path: Path = Path("sample.py"),
) -> tuple[LintRunner, list[LintViolation]]:
    code = dedent(source)
    runner = LintRunner(path, code.encode())
    return runner, list(runner.collect_violations([rule], Config(path=path)))


def test_public_rule_names_match_the_documented_selectors() -> None:
    assert NoChainedCasts.name == "no-chained-casts"
    assert NoCastsToNever.name == "no-casts-to-never"
    assert NoWidenThenCast.name == "no-widen-then-cast"
    assert RequireSafetyCommentForCast.name == "require-safety-comment-for-cast"


def test_chained_casts_resolves_qualified_import_and_assignment_aliases() -> None:
    _runner, reports = _reports(
        NoChainedCasts(),
        """
        import typing as types
        from typing import cast as imported_cast

        assigned_cast = imported_cast
        first = types.cast(str, types.cast(object, value))
        second = imported_cast(str, imported_cast(object, value))
        third = assigned_cast(str, assigned_cast(object, value))
        """,
    )

    assert [report.message for report in reports] == [CHAINED_MESSAGE] * 3


def test_chained_casts_looks_through_parentheses_and_reports_only_outermost_chain() -> None:
    _runner, reports = _reports(
        NoChainedCasts(),
        """
        from typing import cast

        result = cast(bytes, (cast(str, (cast(object, value)))))
        """,
    )

    assert [report.message for report in reports] == [CHAINED_MESSAGE]


def test_chained_casts_allows_separate_casts_and_shadowed_names() -> None:
    _runner, reports = _reports(
        NoChainedCasts(),
        """
        import typing
        from typing import cast

        first = cast(str, value)
        second = cast(bytes, first)

        def local(typing, cast):
            return (
                typing.cast(str, typing.cast(object, value)),
                cast(str, cast(object, value)),
            )
        """,
    )

    assert reports == []


@pytest.mark.parametrize(
    "target",
    [
        "Never",
        "NoReturn",
        "types.Never",
        "types.NoReturn",
        "extensions.Never",
        "extensions.NoReturn",
        "Bottom",
        "LegacyBottom",
        "ExtensionBottom",
        '"Never"',
        '"NoReturn"',
        '"Bottom"',
    ],
)
def test_never_rule_resolves_aliases_and_quoted_targets(target: str) -> None:
    _runner, reports = _reports(
        NoCastsToNever(),
        f"""\
        import typing as types
        import typing_extensions as extensions
        from typing import Never, NoReturn, cast as imported_cast

        assigned_cast = imported_cast
        Bottom = Never
        LegacyBottom = NoReturn
        ExtensionBottom = extensions.Never
        result = assigned_cast({target}, value)
        """,
    )

    assert [report.message for report in reports] == [NEVER_MESSAGE]


def test_never_rule_resolves_qualified_import_and_assignment_cast_aliases() -> None:
    _runner, reports = _reports(
        NoCastsToNever(),
        """
        import typing as types
        from typing import NoReturn, cast as imported_cast

        assigned_cast = imported_cast
        first = types.cast((types.Never), (value))
        second = imported_cast(NoReturn, value)
        third = assigned_cast("types.Never", value)
        """,
    )

    assert [report.message for report in reports] == [NEVER_MESSAGE] * 3


def test_never_rule_allows_control_flow_exhaustiveness() -> None:
    _runner, reports = _reports(
        NoCastsToNever(),
        """
        from typing import Never, assert_never

        def unreachable(value: Never) -> Never:
            assert_never(value)

        def fail(message: str) -> Never:
            raise RuntimeError(message)
        """,
    )

    assert reports == []


def test_never_rule_ignores_shadowed_cast_and_bottom_type_names() -> None:
    _runner, reports = _reports(
        NoCastsToNever(),
        """
        import typing
        from typing import Never, cast

        def local(typing, cast, Never):
            first = typing.cast(typing.Never, value)
            second = cast(Never, value)
            return first, second
        """,
    )

    assert reports == []


def test_widen_rule_reports_same_scope_object_and_any_round_trips() -> None:
    _runner, reports = _reports(
        NoWidenThenCast(),
        """
        from typing import Any, cast

        text: str
        widened_object: object = text
        first = cast(str, widened_object)

        count: int
        widened_any: Any = count
        second = cast(int, widened_any)
        """,
    )

    assert [report.message for report in reports] == [WIDEN_MESSAGE, WIDEN_MESSAGE]


def test_widen_rule_resolves_qualified_import_and_assignment_cast_aliases() -> None:
    _runner, reports = _reports(
        NoWidenThenCast(),
        """
        import typing as types
        from typing import cast as imported_cast

        assigned_cast = imported_cast
        text: str
        first: object = text
        second: object = text
        third: object = text
        a = types.cast(str, first)
        b = imported_cast(str, second)
        c = assigned_cast(str, third)
        """,
    )

    assert [report.message for report in reports] == [WIDEN_MESSAGE] * 3


def test_widen_rule_reports_narrower_open_mapping_value_types() -> None:
    _runner, reports = _reports(
        NoWidenThenCast(),
        """
        from collections.abc import Mapping
        from typing import cast

        original: dict[str, int]
        widened: Mapping[str, object] = original
        first = cast(dict[str, int], widened)
        second = cast(Mapping[str, bytes], widened)
        """,
    )

    assert [report.message for report in reports] == [WIDEN_MESSAGE, WIDEN_MESSAGE]


def test_widen_rule_stops_at_reassignment_and_lexical_scope_boundaries() -> None:
    _runner, reports = _reports(
        NoWidenThenCast(),
        """
        from typing import cast

        text: str
        reassigned: object = text
        reassigned = other
        first = cast(str, reassigned)

        outer: object = text
        def nested():
            return cast(str, outer)
        """,
    )

    assert reports == []


def test_widen_rule_ignores_declarations_without_initializers() -> None:
    _runner, reports = _reports(
        NoWidenThenCast(),
        """
        from typing import cast

        value: object
        result = cast(str, value)
        """,
    )

    assert reports == []


def test_widen_rule_ignores_conditional_widening_evidence() -> None:
    _runner, reports = _reports(
        NoWidenThenCast(),
        """
        from typing import cast

        text: str
        if condition:
            value: object = text
        result = cast(str, value)
        """,
    )

    assert reports == []


@pytest.mark.parametrize(
    "target",
    [
        "object",
        "Any",
        "types.Any",
        "types.Optional[object]",
        "list[Any]",
        "dict[str, object]",
    ],
)
def test_widen_rule_excludes_broad_cast_targets(target: str) -> None:
    _runner, reports = _reports(
        NoWidenThenCast(),
        f"""
        import typing as types
        from typing import Any, cast

        text: str
        widened: object = text
        result = cast({target}, widened)
        """,
    )

    assert reports == []


def test_widen_rule_excludes_open_mapping_cast_targets() -> None:
    _runner, reports = _reports(
        NoWidenThenCast(),
        """
        from collections.abc import Mapping
        from typing import Any, cast

        original: dict[str, int]
        widened: Mapping[str, object] = original
        same = cast(Mapping[str, object], widened)
        still_broad = cast(Mapping[str, Any], widened)
        """,
    )

    assert reports == []


def test_widen_rule_ignores_shadowed_casts() -> None:
    _runner, reports = _reports(
        NoWidenThenCast(),
        """
        from typing import cast

        def local(cast):
            text: str
            widened: object = text
            return cast(str, widened)
        """,
    )

    assert reports == []


def test_safety_rule_resolves_qualified_import_and_assignment_cast_aliases() -> None:
    _runner, reports = _reports(
        RequireSafetyCommentForCast(),
        """
        import typing as types
        from typing import cast as imported_cast

        assigned_cast = imported_cast
        first = types.cast(str, value)
        second = imported_cast(str, value)
        third = assigned_cast(str, value)
        """,
    )

    assert [report.message for report in reports] == [SAFETY_MESSAGE] * 3


def test_safety_rule_accepts_comment_before_statement_or_parenthesized_cast() -> None:
    _runner, reports = _reports(
        RequireSafetyCommentForCast(),
        """
        from typing import cast

        # Boundary validation is the relevant review context.
        # SAFETY: validated by the parser at the boundary.
        first = cast(str, value)

        second = (
            # SAFETY: the protocol guarantees bytes in this branch.
            cast(bytes, value)
        )
        """,
    )

    assert reports == []


def test_statement_safety_comment_owns_all_casts_in_that_statement_only() -> None:
    _runner, reports = _reports(
        RequireSafetyCommentForCast(),
        """
        from typing import cast

        # SAFETY: both tuple fields were validated together.
        pair = (cast(str, left), cast(int, right))
        later = cast(bytes, value)
        """,
    )

    assert [report.message for report in reports] == [SAFETY_MESSAGE]


@pytest.mark.parametrize(
    "source",
    [
        """
        from typing import cast

        # SAFETY: stale justification.

        result = cast(str, value)
        """,
        """
        from typing import cast

        # SAFETY: justification belongs to the next statement.
        unrelated = value
        result = cast(str, value)
        """,
        """
        from typing import cast

        result = cast(str, value)  # SAFETY: trailing comments are not review gates.
        """,
    ],
)
def test_safety_rule_rejects_non_immediate_or_unowned_comments(source: str) -> None:
    _runner, reports = _reports(RequireSafetyCommentForCast(), source)

    assert [report.message for report in reports] == [SAFETY_MESSAGE]


def test_safety_rule_ignores_shadowed_cast_names() -> None:
    _runner, reports = _reports(
        RequireSafetyCommentForCast(),
        """
        import typing
        from typing import cast

        def local(typing, cast):
            return typing.cast(str, value), cast(bytes, value)
        """,
    )

    assert reports == []


@pytest.mark.parametrize(
    ("rule", "source", "message"),
    [
        (
            NoChainedCasts(),
            "from typing import cast\nresult = cast(str, cast(object, value))\n",
            CHAINED_MESSAGE,
        ),
        (
            NoCastsToNever(),
            "from typing import Never, cast\nresult = cast(Never, value)\n",
            NEVER_MESSAGE,
        ),
        (
            NoWidenThenCast(),
            "from typing import cast\ntext: str\nvalue: object = text\nresult = cast(str, value)\n",
            WIDEN_MESSAGE,
        ),
        (
            RequireSafetyCommentForCast(),
            "from typing import cast\nresult = cast(str, value)\n",
            SAFETY_MESSAGE,
        ),
    ],
)
def test_cast_policy_diagnostics_have_exact_messages_and_no_replacements(
    rule: LintRule,
    source: str,
    message: str,
) -> None:
    runner, reports = _reports(rule, source)

    assert [report.message for report in reports] == [message]
    assert [report.replacement for report in reports] == [None]
    assert runner.apply_replacements(reports).code == source
