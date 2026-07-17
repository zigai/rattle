---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-redundant-arguments-super)=

# no-redundant-arguments-super

<p class="rule-metadata">
  <span>Collection: <code>fixit-extra</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Prefer zero-argument super calls.

## Message

Call `super()` without arguments.

## References

- [PEP 3135](https://www.python.org/dev/peps/pep-3135/)

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
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
class Foo(Bar):
    @classmethod
    def foo(cls, bar):
        super(Bar, cls).foo(bar)
```
```python
class Foo:
    class InnerBar(Bar):
        def foo(self, bar):
            pass

    class InnerFoo(InnerBar):
        def foo(self, bar):
            super(InnerBar, self).foo(bar)
```
```python
class Foo(Bar):
    def foo(self, other):
        super(Foo, other).foo()
```
```python
class Foo(Bar):
    @classmethod
    def foo(cls, other):
        super(Foo, other).foo()
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
class Foo(Bar):
    def foo(self, bar):
        super(Foo, self).foo(bar)
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
class Foo(Bar):
    @classmethod
    def foo(cls, bar):
        super(Foo, cls).foo(bar)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
class Foo:
    class InnerFoo(Bar):
        def foo(self, bar):
            super(Foo.InnerFoo, self).foo(bar)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
class Foo:
    class InnerFoo(Bar):
        class InnerInnerFoo(Bar):
            def foo(self, bar):
                super(Foo.InnerFoo.InnerInnerFoo, self).foo(bar)
```
```{raw} html
</div>
```
```{raw} html
</details>
```
