---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-assert-in)=

# UseAssertIn

Discourages use of ``assertTrue(x in y)`` and ``assertFalse(x in y)``
as it is deprecated (https://docs.python.org/3.8/library/unittest.html#deprecated-aliases).
Use ``assertIn(x, y)`` and ``assertNotIn(x, y)``) instead.

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.use_assert_in</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

## Message

Use assertIn/assertNotIn instead of assertTrue/assertFalse for inclusion check.
See https://docs.python.org/3/library/unittest.html#unittest.TestCase.assertIn)

## Valid examples

```python
self.assertIn(a, b)
```
```python
self.assertIn(f(), b)
```

## Invalid examples

```python
self.assertTrue(a in b)

# suggested fix
self.assertIn(a, b)
```
```python
self.assertTrue(f() in b)

# suggested fix
self.assertIn(f(), b)
```
