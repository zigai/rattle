---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-compare-singleton-primitives-by-is)=

# CompareSingletonPrimitivesByIs

Enforces the use of `is` and `is not` in comparisons to singleton primitives (None, True, False) rather than == and !=.
The == operator checks equality, when in this scenario, we want to check identity.
See Flake8 rules E711 (https://www.flake8rules.com/rules/E711.html) and E712 (https://www.flake8rules.com/rules/E712.html).

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.compare_singleton_primitives_by_is</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

## Message

Comparisons to singleton primitives should not be done with == or !=, as they check equality rather than identity. Use `is` or `is not` instead.

## Valid examples

```python
if x: pass
```
```python
if not x: pass
```

## Invalid examples

```python
x != True

# suggested fix
x is not True
```
```python
x != False

# suggested fix
x is not False
```
