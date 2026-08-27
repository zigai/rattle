---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-chained-casts)=

# no-chained-casts

<p class="rule-metadata">
  <span>Collection: <code>typing</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Disallow using one ``typing.cast`` directly as the value of another.

## Message

This cast chain discards type evidence. Keep the original precise type or validate the value once.


## Valid examples

```python
from typing import cast

value = cast(str, payload)
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
def cast(target, value):
    return value

value = cast(str, cast(bytes, payload))
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
from typing import cast

value = cast(str, cast(bytes, payload))
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
import typing

checked = typing.cast
value = checked(str, (checked(bytes, payload)))
```
```{raw} html
</div>
```
```{raw} html
</details>
```
