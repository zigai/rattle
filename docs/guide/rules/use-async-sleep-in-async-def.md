---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-async-sleep-in-async-def)=

# UseAsyncSleepInAsyncDef

Detect if asyncio.sleep is used in an async function.

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.use_async_sleep_in_async_def</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

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

## Invalid examples

```python
import time
async def func():
    time.sleep(1)
```
```python
from time import sleep
async def func():
    sleep(1)
```
