---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-assert-is-not-none)=

# UseAssertIsNotNone

Discourages use of ``assertTrue(x is not None)`` and ``assertFalse(x is not None)`` as it is deprecated (https://docs.python.org/3.8/library/unittest.html#deprecated-aliases).
Use ``assertIsNotNone(x)`` and ``assertIsNone(x)``) instead.

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.use_assert_is_not_none</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

## Message

"assertTrue" and "assertFalse" are deprecated. Use "assertIsNotNone" and "assertIsNone" instead.
See https://docs.python.org/3.8/library/unittest.html#deprecated-aliases

## Valid examples

```python
self.assertIsNotNone(x)
```
```python
self.assertIsNone(x)
```

## Invalid examples

```python
self.assertTrue(a is not None)

# suggested fix
self.assertIsNotNone(a)
```
```python
self.assertTrue(not x is None)

# suggested fix
self.assertIsNotNone(x)
```
