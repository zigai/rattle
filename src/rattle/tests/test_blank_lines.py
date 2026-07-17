from __future__ import annotations

import re
import textwrap
from pathlib import Path

import pytest

from rattle import Config, Invalid, LintRule, Valid
from rattle.config import QualifiedRule, find_rules, resolve_rule_settings
from rattle.engine import LintRunner
from rattle.ftypes import RuleOptions
from rattle.rules.blank_lines import (
    BlankLineAfterControlBlock,
    BlankLineAfterTerminalControlBlock,
    BlankLineBeforeBranchInLargeSuite,
    BlockHeaderCuddleRelaxed,
    NoSuiteLeadingTrailingBlankLines,
)
from rattle.rules.blank_lines.blank_line_before_assignment import BlankLineBeforeAssignment
from rattle.rules.blank_lines.block_header_cuddle_strict import BlockHeaderCuddleStrict
from rattle.rules.blank_lines.match_case_separation import MatchCaseSeparation

RULE_CLASSES: tuple[type[LintRule], ...] = (
    NoSuiteLeadingTrailingBlankLines,
    BlankLineAfterTerminalControlBlock,
    BlankLineBeforeAssignment,
    BlankLineBeforeBranchInLargeSuite,
    BlockHeaderCuddleRelaxed,
    BlockHeaderCuddleStrict,
    BlankLineAfterControlBlock,
    MatchCaseSeparation,
)

DEFAULT_RULE_COLLECTION: tuple[type[LintRule], ...] = (
    NoSuiteLeadingTrailingBlankLines,
    BlankLineAfterTerminalControlBlock,
    BlankLineBeforeBranchInLargeSuite,
    BlockHeaderCuddleRelaxed,
    BlankLineAfterControlBlock,
)


def _dedent(source: str) -> str:
    return textwrap.dedent(re.sub(r"\A\n", "", source))


def _as_valid(case: str | Valid) -> Valid:
    if isinstance(case, str):
        return Valid(code=case)

    return case


def _as_invalid(case: str | Invalid) -> Invalid:
    if isinstance(case, str):
        return Invalid(code=case)

    return case


def _run_rule(
    rule_cls: type[LintRule],
    source: str,
    options: RuleOptions | None = None,
) -> tuple[LintRunner, list]:
    path = Path("fixture.py")
    rule = rule_cls()
    if options is not None:
        rule.configure(options)
    runner = LintRunner(path, _dedent(source).encode())
    reports = list(runner.collect_violations([rule], Config(path=path, root=Path.cwd())))

    return runner, reports


def _run_rules(
    rule_classes: tuple[type[LintRule], ...],
    source: str,
) -> tuple[LintRunner, list]:
    path = Path("fixture.py")
    rules = [rule_cls() for rule_cls in rule_classes]
    runner = LintRunner(path, _dedent(source).encode())
    reports = list(runner.collect_violations(rules, Config(path=path, root=Path.cwd())))

    return runner, reports


VALID_CASES = [
    pytest.param(
        rule_cls,
        _as_valid(case),
        id=f"{rule_cls.name}.VALID[{index}]",
    )
    for rule_cls in RULE_CLASSES
    for index, case in enumerate(rule_cls.VALID)
]

INVALID_CASES = [
    pytest.param(
        rule_cls,
        _as_invalid(case),
        id=f"{rule_cls.name}.INVALID[{index}]",
    )
    for rule_cls in RULE_CLASSES
    for index, case in enumerate(rule_cls.INVALID)
]


@pytest.mark.parametrize(("rule_cls", "case"), VALID_CASES)
def test_valid_fixtures_produce_no_reports(rule_cls: type[LintRule], case: Valid) -> None:
    _, reports = _run_rule(rule_cls, case.code, case.options)
    assert reports == []


@pytest.mark.parametrize(("rule_cls", "case"), INVALID_CASES)
def test_invalid_fixtures_produce_expected_reports(
    rule_cls: type[LintRule],
    case: Invalid,
) -> None:
    runner, reports = _run_rule(rule_cls, case.code, case.options)

    assert reports

    if case.expected_message is not None:
        assert all(report.message == case.expected_message for report in reports)

    if case.expected_replacement is not None:
        fixed_code = runner.apply_replacements(reports).code
        assert fixed_code == _dedent(case.expected_replacement)

        _, fixed_reports = _run_rule(rule_cls, fixed_code, case.options)
        assert fixed_reports == []


