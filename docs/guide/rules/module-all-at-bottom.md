---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-module-all-at-bottom)=

# module-all-at-bottom

<p class="rule-metadata">
  <span>Collection: <code>exports</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Require module \_\_all\_\_ declarations to appear after runtime definitions.

## Message

Define module \_\_all\_\_ at the bottom of the file.


## Valid examples

```python
from package import value

def build() -> str:
    return value

__all__ = ["build"]
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
"""Module docstring."""

class Exported:
    pass

__all__: list[str] = ["Exported"]
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
__all__ = ["build"]

def build():
    return "value"
```
<p class="rule-example-label">Suggested fix</p>

```python
def build():
    return "value"

__all__ = ["build"]
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
__all__: list[str] = ["Exported"]

class Exported:
    pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from package import value

__all__ = ["value"]
value = "updated"
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
__all__ = []
__all__.append("build")

def build():
    return "value"
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
__all__ += ["build"]

def build():
    return "value"
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
__all__.insert(0, "build")

def build():
    return "value"
```
```{raw} html
</div>
```
```{raw} html
</details>
```
