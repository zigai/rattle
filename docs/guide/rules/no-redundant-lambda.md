---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-redundant-lambda)=

# NoRedundantLambda

A lambda function which has a single objective of
passing all it is arguments to another callable can
be safely replaced by that callable.

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.no_redundant_lambda</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>


## Valid examples

```python
lambda x: foo(y)
```
```python
lambda x: foo(x, y)
```

## Invalid examples

```python
lambda: self.func()

# suggested fix
self.func
```
```python
lambda x: foo(x)

# suggested fix
foo
```
