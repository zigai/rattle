---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-blank-line-after-control-block)=

# blank-line-after-control-block

<p class="rule-metadata">
  <span>Collection: <code>blank-lines</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Require separation after multiline control-flow block statements.

## Message

Missing blank line after multiline control-flow block statement.


## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">allow_compact_guard_ladders</span></td>
      <td>Allow compact guard-ladder control-flow blocks without an extra blank line.</td>
      <td><span class="rule-setting-type">bool</span></td>
      <td><span class="rule-setting-default rule-setting-default-constant">True</span></td>
    </tr>
<tr>
      <td><span class="rule-setting-name">allow_pytest_raises_clusters</span></td>
      <td>Allow adjacent pytest.raises blocks that form one test cluster.</td>
      <td><span class="rule-setting-type">bool</span></td>
      <td><span class="rule-setting-default rule-setting-default-constant">True</span></td>
    </tr>
<tr>
      <td><span class="rule-setting-name">allow_with_immediate_inspection</span></td>
      <td>Allow a with block followed immediately by inspection of its bound value.</td>
      <td><span class="rule-setting-type">bool</span></td>
      <td><span class="rule-setting-default rule-setting-default-constant">True</span></td>
    </tr>
<tr>
      <td><span class="rule-setting-name">related_use_lookahead</span></td>
      <td>Number of following statements inspected for related value usage.</td>
      <td><span class="rule-setting-type">int</span></td>
      <td><span class="rule-setting-default rule-setting-default-number">2</span></td>
    </tr>
</tbody>
</table>
```

## Valid examples

```python
def f(value: int) -> int:
    if value > 0:
        value += 1

    return value
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
def f(value: int) -> int:
    if value > 0:
        value += 1
    # comment separator
    return value
```
```python
def f(value: int) -> int:
    if value > 0: return value
    return 0
```
```python
def load_config(text: str, format_name: str) -> object:
    if format_name == "json":
        return json.loads(text)
    if format_name == "toml":
        return tomllib.loads(text)
    if format_name == "yaml":
        return _load_yaml_text(text)

    raise ValueError(format_name)
```
```python
def normalize(parts: list[str], values: list[str]) -> None:
    for part in values:
        if part == "..":
            parts.pop()
            continue
        parts.append(part)
```
```python
def render(parser: object, capsys: object) -> object:
    try:
        parser.run()
    except SystemExit:
        pass
    out = capsys.readouterr()
    return out
```
```python
def f() -> None:
    with pytest.raises(ValueError):
        parse("x")
    with pytest.raises(TypeError):
        parse(3)
```
```python
def f(path: str) -> None:
    with open(path) as handle:
        content = handle.read()
    assert content
```
```python
def f(width: int | None, columns: list[str]) -> list[str]:
    if width is not None:
        template = f"{width:02d}"
        columns.append(template)
    columns.append(template if width is not None else "default")
    return columns
```
```python
def f(flag: bool, label: str) -> str:
    if not flag:
        return label
    cleaned = label.strip()
    return cleaned
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
def f(primary: str | None, fallback: str | None) -> str:
    if primary is not None:
        return primary
    if fallback is not None:
        return fallback

    return "guest"
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
    if value > 0:
        value += 1
    return value
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(value: int) -> int:
    if value > 0:
        value += 1

    return value
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
    for value in values:
        total += value
    return total
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(values: list[int]) -> int:
    total = 0
    for value in values:
        total += value

    return total
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
def f(value: int, other: int) -> int:
    if value > 0:
        log(value)
        audit(value)
        return value
    if other > 0:
        return other
    return 0
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(value: int, other: int) -> int:
    if value > 0:
        log(value)
        audit(value)
        return value
    if other > 0:
        return other

    return 0
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
def f(flag: bool, label: str) -> str:
    if not flag:
        return label
    return label.strip()
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(flag: bool, label: str) -> str:
    if not flag:
        return label

    return label.strip()
```
```{raw} html
</div>
```
```{raw} html
</details>
```
