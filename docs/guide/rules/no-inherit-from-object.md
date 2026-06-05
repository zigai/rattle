---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-inherit-from-object)=

# no-inherit-from-object

<p class="rule-metadata">
  <span>Collection: <code>fixit-extra</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

In Python 3, a class is inherited from ``object`` by default.
Explicitly inheriting from ``object`` is redundant, so removing it keeps the code simpler.

## Message

Inheriting from object is a no-op.  'class Foo:' is just fine =)


## Valid examples

```python
class A(something):    pass
```
```python
class A:
    pass
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
class B(object):
    pass
```
<p class="rule-example-label">Suggested fix</p>

```python
class B:
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
class B(object, A):
    pass
```
<p class="rule-example-label">Suggested fix</p>

```python
class B(A):
    pass
```
```{raw} html
</div>
```
```{raw} html
</details>
```
