# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import libcst as cst
import libcst.matchers as m
from libcst.metadata import ParentNodeProvider

from rattle import CodePosition, CodeRange, Invalid, LintRule, Valid


class NoRedundantFString(LintRule):
    """Remove f-string prefixes from strings without placeholders."""

    SOURCE_PATTERNS = (
        "f'",
        'f"',
        "F'",
        'F"',
        "fr'",
        'fr"',
        "fR'",
        'fR"',
        "Fr'",
        'Fr"',
        "FR'",
        'FR"',
    )

    MESSAGE: str = "Remove the `f` prefix; this f-string has no replacement fields."
    METADATA_DEPENDENCIES = (ParentNodeProvider,)

    VALID = [
        Valid('good: str = "good"'),
        Valid('good: str = f"with_arg{arg}"'),
        Valid('good = "good{arg1}".format(1234)'),
        Valid('good = "good".format()'),
        Valid('good = "good" % {}'),
        Valid('good = "good" % ()'),
        Valid('good = rf"good\t+{bar}"'),
    ]

    INVALID = [
        Invalid(
            'bad: str = f"bad" + "bad"',
            expected_replacement='bad: str = "bad" + "bad"',
            range=CodeRange(start=CodePosition(1, 11), end=CodePosition(1, 17)),
        ),
        Invalid(
            "bad: str = f'bad'",
            expected_replacement="bad: str = 'bad'",
            range=CodeRange(start=CodePosition(1, 11), end=CodePosition(1, 17)),
        ),
        Invalid(
            "bad: str = rf'bad\t+'",
            expected_replacement="bad: str = r'bad\t+'",
            range=CodeRange(start=CodePosition(1, 11), end=CodePosition(1, 20)),
        ),
        Invalid(
            "bad: str = fr'bad\t+'",
            expected_replacement="bad: str = r'bad\t+'",
            range=CodeRange(start=CodePosition(1, 11), end=CodePosition(1, 20)),
        ),
        Invalid(
            'bad: str = f"no args but messing up {{ braces }}"',
            expected_replacement='bad: str = "no args but messing up { braces }"',
            range=CodeRange(start=CodePosition(1, 11), end=CodePosition(1, 49)),
        ),
    ]

    def visit_FormattedString(self, node: cst.FormattedString) -> None:
        if any(isinstance(part, cst.FormattedStringExpression) for part in node.parts):
            return
        if self._would_become_docstring(node):
            return

        old_string_inner = "".join(
            cst.ensure_type(part, cst.FormattedStringText).value for part in node.parts
        )
        if "{{" in old_string_inner or "}}" in old_string_inner:
            old_string_inner = old_string_inner.replace("{{", "{").replace("}}", "}")

        new_string_literal = (
            node.start.replace("f", "").replace("F", "") + old_string_inner + node.end
        )

        self.report(node, self.MESSAGE, replacement=cst.SimpleString(new_string_literal))

    def _would_become_docstring(self, node: cst.FormattedString) -> bool:
        literal: cst.CSTNode = node
        while isinstance(
            parent := self.get_metadata(ParentNodeProvider, literal, None),
            cst.ConcatenatedString,
        ):
            literal = parent
        result = False
        if not m.findall(literal, m.FormattedStringExpression()):
            expression = self.get_metadata(ParentNodeProvider, literal, None)
            if isinstance(expression, cst.Expr):
                statement = self.get_metadata(ParentNodeProvider, expression, None)
                if (
                    isinstance(statement, (cst.SimpleStatementLine, cst.SimpleStatementSuite))
                    and statement.body
                    and statement.body[0] is expression
                ):
                    suite = self.get_metadata(ParentNodeProvider, statement, None)
                    if isinstance(suite, (cst.Module, cst.IndentedBlock)):
                        result = bool(suite.body) and suite.body[0] is statement
                    elif isinstance(statement, cst.SimpleStatementSuite):
                        result = isinstance(suite, (cst.ClassDef, cst.FunctionDef))
        return result


__all__ = [
    "NoRedundantFString",
]
