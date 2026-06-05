---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-blank-line-before-assignment)=

# blank-line-before-assignment

<p class="rule-metadata">
  <span>Collection: <code>blank-lines</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Require separators before assignments that do not continue the local flow.

## Message

Missing blank line before assignment statement that follows a non-assignment statement.


## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">allow_local_helper_capture</span></td>
      <td>Allow local helper assignments that capture values from preceding code.</td>
      <td><span class="rule-setting-type">bool</span></td>
      <td><span class="rule-setting-default rule-setting-default-constant">True</span></td>
    </tr>
<tr>
      <td><span class="rule-setting-name">allow_post_guard_continuation</span></td>
      <td>Allow assignments that continue immediately after a guard statement.</td>
      <td><span class="rule-setting-type">bool</span></td>
      <td><span class="rule-setting-default rule-setting-default-constant">False</span></td>
    </tr>
<tr>
      <td><span class="rule-setting-name">related_use_lookahead</span></td>
      <td>Number of following statements inspected for assignment-related usage.</td>
      <td><span class="rule-setting-type">int</span></td>
      <td><span class="rule-setting-default rule-setting-default-number">2</span></td>
    </tr>
<tr>
      <td><span class="rule-setting-name">short_control_flow_max_statements</span></td>
      <td>Maximum short control-flow size allowed before a following assignment.</td>
      <td><span class="rule-setting-type">int</span></td>
      <td><span class="rule-setting-default rule-setting-default-number">3</span></td>
    </tr>
</tbody>
</table>
```

## Valid examples

```python
def f() -> int:
    value = 1
    other = value + 1
    return other
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
def f() -> int:
    log_start()

    value = compute()
    log_value(value)
    return value
```
```python
def f() -> int:
    total = 0
    total += 1
    return total
```
```python
def f() -> int:
    """Compute value."""
    value = compute()
    return value
```
```python
def f(backend: object, archiver: object, writer: object) -> None:
    if needs_status:
        log_status(backend=backend, archiver=archiver, writer=writer)
        last_status_time = loop.time()
```
```python
def f() -> None:
    if needs_status:
        log_status()
        update_metrics()
        last_status_time = loop.time()
```
```python
def f() -> None:
    if needs_status:
        log_status()
        update_metrics()
        refresh_cache()
        last_status_time = loop.time()
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
def f(output: object) -> None:
    output.write("ok")
    bar = output.bars["task"]
    assert bar.n == 1
```
```python
def f() -> None:
    assert output.exists()
    payload = json.loads(output.read_text())
    assert "themes" in payload
```
```python
def f(name: str | None) -> object:
    configure_logging()
    logger_name = "default" if name is None else name
    return make_logger(logger_name)
```
```python
def f(candidate: object, parser_input: str, style: object) -> object:
    validate(candidate)
    display_value = parser_input or str(candidate)
    if supports_live_interaction():
        highlight(display_value, style)
    else:
        summarize(display_value, style)
    return candidate
```
```python
def f(monkeypatch: object) -> dict[str, object]:
    monkeypatch.setenv("TOKEN", "abc")
    calls: dict[str, object] = {}
    class FakeRepo:
        def __init__(self) -> None:
            calls["created"] = True
    return calls
```
```python
def f(logger: logging.Logger, handler: logging.Handler) -> None:
    logger.addHandler(handler)
    logger.propagate = False
```
```python
def f() -> int:
    log_start()
    value = compute()
    return value
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
def f(values: list[int]) -> int:
    total = 0
    if values:
        total += len(values)
    total += 1
    return total
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(values: list[int]) -> int:
    total = 0
    if values:
        total += len(values)

    total += 1
    return total
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
def f(flag: bool, value: str) -> str:
    if not flag:
        return value
    normalized = value.strip()
    return normalized
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(flag: bool, value: str) -> str:
    if not flag:
        return value

    normalized = value.strip()
    return normalized
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
def f(value: int) -> int:
    if value > 0:
        log_status(value)
        update_metrics(value)
        adjusted = value + 1
        return adjusted

    return value
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(value: int) -> int:
    if value > 0:
        log_status(value)
        update_metrics(value)

        adjusted = value + 1
        return adjusted

    return value
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
def f() -> None:
    if needs_status:
        log_status()
        last_status_time = loop.time()
```
<p class="rule-example-label">Suggested fix</p>

```python
def f() -> None:
    if needs_status:
        log_status()

        last_status_time = loop.time()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
def f(candidate: object) -> object:
    validate(candidate)
    display_value = str(candidate)
    if supports_live_interaction():
        highlight(candidate)
    return candidate
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(candidate: object) -> object:
    validate(candidate)

    display_value = str(candidate)
    if supports_live_interaction():
        highlight(candidate)
    return candidate
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
def f(logger: logging.Logger, handler: logging.Handler) -> None:
    logger.addHandler(handler)

    logger.propagate = False
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(logger: logging.Logger, handler: logging.Handler) -> None:
    logger.addHandler(handler)
    logger.propagate = False
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
def f() -> int:
    log_start()

    value = compute()
    return value
```
<p class="rule-example-label">Suggested fix</p>

```python
def f() -> int:
    log_start()
    value = compute()
    return value
```
```{raw} html
</div>
```
```{raw} html
</details>
```
