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

Avoid using 'or' in an except block. For example:'except ValueError or TypeError' only catches 'ValueError'. Instead, use parentheses, 'except (ValueError, TypeError)'

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