def test_rule_discovery_only_returns_concrete_rules() -> None:
    discovered = {rule.__name__ for rule in find_rules(QualifiedRule("rattle.rules.blank_lines"))}
    assert "BaseBlankLinesRule" not in discovered
    assert "BaseBlockHeaderCuddleRule" not in discovered
    assert "BlockHeaderCuddleStrict" not in discovered
    assert "MatchCaseSeparation" not in discovered


def test_strict_rule_can_be_enabled_explicitly() -> None:
    discovered = {
        rule.__name__
        for rule in find_rules(QualifiedRule("rattle.rules.blank_lines.block_header_cuddle_strict"))
    }
    assert discovered == {"BlockHeaderCuddleStrict"}


def test_match_case_rule_can_be_enabled_explicitly() -> None:
    discovered = {
        rule.__name__
        for rule in find_rules(QualifiedRule("rattle.rules.blank_lines.match_case_separation"))
    }
    assert discovered == {"MatchCaseSeparation"}


def test_rule_settings_resolve_from_short_selectors() -> None:
    path = Path("fixture.py")
    config = Config(
        path=path,
        root=Path.cwd(),
        options={
            "blank-line-before-branch": {"max_suite_non_empty_lines": 4},
            "blank-line-after-terminal-control-block": {"allow_compact_guard_ladders": False},
            "match-case-separation": {"max_case_non_empty_lines": 5},
        },
    )

    resolved = resolve_rule_settings(
        config,
        {
            BlankLineBeforeBranchInLargeSuite,
            BlankLineAfterTerminalControlBlock,
            MatchCaseSeparation,
        },
    )

    assert resolved == {
        BlankLineBeforeBranchInLargeSuite: {"max_suite_non_empty_lines": 4},
        BlankLineAfterTerminalControlBlock: {"allow_compact_guard_ladders": False},
        MatchCaseSeparation: {"max_case_non_empty_lines": 5},
    }


def test_bl200_reports_branch_keyword_instead_of_full_multiline_return() -> None:
    _, reports = _run_rule(
        BlankLineBeforeBranchInLargeSuite,
        """
        def f(value: int) -> dict[str, int]:
            first = value + 1
            second = first + 1
            return {
                "first": first,
                "second": second,
            }
        """,
        {"allow_related_return_tails": False},
    )

    assert len(reports) == 1
    report = reports[0]
    assert report.range.start.line == 4
    assert report.range.end.line == 4
    assert report.range.end.column - report.range.start.column == len("return")


def test_bl200_allows_typed_result_binding_immediately_before_return() -> None:
    _, reports = _run_rule(
        BlankLineBeforeBranchInLargeSuite,
        """
        def f(parts: list[str]) -> dict[str, int]:
            cleaned = [part.strip() for part in parts]
            joined = ",".join(cleaned)
            payload: dict[str, int] = {"count": len(cleaned), "width": len(joined)}
            return payload
        """,
    )

    assert reports == []


def test_bl100_allows_ruff_style_blank_line_before_nested_loop_handler() -> None:
    _, reports = _run_rule(
        NoSuiteLeadingTrailingBlankLines,
        """
        def f(keys: str) -> None:
            for key in keys:

                @register(key)
                def handle() -> None:
                    print(key)
        """,
    )

    assert reports == []


def test_bl100_keeps_class_body_compact_at_suite_start() -> None:
    _, reports = _run_rule(
        NoSuiteLeadingTrailingBlankLines,
        """
        class Handler:

            def handle(self) -> None:
                print("x")
        """,
    )

    assert len(reports) == 1
    assert reports[0].message == NoSuiteLeadingTrailingBlankLines.LEADING_MESSAGE


def test_bl210_reports_first_line_of_multiline_assignment() -> None:
    _, reports = _run_rule(
        BlankLineBeforeAssignment,
        """
        def f(value: int) -> dict[str, int]:
            log_value(value)
            payload = {
                "value": value,
            }
            return payload
        """,
    )

    assert len(reports) == 1
    report = reports[0]
    assert report.range.start.line == 3
    assert report.range.end.line == 3


