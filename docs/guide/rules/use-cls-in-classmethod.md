---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-cls-in-classmethod)=

# use-cls-in-classmethod

<p class="rule-metadata">
  <span>Collection: <code>fixit-extra</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Enforces using ``cls`` as the first argument in a ``@classmethod``.

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
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
class foo:
    # non-classmethod with non-cls first arg.
    def nm(self, a, b, c):
        pass
```
```python
class foo:
    # staticmethod with non-cls first arg.
    @staticmethod
    def sm(a):
        pass
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
class foo:
    # No args at all.
    @classmethod
    def cm():
        pass
```
<p class="rule-example-label">Suggested fix</p>

```python
class foo:
    # No args at all.
    @classmethod
    def cm(cls):
        pass
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
class foo:
    # Single arg + reference.
    @classmethod
    def cm(a):
        return a
```
<p class="rule-example-label">Suggested fix</p>

```python
class foo:
    # Single arg + reference.
    @classmethod
    def cm(cls):
        return cls
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
class foo:
    # Another "cls" exists: do not autofix.
    @classmethod
    def cm(a):
        cls = 2
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
class foo:
    # Multiple args + references.
    @classmethod
    async def cm(a, b):
        b = a
        b = a.__name__
```
<p class="rule-example-label">Suggested fix</p>

```python
class foo:
    # Multiple args + references.
    @classmethod
    async def cm(cls, b):
        b = cls
        b = cls.__name__
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
class foo:
    # Do not replace in nested scopes.
    @classmethod
    async def cm(a, b):
        b = a
        b = lambda _: a.__name__
        def g():
            return a.__name__

        # Same-named vars in sub-scopes should not be replaced.
        b = [a for a in [1,2,3]]
        def f(a):
            return a + 1
```
<p class="rule-example-label">Suggested fix</p>

```python
class foo:
    # Do not replace in nested scopes.
    @classmethod
    async def cm(cls, b):
        b = cls
        b = lambda _: cls.__name__
        def g():
            return cls.__name__

        # Same-named vars in sub-scopes should not be replaced.
        b = [a for a in [1,2,3]]
        def f(a):
            return a + 1
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
# Do not replace in surrounding scopes.
a = 1

class foo:
    a = 2

    def im(a):
        a = a

    @classmethod
    def cm(a):
        a[1] = foo.cm(a=a)
```
<p class="rule-example-label">Suggested fix</p>

```python
# Do not replace in surrounding scopes.
a = 1

class foo:
    a = 2

    def im(a):
        a = a

    @classmethod
    def cm(cls):
        cls[1] = foo.cm(a=cls)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
def another_decorator(x): pass

class foo:
    # Multiple decorators.
    @another_decorator
    @classmethod
    @another_decorator
    async def cm(a, b, c):
        pass
```
<p class="rule-example-label">Suggested fix</p>

```python
def another_decorator(x): pass

class foo:
    # Multiple decorators.
    @another_decorator
    @classmethod
    @another_decorator
    async def cm(cls, b, c):
        pass
```
```{raw} html
</div>
```
```{raw} html
</details>
```
