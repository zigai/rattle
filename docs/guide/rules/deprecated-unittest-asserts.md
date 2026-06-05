---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-deprecated-unittest-asserts)=

# DeprecatedUnittestAsserts

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.deprecated_unittest_asserts</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Discourages the use of various deprecated unittest.TestCase functions.

See https://docs.python.org/3/library/unittest.html#deprecated-aliases

## Message

{deprecated} is deprecated, use {replacement} instead

## Valid examples

```python
self.assertEqual(a, b)
```
```python
self.assertNotEqual(a, b)
```
```python
self.assertAlmostEqual(a, b)
```
```python
self.assertNotAlmostEqual(a, b)
```
```python
self.assertRegex(text, regex)
```
```python
self.assertNotRegex(text, regex)
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
self.assertRaisesRegex(exception, regex)
```
```python
obj.assertEquals(a, b)
```
```python
obj.assertNotEquals(a, b)
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertEquals(a, b)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertEqual(a, b)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertNotEquals(a, b)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertNotEqual(a, b)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
self.assertAlmostEquals(a, b)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertAlmostEqual(a, b)
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
self.assertNotAlmostEquals(a, b)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertNotAlmostEqual(a, b)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertRegexpMatches(text, regex)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertRegex(text, regex)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertNotRegexpMatches(text, regex)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertNotRegex(text, regex)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
self.assertRaisesRegexp(exception, regex)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertRaisesRegex(exception, regex)
```
```{raw} html
</div>
```
```{raw} html
</details>
```
