---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-relative-imports)=

# no-relative-imports

<p class="rule-metadata">
  <span>Collection: <code>policy</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Require absolute imports instead of package-relative imports.

## Message

Use absolute imports instead of relative imports.


## Valid examples

```python
from package.subpackage.types import ItemType
```
```python
import package.subpackage.types
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
from .types import ItemType
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from	.types import ItemType
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from ..utilities import create_page
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from . import helpers
```
```{raw} html
</div>
```
