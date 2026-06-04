---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-variadic-callable-syntax)=

# VariadicCallableSyntax

Callable types with arbitrary parameters should be written as `Callable[..., T]`.

<p class="rule-metadata">
  <span>Pack: <code>fixit</code></span>
  <span>Module: <code>rattle.rules.fixit.variadic_callable_syntax</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>


## Valid examples

```python
from typing import Callable
x: Callable[[int], int]
```
```python
from typing import Callable
x: Callable[[int, int, ...], int]
```

## Invalid examples

```python
from typing import Callable
x: Callable[[...], int] = ...

# suggested fix
from typing import Callable
x: Callable[..., int] = ...
```
```python
import typing as t
x: t.Callable[[...], int] = ...

# suggested fix
import typing as t
x: t.Callable[..., int] = ...
```
