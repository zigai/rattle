---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-assert-is-not-none)=

# use-assert-is-not-none

<p class="rule-metadata">
  <span>Collection: <code>fixit-extra</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Prefer ``assertIsNotNone`` and ``assertIsNone`` for unittest ``None`` checks.

## Message

Use `assertIsNone()` or `assertIsNotNone()` for `None` checks.


## Valid examples

```python
self.assertIsNotNone(x)
```
```python
self.assertIsNone(x)
```
```python
self.assertIsNone(None)
```
```python
self.assertIsNotNone(f(x))
```
```python
self.assertIsNone(f(x))
```
```python
self.assertIsNone(object.key)
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
self.assertIsNotNone(object.key)
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertTrue(a is not None)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertIsNotNone(a)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertTrue(not x is None)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertIsNotNone(x)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
self.assertTrue(f() is not None)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertIsNotNone(f())
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
self.assertTrue(not x is not None)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertIsNone(x)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertTrue(f(x) is not None)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertIsNotNone(f(x))
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertTrue(x is None)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertIsNone(x)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertFalse(x is not None)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertIsNone(x)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertFalse(not x is None)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertIsNone(x)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertFalse(f() is not None)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertIsNone(f())
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertFalse(not x is not None)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertIsNotNone(x)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
self.assertFalse(f(x) is not None)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertIsNone(f(x))
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
self.assertFalse(x is None)
```
<p class="rule-example-label">Suggested fix</p>

```python
self.assertIsNotNone(x)
```
```{raw} html
</div>
```
```{raw} html
</details>
```
