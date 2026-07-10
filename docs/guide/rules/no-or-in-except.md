---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-no-or-in-except)=

# no-or-in-except

<p class="rule-metadata">
  <span>Collection: <code>fixit-extra</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Require tuples instead of or-expressions when catching multiple exception types.

## Message

Use `except (ValueError, TypeError):`; `except ValueError or TypeError:` catches only `ValueError`.

## References

- [Python exception handling](https://docs.python.org/3/tutorial/errors.html#handling-exceptions)

## Valid examples

```python
try:
    print()
except (ValueError, TypeError) as err:
    pass
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
try:
    print()
except ValueError or TypeError:
    pass
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
try:
    print()
except ValueError:
    pass
except TypeError or OSError:
    pass
```
```{raw} html
</div>
```
```{raw} html
</details>
```
