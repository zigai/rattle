---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-redundant-list-comprehension)=

# no-redundant-list-comprehension

<p class="rule-metadata">
  <span>Collection: <code>fixit-extra</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Prefer generator expressions inside ``any()`` and ``all()``. Replacing a list
comprehension changes eager evaluation into lazy short-circuiting, so side
effects in later iterations may no longer run.

## Message

Unnecessary list comprehension inside {func}(). Use a generator expression instead.


## Valid examples

```python
any(val for val in iterable)
```
```python
all(val for val in iterable)
```
```python
frozenset([val for val in iterable])
```
```python
max([val for val in iterable])
```
```python
min([val for val in iterable])
```
```python
sorted([val for val in iterable])
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
sum([val for val in iterable])
```
```python
tuple([val for val in iterable])
```
```python
def any(value):
    return value

any([val for val in iterable])
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
any([val for val in iterable])
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
all([val for val in iterable])
```
```{raw} html
</div>
```
