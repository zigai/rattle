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
<span>Tags: `exports`, `style`</span></p>

Forbid exporting underscore-prefixed names from module __all__.

## Message

Do not export underscore-prefixed symbols in __all__. Either remove them from __all__ or rename them to be public.


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
