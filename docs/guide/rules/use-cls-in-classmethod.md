---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-cls-in-classmethod)=

# UseClsInClassmethod

Enforces using ``cls`` as the first argument in a ``@classmethod``.

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.cls_in_classmethod</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

## Message

When using @classmethod, the first argument must be `cls`.

## Valid examples

```python
class foo:
    # classmethod with cls first arg.
    @classmethod
    def cm(cls, a, b, c):
        pass
```
```python
class foo:
    # non-classmethod with non-cls first arg.
    def nm(self, a, b, c):
        pass
```

## Invalid examples

```python
class foo:
    # No args at all.
    @classmethod
    def cm():
        pass

# suggested fix
class foo:
    # No args at all.
    @classmethod
    def cm(cls):
        pass
```
```python
class foo:
    # Single arg + reference.
    @classmethod
    def cm(a):
        return a

# suggested fix
class foo:
    # Single arg + reference.
    @classmethod
    def cm(cls):
        return cls
```
