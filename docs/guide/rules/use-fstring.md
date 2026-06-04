---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-fstring)=

# UseFstring

Encourages the use of f-string instead of %-formatting or .format() for high code quality and efficiency.

Following two cases not covered:

1. arguments length greater than 30 characters: for better readability reason
    For example:

    1: this is the answer: %d" % (a_long_function_call() + b_another_long_function_call())
    2: f"this is the answer: {a_long_function_call() + b_another_long_function_call()}"
    3: result = a_long_function_call() + b_another_long_function_call()
    f"this is the answer: {result}"

    Line 1 is more readable than line 2. Ideally, we'd like developers to manually fix this case to line 3

2. only %s placeholders are linted against for now. We leave it as future work to support other placeholders.
    For example, %d raises TypeError for non-numeric objects, whereas f"{x:d}" raises ValueError.
    This discrepancy in the type of exception raised could potentially break the logic in the code where the exception is handled

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.use_fstring</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

## Message

Do not use printf style formatting or .format(). Use f-string instead to be more readable and efficient. See https://www.python.org/dev/peps/pep-0498/

## Settings

| Setting | Type | Default |
| --- | --- | --- |
| `simple_expression_max_length` | `int` | `30` |

## Valid examples

```python
somebody='you'; f"Hey, {somebody}."
```
```python
"hey"
```

## Invalid examples

```python
"Hey, {somebody}.".format(somebody="you")
```
```python
"%s" % "hi"

# suggested fix
f"{'hi'}"
```
