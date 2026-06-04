---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-block-header-cuddle-relaxed)=

# BlockHeaderCuddleRelaxed

Allow cuddling when the setup remains part of the same control-flow step.

<p class="rule-metadata">
  <span>Pack: <code>blank_lines</code></span>
  <span>Module: <code>rattle.rules.blank_lines.block_header_cuddle_relaxed</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

## Message

Illegal cuddle before block header. The preceding setup must directly feed the upcoming block.

## Settings

| Setting | Type | Default |
| --- | --- | --- |
| `allow_setup_before_compact_guard_ladder` | `bool` | `True` |
| `body_usage_lookahead` | `int` | `4` |
| `setup_run_lookback` | `int` | `3` |

## Valid examples

```python
def f(value: int) -> int:
    prepared = value + 1
    if prepared > 0:
        return prepared

    return 0
```
```python
def f(value: int) -> int:
    prepared = value + 1
    if value > 0:
        result = prepared
        return result

    return 0
```

## Invalid examples

```python
def f(value: int) -> int:
    prepared = value + 1
    if value > 0:
        return value

    return 0

# suggested fix
def f(value: int) -> int:
    prepared = value + 1

    if value > 0:
        return value

    return 0
```
```python
def f(value: int) -> int:
    prepared = value + 1
    log(prepared)
    if prepared > 0:
        return prepared

    return 0

# suggested fix
def f(value: int) -> int:
    prepared = value + 1
    log(prepared)

    if prepared > 0:
        return prepared

    return 0
```
