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

Python 3 classes inherit from ``object`` implicitly, so an explicit
``object`` base class is redundant.

## Message

Remove the redundant `object` base class.


## Valid examples

```python
class A(something):    pass
```
```python
class A:
    pass
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
class object:
    pass

class A(object):
    pass
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
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
<div class="rule-invalid-example">
```
```python
class B(object, A):
    pass
```
```{raw} html
</div>
```
