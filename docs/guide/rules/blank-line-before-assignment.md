---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-blank-line-before-assignment)=

# BlankLineBeforeAssignment

Require separators before assignments that do not continue the local flow.

<p class="rule-metadata">
  <span>Pack: <code>blank_lines</code></span>
  <span>Module: <code>rattle.rules.blank_lines.blank_line_before_assignment</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

## Message

Missing blank line before assignment statement that follows a non-assignment statement.

## Settings

| Setting | Type | Default |
| --- | --- | --- |
| `allow_local_helper_capture` | `bool` | `True` |
| `allow_post_guard_continuation` | `bool` | `False` |
| `related_use_lookahead` | `int` | `2` |
| `short_control_flow_max_statements` | `int` | `3` |

## Valid examples

```python
def f() -> int:
    value = 1
    other = value + 1
    return other
```
```python
def f() -> int:
    log_start()

    value = compute()
    log_value(value)
    return value
```

## Invalid examples

```python
def f(values: list[int]) -> int:
    total = 0
    if values:
        total += len(values)
    total += 1
    return total

# suggested fix
def f(values: list[int]) -> int:
    total = 0
    if values:
        total += len(values)

    total += 1
    return total
```
```python
def f(flag: bool, value: str) -> str:
    if not flag:
        return value
    normalized = value.strip()
    return normalized

# suggested fix
def f(flag: bool, value: str) -> str:
    if not flag:
        return value

    normalized = value.strip()
    return normalized
```
