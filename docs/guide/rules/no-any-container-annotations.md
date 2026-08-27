---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-any-container-annotations)=

# no-any-container-annotations

<p class="rule-metadata">
  <span>Collection: <code>typing</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Disallow ``Any`` in the semantic type arguments of standard containers.

## Message

Replace `Any` in this container annotation with concrete element, key, or value types.


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

class Envelope:
    pass

payload: Envelope[Any]
rows: list[dict[str, int]]
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
class Any:
    pass

values: list[Any]
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

values: list[Any]
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import typing as t

rows: t.Mapping[str, t.Sequence[t.Any]]
```
```{raw} html
</div>
```
