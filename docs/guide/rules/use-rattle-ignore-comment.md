---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-rattle-ignore-comment)=

# use-rattle-ignore-comment

<p class="rule-metadata">
  <span>Collection: <code>fixit</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Use an inline or preceding ``rattle: ignore[...]`` comment to suppress warnings.
Listing rule names prevents unrelated warnings from being suppressed. Rattle does
not recognize ``noqa`` because it may also affect other linters.

## Message

Use `rattle: ignore[rule-name]`; Rattle does not support `noqa`.


## Valid examples

```python
# rattle: ignore[use-f-string]
"%s" % "hi"
```
```python
'ab' 'cd'  # rattle: ignore[use-plus-for-string-concat]
```
```python
fn()  # noqaed by another tool
```
```python
fn()  # See https://example.test/noqa-policy
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
fn() # noqa
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
fn() # NOQA
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
# flake8: noqa
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
fn()  # type: ignore  # noqa
```
```{raw} html
</div>
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
(
 1,
 2,  # noqa
)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
class C:
    # noqa
    ...
```
```{raw} html
</div>
```
```{raw} html
</details>
```
