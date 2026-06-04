---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-blank-line-after-control-block)=

# BlankLineAfterControlBlock

Require separation after multiline control-flow block statements.

<p class="rule-metadata">
  <span>Pack: <code>blank_lines</code></span>
  <span>Module: <code>rattle.rules.blank_lines.blank_line_after_control_block</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

## Message

Missing blank line after multiline control-flow block statement.

## Settings

| Setting | Type | Default |
| --- | --- | --- |
| `allow_compact_guard_ladders` | `bool` | `True` |
| `allow_pytest_raises_clusters` | `bool` | `True` |
| `allow_with_immediate_inspection` | `bool` | `True` |
| `related_use_lookahead` | `int` | `2` |

## Valid examples

```python
def f(value: int) -> int:
    if value > 0:
        value += 1

    return value
```
```python
def f(value: int) -> int:
    if value > 0:
        value += 1
    # comment separator
    return value
```

## Invalid examples

```python
def f(value: int) -> int:
    if value > 0:
        value += 1
    return value

# suggested fix
def f(value: int) -> int:
    if value > 0:
        value += 1

    return value
```
```python
def f(values: list[int]) -> int:
    total = 0
    for value in values:
        total += value
    return total

# suggested fix
def f(values: list[int]) -> int:
    total = 0
    for value in values:
        total += value

    return total
```
