---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-blank-line-after-terminal-control-block)=

# blank-line-after-terminal-control-block

<p class="rule-metadata">
  <span>Collection: <code>blank-lines</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Require a blank line after control-flow blocks whose body always exits.

## Message

Add a blank line after this early-exit control-flow block.


## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">allow_compact_guard_ladders</span></td>
      <td>Allow consecutive early-exit branches without extra blank lines.</td>
      <td><span class="rule-setting-type">bool</span></td>
      <td><span class="rule-setting-default rule-setting-default-constant">True</span></td>
    </tr>
</tbody>
</table>
```

## Valid examples

```python
def normalize(value: str | None) -> str:
    if value is None:
        return ""

    cleaned = value.strip()
    return cleaned
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
def shell_args(shell_name: str, interactive: bool) -> list[str]:
    if shell_name == "zsh":
        return ["-lic"]
    if interactive:
        return ["-ic"]
    return ["-lc"]
```
```python
def consume(name: str) -> str:
    parts: list[str] = []
    index = 0
    while index < len(name):
        ch = name[index]
        if ch in {"'", '"'}:
            end = _consume_quoted_segment(name, index)
            parts.append(name[index:end])
            index = end
            continue

        parts.append(ch)
        index += 1

    return "".join(parts)
```
```python
def collect(values: list[int]) -> list[int]:
    result: list[int] = []
    for value in values:
        if value < 0:
            continue

        result.append(value)

    return result
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
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
def normalize(value: str | None) -> str:
    if value is None:
        return ""
    cleaned = value.strip()
    return cleaned
```
<p class="rule-example-label">Suggested fix</p>

```python
def normalize(value: str | None) -> str:
    if value is None:
        return ""

    cleaned = value.strip()
    return cleaned
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
def collect(values: list[int]) -> list[int]:
    result: list[int] = []
    for value in values:
        if value < 0:
            continue
        result.append(value)

    return result
```
<p class="rule-example-label">Suggested fix</p>

```python
def collect(values: list[int]) -> list[int]:
    result: list[int] = []
    for value in values:
        if value < 0:
            continue

        result.append(value)

    return result
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
def parse(text: str) -> object:
    try:
        return json.loads(text)
    except ValueError:
        pass
    parsed = tomllib.loads(text)
    return parsed
```
<p class="rule-example-label">Suggested fix</p>

```python
def parse(text: str) -> object:
    try:
        return json.loads(text)
    except ValueError:
        pass

    parsed = tomllib.loads(text)
    return parsed
```
```{raw} html
</div>
```
```{raw} html
</details>
```
