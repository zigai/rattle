---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-exception-message-variables)=

# no-exception-message-variables

<p class="rule-metadata">
  <span>Collection: <code>style</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Forbid throwaway local variables used only as exception messages.

## Message

Inline exception message strings instead of assigning throwaway variables.


## Valid examples

```python
msg = "invalid value"
logger.warning(msg)
raise ValueError(msg)
```
```python
msg = "invalid value"
raise ValueError(f"{msg}: {value}")
```
```python
raise ValueError("invalid value")
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
message = build_message()
raise ValueError(message)
```
<p class="rule-example-label">Suggested fix</p>

```python
raise ValueError(build_message())
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
msg = "invalid value"
raise ValueError(msg)
```
<p class="rule-example-label">Suggested fix</p>

```python
raise ValueError("invalid value")
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
message = f"invalid value: {value}"
raise RuntimeError(message) from exc
```
<p class="rule-example-label">Suggested fix</p>

```python
raise RuntimeError(f"invalid value: {value}") from exc
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
detail = "invalid value"
raise CustomError(code=code, detail=detail)
```
<p class="rule-example-label">Suggested fix</p>

```python
raise CustomError(code=code, detail="invalid value")
```
```{raw} html
</div>
```
```{raw} html
</details>
```
