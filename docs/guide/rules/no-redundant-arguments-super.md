---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-redundant-arguments-super)=

# NoRedundantArgumentsSuper

Remove redundant arguments when using super for readability.

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.no_redundant_arguments_super</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

## Message

Do not use arguments when calling super for the parent class. See https://www.python.org/dev/peps/pep-3135/

## Valid examples

```python
class Foo(Bar):
    def foo(self, bar):
        super().foo(bar)
```
```python
class Foo(Bar):
    def foo(self, bar):
        super(Bar, self).foo(bar)
```

## Invalid examples

```python
class Foo(Bar):
    def foo(self, bar):
        super(Foo, self).foo(bar)

# suggested fix
class Foo(Bar):
    def foo(self, bar):
        super().foo(bar)
```
```python
class Foo(Bar):
    @classmethod
    def foo(cls, bar):
        super(Foo, cls).foo(bar)

# suggested fix
class Foo(Bar):
    @classmethod
    def foo(cls, bar):
        super().foo(bar)
```
