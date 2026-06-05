---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-explicit-frozen-dataclass)=

# explicit-frozen-dataclass

<p class="rule-metadata">
  <span>Collection: <code>fixit</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Requires dataclass mutability to be explicit.

## Message

Dataclass mutability must be explicit. Add `frozen=True` for immutable value objects or `frozen=False` when instances are intentionally mutable.


## Valid examples

```python
@some_other_decorator
class Cls: pass
```
```python
from dataclasses import dataclass
@dataclass(frozen=False)
class Cls: pass
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
import dataclasses
@dataclasses.dataclass(frozen=False)
class Cls: pass
```
```python
import dataclasses as dc
@dc.dataclass(frozen=False)
class Cls: pass
```
```python
from dataclasses import dataclass as dc
@dc(frozen=False)
class Cls: pass
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
from dataclasses import dataclass
@some_unrelated_decorator
@dataclass  # not called as a function
@another_unrelated_decorator
class Cls: pass
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
from dataclasses import dataclass
@dataclass()  # called as a function, no kwargs
class Cls: pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from dataclasses import dataclass
@dataclass(other_kwarg=False)
class Cls: pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import dataclasses
@dataclasses.dataclass
class Cls: pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import dataclasses
@dataclasses.dataclass()
class Cls: pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import dataclasses
@dataclasses.dataclass(other_kwarg=False)
class Cls: pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from dataclasses import dataclass as dc
@dc
class Cls: pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from dataclasses import dataclass as dc
@dc()
class Cls: pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from dataclasses import dataclass as dc
@dc(other_kwarg=False)
class Cls: pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import dataclasses as dc
@dc.dataclass
class Cls: pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import dataclasses as dc
@dc.dataclass()
class Cls: pass
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import dataclasses as dc
@dc.dataclass(other_kwarg=False)
class Cls: pass
```
```{raw} html
</div>
```
```{raw} html
</details>
```
