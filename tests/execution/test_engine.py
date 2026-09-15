# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from pathlib import Path
from textwrap import dedent
from unittest import TestCase
from unittest.mock import patch

import pytest
from libcst import (
    Call,
    Expr,
    ImportFrom,
    Module,
    ParserSyntaxError,
    SimpleStatementLine,
    SimpleString,
    ensure_type,
    parse_module,
)
from libcst.metadata import CodePosition, CodeRange

from rattle.config.models import Config
from rattle.diagnostics import LintViolation
from rattle.engine import LintRunner, diff_violation
from rattle.rule import LintRule


class EngineTest(TestCase):
    def test_diff_violation(self) -> None:
        src = dedent(
            """\
                import sys
                print("hello world")
            """
        )
        path = Path("foo.py")
        module = parse_module(src)
        node = ensure_type(
            ensure_type(ensure_type(module.body[-1], SimpleStatementLine).body[0], Expr).value,
            Call,
        ).args[0]
        repl = node.with_changes(value=SimpleString('"goodnight moon"'))

        violation = LintViolation(
            "Fake",
            CodeRange(CodePosition(1, 1), CodePosition(2, 2)),
            message="some error",
            node=node,
            replacement=repl,
        )

        expected = dedent(
            """\
                --- a/foo.py
                +++ b/foo.py
                @@ -1,2 +1,2 @@
                 import sys
                -print("hello world")
                +print("goodnight moon")
            """
        )
        result = diff_violation(path, module, violation)
        assert expected == result

    def test_collect_violations_skips_rules_when_source_lacks_visited_syntax(self) -> None:
        class ImportFromRule(LintRule):
            visited_import = False

            def visit_ImportFrom(self, node: ImportFrom) -> None:
                type(self).visited_import = True

        runner = LintRunner(Path("clean.py"), b"x = 1\n")
        rule = ImportFromRule()

        with patch.object(rule, "get_visitors", wraps=rule.get_visitors) as get_visitors:
            assert (
                list(
                    runner.collect_violations(
                        [rule],
                        Config(path=Path("clean.py")),
                    )
                )
                == []
            )
            get_visitors.assert_not_called()
        assert not ImportFromRule.visited_import

        matching_rule = ImportFromRule()
        matching_runner = LintRunner(Path("matching.py"), b"from x import y\n")
        with patch.object(
            matching_rule, "get_visitors", wraps=matching_rule.get_visitors
        ) as get_visitors:
            assert (
                list(
                    matching_runner.collect_violations(
                        [matching_rule],
                        Config(path=Path("matching.py")),
                    )
                )
                == []
            )
            get_visitors.assert_called_once()
        assert ImportFromRule.visited_import

    def test_collect_violations_still_parses_when_all_rules_are_source_filtered(self) -> None:
        class PatternRule(LintRule):
            SOURCE_PATTERNS = ("def ",)

            def visit_Module(self, node: Module) -> None:
                pass

        runner = LintRunner(Path("invalid.py"), b"(")

        with pytest.raises(ParserSyntaxError):
            list(
                runner.collect_violations(
                    [PatternRule()],
                    Config(path=Path("invalid.py")),
                )
            )

    def test_inferred_source_filters_allow_keyword_tabs(self) -> None:
        class ClassRule(LintRule):
            visited = False

            def visit_ClassDef(self, node: object) -> None:
                type(self).visited = True

        class FunctionRule(LintRule):
            visited = False

            def visit_FunctionDef(self, node: object) -> None:
                type(self).visited = True

        runner = LintRunner(
            Path("keyword_tabs.py"),
            b"class\tC(object):\n    pass\n\ndef\tf():\n    pass\n",
        )

        assert (
            list(
                runner.collect_violations(
                    [ClassRule(), FunctionRule()],
                    Config(path=Path("keyword_tabs.py")),
                )
            )
            == []
        )
        assert ClassRule.visited
        assert FunctionRule.visited

    def test_structural_replacement_transformer_duplicate_subtrees(self) -> None:
        import libcst as cst

        code = "items = foo(list([1, 2]), list([1, 2]))\n"
        runner = LintRunner(Path("test.py"), code.encode())

        class Finder(cst.CSTVisitor):
            def __init__(self) -> None:
                self.calls: list[cst.Call] = []
                self.stmt: cst.SimpleStatementLine | None = None

            def visit_SimpleStatementLine(self, node: cst.SimpleStatementLine) -> None:
                self.stmt = node

            def visit_Call(self, node: cst.Call) -> None:
                if getattr(node.func, "value", None) == "list":
                    self.calls.append(node)

        finder = Finder()
        runner.module.visit(finder)
        assert finder.stmt is not None
        assert len(finder.calls) == 2

        v1 = LintViolation(
            "RuleStmt",
            None,
            "stmt",
            finder.stmt,
            finder.stmt.with_changes(leading_lines=[cst.EmptyLine()]),
        )
        v2 = LintViolation(
            "RuleCall",
            None,
            "call2",
            finder.calls[1],
            cst.List([cst.Element(cst.Integer("1")), cst.Element(cst.Integer("2"))]),
        )

        fixed = runner.apply_replacements([v1, v2])
        assert fixed.code.strip() == "items = foo(list([1, 2]), [1, 2])"

    def test_multi_level_nested_replacements_do_not_revert_children(self) -> None:
        from rattle.rules.legacy.rewrite_to_literal import RewriteToLiteral
        from rattle.rules.style.sorted_attributes import SortedAttributes

        code = '''class Constants:
    """@sorted-attributes"""
    Z = 1
    A = 2

    def check(self, val):
        if val:
            return 1
        items = list([1, 2, 3])
        return items
'''
        runner = LintRunner(Path("test.py"), code.encode())
        violations = list(
            runner.collect_violations(
                [SortedAttributes(), RewriteToLiteral()],
                config=Config(path=Path("test.py")),
            )
        )
        fixed = runner.apply_replacements(violations)
        assert "list([1, 2, 3])" not in fixed.code
        assert "[1, 2, 3]" in fixed.code

    def test_rule_violations_cleared_across_files(self) -> None:
        from rattle.rules.style.no_annotated_self import NoAnnotatedSelf

        rule = NoAnnotatedSelf()
        config = Config(path=Path("f1.py"))

        runner1 = LintRunner(Path("f1.py"), b"class A:\n    def f(self: A): pass\n")
        v1 = list(runner1.collect_violations([rule], config=config))
        assert len(v1) == 1

        runner2 = LintRunner(Path("f2.py"), b"class B:\n    def g(self): pass\n")
        v2 = list(runner2.collect_violations([rule], config=config))
        assert len(v2) == 0
