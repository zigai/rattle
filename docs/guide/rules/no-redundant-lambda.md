---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-redundant-lambda)=

# NoRedundantLambda

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.no_redundant_lambda</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

A lambda function which has a single objective of
passing all it is arguments to another callable can
be safely replaced by that callable.


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
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
lambda: self.func()
```
<p class="rule-example-label">Suggested fix</p>

```python
self.func
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
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
```{raw} html
<div class="rule-invalid-example">
```
```python
lambda x, y, z: (t + u).math_call(x, y, z)
```
<p class="rule-example-label">Suggested fix</p>

```python
(t + u).math_call
```
```{raw} html
</div>
```
