---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-redundant-f-string)=

# NoRedundantFString

Remove redundant f-string without placeholders.

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.no_redundant_fstring</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

## Message

f-string doesn't have placeholders, remove redundant f-string.

## Valid examples

```python
good: str = "good"
```
```python
good: str = f"with_arg{arg}"
```

## Invalid examples

```python
bad: str = f"bad" + "bad"

# suggested fix
bad: str = "bad" + "bad"
```
```python
bad: str = f'bad'

# suggested fix
bad: str = 'bad'
```
