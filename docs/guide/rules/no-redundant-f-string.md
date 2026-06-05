---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-redundant-f-string)=

# NoRedundantFString

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.no_redundant_fstring</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Remove redundant f-string without placeholders.

## Message

f-string doesn't have placeholders, remove redundant f-string.

## Valid examples

```python
good: str = "good"
```
```python
good: str = f"with_arg{arg}"
```
```python
good = "good{arg1}".format(1234)
```
```python
good = "good".format()
```
```python
good = "good" % {}
```
```python
good = "good" % ()
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
good = rf"good	+{bar}"
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
bad: str = f"bad" + "bad"
```
<p class="rule-example-label">Suggested fix</p>

```python
bad: str = "bad" + "bad"
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
bad: str = f'bad'
```
<p class="rule-example-label">Suggested fix</p>

```python
bad: str = 'bad'
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
bad: str = rf'bad	+'
```
<p class="rule-example-label">Suggested fix</p>

```python
bad: str = r'bad	+'
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
bad: str = fr'bad	+'
```
<p class="rule-example-label">Suggested fix</p>

```python
bad: str = r'bad	+'
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
bad: str = f"no args but messing up {{ braces }}"
```
<p class="rule-example-label">Suggested fix</p>

```python
bad: str = "no args but messing up { braces }"
```
```{raw} html
</div>
```
```{raw} html
</details>
```
