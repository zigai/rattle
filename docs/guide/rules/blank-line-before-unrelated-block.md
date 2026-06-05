---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-blank-line-before-unrelated-block)=

# blank-line-before-unrelated-block

<p class="rule-metadata">
  <span>Collection: <code>blank-lines</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Allow cuddling when the setup remains part of the same control-flow step.

## Message

Illegal cuddle before block header. The preceding setup must directly feed the upcoming block.


## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">allow_setup_before_compact_guard_ladder</span></td>
      <td>Allow setup statements before compact guard-ladder branches.</td>
      <td><span class="rule-setting-type">bool</span></td>
      <td><span class="rule-setting-default rule-setting-default-constant">True</span></td>
    </tr>
<tr>
      <td><span class="rule-setting-name">body_usage_lookahead</span></td>
      <td>Number of following statements inspected for setup-value usage.</td>
      <td><span class="rule-setting-type">int</span></td>
      <td><span class="rule-setting-default rule-setting-default-number">4</span></td>
    </tr>
<tr>
      <td><span class="rule-setting-name">setup_run_lookback</span></td>
      <td>Number of preceding setup statements that may stay attached to a block.</td>
      <td><span class="rule-setting-type">int</span></td>
      <td><span class="rule-setting-default rule-setting-default-number">3</span></td>
    </tr>
</tbody>
</table>
```

## Valid examples

```python
def f(value: int) -> int:
    prepared = value + 1
    if prepared > 0:
        return prepared

    return 0
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
def f(value: int) -> int:
    prepared = value + 1
    if value > 0:
        result = prepared
        return result

    return 0
```
```python
def f(value: int) -> int:
    log_start()
    prepared = value + 1
    if prepared > 0:
        return prepared

    return 0
```
```python
def f(value: int) -> int:
    prepared = value + 1
    not_used = value + 2

    if value > 0:
        return value

    return prepared
```
```python
def f(value: int) -> int:
    """Compute value."""
    if value > 0:
        return value

    return 0
```
```python
def f(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    merged = dict(base)
    for key, value in override.items():
        if key not in merged:
            merged[key] = value
            continue
        merged[key] = value

    return merged
```
```python
def f(directory: str) -> None:
    queue = Queue()
    queue.put(directory)
    while not queue.empty():
        item = queue.get()
        visit(item)
```
```python
def f(shell_name: str) -> list[str]:
    interactive = shell_name == "zsh"
    if shell_name == "zsh":
        return ["-lic"]
    if interactive:
        return ["-ic"]
    return ["-lc"]
```
```python
def f(candidate: object, parser_input: str, style: object) -> object:
    display_value = parser_input or str(candidate)
    if supports_live_interaction():
        highlight(display_value, style)
    else:
        summarize(display_value, style)
    return candidate
```
```python
def f(override_name: str | None) -> str:
    display_name = "guest"
    if override_name is not None:
        display_name = override_name
    return display_name
```
```python
def f(default_value: object) -> dict[str, object]:
    prompt_kwargs: dict[str, object] = {}
    if default_value:
        prompt_kwargs["placeholder"] = str(default_value)
    return prompt_kwargs
```
```python
def f() -> None:
    session = build_session()
    session.refresh()
    if session.is_stale():
        reset_session(session)
        return
    cleanup()
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
    prepared = value + 1
    if value > 0:
        return value

    return 0
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(value: int) -> int:
    prepared = value + 1

    if value > 0:
        return value

    return 0
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
def f(value: int) -> int:
    prepared = value + 1
    log(prepared)
    if prepared > 0:
        return prepared

    return 0
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(value: int) -> int:
    prepared = value + 1
    log(prepared)

    if prepared > 0:
        return prepared

    return 0
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
def f(value: int) -> int:
    prepared = value + 1
    trailing = value + 2
    if prepared > 0:
        return prepared

    return 0
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(value: int) -> int:
    prepared = value + 1
    trailing = value + 2

    if prepared > 0:
        return prepared

    return 0
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
def f(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    merged = dict(base)
    for key, value in override.items():
        log_key(key)
        audit(value)
        publish(key, value)
        notify_team(key)
        merged[key] = value

    return merged
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    merged = dict(base)

    for key, value in override.items():
        log_key(key)
        audit(value)
        publish(key, value)
        notify_team(key)
        merged[key] = value

    return merged
```
```{raw} html
</div>
```
```{raw} html
</details>
```
