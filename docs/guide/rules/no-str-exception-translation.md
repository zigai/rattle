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

Forbid translated exceptions from reusing a caught exception's rendered message.

## Message

Use a fixed message when translating an exception, and preserve the cause with `raise ... from e`.


## Valid examples

```python
try:
    run()
except ValueError as e:
    raise CommandArgumentError("Invalid resource identifier.") from e
```
```python
message = str(value)
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
try:
    run()
except ValueError as e:
    str = lambda value: "fixed"
    raise RuntimeError(str(e)) from e
```
```python
error = "fixed"

try:
    run()
except ValueError as e:

    def capture() -> None:
        error = e

    raise RuntimeError(str(error)) from e
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
try:
    run()
except ValueError as e:
    raise CommandArgumentError(str(e)) from e
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
<div class="rule-invalid-example">
```
```python
try:
    run()
except ValueError as e:
    raise RuntimeError(message=str(e)) from e
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
try:
    run()
except ValueError as e:
    raise RuntimeError(f"{e}") from e
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
try:
    run()
except ValueError as e:
    raise RuntimeError("{}".format(e)) from e
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
try:
    run()
except ValueError as e:
    raise RuntimeError("%s" % e) from e
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
try:
    run()
except ValueError as e:
    raise RuntimeError("%s" % (e,)) from e
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import builtins

try:
    run()
except ValueError as e:
    raise RuntimeError(builtins.str(e)) from e
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import builtins as builtin_values

try:
    run()
except ValueError as e:
    raise RuntimeError(builtin_values.str(e)) from e
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from builtins import str as stringify

try:
    run()
except ValueError as e:
    raise RuntimeError(stringify(e)) from e
```
```{raw} html
</div>
```
```{raw} html
</details>
```
