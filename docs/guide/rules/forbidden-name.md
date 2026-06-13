---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-forbidden-name)=

# forbidden-name

<p class="rule-metadata">
  <span>Collection: <code>policy</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Ban configured names by identifier kind and pattern.

## Message

Do not use forbidden {kind} name '{name}'.


## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">forbidden_names</span></td>
      <td>—</td>
      <td><span class="rule-setting-type">list</span></td>
      <td><span class="rule-setting-default rule-setting-default-plain">[]</span></td>
    </tr>
</tbody>
</table>
```

## Valid examples

```python
import foo.bar
```
```python
import foo.bar as fb
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
from foo import bar as baz
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import foo.bar as baz
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
match value:
    case {"x": bad}:
        pass
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
match value:
    case [*bad]:
        pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
match value:
    case {"x": value, **bad}:
        pass
```
```{raw} html
</div>
```
```{raw} html
</details>
```
