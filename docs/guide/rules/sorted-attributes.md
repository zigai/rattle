---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-sorted-attributes)=

# sorted-attributes

<p class="rule-metadata">
  <span>Collection: <code>fixit</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

Ever wanted to sort a bunch of class attributes alphabetically?
Well now it's easy! Just add "@sorted-attributes" in the doc string of
a class definition and lint will automatically sort all attributes alphabetically.

Feel free to add other methods and such -- it should only affect class attributes.

## Message

It appears you are using the @sorted-attributes directive and the class variables are unsorted. See the lint autofix suggestion.


## Valid examples

```python
class MyConstants:
    """
    @sorted-attributes
    """
    A = 'zzz123'
    B = 'aaa234'

class MyUnsortedConstants:
    B = 'aaa234'
    A = 'zzz123'
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
class MyConstants:
    """
    @sorted-attributes
    """
    z = side_effect("z")

    def method(self):
        pass

    a = side_effect("a")
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
class MyUnsortedConstants:
    """
    @sorted-attributes
    """
    z = "hehehe"
    B = 'aaa234'
    A = 'zzz123'
    cab = "foo bar"
    Daaa = "banana"

    @classmethod
    def get_foo(cls) -> str:
        return "some random thing"
```
<p class="rule-example-label">Suggested fix</p>

```python
class MyUnsortedConstants:
    """
    @sorted-attributes
    """
    A = 'zzz123'
    B = 'aaa234'
    Daaa = "banana"
    cab = "foo bar"
    z = "hehehe"

    @classmethod
    def get_foo(cls) -> str:
        return "some random thing"
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
class MyUnsortedConstants:
    """
    @sorted-attributes
    """
    z: int = 1
    a: int = 2
```
<p class="rule-example-label">Suggested fix</p>

```python
class MyUnsortedConstants:
    """
    @sorted-attributes
    """
    a: int = 2
    z: int = 1
```
```{raw} html
</div>
```
```{raw} html
</details>
```
