---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-bare-object-annotations)=

# no-bare-object-annotations

<p class="rule-metadata">
  <span>Collection: <code>typing</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Require annotations to use a more precise boundary type than bare object.

## Message

Use a narrower type than bare object in annotations.


## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">excluded_path_parts</span></td>
      <td>Path parts that should be excluded in addition to test_*.py files.</td>
      <td><span class="rule-setting-type">list</span></td>
      <td><span class="rule-setting-default rule-setting-default-plain">[&#x27;tests&#x27;]</span></td>
    </tr>
</tbody>
</table>
```

## Valid examples

```python
def fn(payload: dict[str, object]) -> None:
    return None
```
```python
def fn(settings_type: type[object]) -> None:
    return None
```
```python
sentinel = object()
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
from typing import Protocol

class SettingsProvider(Protocol):
    pass

def fn(value: object | SettingsProvider | None) -> None:
    return None
```
```python
class object:
    pass

def fn(value: object) -> None:
    return None
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
def fn(value: object) -> None:
    return None
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
def fn() -> object:
    return None
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
value: object = payload
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
value: object | None = None
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
value: None | object = None
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from typing import Optional

value: Optional[object] = None
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from typing import Union

value: Union[object, None] = None
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
value: "object" = payload
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
value: "object" "" = payload
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import builtins

value: builtins.object = payload
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import builtins as builtin_types

value: builtin_types.object = payload
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import builtins
from typing import Optional

value: Optional[builtins.object] = None
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from typing import Annotated

value: Annotated[object, "metadata"] = payload
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from typing import TypeAlias

Object: TypeAlias = object
value: Object = payload
```
```{raw} html
</div>
```
```{raw} html
</details>
```
