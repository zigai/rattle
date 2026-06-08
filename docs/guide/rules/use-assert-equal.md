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
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Prefer specific unittest comparison assertions over assertTrue comparisons.

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
```python
self.assertTrue(a, 3)
```
```python
self.assertTrue(optional, None)
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
self.assertTrue(b == a, True)
```
```{raw} html
</details>
```

## Invalid examples

No invalid examples are documented.
