# Optional AST Analysis

Read this reference only when a rule requires Python's compiler-normalized AST.
LibCST remains the authority for traversal, diagnostics, ignore comments, and
autofixes.

## Decision boundary

Use `AstProvider` when the contract depends on semantics exposed by `ast`, such
as compiler-normalized constants or operators. Do not use it merely to avoid
modeling the corresponding LibCST nodes. Request the provider instead of calling
`ast.parse` directly so rules share Rattle's cached context and parse-error
handling.

AST parsing is opt-in and uses the interpreter running Rattle. It also parses
legacy `# type:` comments. Parsing can therefore fail when source syntax is
newer than the host interpreter or when a type comment is misplaced; Rattle
surfaces this as `AstParseError`.

## Analysis pattern

Request `AstProvider` and `PositionProvider`, collect AST ranges from the CST
module, then report on corresponding CST nodes:

```python
import ast

import libcst as cst
from libcst.metadata import PositionProvider

from rattle import AstContext, AstProvider, CodeRange, LintRule


class LargeIntegerRule(LintRule):
    METADATA_DEPENDENCIES = (AstProvider, PositionProvider)

    def __init__(self) -> None:
        super().__init__()
        self.large_integer_ranges: set[CodeRange] = set()

    def visit_Module(self, node: cst.Module) -> None:
        context = self.get_metadata(AstProvider, node, None)
        assert isinstance(context, AstContext)
        self.large_integer_ranges = {
            context.code_range(ast_node)
            for ast_node in ast.walk(context.tree)
            if isinstance(ast_node, ast.Constant)
            and isinstance(ast_node.value, int)
            and ast_node.value > 1_000
        }

    def visit_Integer(self, node: cst.Integer) -> None:
        code_range = self.get_metadata(PositionProvider, node)
        if code_range in self.large_integer_ranges:
            self.report(node, "Avoid large integer literals")
```

`AstContext.code_range(ast_node)` converts CPython AST byte offsets into
Rattle's character-based ranges, including non-ASCII source. Rattle does not
automatically map AST nodes back to CST nodes.

Keep `self.report(...)` anchored to CST so `# rattle: ignore[...]` and CST
replacements retain their behavior. AST replacements are unsupported; every
autofix must replace LibCST nodes.

Before completing an AST-backed rule, test non-ASCII positions, a parse failure,
the supported host/target syntax boundary, and local ignore behavior where they
apply to the contract.
