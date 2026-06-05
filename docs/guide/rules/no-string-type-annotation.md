---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-string-type-annotation)=

# NoStringTypeAnnotation

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.no_string_type_annotation</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Enforce the use of type identifier instead of using string type hints for simplicity and better syntax highlighting.
Starting in Python 3.7, ``from __future__ import annotations`` can postpone evaluation of type annotations
`PEP 563 <https://www.python.org/dev/peps/pep-0563/#forward-references>`_
and thus forward references no longer need to use string annotation style.

## Message

String type hints are no longer necessary in Python, use the type identifier directly.

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
<div class="rule-invalid-example">
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
</details>
```
