---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-forbidden-call)=

# forbidden-call

<p class="rule-metadata">
  <span>Collection: <code>policy</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Ban calls to configured functions, constructors, and helper APIs.

## Message

Do not call forbidden callable '{symbol}'.


## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">forbidden_calls</span></td>
      <td>—</td>
      <td><span class="rule-setting-type">list</span></td>
      <td><span class="rule-setting-default rule-setting-default-plain">[]</span></td>
    </tr>
</tbody>
</table>
```

## Valid examples

```python
import os

delete = os.remove

def cleanup(delete):
    delete("path")
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
import os

delete = os.remove
remove_file = delete

def remove_file(path):
    return path

remove_file("path")
```
```python
import os

delete = os.remove

def cleanup():
    delete = fake_delete
    delete("path")
```
```python
from os import *

def cleanup(remove):
    remove("path")
```
```python
import os

delete = os.remove

def delete(path):
    return path

delete("path")
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
import os

delete = os.remove

delete("path")
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
import os

delete = os.remove

def cleanup():
    delete = fake_delete
    delete("path")

delete("path")
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import os

def cleanup():
    delete = os.remove
    delete("path")
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from os import *

remove("path")
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import os

delete = os.remove
remove_file = delete
remove_file("path")
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import os

delete = remove_file = os.remove
remove_file("path")
```
```{raw} html
</div>
```
```{raw} html
</details>
```
