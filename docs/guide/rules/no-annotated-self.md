---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-annotated-self)=

# no-annotated-self

<p class="rule-metadata">
  <span>Collection: <code>style</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
<span>Tags: `style`, `typing`</span></p>

Forbid explicit type annotations on instance-method self parameters.

## Message

Do not annotate self in instance methods.


## Valid examples

```python
class A:
    def method(self, value: int) -> int:
        return value
```
```python
def helper(self: object, value: int) -> int:
    return value
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
class A:
    @classmethod
    def build(cls, value: int) -> "A":
        return cls()
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
class A:
    def method(self: "A", value: int) -> int:
        return value
```
<p class="rule-example-label">Suggested fix</p>

```python
class A:
    def method(self, value: int) -> int:
        return value
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
class A:
    async def method(self: "A") -> None:
        return None
```
<p class="rule-example-label">Suggested fix</p>

```python
class A:
    async def method(self) -> None:
        return None
```
```{raw} html
</div>
```
```{raw} html
</details>
```
