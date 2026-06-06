---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-forbidden-import)=

# forbidden-import

<p class="rule-metadata">
  <span>Collection: <code>policy</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Ban imports that cross configured package or module boundaries.

## Message

Do not import across forbidden boundary '{boundary}'.


## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">forbidden_imports</span></td>
      <td>—</td>
      <td><span class="rule-setting-type">list</span></td>
      <td><span class="rule-setting-default rule-setting-default-plain">[]</span></td>
    </tr>
</tbody>
</table>
```

## Valid examples

```python
import services.public_api
```
```python
from services import public_api
```
```python
import services_internal
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
import services.internal
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import services.internal.jobs
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from services import internal
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from services.internal import jobs
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from services.internal import *
```
```{raw} html
</div>
```
