---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-static-if-condition)=

# NoStaticIfCondition

Discourages ``if`` conditions which evaluate to a static value (e.g. ``or True``, ``and False``, etc).

<p class="rule-metadata">
  <span>Pack: <code>fixit</code></span>
  <span>Module: <code>rattle.rules.fixit.no_static_if_condition</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

## Message

Your if condition appears to evaluate to a static value (e.g. `or True`, `and False`). Please double check this logic and if it is actually temporary debug code.

## Valid examples

```python
if my_func() or not else_func():
    pass
```
```python
if function_call(True):
    pass
```

## Invalid examples

```python
if True:
    do_something()
```
```python
if crazy_expression or True:
    do_something()
```
