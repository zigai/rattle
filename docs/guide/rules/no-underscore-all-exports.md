---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-underscore-all-exports)=

# no-underscore-all-exports

<p class="rule-metadata">
  <span>Collection: <code>exports</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Forbid exporting underscore-prefixed names from module \_\_all\_\_.

## Message

Do not export underscore-prefixed symbols in \_\_all\_\_. Either remove them from \_\_all\_\_ or rename them to be public.


## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">allow_dunder_exports</span></td>
      <td>Allow double-underscore names such as __version__ in __all__.</td>
      <td><span class="rule-setting-type">bool</span></td>
      <td><span class="rule-setting-default rule-setting-default-constant">False</span></td>
    </tr>
<tr>
      <td><span class="rule-setting-name">allowed_exports</span></td>
      <td>Underscore-prefixed __all__ entries to allow by exact name.</td>
      <td><span class="rule-setting-type">list</span></td>
      <td><span class="rule-setting-default rule-setting-default-plain">[]</span></td>
    </tr>
</tbody>
</table>
```

## Valid examples

```python
__all__ = ["PublicThing", "public_thing"]
```
```python
__all__: list[str] = ["public_name"]
```
```python
__all__ = ("PublicThing", "public_thing")
```
```python
EXPORTS = ["_private_name"]
__all__ = list(EXPORTS)
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
def build() -> None:
    __all__ = ["_private_name"]
```
```python
module.__all__ = ["_private_name"]
```
```python
__all__ = ["__version__"]
```
```python
__all__ = ["_C_API", "_Sentinel"]
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
__all__ = ["_private_name"]
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
__all__: tuple[str, ...] = ("public_name", "_private_name")
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
__all__ += ["__version__"]
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
__all__.append("_private_name")
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
__all__.extend(["_private_name"])
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
__all__.insert(0, "_private_name")
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
__all__ = [*["_private_name"]]
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
__all__ = ["_private" "_name"]
```
```{raw} html
</div>
```
```{raw} html
</details>
```
