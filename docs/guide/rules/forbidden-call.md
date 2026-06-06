---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-forbidden-call)=

# forbidden-call

<p class="rule-metadata">
  <span>Collection: <code>policy</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
<span>Tags: `architecture`</span></p>

Ban calls to configured functions, constructors, and helper APIs.

## Message

Do not call forbidden callable '{symbol}'.


## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">forbidden_calls</span></td>
      <td>—</td>
      <td><span class="rule-setting-type">list</span></td>
      <td><span class="rule-setting-default rule-setting-default-plain">[]</span></td>
    </tr>
</tbody>
</table>
```

## Valid examples

```python
typing.cast(str, value)
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
from typing import cast

def cast(value: object) -> object:
    return value

result = cast(value)
```
```python
import typing

value = typing.NamedTuple("Row", [("id", int)])
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
import typing

value = typing.cast(str, value)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import typing as t

value = t.cast(str, value)
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
from typing import cast as type_cast

value = type_cast(str, value)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from typing_extensions import cast

value = cast(str, value)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import legacy_math

value = legacy_math.sqrt(4)
```
```{raw} html
</div>
```
```{raw} html
</details>
```
