---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-redundant-lambda)=

# no-redundant-lambda

<p class="rule-metadata">
  <span>Collection: <code>fixit-extra</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

A lambda function which has a single objective of
passing all it is arguments to another callable can
be safely replaced by that callable.

## Message

The lambda that is wrapping {function} is redundant. It can unwrapped safely and used purely.


## Valid examples

```python
lambda x: foo(y)
```
```python
lambda x: foo(x, y)
```
```python
lambda x, y: foo(x)
```
```python
lambda *, x: foo(x)
```
```python
lambda x = y: foo(x)
```
```python
lambda x, y: foo(y, x)
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
lambda self: self.func()
```
```python
lambda x, y: foo(y=x, x=y)
```
```python
lambda x, y, *z: foo(x, y, z)
```
```python
lambda x, y, **z: foo(x, y, z)
```
```python
lambda: self.func()
```
```python
lambda x, y, z: (t + u).math_call(x, y, z)
```
```python
lambda x: obj.method(x)
```
```python
class C:
    callback = lambda x: foo(x)
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
lambda x: foo(x)
```
<p class="rule-example-label">Suggested fix</p>

```python
foo
```
```{raw} html
</div>
```
