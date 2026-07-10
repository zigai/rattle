---
name: create-rattle-lint-rules
description: Author and configure custom Rattle lint rules and autofixes. Use when adding Rattle to a Python project or creating, testing, or refining in-repo Rattle rules.
---

# Author Custom Rattle Rules

Rattle is a LibCST-based linter and autofixer. Use Rattle commands, selectors,
configuration, and terminology rather than Fixit equivalents.

Do not invent a rule unless the user explicitly asks for suggestions. Work
spec-first: settle what must and must not report before implementing it.

## 1. Lock the rule contract

Inspect repository instructions, existing Rattle configuration, local rule
layout, task runners, CI, and the dirty tree. Preserve unrelated work.

Require an explicit contract covering:

- intent and rationale;
- repository and path scope, including exceptions;
- exact syntax and semantic conditions that report;
- aliases, import shapes, rebinding, and other equivalent forms;
- two to five valid and invalid examples; and
- whether an autofix is requested and mechanically safe.

If essential contract details are missing, obtain them before writing the rule.
Express path-only policy in Rattle configuration rather than hard-coding paths
inside a visitor.

Complete this step when every intended report and exemption is represented by
an example and the autofix decision is explicit.

## 2. Choose the analysis seam

Choose the smallest LibCST node that uniquely represents the violation. Prefer
structural matching over source text. Use visitor state only when syntax context
requires it.

When names can be imported, aliased, shadowed, or rebound, use LibCST metadata
such as `ScopeProvider` and `QualifiedNameProvider`; do not infer identity from
spelling alone. Account for the binding that reaches each access.

If the rule needs Python's compiler-normalized representation, read
[`references/ast-analysis.md`](references/ast-analysis.md) before implementing
it. Use `AstProvider` only for semantics the CST model does not provide, not as
a substitute for learning LibCST.

Complete this step when the report node, required metadata, state, and any
AST-to-CST mapping are identified for every contract example.

## 3. Implement diagnostics and tests together

Subclass `rattle.LintRule` and keep executable examples on the rule:

```python
import libcst as cst

from rattle import Invalid, LintRule, RuleSetting, Valid


class MyRule(LintRule):
    MESSAGE = "Describe the required change."
    NAME = "my-rule"
    PYTHON_VERSION = ">=3.10"
    SETTINGS = {
        "limit": RuleSetting(int, default=10, description="Maximum allowed value."),
    }

    VALID = [Valid("allowed()")]
    INVALID = [
        Invalid(
            "forbidden()",
            expected_message=MESSAGE,
        ),
    ]

    def visit_Call(self, node: cst.Call) -> None:
        if matches_contract(node):
            self.report(node, self.MESSAGE)
```

Use these class attributes when the contract needs them:

- `NAME` for an explicit kebab-case public name;
- `TAGS` for configuration filtering;
- `PYTHON_VERSION` for a PEP 440 compatibility range;
- `SETTINGS` with typed `RuleSetting` values and validators;
- `REFERENCES` for relevant external documentation; and
- `VALID` / `INVALID` for inline behavior tests, including option variants.

Anchor `self.report(...)` to the smallest CST node that should own the
diagnostic and local ignore comment.

Add an autofix only when the replacement is local, syntactically valid in
place, and mechanically safe. Avoid fixes that require semantic guesses, alter
control flow or exception behavior, or coordinate multiple files. Do not add or
remove imports unless the user explicitly accepts that risk. A safe fix must
include `replacement=...` and an `Invalid(..., expected_replacement=...)` case;
Rattle derives autofix capability from those cases. Otherwise keep the rule
diagnostic-only and record the reason.

Complete this step when every contract example is an executable `VALID` or
`INVALID` case and every replacement converges without another report.

## 4. Configure discovery and scope

When adding Rattle, changing selectors, defining rule options, or applying path
scope, read [`references/configuration.md`](references/configuration.md) before
editing configuration.

Enable local rules with import selectors and use canonical kebab-case names in
configuration and CLI commands. Target options at one concrete rule, never a
package or module selector.

Complete this step when `rattle rules <path>` resolves the intended rule,
settings, and path scope without enabling unrelated rules.

## 5. Prove the rule

Use the repository's command runner and configuration context. At minimum run:

```bash
rattle validate pyproject.toml
rattle rules --test --config pyproject.toml .
rattle lint --diff .
```

Run focused project tests for affected code. Apply `rattle fix` across the
repository only when the user requests it.

If the rule is noisy, add valid cases before changing the implementation. Test
aliases, alternate imports, rebinding, nested scopes, syntax-version boundaries,
comments, and formatting variants whenever they can change the result. Narrow
the structural match rather than weakening the diagnostic. Prefer configuration
for path exceptions; suggest inline `rattle: ignore[...]` only when matching and
configuration cannot express a legitimate exception.

Complete this step when configuration validates, every inline case passes, the
lint output matches the contract, safe fixes converge, and affected project
tests pass.

## Deliverables

Provide:

1. the rule module and package wiring;
2. configuration changes for discovery, settings, and scope;
3. executable valid, invalid, and replacement cases;
4. the autofix or the diagnostic-only safety reason; and
5. the exact validation commands and outcomes.
