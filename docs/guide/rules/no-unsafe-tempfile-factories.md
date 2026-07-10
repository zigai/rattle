---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-unsafe-tempfile-factories)=

# no-unsafe-tempfile-factories

<p class="rule-metadata">
  <span>Collection: <code>policy</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Require tempfile context managers instead of unmanaged mkstemp or mkdtemp calls.

## Message

Use tempfile context managers instead of mkstemp or mkdtemp.


## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">excluded_path_parts</span></td>
      <td>Path components in which this rule is disabled.</td>
      <td><span class="rule-setting-type">list</span></td>
      <td><span class="rule-setting-default rule-setting-default-plain">[&#x27;tests&#x27;, &#x27;benchmarks&#x27;]</span></td>
    </tr>
</tbody>
</table>
```

## Valid examples

```python
import tempfile

with tempfile.TemporaryDirectory() as path:
    use(path)
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
from tempfile import NamedTemporaryFile

with NamedTemporaryFile() as file:
    use(file.name)
```
```python
from tempfile import mkstemp

factory().mkstemp()
```
```python
class tempfile:
    @staticmethod
    def mkstemp():
        pass

tempfile.mkstemp()
```
```python
import tempfile

tempfile = fake
tempfile.mkstemp()
```
```python
import tempfile

def write_temp(tempfile):
    tempfile.mkstemp()
```
```python
from tempfile import mkstemp

def write_temp(mkstemp):
    mkstemp()
```
```python
from tempfile import *

def write_temp(mkstemp):
    mkstemp()
```
```python
import tempfile

make_temp = tempfile.mkstemp

def write_temp(make_temp):
    make_temp()
```
```python
import tempfile

make_temp = tempfile.mkstemp

def make_temp():
    pass

make_temp()
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
import tempfile

fd, path = tempfile.mkstemp()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from tempfile import mkdtemp as make_temp_dir

path = make_temp_dir()
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
from tempfile import *

fd, path = mkstemp()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from tempfile import mkstemp

def write_temp():
    mkstemp = factory()
    mkstemp()

fd, path = mkstemp()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import tempfile

make_temp = tempfile.mkstemp
fd, path = make_temp()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from tempfile import mkdtemp

make_temp_dir = mkdtemp
path = make_temp_dir()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from tempfile import mkdtemp

make_temp_dir = other_make_temp_dir = mkdtemp
path = other_make_temp_dir()
```
```{raw} html
</div>
```
```{raw} html
</details>
```
