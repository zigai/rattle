---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-assert-in)=

# UseAssertIn

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.use_assert_in</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Discourages use of ``assertTrue(x in y)`` and ``assertFalse(x in y)``
as it is deprecated (https://docs.python.org/3.8/library/unittest.html#deprecated-aliases).
Use ``assertIn(x, y)`` and ``assertNotIn(x, y)``) instead.

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
```python
self.assertIn(f(x), b)
```
```python
self.assertIn(f(g(x)), b)
```
```python
self.assertNotIn(a, b)
```
```python
self.assertNotIn(f(), b)
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
self.assertNotIn(f(x), b)
```
```python
self.assertNotIn(f(g(x)), b)
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertTrue(a in b)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertIn(a, b)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertTrue(f() in b)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertIn(f(), b)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
self.assertTrue(f(x) in b)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertIn(f(x), b)
```
```{raw} html
</div>
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertTrue(f(g(x)) in b)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertIn(f(g(x)), b)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertTrue(a not in b)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertNotIn(a, b)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertTrue(not a in b)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertNotIn(a, b)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
self.assertFalse(a in b)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertNotIn(a, b)
```
```{raw} html
</div>
```
```{raw} html
</details>
```
