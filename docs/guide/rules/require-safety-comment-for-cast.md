---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-require-safety-comment-for-cast)=

# require-safety-comment-for-cast

<p class="rule-metadata">
  <span>Collection: <code>typing</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Require an immediately preceding ``SAFETY:`` justification for every cast.

## Message

This cast has no `SAFETY:` justification. State the invariant immediately before the cast or its containing statement.


## Valid examples

```python
from typing import cast

# SAFETY: validation established that payload is text.
value = cast(str, payload)
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
import typing

value = consume(
    # SAFETY: the producer always emits bytes.
    typing.cast(bytes, payload)
)
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

value = cast(str, payload)
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
from typing import cast

# SAFETY: this belongs to the earlier statement.
prepare()
value = cast(str, payload)
```
```{raw} html
</div>
```
```{raw} html
</details>
```
