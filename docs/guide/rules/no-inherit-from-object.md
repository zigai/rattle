---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-inherit-from-object)=

# NoInheritFromObject

In Python 3, a class is inherited from ``object`` by default.
Explicitly inheriting from ``object`` is redundant, so removing it keeps the code simpler.

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.no_inherit_from_object</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

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

```python
class B(object):
    pass

# suggested fix
class B:
    pass
```
```python
class B(object, A):
    pass

# suggested fix
class B(A):
    pass
```
