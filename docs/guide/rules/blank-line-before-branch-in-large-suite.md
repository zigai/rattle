---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-blank-line-before-branch-in-large-suite)=

# BlankLineBeforeBranchInLargeSuite

Require branch statements to be visually separated in large suites.

<p class="rule-metadata">
  <span>Pack: <code>blank_lines</code></span>
  <span>Module: <code>rattle.rules.blank_lines.blank_line_before_branch_in_large_suite</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

## Message

Missing blank line before return/raise/break/continue in a large suite.

## Settings

| Setting | Type | Default |
| --- | --- | --- |
| `allow_guard_ladder_final_branch` | `bool` | `True` |
| `allow_related_return_tails` | `bool` | `True` |
| `compact_tail_max_statements` | `int` | `2` |
| `max_suite_non_empty_lines` | `int` | `2` |

## Valid examples

```python
def f(value: int) -> int:
    x = value + 1
    y = x + 1

    return y
```
```python
def f(value: int) -> int:
    x = value + 1
    return x
```

## Invalid examples

```python
def f(value: int) -> int:
    x = value + 1
    y = x + 1
    z = y + 1
    return z

# suggested fix
def f(value: int) -> int:
    x = value + 1
    y = x + 1
    z = y + 1

    return z
```
```python
def f(values: list[int]) -> int:
    total = 0
    message = str(total)
    flag = bool(message)
    raise RuntimeError("boom")

# suggested fix
def f(values: list[int]) -> int:
    total = 0
    message = str(total)
    flag = bool(message)

    raise RuntimeError("boom")
```
