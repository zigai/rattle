---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-block-header-cuddle-strict)=

# block-header-cuddle-strict

<p class="rule-metadata">
  <span>Collection: <code>blank-lines</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Allow only the immediately preceding assignment to remain next to a block.

## Message

Add a blank line before this block; only an immediately preceding assignment used by the block may remain attached.


## Valid examples

```python
def f(value: int) -> int:
    prepared = value + 1
    if prepared > 0:
        return prepared

    return 0
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
def f(value: int) -> int:
    prepared = value + 1

    if value > 0:
        return value

    return 0
```
```python
def f(value: int) -> int:
    """Compute value."""
    if value > 0:
        return value

    return 0
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
def f(value: int) -> int:
    header_value = value + 1
    trailing = value + 2
    if header_value > 0:
        return header_value

    return 0
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(value: int) -> int:
    header_value = value + 1
    trailing = value + 2

    if header_value > 0:
        return header_value

    return 0
```
```{raw} html
</div>
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
def f(value: int) -> int:
    prepared = value + 1
    if value > 0:
        result = prepared
        return result

    return 0
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(value: int) -> int:
    prepared = value + 1

    if value > 0:
        result = prepared
        return result

    return 0
```
```{raw} html
</div>
```
```{raw} html
</details>
```
