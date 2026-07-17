---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-replace-union-with-optional)=

# replace-union-with-optional

<p class="rule-metadata">
  <span>Collection: <code>fixit-extra</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Enforces the use of ``Optional[T]`` over ``Union[T, None]`` and ``Union[None, T]``.

## Message

`Optional[T]` is preferred over `Union[T, None]` or `Union[None, T]`.

## References

- [typing.Optional](https://docs.python.org/3/library/typing.html#typing.Optional)

## Valid examples

```python
def func() -> Optional[str]:
    pass
```
```python
def func() -> Optional[Dict]:
    pass
```
```python
def func() -> Union[str, int, None]:
    pass
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
def func() -> Union[str, None]:
    pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from typing import Optional
def func() -> Union[Dict[str, int], None]:
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
from typing import Optional
def func() -> Union[str, None]:
    pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from typing import Optional
def func() -> Union[Dict, None]:
    pass
```
```{raw} html
</div>
```
```{raw} html
</details>
```
