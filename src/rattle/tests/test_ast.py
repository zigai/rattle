from __future__ import annotations

import ast
from pathlib import Path

import libcst as cst
import pytest
from libcst.metadata import CodePosition, CodeRange, MetadataWrapper, PositionProvider

from rattle import AstContext, AstParseError, AstProvider, LintRule
from rattle.engine import LintRunner
from rattle.ftypes import Config, Result
from rattle.output import render_rattle_result


def _ast_context(source: str) -> AstContext:
    wrapper = MetadataWrapper(cst.parse_module(source))
    return wrapper.resolve(AstProvider)[wrapper.module]


class CaptureAstRule(LintRule):
    METADATA_DEPENDENCIES = (AstProvider,)

    def __init__(self) -> None:
        super().__init__()
        self.context: AstContext | None = None

    def visit_Module(self, node: cst.Module) -> None:
        context = self.get_metadata(AstProvider, node, None)
        assert isinstance(context, AstContext)
        self.context = context


def test_ast_provider_parses_type_comments() -> None:
    rule = CaptureAstRule()
    runner = LintRunner(Path("typed.py"), b"value = 0x10  # type: int\n")

    assert list(runner.collect_violations([rule], Config(path=Path("typed.py")))) == []
    assert rule.context is not None
    assignment = rule.context.tree.body[0]
    assert isinstance(assignment, ast.Assign)
    assert isinstance(assignment.value, ast.Constant)
    assert assignment.value.value == 16
    assert assignment.type_comment == "int"


def test_ast_provider_shares_one_context_between_rules() -> None:
    first_rule = CaptureAstRule()
    second_rule = CaptureAstRule()
    runner = LintRunner(Path("shared.py"), b"value = 1\n")

    assert (
        list(
            runner.collect_violations(
                [first_rule, second_rule],
                Config(path=Path("shared.py")),
            )
        )
        == []
    )
    assert first_rule.context is not None
    assert first_rule.context is second_rule.context


def test_ast_provider_is_not_resolved_without_an_ast_rule() -> None:
    class CstOnlyRule(LintRule):
        def visit_Pass(self, node: cst.Pass) -> None:
            pass

    runner = LintRunner(Path("cst_only.py"), b"pass  # type: int\n")

    assert (
        list(
            runner.collect_violations(
                [CstOnlyRule()],
                Config(path=Path("cst_only.py")),
            )
        )
        == []
    )


def test_ast_provider_translates_parse_errors() -> None:
    runner = LintRunner(Path("invalid_type_comment.py"), b"pass  # type: int\n")

    with pytest.raises(AstParseError) as caught:
        list(
            runner.collect_violations(
                [CaptureAstRule()],
                Config(path=Path("invalid_type_comment.py")),
            )
        )

    assert caught.value.syntax_error.msg == "invalid syntax"
    assert caught.value.message == "invalid syntax"
    assert caught.value.line == 1
    assert caught.value.column == 14
    assert caught.value.python_version
    assert str(caught.value).startswith("Unable to build an AST using Python ")


def test_ast_context_converts_utf8_byte_offsets_to_character_columns() -> None:
    context = _ast_context("é = value\n")
    name = next(
        node for node in ast.walk(context.tree) if isinstance(node, ast.Name) and node.id == "value"
    )

    assert context.code_range(name) == CodeRange(
        start=CodePosition(line=1, column=4),
        end=CodePosition(line=1, column=9),
    )


def test_ast_context_converts_multiline_ranges() -> None:
    context = _ast_context("result = call(\n    value,\n)\n")
    call = next(node for node in ast.walk(context.tree) if isinstance(node, ast.Call))

    assert context.code_range(call) == CodeRange(
        start=CodePosition(line=1, column=9),
        end=CodePosition(line=3, column=1),
    )


def test_ast_context_rejects_positionless_nodes() -> None:
    context = _ast_context("value = 1\n")

    with pytest.raises(
        ValueError,
        match="Module does not have a complete source position",
    ):
        context.code_range(context.tree)


class AstNameRule(LintRule):
    METADATA_DEPENDENCIES = (AstProvider, PositionProvider)

    def __init__(self) -> None:
        super().__init__()
        self.ast_ranges: set[CodeRange] = set()

    def visit_Module(self, node: cst.Module) -> None:
        context = self.get_metadata(AstProvider, node, None)
        assert isinstance(context, AstContext)
        self.ast_ranges = {
            context.code_range(ast_node)
            for ast_node in ast.walk(context.tree)
            if isinstance(ast_node, ast.Name) and ast_node.id == "forbidden"
        }

    def visit_Name(self, node: cst.Name) -> None:
        if self.get_metadata(PositionProvider, node) in self.ast_ranges:
            self.report(node, "Forbidden AST name")


@pytest.mark.parametrize(
    ("source", "expected_count"),
    [
        (b"forbidden = 1\n", 1),
        (b"forbidden = 1  # rattle: ignore[ast-name-rule]\n", 0),
    ],
)
def test_ast_rule_uses_cst_anchor_for_local_suppressions(
    source: bytes,
    expected_count: int,
) -> None:
    runner = LintRunner(Path("names.py"), source)

    violations = list(
        runner.collect_violations(
            [AstNameRule()],
            Config(path=Path("names.py")),
        )
    )

    assert len(violations) == expected_count
    if violations:
        assert violations[0].range == CodeRange(
            start=CodePosition(line=1, column=0),
            end=CodePosition(line=1, column=9),
        )


def test_render_ast_parse_error() -> None:
    source = b"pass  # type: int\nvalue = 1\n"
    try:
        ast.parse(source, type_comments=True)
    except SyntaxError as e:
        error = AstParseError(e)
    else:
        pytest.fail("expected invalid type comment placement to fail AST parsing")

    rendered = render_rattle_result(
        Result(
            Path("typed.py"),
            violation=None,
            error=(error, "traceback"),
            source=source,
        ),
        path=Path("typed.py"),
    )

    assert rendered is not None
    assert rendered.startswith(
        f"ast-parse-error: Unable to build an AST using Python {error.python_version}: "
        "invalid syntax\n"
    )
    assert " --> typed.py:1:15\n" in rendered
    assert "1 | pass  # type: int\n" in rendered


def test_render_brief_ast_parse_error() -> None:
    source = b"pass  # type: int\n"
    try:
        ast.parse(source, type_comments=True)
    except SyntaxError as e:
        error = AstParseError(e)
    else:
        pytest.fail("expected invalid type comment placement to fail AST parsing")

    rendered = render_rattle_result(
        Result(
            Path("typed.py"),
            violation=None,
            error=(error, "traceback"),
            source=source,
        ),
        path=Path("typed.py"),
        brief=True,
    )

    assert rendered == (
        f"ast-parse-error: Unable to build an AST using Python {error.python_version}: "
        "invalid syntax  --> typed.py:1:15"
    )
