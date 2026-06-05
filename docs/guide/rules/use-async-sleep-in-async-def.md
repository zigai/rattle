---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-async-sleep-in-async-def)=

# use-async-sleep-in-async-def

<p class="rule-metadata">
  <span>Collection: <code>fixit-extra</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Detect if asyncio.sleep is used in an async function.

## Message

Use asyncio.sleep in async function

## Valid examples

```python
import time
def func():
    time.sleep(1)
```
```python
from time import sleep
def func():
    sleep(1)
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
from asyncio import sleep
async def func():
    await sleep(1)
```
```python
import asyncio
async def func():
    await asyncio.sleep(1)
```
```python
import time
import asyncio
def func():
    time.sleep(1)
```
```python
import time
import asyncio
async def func():
    await asyncio.sleep(1)
```
```python
import time
import asyncio
async def func():
    fut = asyncio.sleep(1)
    await fut
```
```python
import something
async def func():
    something.sleep(3)
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
import time
async def func():
    time.sleep(1)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from time import sleep
async def func():
    sleep(1)
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
from time import sleep
import asyncio
async def func():
    sleep(2)
    asyncio.sleep(1)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from asyncio import sleep
import time
async def func():
    sleep(2)
    time.sleep(1)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
import time
async def outer():
    def inner():
        pass
    time.sleep(1)
```
```{raw} html
</div>
```
```{raw} html
</details>
```
