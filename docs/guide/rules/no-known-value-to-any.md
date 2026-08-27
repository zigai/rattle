---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-known-value-to-any)=

# no-known-value-to-any

<p class="rule-metadata">
  <span>Collection: <code>typing</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Disallow direct ``Any`` annotations that erase syntactically known evidence.

## Message

This explicit `Any` annotation discards known type evidence. Keep inference or use a concrete owner contract.


## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">excluded_path_parts</span></td>
      <td>Skip files whose path contains any of these components, in addition to files named test_*.py.</td>
      <td><span class="rule-setting-type">list</span></td>
      <td><span class="rule-setting-default rule-setting-default-plain">[&#x27;tests&#x27;]</span></td>
    </tr>
</tbody>
</table>
```

## Valid examples

```python
from typing import Any

pending: Any
placeholder: Any = None
supplied: Any = value
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
from typing import Any

values: list[Any] = []
```
```python
class Any:
    pass

value: Any = make_value()
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
from typing import Any

payload: Any = {"ready": True}
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
from typing import Any

created = build_payload()
self.payload: Any = created
```
```{raw} html
</div>
```
```{raw} html
</details>
```
