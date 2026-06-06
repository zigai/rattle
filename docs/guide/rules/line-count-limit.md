---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-line-count-limit)=

# line-count-limit

<p class="rule-metadata">
  <span>Collection: <code>policy</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Limit file, function, and method length with optional path-specific settings.

## Message

{target} has {actual_lines} lines, exceeding the configured limit of {max_lines}.


## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">glob_limits</span></td>
      <td>Glob-specific limit settings keyed by path glob. More specific matching globs override less specific matching globs.</td>
      <td><span class="rule-setting-type">dict</span></td>
      <td><span class="rule-setting-default rule-setting-default-plain">{}</span></td>
    </tr>
<tr>
      <td><span class="rule-setting-name">max_file_lines</span></td>
      <td>Maximum lines allowed in a file. Set to 0 to disable.</td>
      <td><span class="rule-setting-type">int</span></td>
      <td><span class="rule-setting-default rule-setting-default-number">0</span></td>
    </tr>
<tr>
      <td><span class="rule-setting-name">max_function_lines</span></td>
      <td>Maximum lines allowed in top-level functions. Set to 0 to disable.</td>
      <td><span class="rule-setting-type">int</span></td>
      <td><span class="rule-setting-default rule-setting-default-number">0</span></td>
    </tr>
<tr>
      <td><span class="rule-setting-name">max_method_lines</span></td>
      <td>Maximum lines allowed in methods. Set to 0 to disable.</td>
      <td><span class="rule-setting-type">int</span></td>
      <td><span class="rule-setting-default rule-setting-default-number">0</span></td>
    </tr>
<tr>
      <td><span class="rule-setting-name">per_file_limits</span></td>
      <td>Exact per-file limit settings keyed by repo-relative path. These override base settings and glob_limits.</td>
      <td><span class="rule-setting-type">dict</span></td>
      <td><span class="rule-setting-default rule-setting-default-plain">{}</span></td>
    </tr>
</tbody>
</table>
```

## Valid examples

```python
def small() -> None:
    pass
```
```python
class Service:
    def small(self) -> None:
        pass
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
def large() -> None:
    pass

    pass
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
def oversized() -> None:
    first()
    second()
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
class Service:
    def oversized(self) -> None:
        first()
        second()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
one()
two()
three()
```
```{raw} html
</div>
```
```{raw} html
</details>
```