def test_default_rule_collection_converges_after_guard_to_assignment_fix() -> None:
    runner, reports = _run_rules(
        DEFAULT_RULE_COLLECTION,
        """
        def f(flag: bool, label: str) -> str:
            if not flag:
                return label
            cleaned = label.strip()
            return cleaned
        """,
    )

    assert reports

    fixed_code = runner.apply_replacements(reports).code
    assert fixed_code == _dedent(
        """
        def f(flag: bool, label: str) -> str:
            if not flag:
                return label

            cleaned = label.strip()
            return cleaned
        """
    )

    _, fixed_reports = _run_rules(DEFAULT_RULE_COLLECTION, fixed_code)
    assert fixed_reports == []


def test_default_rule_collection_keeps_compact_loop_exit_tail() -> None:
    _, reports = _run_rules(
        DEFAULT_RULE_COLLECTION,
        """
        def f(name: str) -> str:
            parts: list[str] = []
            index = 0
            while index < len(name):
                ch = name[index]
                if ch in {"'", '"'}:
                    end = _consume_quoted_segment(name, index)
                    parts.append(name[index:end])
                    index = end
                    continue

                parts.append(ch)
                index += 1

            return "".join(parts)
        """,
    )

    assert reports == []


def test_default_rule_collection_keeps_compact_guard_return_chain() -> None:
    _, reports = _run_rules(
        DEFAULT_RULE_COLLECTION,
        """
        def f(shell_name: str, interactive: bool) -> list[str]:
            if shell_name == "zsh":
                return ["-lic"]
            if interactive:
                return ["-ic"]
            return ["-lc"]
        """,
    )

    assert reports == []


def test_default_rule_collection_allows_compact_terminal_simple_return_tail() -> None:
    _, reports = _run_rules(
        DEFAULT_RULE_COLLECTION,
        """
        def f() -> int:
            log_start()
            value = compute()
            return value
        """,
    )

    assert reports == []


def test_default_rule_collection_allows_ruff_style_nested_definition_at_loop_start() -> None:
    _, reports = _run_rules(
        DEFAULT_RULE_COLLECTION,
        """
        def f(digits: str) -> None:
            for digit in digits:

                @register(digit)
                def handle() -> None:
                    print(digit)
        """,
    )

    assert reports == []


def test_default_rule_collection_converges_after_nested_loop_tail_return() -> None:
    runner, reports = _run_rules(
        DEFAULT_RULE_COLLECTION,
        """
        def f(items: list[int]) -> tuple[int, ...]:
            result: list[int] = []
            if items:
                for item in items:
                    if item % 2 == 0:
                        result.append(item)
                return tuple(result)

            return ()
        """,
    )

    assert reports

    fixed_code = runner.apply_replacements(reports).code
    _, fixed_reports = _run_rules(DEFAULT_RULE_COLLECTION, fixed_code)
    assert fixed_reports == []


def test_default_rule_collection_converges_after_nested_guard_chain_assignment_followup() -> None:
    runner, reports = _run_rules(
        DEFAULT_RULE_COLLECTION,
        """
        def f(values: list[str]) -> dict[str, str]:
            result: dict[str, str] = {}
            for value in values:
                if value == "":
                    continue
                if value.startswith("#"):
                    cleaned = value.removeprefix("#")
                    if not cleaned:
                        continue
                    value = cleaned
                result[value] = value

            return result
        """,
    )

    assert reports

    fixed_code = runner.apply_replacements(reports).code
    second_runner, fixed_reports = _run_rules(DEFAULT_RULE_COLLECTION, fixed_code)
    assert fixed_reports

    fixed_code = second_runner.apply_replacements(fixed_reports).code
    _, fixed_reports = _run_rules(DEFAULT_RULE_COLLECTION, fixed_code)
    assert fixed_reports == []


def test_bl300_reports_block_header_line_only() -> None:
    _, reports = _run_rule(
        BlockHeaderCuddleRelaxed,
        """
        def f(default_value: object) -> object:
            prepared = default_value
            if default_value:
                log(default_value)
            return prepared
        """,
    )

    assert len(reports) == 1
    report = reports[0]
    assert report.range.start.line == 3
    assert report.range.end.line == 3
    assert report.range.end.column - report.range.start.column == len("if")


