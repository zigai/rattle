---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-comprehension)=

# use-comprehension

<p class="rule-metadata">
  <span>Collection: <code>fixit-extra</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Prefer comprehensions over unnecessary collection constructor calls.

## Message

It's unnecessary to use {func} around a generator expression, since there are equivalent comprehensions for this type.


## Valid examples

```python
[val for val in iterable]
```
```python
{val for val in iterable}
```
```python
{val: val+1 for val in iterable}
```
```python
dict(line.strip().split('=', 1) for line in attr_file)
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
def list(value):
    return value

list(val for val in iterable)
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
list(val for val in iterable)
```
<p class="rule-example-label">Suggested fix</p>

```python
[val for val in iterable]
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
list(val for row in matrix for val in row)
```
<p class="rule-example-label">Suggested fix</p>

```python
[val for row in matrix for val in row]
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
set(val for val in iterable)
```
<p class="rule-example-label">Suggested fix</p>

```python
{val for val in iterable}
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
dict((x, f(x)) for val in iterable)
```
<p class="rule-example-label">Suggested fix</p>

```python
{x: f(x) for val in iterable}
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
dict((x, y) for y, x in iterable)
```
<p class="rule-example-label">Suggested fix</p>

```python
{x: y for y, x in iterable}
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
dict([val, val+1] for val in iterable)
```
<p class="rule-example-label">Suggested fix</p>

```python
{val: val+1 for val in iterable}
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
dict((x["name"], json.loads(x["data"])) for x in responses)
```
<p class="rule-example-label">Suggested fix</p>

```python
{x["name"]: json.loads(x["data"]) for x in responses}
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
dict((k, v) for k, v in iter for iter in iters)
```
<p class="rule-example-label">Suggested fix</p>

```python
{k: v for k, v in iter for iter in iters}
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
set([val for val in iterable])
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
dict([[val, val+1] for val in iterable])
```
<p class="rule-example-label">Suggested fix</p>

```python
{val: val+1 for val in iterable}
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
dict([(x, f(x)) for x in foo])
```
<p class="rule-example-label">Suggested fix</p>

```python
{x: f(x) for x in foo}
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
dict([(x, y) for y, x in iterable])
```
<p class="rule-example-label">Suggested fix</p>

```python
{x: y for y, x in iterable}
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
set([val for row in matrix for val in row])
```
```{raw} html
</div>
```
```{raw} html
</details>
```
