---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-assert-true-for-comparisons)=

# NoAssertTrueForComparisons

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.no_assert_true_for_comparison</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Finds incorrect use of ``assertTrue`` when the intention is to compare two values.
These calls are replaced with ``assertEqual``.
Comparisons with True, False and None are replaced with one-argument
calls to ``assertTrue``, ``assertFalse`` and ``assertIsNone``.

## Message

"assertTrue" does not compare its arguments, use "assertEqual" or other appropriate functions.

## Valid examples

```python
self.assertTrue(a == b)
```
```python
self.assertTrue(data.is_valid(), "is_valid() method")
```
```python
self.assertTrue(validate(len(obj.getName(type=SHORT))))
```
```python
self.assertTrue(condition, message_string)
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertTrue(a, 3)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertEqual(a, 3)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertTrue(hash(s[:4]), 0x1234)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertEqual(hash(s[:4]), 0x1234)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
self.assertTrue(list, [1, 3])
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertEqual(list, [1, 3])
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
self.assertTrue(optional, None)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertIsNone(optional)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertTrue(b == a, True)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertTrue(b == a)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
self.assertTrue(b == a, False)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertFalse(b == a)
```
```{raw} html
</div>
```
```{raw} html
</details>
```
