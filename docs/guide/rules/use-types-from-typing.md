---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-types-from-typing)=

# UseTypesFromTyping

Enforces the use of types from the ``typing`` module in type annotations in place
of ``builtins.{builtin_type}`` since the type system doesn't recognize the latter
as a valid type before Python ``3.10``.

<p class="rule-metadata">
  <span>Pack: <code>fixit</code></span>
  <span>Module: <code>rattle.rules.fixit.use_types_from_typing</code></span>
  <span>Autofix: Yes</span>
  <span>Python: `< 3.10`</span>
</p>


## Valid examples

```python
def function(list: List[str]) -> None:
    pass
```
```python
def function() -> None:
    thing: Dict[str, str] = {}
```

## Invalid examples

```python
from typing import List
def whatever(list: list[str]) -> None:
    pass

# suggested fix
from typing import List
def whatever(list: List[str]) -> None:
    pass
```
```python
def function(list: list[str]) -> None:
    pass
```
