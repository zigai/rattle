---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-explicit-frozen-dataclass)=

# ExplicitFrozenDataclass

Requires dataclass mutability to be explicit.

<p class="rule-metadata">
  <span>Pack: <code>fixit</code></span>
  <span>Module: <code>rattle.rules.fixit.explicit_frozen_dataclass</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

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

## Invalid examples

```python
from dataclasses import dataclass
@some_unrelated_decorator
@dataclass  # not called as a function
@another_unrelated_decorator
class Cls: pass
```
```python
from dataclasses import dataclass
@dataclass()  # called as a function, no kwargs
class Cls: pass
```
