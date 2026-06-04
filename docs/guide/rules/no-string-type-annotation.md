---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-string-type-annotation)=

# NoStringTypeAnnotation

Enforce the use of type identifier instead of using string type hints for simplicity and better syntax highlighting.
Starting in Python 3.7, ``from __future__ import annotations`` can postpone evaluation of type annotations
`PEP 563 <https://www.python.org/dev/peps/pep-0563/#forward-references>`_
and thus forward references no longer need to use string annotation style.

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.no_string_type_annotation</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

## Message

String type hints are no longer necessary in Python, use the type identifier directly.

## Valid examples

```python
from a.b import Class

def foo() -> Class:
    return Class()
```
```python
import typing
from a.b import Class

def foo() -> typing.Type[Class]:
    return Class
```

## Invalid examples

```python
from __future__ import annotations

from a.b import Class

def foo() -> "Class":
    return Class()

# suggested fix
from __future__ import annotations

from a.b import Class

def foo() -> Class:
    return Class()
```
```python
from __future__ import annotations

from a.b import Class

async def foo() -> "Class":
    return await Class()

# suggested fix
from __future__ import annotations

from a.b import Class

async def foo() -> Class:
    return await Class()
```
