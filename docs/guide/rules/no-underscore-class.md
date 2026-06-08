---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-underscore-class)=

# no-underscore-class

<p class="rule-metadata">
  <span>Collection: <code>style</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Forbid underscore-prefixed class names.

## Message

Class names must not start with an underscore prefix.


## Valid examples

```python
class MyClass: ...
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
class _Internal: ...
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
class	_Internal: ...
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
class __Private: ...
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
class _MyClass: ...
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
class _ASTVisitor: ...
```
```{raw} html
</div>
```
