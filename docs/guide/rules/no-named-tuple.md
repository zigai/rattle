---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-named-tuple)=

# NoNamedTuple

<p class="rule-metadata">
  <span>Pack: <code>fixit</code></span>
  <span>Module: <code>rattle.rules.fixit.no_namedtuple</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Enforce the use of ``dataclasses.dataclass`` decorator instead of ``NamedTuple`` for cleaner customization and
inheritance. It supports default value, combining fields for inheritance, and omitting optional fields at
instantiation. See `PEP 557 <https://www.python.org/dev/peps/pep-0557>`_.
``@dataclass`` is faster at reading an object's nested properties and executing its methods. (`benchmark <https://medium.com/@jacktator/dataclass-vs-namedtuple-vs-object-for-performance-optimization-in-python-691e234253b9>`_).

## Message

Instead of NamedTuple, consider using the @dataclass decorator from dataclasses instead for simplicity, efficiency and consistency.

## Valid examples

```python
@dataclass(frozen=True)
class Foo:
    pass
```
```python
@dataclass(frozen=False)
class Foo:
    pass
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
class Foo:
    pass
```
```python
class Foo(SomeOtherBase):
    pass
```
```python
@some_other_decorator
class Foo:
    pass
```
```python
@some_other_decorator
class Foo(SomeOtherBase):
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
from typing import NamedTuple

class Foo(NamedTuple):
    pass
```
<p class="rule-example-label">Suggested fix</p>

```python
import dataclasses

@dataclasses.dataclass(frozen=True)
class Foo:
    pass
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
from typing import NamedTuple as NT

class Foo(NT):
    pass
```
<p class="rule-example-label">Suggested fix</p>

```python
import dataclasses

@dataclasses.dataclass(frozen=True)
class Foo:
    pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
import typing as typ

class Foo(typ.NamedTuple):
    pass
```
<p class="rule-example-label">Suggested fix</p>

```python
import dataclasses
import typing as typ

@dataclasses.dataclass(frozen=True)
class Foo:
    pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
from typing import NamedTuple

class Foo(NamedTuple, AnotherBase, YetAnotherBase):
    pass
```
<p class="rule-example-label">Suggested fix</p>

```python
import dataclasses

@dataclasses.dataclass(frozen=True)
class Foo(AnotherBase, YetAnotherBase):
    pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
from typing import NamedTuple

class OuterClass(SomeBase):
    class InnerClass(NamedTuple):
        pass
```
<p class="rule-example-label">Suggested fix</p>

```python
import dataclasses

class OuterClass(SomeBase):
    @dataclasses.dataclass(frozen=True)
    class InnerClass:
        pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from typing import NamedTuple

@some_other_decorator
class Foo(NamedTuple):
    pass
```
<p class="rule-example-label">Suggested fix</p>

```python
import dataclasses

@some_other_decorator
@dataclasses.dataclass(frozen=True)
class Foo:
    pass
```
```{raw} html
</div>
```
```{raw} html
</details>
```
