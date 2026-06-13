---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-static-if-condition)=

# no-static-if-condition

<p class="rule-metadata">
  <span>Collection: <code>fixit</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Discourages ``if`` conditions which evaluate to a static value (e.g. ``or True``, ``and False``, etc).

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
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
# ew who would this???
def true():
    return False
if true() and else_call():  # True or False
    pass
```
```python
# ew who would this???
if False or some_func():
    pass
```
```python
if [*values]:
    pass
```
```python
if {**mapping}:
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
if True:
    do_something()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
if 1:
    do_something()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
if None:
    do_something()
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
if "":
    do_something()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
if 0.0:
    do_something()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
if -1:
    do_something()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
if b"":
    do_something()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
if ...:
    do_something()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
if [*values, sentinel]:
    do_something()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
if {**mapping, "sentinel": sentinel}:
    do_something()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
if crazy_expression or True:
    do_something()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
if crazy_expression and False:
    do_something()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
if crazy_expression and not True:
    do_something()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
if crazy_expression or not False:
    do_something()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
if crazy_expression or (something() or True):
    do_something()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
if crazy_expression and (something() and (not True)):
    do_something()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
if crazy_expression and (something() and (other_func() and not True)):
    do_something()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
if (crazy_expression and (something() and (not True))) or True:
    do_something()
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
async def some_func() -> none:
    if (await expression()) and False:
        pass
```
```{raw} html
</div>
```
```{raw} html
</details>
```
