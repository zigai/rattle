---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-string-type-annotation)=

# no-string-type-annotation

<p class="rule-metadata">
  <span>Collection: <code>fixit-extra</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Replace quoted annotations when postponed annotation evaluation is enabled.

## Message

Remove the quotes from this annotation; postponed evaluation is already enabled.

## References

- [PEP 563](https://www.python.org/dev/peps/pep-0563/#forward-references)

## Valid examples

```python
from a.b import Class

def foo() -> Class:
    return Class()
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
import typing
from a.b import Class

def foo() -> typing.Type[Class]:
    return Class
```
```python
import typing
from a.b import Class
from c import func

def foo() -> typing.Optional[typing.Type[Class]]:
    return Class if func() else None
```
```python
from a.b import Class

def foo(arg: Class) -> None:
    pass

foo(Class())
```
```python
from a.b import Class

module_var: Class = Class()
```
```python
from typing import Literal

def foo() -> Literal["a", "b"]:
    return "a"
```
```python
import typing

def foo() -> typing.Optional[typing.Literal["a", "b"]]:
    return "a"
```
```python
import typing

def foo() -> typing.Optional[typing.Literal["class", "function"]]:
    return "class"
```
```python
from __future__ import annotations
from typing import Annotated

value: Annotated[int, "units"]
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
from __future__ import annotations

from a.b import Class

def foo() -> "Class":
    return Class()
```
<p class="rule-example-label">Suggested fix</p>

```python
from __future__ import annotations

from a.b import Class

def foo() -> Class:
    return Class()
```
```{raw} html
</div>
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
from __future__ import annotations

from a.b import Class

async def foo() -> "Class":
    return await Class()
```
<p class="rule-example-label">Suggested fix</p>

```python
from __future__ import annotations

from a.b import Class

async def foo() -> Class:
    return await Class()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
from __future__ import annotations

import typing
from a.b import Class

def foo() -> typing.Type["Class"]:
    return Class
```
<p class="rule-example-label">Suggested fix</p>

```python
from __future__ import annotations

import typing
from a.b import Class

def foo() -> typing.Type[Class]:
    return Class
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
from __future__ import annotations

import typing
from a.b import Class
from c import func

def foo() -> Optional[typing.Type["Class"]]:
    return Class if func() else None
```
<p class="rule-example-label">Suggested fix</p>

```python
from __future__ import annotations

import typing
from a.b import Class
from c import func

def foo() -> Optional[typing.Type[Class]]:
    return Class if func() else None
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
from __future__ import annotations

from a.b import Class

def foo(arg: "Class") -> None:
    pass

foo(Class())
```
<p class="rule-example-label">Suggested fix</p>

```python
from __future__ import annotations

from a.b import Class

def foo(arg: Class) -> None:
    pass

foo(Class())
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
from __future__ import annotations

from a.b import Class

module_var: "Class" = Class()
```
<p class="rule-example-label">Suggested fix</p>

```python
from __future__ import annotations

from a.b import Class

module_var: Class = Class()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
from __future__ import annotations

import typing
from typing_extensions import Literal
from a.b import Class

def foo() -> typing.Tuple[Literal["a", "b"], "Class"]:
    return Class()
```
<p class="rule-example-label">Suggested fix</p>

```python
from __future__ import annotations

import typing
from typing_extensions import Literal
from a.b import Class

def foo() -> typing.Tuple[Literal["a", "b"], Class]:
    return Class()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from __future__ import annotations

value: b"\xff"
```
```{raw} html
</div>
```
```{raw} html
</details>
```
