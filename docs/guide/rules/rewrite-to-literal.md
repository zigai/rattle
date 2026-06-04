---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-rewrite-to-literal)=

# RewriteToLiteral

A derivative of flake8-comprehensions' C405-C406 and C409-C410. It's
unnecessary to use a list or tuple literal within a call to tuple, list,
set, or dict since there is literal syntax for these types.

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.rewrite_to_literal</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>


## Valid examples

```python
(1, 2)
```
```python
()
```

## Invalid examples

```python
tuple([1, 2])

# suggested fix
(1, 2)
```
```python
tuple((1, 2))

# suggested fix
(1, 2)
```
