from pathlib import Path

from libcst import Name

from rattle.api import rattle_bytes
from rattle.config.models import Config
from rattle.rendering.results import render_console_result
from rattle.rule import LintRule
from rattle.util import capture


class TestApi:
    def test_rattle_bytes_redacts_unexpected_exception_details(self) -> None:
        class ExplodingRule(LintRule):
            def visit_Module(self, node: object) -> None:
                del node
                raise ValueError("api_token=TOP-SECRET")

        path = Path("secret.py")
        results = list(
            rattle_bytes(
                path,
                b"value = 1\n",
                config=Config(path=path),
                rules=[ExplodingRule()],
            )
        )

        assert len(results) == 1
        rendered = render_console_result(results[0], path=path)
        assert rendered is not None
        assert "TOP-SECRET" not in rendered
        assert "ValueError" in rendered

    def test_rattle_bytes_automatic_diff_is_aggregate(self) -> None:
        class RenameXRule(LintRule):
            def visit_Name(self, node: Name) -> None:
                if node.value == "x":
                    self.report(node, "rename x", replacement=Name("y"))

        runner = capture(
            rattle_bytes(
                Path("rename.py"),
                b"x = x\nz = x\n",
                config=Config(path=Path("rename.py")),
                autofix=True,
                include_diff=True,
                rules=[RenameXRule()],
            )
        )

        results = list(runner)

        assert runner.result == b"y = y\nz = y\n"
        diffs = [result.violation.diff for result in results if result.violation]
        assert len(diffs) == 3
        assert diffs[0].count("-x = x") == 1
        assert diffs[0].count("+y = y") == 1
        assert diffs[0].count("-z = x") == 1
        assert diffs[0].count("+z = y") == 1
        assert diffs[1:] == ["", ""]

    def test_rattle_bytes_handles_syntax_error_null_bytes(self) -> None:
        class DummyRule(LintRule):
            pass

        path = Path("binary.py")
        results = list(
            rattle_bytes(
                path,
                b"\x00\x00\x00\x00",
                config=Config(path=path),
                rules=[DummyRule()],
            )
        )
        assert results[0].error is not None
        assert "SyntaxError" in str(results[0].error[0])