def test_bl300_allows_same_result_slot_guarded_overwrite() -> None:
    _, reports = _run_rule(
        BlockHeaderCuddleRelaxed,
        """
        def f(override_name: str | None) -> str:
            display_name = "guest"
            if override_name is not None:
                display_name = override_name
            return display_name
        """,
    )

    assert reports == []


def test_bl300_allows_compact_guard_ladder_before_separated_main_path_return() -> None:
    _, reports = _run_rule(
        BlockHeaderCuddleRelaxed,
        """
        def f(primary: str | None, fallback: str | None) -> str:
            if primary is not None:
                return primary
            if fallback is not None:
                return fallback

            return "guest"
        """,
    )

    assert reports == []


def test_bl300_allows_container_initialized_before_guarded_mutation() -> None:
    _, reports = _run_rule(
        BlockHeaderCuddleRelaxed,
        """
        def f(default_value: object) -> dict[str, object]:
            prompt_kwargs: dict[str, object] = {}
            if default_value:
                prompt_kwargs["placeholder"] = str(default_value)
            return prompt_kwargs
        """,
    )

    assert reports == []


def test_bl300_allows_immediate_same_receiver_setup_and_guard() -> None:
    _, reports = _run_rule(
        BlockHeaderCuddleRelaxed,
        """
        def f() -> None:
            session = build_session()
            session.refresh()
            if session.is_stale():
                reset_session(session)
                return
            cleanup()
        """,
    )

    assert reports == []


def test_bl300_allows_immediate_subscript_update_and_guard() -> None:
    _, reports = _run_rule(
        BlockHeaderCuddleRelaxed,
        """
        def f(slots: dict[str, int], key: str) -> None:
            slots[key] -= 1
            if slots[key] < 0:
                raise ValueError(key)
        """,
    )

    assert reports == []


def test_bl300_allows_immediate_attribute_assignment_and_guard() -> None:
    _, reports = _run_rule(
        BlockHeaderCuddleRelaxed,
        """
        def f(session: object) -> None:
            session.ready = compute_ready_flag()
            if session.ready:
                start(session)
        """,
    )

    assert reports == []


def test_bl300_allows_immediate_same_receiver_rhs_and_guard() -> None:
    _, reports = _run_rule(
        BlockHeaderCuddleRelaxed,
        """
        def f(task_state: object) -> None:
            total = 0.0
            total += task_state.total
            if task_state.completed is not None:
                consume(task_state.completed, total)
        """,
    )

    assert reports == []


def test_bl300_allows_expression_setup_before_related_match() -> None:
    _, reports = _run_rule(
        BlockHeaderCuddleRelaxed,
        """
        def f(registry: object, handler: object) -> object:
            registry.attach(handler)
            match registry.mode:
                case "primary":
                    return registry.dispatch("x")
                case _:
                    return registry.dispatch("fallback")
        """,
    )

    assert reports == []


def test_bl300_allows_expression_setup_before_related_with_block() -> None:
    _, reports = _run_rule(
        BlockHeaderCuddleRelaxed,
        """
        def f(tracker: object) -> object:
            tracker.prepare("job")
            with tracker.capture() as snapshot:
                tracker.enable()
                return tracker.finish(), snapshot
        """,
    )

    assert reports == []


def test_bl300_allows_tuple_unpack_before_related_guard() -> None:
    _, reports = _run_rule(
        BlockHeaderCuddleRelaxed,
        """
        def f(subject: object) -> None:
            left, candidate, payload = inspect_subject(subject)
            if not isinstance(candidate, ExpectedNode):
                raise UnexpectedNodeError(f"Unexpected node type: {type(candidate)!r}")
            consume(left, payload)
        """,
    )

    assert reports == []


def test_bl350_reports_first_line_of_following_multiline_statement() -> None:
    _, reports = _run_rule(
        BlankLineAfterControlBlock,
        """
        def f(value: int) -> dict[str, int]:
            if value > 0:
                value += 1
            return {
                "value": value,
            }
        """,
    )

    assert len(reports) == 1
    report = reports[0]
    assert report.range.start.line == 4
    assert report.range.end.line == 4


