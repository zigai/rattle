---
name: create-rattle-lint-rules
description: Use when adding Rattle to a Python project or creating/refining custom in-repo Rattle lint rules and autofixes.
---

# Create Custom Rattle Lint Rules

Use this skill when a repository uses Rattle, or when the user wants to add Rattle and create custom in-repo rules.

Rattle is a LibCST-based linter and autofixer. It is a fork of Fixit, but its commands, selectors, config tables, and rule APIs are Rattle-specific. Use Rattle terminology throughout.

## Before Writing Code

Do not invent lint rules unless the user explicitly asks for suggestions.

Before implementing a rule, make sure the user has provided an explicit rule spec. If not, collect:

1. Intent

- What syntax or pattern is forbidden or required?
- Why: readability, correctness, architecture, performance, security?

2. Scope

- Entire repo, one package, tests excluded, only selected paths?
- Any explicit exceptions?

3. Match criteria

- What exact syntax should report?
- Are there aliases, multiple call shapes, or import styles?

4. Autofix

- Determine whether a safe autofix is possible for the requested rule.
- If the rewrite is local, syntactically valid, and mechanically safe, implement the autofix logic.
- If no safe autofix is possible, implement a diagnostic-only rule and explain that decision in the response.

5. Examples

- 2-5 valid examples that must not report
- 2-5 invalid examples that must report
- If autofix is enabled, expected replacement code for invalid examples

If requested scope is path-based, prefer Rattle config in `pyproject.toml` over hard-coded path checks inside the rule.

## Quick Basics

Install:

```bash
pip install "rattle-lint>=2.1.0"
```

Common commands:

```bash
rattle lint <path>
rattle lint --compact <path>
rattle lint --diff <path>
rattle fix <path>
rattle fix --diff <path>
rattle fix --interactive <path>
rattle rules
rattle rules --test --config pyproject.toml <path>
rattle validate pyproject.toml
```

`rattle fix` applies available fixes automatically by default. Use `--interactive` to prompt for each fix.

Silencing comments:

- `# rattle: ignore[rule-name]`
- `# rattle: ignore`

If the rule name is omitted, the directive silences all rules attached to that statement. Multiple kebab-case names may be comma-separated.

## Local Rule Layout

Recommended layout:

```text
repo/
  pyproject.toml
  rules/
    __init__.py
    <rule_module>.py
```

Enable local rules with selectors relative to the config file:

- `.rules`
- `.rules.my_module`
- `.rules:my-rule`

Without `enable-root-import`, local rules should use relative imports that stay inside the tree rooted at the config file.

If local rules need absolute imports from the repo, configure `enable-root-import` in the root config. It may be `true` or a single path relative to the root config:

```toml
[tool.rattle]
root = true
enable-root-import = "src"
enable = ["myproject.rules"]
```

## Configuration

Minimal config:

```toml
[tool.rattle]
root = true

# Rattle enables no rules by default. Enable explicit collections or local rules.
enable = [
  "blank-lines",
  ".rules",
]

disable = [
  # "use-f-string",
  # ".rules:my-rule",
]

python-version = "3.11"
```

Per-rule options must target one concrete rule class. Prefer table form, and quote keys that contain `:` or start with `.`:

```toml
[tool.rattle.options.".rules:my-rule"]
max_length = 42
```

Inline mappings are also valid:

```toml
[tool.rattle.options]
".rules:my-rule" = { max_length = 42 }
```

Path-based scoping can use overrides or per-file tables:

```toml
[[tool.rattle.overrides]]
path = "tests"
enable = [".rules:tests-only-rule"]
options = { ".rules:tests-only-rule" = { max_length = 80 } }

[tool.rattle.per-file-disable]
"tests/generated.py" = [".rules:my-rule"]

[tool.rattle.per-file-enable]
"scripts/**/*.py" = [".rules:scripts-only-rule"]
```

`per-file-disable` is the final suppression layer after base config and matching overrides.

## Rule Authoring

Implement rules as subclasses of `rattle.LintRule` and import test helpers from `rattle`:

```python
import libcst as cst
from rattle import Invalid, LintRule, RuleSetting, Valid
```

Important class attributes:

- `MESSAGE`: conventional default message to pass to `self.report(...)`
- `NAME`: optional explicit kebab-case public rule name; defaults to kebab-case generated from the class name
- `TAGS`: optional tags for configuration filtering
- `PYTHON_VERSION`: optional PEP 440 version specifier
- `SETTINGS`: optional typed config settings using `RuleSetting`
- `REFERENCES`: optional documentation references as URLs or `(label, URL)` pairs
- `VALID` / `INVALID`: inline rule tests

Selector guidance:

- Rule selectors and displayed rule names are canonical kebab-case only.
- Do not use PascalCase class names as selectors.
- For local and third-party rules, use import selectors such as `.rules.my_module` or concrete selectors such as `.rules:my-rule`.
- If the generated class-name conversion is not the desired public name, set `NAME = "my-rule"`.
- Options must target one concrete rule, not a package or module selector.

Settings guidance:

- Use `RuleSetting(type, default=..., description="...")` for configurable behavior.
- Supported setting value types are TOML scalar types and `list[...]` of scalar types.
- If a setting has no default, config must provide it.
- `RuleSetting(..., validator=...)` can enforce extra constraints.
- Use `Valid(..., options={...})` and `Invalid(..., options={...})` to test alternate settings.

