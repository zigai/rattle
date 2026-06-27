---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-f-string)=

# use-f-string

<p class="rule-metadata">
  <span>Collection: <code>fixit-extra</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Prefer f-strings over percent formatting and str.format calls.

## Message

Do not use printf style formatting or .format(). Use f-string instead to be more readable and efficient.

## References

- [PEP 498](https://www.python.org/dev/peps/pep-0498/)

## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">simple_expression_max_length</span></td>
      <td>Maximum expression length to autofix inline in an f-string.</td>
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
```python
u"plain unicode string"
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
f"{'hi'!s}"
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
f"a name: {name!s}"
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
u"%s" % name
```
<p class="rule-example-label">Suggested fix</p>

```python
f"{name!s}"
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
"an attribute %s ." % obj.attr
```
<p class="rule-example-label">Suggested fix</p>

```python
f"an attribute {obj.attr!s} ."
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
fr"raw string value={val!s}"
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
f"{{{val!s}}}"
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
f"{{{val!s}"
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
f"The type of var: {type(var)!s}"
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
<p class="rule-example-label">Options</p>

```toml
simple_expression_max_length = 100
```
```python
"%s" % abcdefghijklmnopqrstuvwxyz1234567890
```
<p class="rule-example-label">Suggested fix</p>

```python
f"{abcdefghijklmnopqrstuvwxyz1234567890!s}"
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
f"type of var: {type(var)!s}, value of var: {var!s}"
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
f'{var!s}" double quote is used'
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
f"var1: {class_object.attribute!s}, var2: {dict_lookup['some_key']!s}, var3: {some_module.some_function()!s}, var4: {var4!s}"
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
"a list: %s" % " ".join(var)
```
<p class="rule-example-label">Suggested fix</p>

```python
f"a list: {' '.join(var)!s}"
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
"%s" % (first, second)
```
```{raw} html
</div>
```
```{raw} html
</details>
```
