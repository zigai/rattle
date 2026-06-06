---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-types-from-typing)=

# use-types-from-typing

<p class="rule-metadata">
  <span>Collection: <code>fixit</code></span>
  <span>Autofix: Yes</span>
  <span>Python: `< 3.10`</span>
</p>

Enforces the use of types from the ``typing`` module in type annotations in place
of ``builtins.{builtin_type}`` since the type system doesn't recognize the latter
as a valid type before Python ``3.10``.

## Message

You are using builtins.{builtin_type} as a type annotation but the type system doesn't recognize it as a valid type. Use typing.{correct_type} instead.


## Valid examples

```python
def function(list: List[str]) -> None:
    pass
```
```python
def function() -> None:
    thing: Dict[str, str] = {}
```
```python
def function() -> None:
    thing: Tuple[str]
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
from typing import Dict, List
def function() -> bool:
        return Dict == List
```
```python
from typing import List as list
from graphene import List

def function(a: list[int]) -> List[int]:
        return []
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
from typing import List
def whatever(list: list[str]) -> None:
    pass
```
<p class="rule-example-label">Suggested fix</p>

```python
from typing import List
def whatever(list: List[str]) -> None:
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
def function(list: list[str]) -> None:
    pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
def func() -> None:
    thing: dict[str, str] = {}
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
def func() -> None:
    thing: tuple[str]
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from typing import Dict
def func() -> None:
    thing: dict[str, str] = {}
```
<p class="rule-example-label">Suggested fix</p>

```python
from typing import Dict
def func() -> None:
    thing: Dict[str, str] = {}
```
```{raw} html
</div>
```
```{raw} html
</details>
```
