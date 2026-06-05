---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-eq-for-primitives)=

# use-eq-for-primitives

<p class="rule-metadata">
  <span>Collection: <code>fixit-extra</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Enforces the use of ``==`` and ``!=`` in comparisons to primitives rather than ``is`` and ``is not``.
The ``==`` operator checks equality, while ``is`` checks identity.

## Message

Don't use `is` or `is not` to compare primitives, as they compare references. Use == or != instead.

## References

- [object.__eq__](https://docs.python.org/3/reference/datamodel.html#object.__eq__)
- [is operator](https://docs.python.org/3/reference/expressions.html#is)

## Valid examples

```python
a == 1
```
```python
a == '1'
```
```python
a != '1'
```
```python
'3' == '1'
```
```python
3 == '1'
```
```python
3 > 2 > 1
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
3 > 2 > '1'
```
```python
a is b > 1
```
```python
a is b is c
```
```python
1 > b is c
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
a is 1
```
<p class="rule-example-label">Suggested fix</p>

```python
a == 1
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
a is '1'
```
<p class="rule-example-label">Suggested fix</p>

```python
a == '1'
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
a is f'1{b}'
```
<p class="rule-example-label">Suggested fix</p>

```python
a == f'1{b}'
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
a is not f'1{d}'
```
<p class="rule-example-label">Suggested fix</p>

```python
a != f'1{d}'
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
1 is a
```
<p class="rule-example-label">Suggested fix</p>

```python
1 == a
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
'2' > '1' is a
```
<p class="rule-example-label">Suggested fix</p>

```python
'2' > '1' == a
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
3 > a is 2
```
<p class="rule-example-label">Suggested fix</p>

```python
3 > a == 2
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
1  is   2
```
<p class="rule-example-label">Suggested fix</p>

```python
1  ==   2
```
```{raw} html
</div>
```
```{raw} html
</details>
```
