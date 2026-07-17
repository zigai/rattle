---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-collapse-isinstance-checks)=

# collapse-isinstance-checks

<p class="rule-metadata">
  <span>Collection: <code>fixit-extra</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Combine repeated ``isinstance`` checks by passing a tuple of types.

## Message

Multiple isinstance calls with the same target but different types can be collapsed into a single call with a tuple of types.


## Valid examples

```python
foo() or foo()
```
```python
foo(x, y) or foo(x, z)
```
```python
foo(x, y) or foo(x, z) or foo(x, q)
```
```python
isinstance() or isinstance()
```
```python
isinstance(x) or isinstance(x)
```
```python
isinstance(x, y) or isinstance(x)
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
isinstance(x) or isinstance(x, y)
```
```python
isinstance(x, y) or isinstance(t, y)
```
```python
isinstance(f(), A) or isinstance(f(), B)
```
```python
isinstance(x, y) and isinstance(x, z)
```
```python
isinstance(x, y) or isinstance(x, (z, q))
```
```python
isinstance(x, (y, z)) or isinstance(x, q)
```
```python
isinstance(x, a) or isinstance(y, b) or isinstance(z, c)
```
```python
def foo():
    def isinstance(x, y):
        return _foo_bar(x, y)
    if isinstance(x, y) or isinstance(x, z):
        print("foo")
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
isinstance(x, y) or isinstance(x, z)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
isinstance(x, y) or isinstance(x, z) or isinstance(x, q)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
something or isinstance(x, y) or isinstance(x, z) or another
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
isinstance(x, y) or isinstance(x, z) or isinstance(x, q) or isinstance(x, w)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
isinstance(x, a) or isinstance(x, b) or isinstance(y, c) or isinstance(y, d)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
isinstance(x, a) or isinstance(x, b) or isinstance(y, c) or isinstance(y, d) or isinstance(z, e)
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
isinstance(x, a) or isinstance(x, b) or isinstance(y, c) or isinstance(y, d) or isinstance(z, e) or isinstance(q, f) or isinstance(q, g) or isinstance(q, h)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import builtins

builtins.isinstance(x, A) or builtins.isinstance(x, B)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from builtins import isinstance as check

check(x, A) or check(x, B)
```
```{raw} html
</div>
```
```{raw} html
</details>
```