def test_bl350_allows_related_expression_fallthrough() -> None:
    _, reports = _run_rule(
        BlankLineAfterControlBlock,
        """
        def f(width: int | None, columns: list[str]) -> list[str]:
            if width is not None:
                template = f"{width:02d}"
                columns.append(template)
            columns.append(template if width is not None else "default")
            return columns
        """,
    )

    assert reports == []


def test_default_rule_collection_keeps_loop_cleanup_compact_but_separates_phases() -> None:
    runner, reports = _run_rules(
        DEFAULT_RULE_COLLECTION,
        """
        def f(stream: object) -> tuple[object, ...]:
            captured: list[object] = []
            while stream.tokens:
                token = stream.tokens[0]
                if token == "<STOP>":
                    stream.tokens.pop(0)
                    captured.extend(stream.tokens)
                    stream.tokens.clear()
                    break
                if stream.is_boundary(token):
                    break
                captured.append(stream.tokens.pop(0))
            return tuple(captured)
        """,
    )

    fixed_code = runner.apply_replacements(reports).code
    assert fixed_code == _dedent(
        """
        def f(stream: object) -> tuple[object, ...]:
            captured: list[object] = []
            while stream.tokens:
                token = stream.tokens[0]
                if token == "<STOP>":
                    stream.tokens.pop(0)
                    captured.extend(stream.tokens)
                    stream.tokens.clear()
                    break

                if stream.is_boundary(token):
                    break

                captured.append(stream.tokens.pop(0))

            return tuple(captured)
        """
    )

    _, fixed_reports = _run_rules(DEFAULT_RULE_COLLECTION, fixed_code)
    assert fixed_reports == []


def test_default_rule_collection_keeps_tuple_unpack_attached_to_guard_then_separates_main_flow() -> (
    None
):
    runner, reports = _run_rules(
        DEFAULT_RULE_COLLECTION,
        """
        def f(subject: object) -> None:
            left, candidate, payload = inspect_subject(subject)
            if not isinstance(candidate, ExpectedNode):
                raise UnexpectedNodeError(f"Unexpected node type: {type(candidate)!r}")
            resolved_name = left if left is not None else (candidate.name or "")
            consume(resolved_name, payload)
        """,
    )

    fixed_code = runner.apply_replacements(reports).code
    assert fixed_code == _dedent(
        """
        def f(subject: object) -> None:
            left, candidate, payload = inspect_subject(subject)
            if not isinstance(candidate, ExpectedNode):
                raise UnexpectedNodeError(f"Unexpected node type: {type(candidate)!r}")

            resolved_name = left if left is not None else (candidate.name or "")
            consume(resolved_name, payload)
        """
    )

    _, fixed_reports = _run_rules(DEFAULT_RULE_COLLECTION, fixed_code)
    assert fixed_reports == []


def test_bl200_allows_compact_cleanup_break_tail() -> None:
    _, reports = _run_rule(
        BlankLineBeforeBranchInLargeSuite,
        """
        def f(stream: object, captured: list[str]) -> None:
            while stream.tokens:
                if stream.tokens[0] == "<STOP>":
                    stream.tokens.pop(0)
                    captured.extend(stream.tokens)
                    stream.tokens.clear()
                    break
        """,
    )

    assert reports == []


def test_bl400_reports_case_keyword_only() -> None:
    _, reports = _run_rule(
        MatchCaseSeparation,
        """
        def f(value: int) -> int:
            match value:
                case 1:
                    first = 1
                    second = 2
                    third = 3
                case _:
                    return 0
        """,
    )

    assert len(reports) == 1
    report = reports[0]
    assert report.range.start.line == 7
    assert report.range.end.line == 7
    assert report.range.end.column - report.range.start.column == len("case")


def test_bl100_combined_suite_boundary_fixes_do_not_overlap() -> None:
    runner, reports = _run_rule(
        NoSuiteLeadingTrailingBlankLines,
        """
        def f() -> None:

            work()


        """,
    )

    assert {report.message for report in reports} == {
        NoSuiteLeadingTrailingBlankLines.LEADING_MESSAGE,
        NoSuiteLeadingTrailingBlankLines.TRAILING_MESSAGE,
    }

    fixed_code = runner.apply_replacements(reports).code
    assert fixed_code == _dedent(
        """
        def f() -> None:
            work()
        """
    )
    _, fixed_reports = _run_rule(NoSuiteLeadingTrailingBlankLines, fixed_code)
    assert fixed_reports == []


