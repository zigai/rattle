---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-fstring)=

# UseFstring

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.use_fstring</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

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

## Message

Do not use printf style formatting or .format(). Use f-string instead to be more readable and efficient. See https://www.python.org/dev/peps/pep-0498/

## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">simple_expression_max_length</span></td>
      <td><span class="rule-setting-type">int</span></td>
      <td><span class="rule-setting-default rule-setting-default-number">30</span></td>
    </tr>
</tbody>
</table>
```

## Valid examples

```python
somebody='you'; f"Hey, {somebody}."
```
```python
"hey"
```
```python
"hey" + "there"
```
```python
b"a type %s" % var
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
"Hey, {somebody}.".format(somebody="you")
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
"%s" % "hi"
```
<p class="rule-example-label">Suggested fix</p>

```python
f"{'hi'}"
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
"a name: %s" % name
```
<p class="rule-example-label">Suggested fix</p>

```python
f"a name: {name}"
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
"an attribute %s ." % obj.attr
```
<p class="rule-example-label">Suggested fix</p>

```python
f"an attribute {obj.attr} ."
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
r"raw string value=%s" % val
```
<p class="rule-example-label">Suggested fix</p>

```python
fr"raw string value={val}"
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
"{%s}" % val
```
<p class="rule-example-label">Suggested fix</p>

```python
f"{{{val}}}"
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
"{%s" % val
```
<p class="rule-example-label">Suggested fix</p>

```python
f"{{{val}"
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
"The type of var: %s" % type(var)
```
<p class="rule-example-label">Suggested fix</p>

```python
f"The type of var: {type(var)}"
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
"%s" % obj.this_is_a_very_long_expression(parameter)["a_very_long_key"]
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
"%s" % abcdefghijklmnopqrstuvwxyz1234567890
```
<p class="rule-example-label">Suggested fix</p>

```python
f"{abcdefghijklmnopqrstuvwxyz1234567890}"
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
"type of var: %s, value of var: %s" % (type(var), var)
```
<p class="rule-example-label">Suggested fix</p>

```python
f"type of var: {type(var)}, value of var: {var}"
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
'%s" double quote is used' % var
```
<p class="rule-example-label">Suggested fix</p>

```python
f'{var}" double quote is used'
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
"var1: %s, var2: %s, var3: %s, var4: %s" % (class_object.attribute, dict_lookup["some_key"], some_module.some_function(), var4)
```
<p class="rule-example-label">Suggested fix</p>

```python
f"var1: {class_object.attribute}, var2: {dict_lookup['some_key']}, var3: {some_module.some_function()}, var4: {var4}"
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
"a list: %s" % " ".join(var)
```
<p class="rule-example-label">Suggested fix</p>

```python
f"a list: {' '.join(var)}"
```
```{raw} html
</div>
```
```{raw} html
</details>
```
