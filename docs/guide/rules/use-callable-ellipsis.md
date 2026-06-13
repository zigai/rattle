---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-callable-ellipsis)=

# use-callable-ellipsis

<p class="rule-metadata">
  <span>Collection: <code>fixit</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Prefer Callable[..., T] for callable types with arbitrary parameters.

## Message

Use Callable[..., T] instead of Callable[[...], T].


## Valid examples

```python
from typing import Callable
x: Callable[[int], int]
```
```python
from typing import Callable
x: Callable[[int, int, ...], int]
```
```python
from typing import Callable
x: Callable
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
from typing import Callable as C
x: C[..., int] = ...
```
```python
from typing import Callable
def foo(bar: Optional[Callable[..., int]]) -> Callable[..., int]:
    ...
```
```python
import typing as t
x: t.Callable[..., int] = ...
```
```python
from typing import Callable
x: Callable[..., int] = ...
```
```python
from typing import Callable
C = Callable

class C:
    def __class_getitem__(cls, item):
        return cls

x: C[[...], int] = ...
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
from typing import Callable
x: Callable[[...], int] = ...
```
<p class="rule-example-label">Suggested fix</p>

```python
from typing import Callable
x: Callable[..., int] = ...
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
import typing as t
x: t.Callable[[...], int] = ...
```
<p class="rule-example-label">Suggested fix</p>

```python
import typing as t
x: t.Callable[..., int] = ...
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
from typing import Callable as C
x: C[[...], int] = ...
```
<p class="rule-example-label">Suggested fix</p>

```python
from typing import Callable as C
x: C[..., int] = ...
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
from typing import Callable
def foo(bar: Optional[Callable[[...], int]]) -> Callable[[...], int]:
    ...
```
<p class="rule-example-label">Suggested fix</p>

```python
from typing import Callable
def foo(bar: Optional[Callable[..., int]]) -> Callable[..., int]:
    ...
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
from collections.abc import Callable
x: Callable[[...], int] = ...
```
<p class="rule-example-label">Suggested fix</p>

```python
from collections.abc import Callable
x: Callable[..., int] = ...
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
from typing import Callable
C = Callable
x: C[[...], int] = ...
```
<p class="rule-example-label">Suggested fix</p>

```python
from typing import Callable
C = Callable
x: C[..., int] = ...
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
from typing import Callable
C = OtherC = Callable
x: OtherC[[...], int] = ...
```
<p class="rule-example-label">Suggested fix</p>

```python
from typing import Callable
C = OtherC = Callable
x: OtherC[..., int] = ...
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from typing import *
x: Callable[[...], int] = ...
```
<p class="rule-example-label">Suggested fix</p>

```python
from typing import *
x: Callable[..., int] = ...
```
```{raw} html
</div>
```
```{raw} html
</details>
```
