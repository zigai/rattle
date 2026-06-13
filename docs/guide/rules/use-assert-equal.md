---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-assert-equal)=

# use-assert-equal

<p class="rule-metadata">
  <span>Collection: <code>fixit-extra</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Prefer specific unittest comparison assertions over assertTrue comparisons.

## Message

"assertTrue" does not compare its arguments, use "assertEqual" or other appropriate functions.


## Valid examples

```python
self.assertEqual(a, b)
```
```python
self.assertNotEqual(a, b)
```
```python
self.assertTrue(a < b)
```
```python
self.assertTrue(a == b == c)
```
```python
self.assertTrue(data.is_valid(), "is_valid() method")
```
```python
self.assertTrue(validate(len(obj.getName(type=SHORT))))
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
self.assertTrue(condition, message_string)
```
```python
self.assertTrue(a, 3)
```
```python
self.assertTrue(optional, None)
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertTrue(a == b)
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
self.assertTrue(a != b)
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
self.assertTrue(a == b, "message")
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertEqual(a, b, "message")
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
self.assertTrue(not a == b)
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
self.assertTrue(not a != b)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertEqual(a, b)
```
```{raw} html
</div>
```
```{raw} html
</details>
```
