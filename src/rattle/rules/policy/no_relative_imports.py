from __future__ import annotations

import libcst as cst

from rattle import Invalid, LintRule, Valid


class NoRelativeImports(LintRule):
    """Require absolute imports instead of package-relative imports."""

    MESSAGE = "Use absolute imports instead of relative imports."
    SOURCE_PATTERNS = (b"from ",)

    VALID = [
        Valid("from package.subpackage.types import ItemType"),
        Valid("import package.subpackage.types"),
    ]

    INVALID = [
        Invalid("from .types import ItemType"),
        Invalid("from\t.types import ItemType"),
        Invalid("from ..utilities import create_page"),
        Invalid("from . import helpers"),
    ]

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if not node.relative:
            return

        self.report(node, self.MESSAGE)
