---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-suite-leading-trailing-blank-lines)=

# NoSuiteLeadingTrailingBlankLines

Disallow leading/trailing empty lines at suite boundaries.

<p class="rule-metadata">
  <span>Pack: <code>blank_lines</code></span>
  <span>Module: <code>rattle.rules.blank_lines.no_suite_leading_trailing_blank_lines</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>


## Valid examples

```python
def f() -> int:
    value = 1
    return value
```
```python
def f() -> int:
    # comment lines are separators, not blank lines
    value = 1
    return value
```

## Invalid examples

```python
def f() -> int:

    value = 1
    return value

# suggested fix
def f() -> int:
    value = 1
    return value
```
```python
def f(items: list[int]) -> None:


    def emit() -> None:
        print(items)

# suggested fix
def f(items: list[int]) -> None:

    def emit() -> None:
        print(items)
```