## Implementation Workflow

### 1. Map the rule spec to LibCST nodes

Pick the smallest CST node that uniquely represents the violation. Prefer structural matching over string matching.

Use visitor state only when needed, for example:

- tracking whether you are inside an annotation
- tracking imports or aliases
- distinguishing syntactic context such as decorators, type annotations, or class bodies

### 2. Implement the rule

Skeleton:

```python
import libcst as cst
from rattle import Invalid, LintRule, RuleSetting, Valid


class MyRule(LintRule):
    MESSAGE = "..."
    NAME = "my-rule"
    TAGS = {"style"}
    PYTHON_VERSION = ">=3.10"
    SETTINGS = {
        "limit": RuleSetting(int, default=10, description="Maximum allowed value."),
    }

    VALID = [
        Valid("..."),
    ]
    INVALID = [
        Invalid(
            "...",
            expected_replacement="...",
            expected_message="...",
        ),
    ]

    def visit_<NodeType>(self, node: cst.<NodeType>) -> None:
        ...
        self.report(node, self.MESSAGE, replacement=<cst node>)
```

Use `self.report(node, message, replacement=...)` to report a violation and optionally attach an autofix.

Rattle sets a rule's autofix capability automatically when any `INVALID` case includes `expected_replacement`.

For every custom rule, evaluate autofix safety as part of implementation. When safe, add `replacement=...` logic and include `Invalid(..., expected_replacement=...)` tests. When unsafe or ambiguous, omit `replacement` and state why the rule is diagnostic-only.

### 3. Wire the rule into config

Enable the rule with an import selector:

```toml
[tool.rattle]
enable = [
  ".rules.my_rule",
]
```

Use kebab-case selectors in config and CLI. If the generated class-name selector is not what the user wants, set `NAME` on the rule class.

### 4. Validate config and tests

Use this sequence:

```bash
rattle validate pyproject.toml
rattle rules --test --config pyproject.toml .
rattle lint --diff .
```

If the user wants autofixes applied across the repo:

```bash
rattle fix .
```

Use `rattle rules <path>` when config inheritance, enabled rules, disabled rules, or resolved settings are unclear.

### 5. Tighten false positives

When a rule is noisy:

- add more `VALID` cases first
- narrow the CST match rather than weakening the message
- use config scoping for path-based exceptions
- only add inline `rattle: ignore[...]` guidance when config and matching are not enough

## Autofix Safety

Evaluate whether each requested rule can have a safe autofix. Provide an autofix when the rewrite is local, syntactically valid in place, and mechanically safe.

Avoid autofixes when:

- the change needs semantic analysis beyond the matched node
- imports must be added or removed, unless the user explicitly accepts that risk
- the rewrite changes control flow or exception behavior
- multiple files must change together

If there is ambiguity, report without a replacement and mention the reason in the final response.

## Deliverables

When implementing a Rattle custom rule, produce:

1. `rules/<module>.py` with one or more `LintRule` subclasses
2. `rules/__init__.py` if needed
3. `pyproject.toml` updates under `[tool.rattle]`, `[tool.rattle.options]`, per-file tables, or overrides as needed
4. Autofix outcome: implemented with `expected_replacement` tests, or diagnostic-only with a reason
5. The commands used to validate: `rattle validate`, `rattle rules --test`, `rattle lint --diff`, and optionally `rattle fix`

## Example Rule

Example only. Do not apply it unless the user asks for this behavior.

```python
import libcst as cst
from rattle import Invalid, LintRule, Valid


class UseBuiltinGenerics(LintRule):
    MESSAGE = "Use built-in generic types instead of typing.List/Dict/Set/Tuple."
    PYTHON_VERSION = ">=3.9"

    VALID = [
        Valid("def f(x: list[int]) -> dict[str, int]: ..."),
    ]

    INVALID = [
        Invalid(
            "import typing\n\ndef f(x: typing.List[int]): ...",
            expected_replacement="import typing\n\ndef f(x: list[int]): ...",
        ),
        Invalid(
            "from typing import Dict\n\ndef f() -> Dict[str, int]: ...",
            expected_replacement="from typing import Dict\n\ndef f() -> dict[str, int]: ...",
        ),
    ]

    _IN_ANNOTATION = 0
    _MAP = {"List": "list", "Dict": "dict", "Set": "set", "Tuple": "tuple"}

    def visit_Annotation(self, node: cst.Annotation) -> None:
        self._IN_ANNOTATION += 1

    def leave_Annotation(self, original_node: cst.Annotation) -> None:
        self._IN_ANNOTATION -= 1

    def visit_Attribute(self, node: cst.Attribute) -> None:
        if not self._IN_ANNOTATION:
            return
        if isinstance(node.value, cst.Name) and node.value.value == "typing":
            replacement = self._MAP.get(node.attr.value)
            if replacement:
                self.report(node, self.MESSAGE, replacement=cst.Name(replacement))

    def visit_Name(self, node: cst.Name) -> None:
        if not self._IN_ANNOTATION:
            return
        replacement = self._MAP.get(node.value)
        if replacement:
            self.report(node, self.MESSAGE, replacement=cst.Name(replacement))
```

Enable it:

```toml
[tool.rattle]
enable = [".rules.typing_generics"]
```
