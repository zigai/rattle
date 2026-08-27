---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-widen-then-cast)=

# no-widen-then-cast

<p class="rule-metadata">
  <span>Collection: <code>typing</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Disallow discarding local type evidence and recovering it with a later cast.

## Message

This value was widened and then cast back to a narrower type. Preserve its original type evidence.


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
from typing import cast

value: object = source
value = replacement
result = cast(str, value)
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
from typing import cast

def convert(value: object) -> str:
    return cast(str, value)
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
from typing import cast

precise: str = "value"
widened: object = precise
result = cast(str, widened)
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
from collections.abc import Mapping
from typing import Any, cast

precise: dict[str, int] = {"answer": 42}
widened: Mapping[str, Any] = precise
result = cast(dict[str, int], widened)
```
```{raw} html
</div>
```
```{raw} html
</details>
```
