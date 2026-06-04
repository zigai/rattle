---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-compare-primitives-by-equal)=

# ComparePrimitivesByEqual

Enforces the use of ``==`` and ``!=`` in comparisons to primitives rather than ``is`` and ``is not``.
The ``==`` operator checks equality (https://docs.python.org/3/reference/datamodel.html#object.__eq__),
while ``is`` checks identity (https://docs.python.org/3/reference/expressions.html#is).

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.compare_primitives_by_equal</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

## Message

Don't use `is` or `is not` to compare primitives, as they compare references. Use == or != instead.

## Valid examples

```python
a == 1
```
```python
a == '1'
```

## Invalid examples

```python
a is 1

# suggested fix
a == 1
```
```python
a is '1'

# suggested fix
a == '1'
```
