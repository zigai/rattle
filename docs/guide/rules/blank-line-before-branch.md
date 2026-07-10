---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-blank-line-before-branch)=

# blank-line-before-branch

<p class="rule-metadata">
  <span>Collection: <code>blank-lines</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Require a blank line before branch statements in larger code blocks.

## Message

Add a blank line before this branch statement in a larger code block.


## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">allow_guard_ladder_final_branch</span></td>
      <td>Allow the final branch in a consecutive sequence of early-exit branches to remain unseparated.</td>
      <td><span class="rule-setting-type">bool</span></td>
      <td><span class="rule-setting-default rule-setting-default-constant">True</span></td>
    </tr>
<tr>
      <td><span class="rule-setting-name">allow_related_return_tails</span></td>
      <td>Allow compact returns that immediately return a just-created value.</td>
      <td><span class="rule-setting-type">bool</span></td>
      <td><span class="rule-setting-default rule-setting-default-constant">True</span></td>
    </tr>
<tr>
      <td><span class="rule-setting-name">compact_tail_max_statements</span></td>
      <td>Maximum number of statements allowed to remain grouped with a final branch statement.</td>
      <td><span class="rule-setting-type">int</span></td>
      <td><span class="rule-setting-default rule-setting-default-number">2</span></td>
    </tr>
<tr>
      <td><span class="rule-setting-name">max_suite_non_empty_lines</span></td>
      <td>Maximum number of non-empty lines allowed in a block before branch statements require a preceding blank line.</td>
      <td><span class="rule-setting-type">int</span></td>
      <td><span class="rule-setting-default rule-setting-default-number">2</span></td>
    </tr>
</tbody>
</table>
```

## Valid examples

```python
def f(value: int) -> int:
    x = value + 1
    y = x + 1

    return y
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
def f(value: int) -> int:
    x = value + 1
    return x
```
```python
def f(parts: list[str]) -> dict[str, int]:
    cleaned = [part.strip() for part in parts]
    joined = ",".join(cleaned)
    payload: dict[str, int] = {"count": len(cleaned), "width": len(joined)}
    return payload
```
```python
def f(value: int) -> int:
    x = value + 1
    y = x + 1
    z = y + 1
    # comment separator
    return z
```
```python
def f() -> int:
    """Return constant."""
    return 1
    value = 2
```
<p class="rule-example-label">Options</p>

```toml
max_suite_non_empty_lines = 3
```
```python
def f(value: int) -> int:
    x = value + 1
    y = x + 1
    return y
```
```python
async def f() -> None:
    try:
        work()
    except Exception:
        cleanup_a()
        cleanup_b()
        await cleanup_c()
        collector_id = None
        raise
```
```python
async def f() -> None:
    try:
        work()
    except Exception:
        cleanup()
        state = None
        log_error()
        raise
```
```python
async def f() -> None:
    try:
        work()
    finally:
        cleanup()
        log_teardown()
        return
```
```python
def f(created_at: object) -> object:
    payload = {"created_at": created_at}
    return ArchivedPost(created_at=created_at, payload=payload)
```
```python
def f(shell_name: str, interactive: bool) -> list[str]:
    if shell_name == "zsh":
        return ["-lic"]
    if interactive:
        return ["-ic"]
    return ["-lc"]
```
```python
def f(values: list[int]) -> int:
    total = 0
    for value in values:
        total += value
    return total
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
def f(value: int) -> int:
    x = value + 1
    y = x + 1
    z = y + 1
    return z
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(value: int) -> int:
    x = value + 1
    y = x + 1
    z = y + 1

    return z
```
```{raw} html
</div>
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
def f(values: list[int]) -> int:
    total = 0
    message = str(total)
    flag = bool(message)
    raise RuntimeError("boom")
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(values: list[int]) -> int:
    total = 0
    message = str(total)
    flag = bool(message)

    raise RuntimeError("boom")
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
<p class="rule-example-label">Options</p>

```toml
allow_related_return_tails = false
max_suite_non_empty_lines = 1
```
```python
def f(value: int) -> int:
    x = value + 1
    return x
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(value: int) -> int:
    x = value + 1

    return x
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
def f(parts: list[str]) -> dict[str, int]:
    cleaned = [part.strip() for part in parts]
    joined = ",".join(cleaned)
    payload: dict[str, int] = {"count": len(cleaned), "width": len(joined)}

    return payload
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(parts: list[str]) -> dict[str, int]:
    cleaned = [part.strip() for part in parts]
    joined = ",".join(cleaned)
    payload: dict[str, int] = {"count": len(cleaned), "width": len(joined)}
    return payload
```
```{raw} html
</div>
```
```{raw} html
</details>
```
