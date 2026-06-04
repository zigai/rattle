---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-deprecated-unittest-asserts)=

# DeprecatedUnittestAsserts

Discourages the use of various deprecated unittest.TestCase functions.

See https://docs.python.org/3/library/unittest.html#deprecated-aliases

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.deprecated_unittest_asserts</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

## Message

{deprecated} is deprecated, use {replacement} instead

## Valid examples

```python
self.assertEqual(a, b)
```
```python
self.assertNotEqual(a, b)
```

## Invalid examples

```python
self.assertEquals(a, b)

# suggested fix
self.assertEqual(a, b)
```
```python
self.assertNotEquals(a, b)

# suggested fix
self.assertNotEqual(a, b)
```
