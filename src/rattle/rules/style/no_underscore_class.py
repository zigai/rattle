from __future__ import annotations

import libcst as cst

from rattle import Invalid, LintRule, Valid


class NoUnderscoreClass(LintRule):
    """Forbid underscore-prefixed class names."""

    MESSAGE = "Class names must not start with an underscore prefix."
    SOURCE_PATTERNS = (b"class _",)

    VALID = [
        Valid("class MyClass: ..."),
    ]

    INVALID = [
        Invalid("class _Internal: ..."),
        Invalid("class __Private: ..."),
        Invalid("class _MyClass: ..."),
        Invalid("class _ASTVisitor: ..."),
    ]

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        if not node.name.value.startswith("_"):
            return

        self.report(node, self.MESSAGE)
