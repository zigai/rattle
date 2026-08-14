---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-match-case-separation)=

# match-case-separation

<p class="rule-metadata">
  <span>Collection: <code>blank-lines</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Require spacing before the next case after large case bodies.

## Message

Missing separator between match cases after a large case body.


## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">max_case_non_empty_lines</span></td>
      <td>Maximum number of non-empty lines allowed in a case body before the next case requires a preceding blank line.</td>
      <td><span class="rule-setting-type">int</span></td>
      <td><span class="rule-setting-default rule-setting-default-number">2</span></td>
    </tr>
</tbody>
</table>
```

## Valid examples

```python
def f(value: int) -> int:
    match value:
        case 1:
            return 1
        case _:
            return 0
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
def f(value: int) -> int:
    match value:
        case 1:
            a = 1
            b = 2
            c = 3

        case _:
            return 0
```
<p class="rule-example-label">Options</p>

```toml
max_case_non_empty_lines = 3
```
```python
def f(value: int) -> int:
    match value:
        case 1:
            a = 1
            b = 2
            c = 3
        case _:
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
    match value:
        case 1:
            a = 1
            b = 2
            c = 3
        case _:
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
    match value:
        case 1:
            first = 1
            second = 2
            third = 3
        case 2:
            return 2
        case _:
            return 0
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
<p class="rule-example-label">Options</p>

```toml
max_case_non_empty_lines = 1
```
```python
def f(value: int) -> int:
    match value:
        case 1:
            a = 1
            b = 2
        case _:
            return 0
```
```{raw} html
</div>
```
```{raw} html
</details>
```
