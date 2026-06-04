---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-replace-union-with-optional)=

# ReplaceUnionWithOptional

Enforces the use of ``Optional[T]`` over ``Union[T, None]`` and ``Union[None, T]``.
See https://docs.python.org/3/library/typing.html#typing.Optional to learn more about Optionals.

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.replace_union_with_optional</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

## Message

`Optional[T]` is preferred over `Union[T, None]` or `Union[None, T]`. Learn more: https://docs.python.org/3/library/typing.html#typing.Optional

## Valid examples

```python
def func() -> Optional[str]:
    pass
```
```python
def func() -> Optional[Dict]:
    pass
```

## Invalid examples

```python
def func() -> Union[str, None]:
    pass
```
```python
from typing import Optional
def func() -> Union[Dict[str, int], None]:
    pass

# suggested fix
from typing import Optional
def func() -> Optional[Dict[str, int]]:
    pass
```
