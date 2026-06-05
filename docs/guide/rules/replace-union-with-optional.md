---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-replace-union-with-optional)=

# ReplaceUnionWithOptional

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.replace_union_with_optional</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Enforces the use of ``Optional[T]`` over ``Union[T, None]`` and ``Union[None, T]``.
See https://docs.python.org/3/library/typing.html#typing.Optional to learn more about Optionals.

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
<details class="rule-extra-examples"><summary>Show more</summary>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
from typing import Optional
def func() -> Union[Dict[str, int], None]:
    pass
```
<p class="rule-example-label">Suggested fix</p>

```python
from typing import Optional
def func() -> Optional[Dict[str, int]]:
    pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
from typing import Optional
def func() -> Union[str, None]:
    pass
```
<p class="rule-example-label">Suggested fix</p>

```python
from typing import Optional
def func() -> Optional[str]:
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
<p class="rule-example-label">Suggested fix</p>

```python
from typing import Optional
def func() -> Optional[Dict]:
    pass
```
```{raw} html
</div>
```
```{raw} html
</details>
```
