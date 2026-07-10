---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-assert-in)=

# use-assert-in

<p class="rule-metadata">
  <span>Collection: <code>fixit-extra</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Prefer ``assertIn`` and ``assertNotIn`` for unittest membership checks.

## Message

Use `assertIn()` or `assertNotIn()` for membership checks.

## References

- [unittest assertIn](https://docs.python.org/3/library/unittest.html#unittest.TestCase.assertIn)

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
```python
class Checker:
    def assertTrue(self, expr):
        print(expr)

    def check(self, a, b):
        self.assertTrue(a in b)
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
