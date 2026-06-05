---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-suite-leading-trailing-blank-lines)=

# no-suite-leading-trailing-blank-lines

<p class="rule-metadata">
  <span>Collection: <code>blank-lines</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Disallow leading/trailing empty lines at suite boundaries.



## Valid examples

```python
def f() -> int:
    value = 1
    return value
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
def f() -> int:
    # comment lines are separators, not blank lines
    value = 1
    return value
```
```python
def f(items: list[int]) -> None:

    def emit() -> None:
        print(items)
```
```python
def f(items: list[int]) -> None:
    for item in items:

        @track(item)
        def emit() -> None:
            print(item)
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
def f() -> int:

    value = 1
    return value
```
<p class="rule-example-label">Suggested fix</p>

```python
def f() -> int:
    value = 1
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
def f(items: list[int]) -> None:


    def emit() -> None:
        print(items)
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(items: list[int]) -> None:

    def emit() -> None:
        print(items)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
def f(items: list[int]) -> None:
    for item in items:


        @track(item)
        def emit() -> None:
            print(item)
```
<p class="rule-example-label">Suggested fix</p>

```python
def f(items: list[int]) -> None:
    for item in items:

        @track(item)
        def emit() -> None:
            print(item)
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
def f() -> int:
    value = 1
    return value
```
<p class="rule-example-label">Suggested fix</p>

```python
def f() -> int:
    value = 1
    return value
```
```{raw} html
</div>
```
```{raw} html
</details>
```