@pytest.mark.parametrize(
    "source",
    [
        """
        def f(first: bool, second: bool) -> None:
            if first:
                work()
            elif second:
                work()
            else:
                return
            followup()
        """,
        """
        def f(items: list[int]) -> None:
            for item in items:
                work(item)
            else:
                return
            followup()
        """,
        """
        def f(items: list[int]) -> None:
            while items:
                items.pop()
            else:
                return
            followup()
        """,
    ],
)
def test_terminal_rule_checks_terminal_alternative_suites(source: str) -> None:
    runner, reports = _run_rule(BlankLineAfterTerminalControlBlock, source)

    assert len(reports) == 1
    fixed_code = runner.apply_replacements(reports).code
    _, fixed_reports = _run_rule(BlankLineAfterTerminalControlBlock, fixed_code)
    assert fixed_reports == []


def test_terminal_rule_does_not_join_noncontiguous_guards_into_ladder() -> None:
    runner, reports = _run_rule(
        BlankLineAfterTerminalControlBlock,
        """
        def f(first: bool, second: bool) -> int:
            if first:
                return 1

            work()
            if second:
                return 2
            return 3
        """,
    )

    assert len(reports) == 1
    fixed_code = runner.apply_replacements(reports).code
    _, fixed_reports = _run_rule(BlankLineAfterTerminalControlBlock, fixed_code)
    assert fixed_reports == []


def test_terminal_rule_supports_exception_group_try_blocks() -> None:
    runner, reports = _run_rule(
        BlankLineAfterTerminalControlBlock,
        """
        def f() -> None:
            try:
                return
            except* ValueError:
                recover()
            followup()
        """,
    )

    assert len(reports) == 1
    fixed_code = runner.apply_replacements(reports).code
    _, fixed_reports = _run_rule(BlankLineAfterTerminalControlBlock, fixed_code)
    assert fixed_reports == []


def test_terminal_rule_disabled_guard_ladder_exemption_requires_spacing() -> None:
    _, reports = _run_rule(
        BlankLineAfterTerminalControlBlock,
        """
        def f(first: bool, second: bool) -> int:
            if first:
                return 1
            if second:
                return 2
            return 3
        """,
        {"allow_compact_guard_ladders": False},
    )

    assert len(reports) == 1


@pytest.mark.parametrize(
    "source",
    [
        """
        def f(flag: bool) -> None:
            if flag:
                pass
            else:
                log()
                value = compute()
        """,
        """
        def f(value: object) -> None:
            match value:
                case _:
                    log()
                    result = compute()
        """,
        """
        def f() -> None:
            try:
                work()
            except Exception:
                log()
                result = compute()
        """,
        """
        def f() -> None:
            try:
                work()
            finally:
                log()
                result = compute()
        """,
    ],
)
def test_bl210_short_control_flow_limit_applies_to_alternative_suites(source: str) -> None:
    _, reports = _run_rule(
        BlankLineBeforeAssignment,
        source,
        {"short_control_flow_max_statements": 2},
    )

    assert reports == []


def test_bl210_local_helper_parameter_shadow_is_not_a_capture() -> None:
    runner, reports = _run_rule(
        BlankLineBeforeAssignment,
        """
        def f() -> None:
            log()
            payload = make_payload()
            def helper(payload: object) -> object:
                return payload
        """,
    )

    assert len(reports) == 1
    fixed_code = runner.apply_replacements(reports).code
    _, fixed_reports = _run_rule(BlankLineBeforeAssignment, fixed_code)
    assert fixed_reports == []


def test_bl210_short_exception_group_handler_is_control_flow() -> None:
    _, reports = _run_rule(
        BlankLineBeforeAssignment,
        """
        def f() -> None:
            try:
                work()
            except* ValueError:
                log()
                result = compute()
        """,
        {"short_control_flow_max_statements": 2},
    )

    assert reports == []


