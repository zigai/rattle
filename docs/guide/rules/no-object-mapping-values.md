---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-object-mapping-values)=

# no-object-mapping-values

<p class="rule-metadata">
  <span>Collection: <code>typing</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Disallow broad ``object`` value types in standard mapping annotations.

## Message

Replace this broad `object` mapping value with a concrete value type or parsed owner type.


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
values: dict[object, str]
items: list[object]
```
```python
class object:
    pass

values: dict[str, object]
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
values: dict[str, object]
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from collections.abc import Mapping
from typing import Annotated

values: Mapping[str, Annotated[object, "decoded later"]]
```
```{raw} html
</div>
```
