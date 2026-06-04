---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-redundant-list-comprehension)=

# NoRedundantListComprehension

A derivative of flake8-comprehensions's C407 rule.

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.no_redundant_list_comprehension</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>


## Valid examples

```python
any(val for val in iterable)
```
```python
all(val for val in iterable)
```

## Invalid examples

```python
any([val for val in iterable])

# suggested fix
any(val for val in iterable)
```
```python
all([val for val in iterable])

# suggested fix
all(val for val in iterable)
```
