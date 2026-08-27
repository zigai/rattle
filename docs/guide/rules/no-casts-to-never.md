---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-casts-to-never)=

# no-casts-to-never

<p class="rule-metadata">
  <span>Collection: <code>typing</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Disallow casts whose target is ``Never`` or ``NoReturn``.

## Message

Do not cast a value to `Never` or `NoReturn`; prove exhaustiveness through control flow.


## Valid examples

```python
from typing import cast

value = cast(str, payload)
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
from typing import cast

Never = str
value = cast(Never, payload)
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
from typing import Never, cast

value = cast(Never, payload)
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
import typing as t
from typing import cast

Bottom = t.NoReturn
value = cast("Bottom", payload)
```
```{raw} html
</div>
```
```{raw} html
</details>
```
