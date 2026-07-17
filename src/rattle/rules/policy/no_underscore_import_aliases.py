from __future__ import annotations

import libcst as cst

from rattle import Invalid, LintRule, Valid


class NoUnderscoreImportAliases(LintRule):
    """Forbid underscore-prefixed aliases in import statements."""

    MESSAGE = "Import aliases must not start with an underscore."

    VALID = [
        Valid("import json"),
        Valid("import json as json_lib"),
        Valid("from collections import deque as deque_type"),
        Valid("from module import _private_name"),
    ]

    INVALID = [
        Invalid("import json as _json"),
        Invalid("import json as  _json"),
        Invalid("import json as\t_json"),
        Invalid(
            """
            import json as\\
                _json
            """
        ),
        Invalid("from collections import deque as _deque"),
        Invalid("from module import name as __name"),
    ]

    def visit_ImportAlias(self, node: cst.ImportAlias) -> None:
        if node.asname is None:
            return
        if not isinstance(node.asname.name, cst.Name):
            return
        if not node.asname.name.value.startswith("_"):
            return

        self.report(node.asname.name, self.MESSAGE)
