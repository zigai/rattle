---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-assert-true-for-comparisons)=

# NoAssertTrueForComparisons

Finds incorrect use of ``assertTrue`` when the intention is to compare two values.
These calls are replaced with ``assertEqual``.
Comparisons with True, False and None are replaced with one-argument
calls to ``assertTrue``, ``assertFalse`` and ``assertIsNone``.

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.no_assert_true_for_comparison</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

## Message

"assertTrue" does not compare its arguments, use "assertEqual" or other appropriate functions.

## Valid examples

```python
self.assertTrue(a == b)
```
```python
self.assertTrue(data.is_valid(), "is_valid() method")
```

## Invalid examples

```python
self.assertTrue(a, 3)

# suggested fix
self.assertEqual(a, 3)
```
```python
self.assertTrue(hash(s[:4]), 0x1234)

# suggested fix
self.assertEqual(hash(s[:4]), 0x1234)
```
