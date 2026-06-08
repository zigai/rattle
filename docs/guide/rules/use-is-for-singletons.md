---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-is-for-singletons)=

# use-is-for-singletons

<p class="rule-metadata">
  <span>Collection: <code>fixit-extra</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Require identity operators when comparing singleton primitives.

## Message

Comparisons to singleton primitives should not be done with == or !=, as they check equality rather than identity. Use `is` or `is not` instead.

## References

- [Flake8 E711](https://www.flake8rules.com/rules/E711.html)
- [Flake8 E712](https://www.flake8rules.com/rules/E712.html)

## Valid examples

```python
if x: pass
```
```python
if not x: pass
```
```python
x is True
```
```python
x is False
```
```python
x is None
```
```python
x is not None
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
x is True is not y
```
```python
y is None is not x
```
```python
None is y
```
```python
True is x
```
```python
False is x
```
```python
x == 2
```
```python
2 != x
```
```python
1 == True
```
```python
True == 1
```
```python
1 != False
```
```python
"True" == "True"
```
```python
"True" != "False".lower()
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
x != True
```
<p class="rule-example-label">Suggested fix</p>

```python
x is not True
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
x != False
```
<p class="rule-example-label">Suggested fix</p>

```python
x is not False
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
x == False
```
<p class="rule-example-label">Suggested fix</p>

```python
x is False
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
x == None
```
<p class="rule-example-label">Suggested fix</p>

```python
x is None
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
x != None
```
<p class="rule-example-label">Suggested fix</p>

```python
x is not None
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
False == x
```
<p class="rule-example-label">Suggested fix</p>

```python
False is x
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
x is True == y
```
<p class="rule-example-label">Suggested fix</p>

```python
x is True is y
```
```{raw} html
</div>
```
```{raw} html
</details>
```
