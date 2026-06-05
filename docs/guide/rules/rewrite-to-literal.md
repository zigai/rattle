---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-rewrite-to-literal)=

# rewrite-to-literal

<p class="rule-metadata">
  <span>Collection: <code>fixit-extra</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

A derivative of flake8-comprehensions' C405-C406 and C409-C410. It's
unnecessary to use a list or tuple literal within a call to tuple, list,
set, or dict since there is literal syntax for these types.


## Valid examples

```python
(1, 2)
```
```python
()
```
```python
[1, 2]
```
```python
[]
```
```python
{1, 2}
```
```python
set()
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
{1: 2, 3: 4}
```
```python
{}
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
tuple([1, 2])
```
<p class="rule-example-label">Suggested fix</p>

```python
(1, 2)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
tuple((1, 2))
```
<p class="rule-example-label">Suggested fix</p>

```python
(1, 2)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
tuple([])
```
<p class="rule-example-label">Suggested fix</p>

```python
()
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
list([1, 2, 3])
```
<p class="rule-example-label">Suggested fix</p>

```python
[1, 2, 3]
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
list((1, 2, 3))
```
<p class="rule-example-label">Suggested fix</p>

```python
[1, 2, 3]
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
list([])
```
<p class="rule-example-label">Suggested fix</p>

```python
[]
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
set([1, 2, 3])
```
<p class="rule-example-label">Suggested fix</p>

```python
{1, 2, 3}
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
set((1, 2, 3))
```
<p class="rule-example-label">Suggested fix</p>

```python
{1, 2, 3}
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
set([])
```
<p class="rule-example-label">Suggested fix</p>

```python
set()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
dict([(1, 2), (3, 4)])
```
<p class="rule-example-label">Suggested fix</p>

```python
{1: 2, 3: 4}
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
dict(((1, 2), (3, 4)))
```
<p class="rule-example-label">Suggested fix</p>

```python
{1: 2, 3: 4}
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
dict([[1, 2], [3, 4], [5, 6]])
```
<p class="rule-example-label">Suggested fix</p>

```python
{1: 2, 3: 4, 5: 6}
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
dict([])
```
<p class="rule-example-label">Suggested fix</p>

```python
{}
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
tuple()
```
<p class="rule-example-label">Suggested fix</p>

```python
()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
list()
```
<p class="rule-example-label">Suggested fix</p>

```python
[]
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
dict()
```
<p class="rule-example-label">Suggested fix</p>

```python
{}
```
```{raw} html
</div>
```
```{raw} html
</details>
```
