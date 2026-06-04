---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-rewrite-to-comprehension)=

# RewriteToComprehension

A derivative of flake8-comprehensions's C400-C402 and C403-C404.
Comprehensions are more efficient than functions calls. This C400-C402
suggest to use `dict/set/list` comprehensions rather than respective
function calls whenever possible. C403-C404 suggest to remove unnecessary
list comprehension in a set/dict call, and replace it with set/dict
comprehension.

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.rewrite_to_comprehension</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>


## Valid examples

```python
[val for val in iterable]
```
```python
{val for val in iterable}
```

## Invalid examples

```python
list(val for val in iterable)

# suggested fix
[val for val in iterable]
```
```python
list(val for row in matrix for val in row)

# suggested fix
[val for row in matrix for val in row]
```