def test_bl210_local_helper_real_closure_capture_remains_compact() -> None:
    _, reports = _run_rule(
        BlankLineBeforeAssignment,
        """
        def f() -> None:
            log()
            payload = make_payload()
            def helper() -> object:
                return payload
        """,
    )

    assert reports == []


def test_bl210_disabled_local_capture_exemption_requires_spacing() -> None:
    _, reports = _run_rule(
        BlankLineBeforeAssignment,
        """
        def f() -> None:
            log()
            payload = make_payload()
            def helper() -> object:
                return payload
        """,
        {"allow_local_helper_capture": False},
    )

    assert len(reports) == 1


def test_bl210_enabled_post_guard_continuation_stays_compact() -> None:
    _, reports = _run_rule(
        BlankLineBeforeAssignment,
        """
        def f(flag: bool) -> str:
            if not flag:
                return ""
            result = compute()
            return result
        """,
        {"allow_post_guard_continuation": True},
    )

    assert reports == []


def test_bl210_related_use_honors_configured_lookahead() -> None:
    _, reports = _run_rule(
        BlankLineBeforeAssignment,
        """
        def f() -> None:
            log_start()
            result = compute()
            log_progress()
            consume(result)
        """,
        {"related_use_lookahead": 1},
    )

    assert len(reports) == 1


def test_bl200_disabled_related_tails_preserve_annotated_return_separator() -> None:
    _, reports = _run_rule(
        BlankLineBeforeBranchInLargeSuite,
        """
        def f() -> int:
            first = 1
            second = 2
            payload: int = first + second

            return payload
        """,
        {"allow_related_return_tails": False},
    )

    assert reports == []


def test_bl200_disabled_guard_ladder_tail_exemption_requires_spacing() -> None:
    _, reports = _run_rule(
        BlankLineBeforeBranchInLargeSuite,
        """
        def f(first: bool, second: bool) -> int:
            if first:
                return 1
            if second:
                return 2
            return 3
        """,
        {"allow_guard_ladder_final_branch": False},
    )

    assert len(reports) == 1


def test_bl200_compact_tail_limit_is_enforced() -> None:
    _, reports = _run_rule(
        BlankLineBeforeBranchInLargeSuite,
        """
        def f(value: int) -> int:
            first = value + 1
            second = first + 1
            return first + second
        """,
        {"compact_tail_max_statements": 1},
    )

    assert len(reports) == 1


@pytest.mark.parametrize(
    "source",
    [
        """
        def f(items: list[object]) -> None:
            item = default_item()
            for item in items:
                consume(item)
        """,
        """
        def f(manager: object) -> None:
            resource = fallback_resource()
            with manager.open() as resource:
                consume(resource)
        """,
        """
        def f(subject: object) -> None:
            item = default_item()
            match subject:
                case item:
                    consume(item)
        """,
    ],
)
def test_bl300_bound_block_names_do_not_fake_setup_relationship(source: str) -> None:
    runner, reports = _run_rule(BlockHeaderCuddleRelaxed, source)

    assert len(reports) == 1
    fixed_code = runner.apply_replacements(reports).code
    _, fixed_reports = _run_rule(BlockHeaderCuddleRelaxed, fixed_code)
    assert fixed_reports == []


def test_bl300_zero_body_lookahead_disables_body_only_relationships() -> None:
    _, reports = _run_rule(
        BlockHeaderCuddleRelaxed,
        """
        def f(flag: bool) -> None:
            prepared = compute()
            if flag:
                consume(prepared)
        """,
        {"body_usage_lookahead": 0},
    )

    assert len(reports) == 1


def test_bl300_disabled_guard_ladder_setup_exemption_requires_spacing() -> None:
    _, reports = _run_rule(
        BlockHeaderCuddleRelaxed,
        """
        def f(first: bool, second: bool) -> int:
            result = default_result()
            if first:
                return 1
            if second:
                return 2
            return result
        """,
        {"allow_setup_before_compact_guard_ladder": False},
    )

    assert len(reports) == 1


def test_bl300_setup_run_lookback_is_enforced() -> None:
    _, reports = _run_rule(
        BlockHeaderCuddleRelaxed,
        """
        def f(first: bool, second: bool) -> int:
            result = default_result()
            if first:
                return 1
            if second:
                return 2
            return result
        """,
        {"setup_run_lookback": 0},
    )

    assert len(reports) == 1


