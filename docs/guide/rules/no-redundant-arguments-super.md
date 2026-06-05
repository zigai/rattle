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
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Remove redundant arguments when using super for readability.

## Message

Do not use arguments when calling super for the parent class.

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
<p class="rule-example-label">Suggested fix</p>

```python
class Foo(Bar):
    def foo(self, bar):
        super().foo(bar)
```
```{raw} html
</div>
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
class Foo(Bar):
    @classmethod
    def foo(cls, bar):
        super(Foo, cls).foo(bar)
```
<p class="rule-example-label">Suggested fix</p>

```python
class Foo(Bar):
    @classmethod
    def foo(cls, bar):
        super().foo(bar)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
class Foo:
    class InnerFoo(Bar):
        def foo(self, bar):
            super(Foo.InnerFoo, self).foo(bar)
```
<p class="rule-example-label">Suggested fix</p>

```python
class Foo:
    class InnerFoo(Bar):
        def foo(self, bar):
            super().foo(bar)
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
<p class="rule-example-label">Suggested fix</p>

```python
class Foo:
    class InnerFoo(Bar):
        class InnerInnerFoo(Bar):
            def foo(self, bar):
                super().foo(bar)
```
```{raw} html
</div>
```
```{raw} html
</details>
```
