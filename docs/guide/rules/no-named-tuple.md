---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-named-tuple)=

# NoNamedTuple

Enforce the use of ``dataclasses.dataclass`` decorator instead of ``NamedTuple`` for cleaner customization and
inheritance. It supports default value, combining fields for inheritance, and omitting optional fields at
instantiation. See `PEP 557 <https://www.python.org/dev/peps/pep-0557>`_.
``@dataclass`` is faster at reading an object's nested properties and executing its methods. (`benchmark <https://medium.com/@jacktator/dataclass-vs-namedtuple-vs-object-for-performance-optimization-in-python-691e234253b9>`_).

<p class="rule-metadata">
  <span>Pack: <code>fixit</code></span>
  <span>Module: <code>rattle.rules.fixit.no_namedtuple</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

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

## Invalid examples

```python
from typing import NamedTuple

class Foo(NamedTuple):
    pass

# suggested fix
import dataclasses

@dataclasses.dataclass(frozen=True)
class Foo:
    pass
```
```python
from typing import NamedTuple as NT

class Foo(NT):
    pass

# suggested fix
import dataclasses

@dataclasses.dataclass(frozen=True)
class Foo:
    pass
```
