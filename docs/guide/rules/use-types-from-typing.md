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
  <span>Python: `< 3.9`</span>
</p>

For Python ``< 3.9`` only, require ``typing.Dict``, ``typing.List``,
``typing.Set``, and ``typing.Tuple`` annotations instead of builtin generic
aliases such as ``dict[str, str]``.

## Message template

Python 3.8 does not support `{builtin_type}[...]` annotations; use `typing.{correct_type}` instead.

Placeholder values are filled in when the violation is reported.


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
```python
from builtins import list as ListType

LT = ListType

class LT:
    def __class_getitem__(cls, item):
        return cls

def func(value: LT[str]) -> None:
    pass
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
<div class="rule-invalid-example rule-invalid-example-separated">
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
<div class="rule-invalid-example">
```
```python
from builtins import list as ListType

def func(value: ListType[str]) -> None:
    pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from builtins import list as ListType

LT = ListType

def func(value: LT[str]) -> None:
    pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from builtins import list as ListType

LT = OtherLT = ListType

def func(value: OtherLT[str]) -> None:
    pass
```
```{raw} html
</div>
```
```{raw} html
</details>
```
