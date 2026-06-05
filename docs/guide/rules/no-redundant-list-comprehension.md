---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-redundant-list-comprehension)=

# NoRedundantListComprehension

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.no_redundant_list_comprehension</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

A derivative of flake8-comprehensions's C407 rule.


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
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
any([val for val in iterable])
```
<p class="rule-example-label">Suggested fix</p>

```python
any(val for val in iterable)
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
<p class="rule-example-label">Suggested fix</p>

```python
all(val for val in iterable)
```
```{raw} html
</div>
```
