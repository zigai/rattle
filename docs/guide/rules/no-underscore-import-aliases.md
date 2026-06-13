---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-underscore-import-aliases)=

# no-underscore-import-aliases

<p class="rule-metadata">
  <span>Collection: <code>policy</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Forbid underscore-prefixed aliases in import statements.

## Message

Import aliases must not start with an underscore.


## Valid examples

```python
import json
```
```python
import json as json_lib
```
```python
from collections import deque as deque_type
```
```python
from module import _private_name
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
import json as _json
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import json as  _json
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import json as	_json
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import json as\
    _json
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from collections import deque as _deque
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
from module import name as __name
```
```{raw} html
</div>
```
```{raw} html
</details>
```
