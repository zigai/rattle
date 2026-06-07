---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-str-exception-translation)=

# no-str-exception-translation

<p class="rule-metadata">
  <span>Collection: <code>style</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Forbid translating exceptions with str(exc) messages that discard typed context.

## Message

Do not translate exceptions by passing str(exc); use a stable message and chain the cause.


## Valid examples

```python
try:
    run()
except ValueError as exc:
    raise CommandArgumentError("Invalid resource identifier.") from exc
```
```python
message = str(value)
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
try:
    run()
except ValueError as exc:
    raise CommandArgumentError(str(exc)) from exc
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
try:
    run()
except ValueError as error:
    raise RuntimeError(str(error)) from error
```
```{raw} html
</div>
```
```{raw} html
</details>
```
