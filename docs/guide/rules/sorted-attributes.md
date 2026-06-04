---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-sorted-attributes)=

# SortedAttributes

Ever wanted to sort a bunch of class attributes alphabetically?
Well now it's easy! Just add "@sorted-attributes" in the doc string of
a class definition and lint will automatically sort all attributes alphabetically.

Feel free to add other methods and such -- it should only affect class attributes.

<p class="rule-metadata">
  <span>Pack: <code>fixit</code></span>
  <span>Module: <code>rattle.rules.fixit.sorted_attributes_rule</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

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

## Invalid examples

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

# suggested fix
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