def test_strict_block_cuddle_does_not_allow_body_only_assignment_use() -> None:
    runner, reports = _run_rule(
        BlockHeaderCuddleStrict,
        """
        def f(flag: bool) -> None:
            prepared = compute()
            if flag:
                consume(prepared)
        """,
    )

    assert len(reports) == 1
    fixed_code = runner.apply_replacements(reports).code
    _, fixed_reports = _run_rule(BlockHeaderCuddleStrict, fixed_code)
    assert fixed_reports == []


def test_bl350_related_value_may_be_created_in_else_suite() -> None:
    _, reports = _run_rule(
        BlankLineAfterControlBlock,
        """
        def f(flag: bool) -> None:
            if flag:
                pass
            else:
                value = compute()
            consume(value)
        """,
    )

    assert reports == []


def test_bl350_disabled_pytest_cluster_exemption_reports_and_fixes() -> None:
    runner, reports = _run_rule(
        BlankLineAfterControlBlock,
        """
        def f() -> None:
            with pytest.raises(ValueError):
                parse("x")
            with pytest.raises(TypeError):
                parse(3)
        """,
        {"allow_pytest_raises_clusters": False},
    )

    assert len(reports) == 1
    fixed_code = runner.apply_replacements(reports).code
    _, fixed_reports = _run_rule(
        BlankLineAfterControlBlock,
        fixed_code,
        {"allow_pytest_raises_clusters": False},
    )
    assert fixed_reports == []


def test_bl350_disabled_with_inspection_exemption_requires_spacing() -> None:
    _, reports = _run_rule(
        BlankLineAfterControlBlock,
        """
        def f(path: str) -> None:
            with open(path) as handle:
                content = handle.read()
            assert content
        """,
        {"allow_with_immediate_inspection": False},
    )

    assert len(reports) == 1


def test_bl350_disabled_guard_ladder_exemption_requires_spacing() -> None:
    _, reports = _run_rule(
        BlankLineAfterControlBlock,
        """
        def f(first: bool, second: bool) -> int:
            if first:
                return 1
            if second:
                return 2
            return 3
        """,
        {"allow_compact_guard_ladders": False},
    )

    assert len(reports) == 2


def test_bl350_related_assignment_lookahead_zero_requires_spacing() -> None:
    _, reports = _run_rule(
        BlankLineAfterControlBlock,
        """
        def f(flag: bool) -> None:
            if flag:
                work()
            result = compute()
            consume(result)
        """,
        {"related_use_lookahead": 0},
    )

    assert len(reports) == 1


def test_bl350_related_assignment_uses_configured_lookahead() -> None:
    _, reports = _run_rule(
        BlankLineAfterControlBlock,
        """
        def f(flag: bool) -> None:
            if flag:
                work()
            result = compute()
            log()
            consume(result)
        """,
        {"related_use_lookahead": 2},
    )

    assert reports == []


def test_bl400_fix_inserts_one_case_separator_and_converges() -> None:
    runner, reports = _run_rule(
        MatchCaseSeparation,
        """
        def f(value: int) -> int:
            match value:
                case 1:
                    first = 1
                    second = 2
                    third = 3
                case _:
                    return 0
        """,
    )

    assert len(reports) == 1
    fixed_code = runner.apply_replacements(reports).code
    assert "        third = 3\n\n        case _:" in fixed_code
    _, fixed_reports = _run_rule(MatchCaseSeparation, fixed_code)
    assert fixed_reports == []


@pytest.mark.parametrize(
    ("header", "expected_length"),
    [("async for item in items:", 9), ("async with context():", 10)],
)
def test_relaxed_cuddle_async_header_range_covers_keyword(
    header: str,
    expected_length: int,
) -> None:
    _runner, reports = _run_rule(
        BlockHeaderCuddleRelaxed,
        f"""
        async def run():
            prepare()
            {header}
                consume()
        """,
    )

    assert len(reports) == 1
    assert reports[0].range is not None
    assert reports[0].range.end.column - reports[0].range.start.column == expected_length
