---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-collapse-isinstance-checks)=

# CollapseIsinstanceChecks

The built-in ``isinstance`` function, instead of a single type,
can take a tuple of types and check whether given target suits
any of them. Rather than chaining multiple ``isinstance`` calls
with a boolean-or operation, a single ``isinstance`` call where
the second argument is a tuple of all types can be used.

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.chained_instance_check</code></span>
  <span>Autofix: Yes</span>
  <span>Python: Any</span>
</p>

## Message

Multiple isinstance calls with the same target but different types can be collapsed into a single call with a tuple of types.

## Valid examples

```python
foo() or foo()
```
```python
foo(x, y) or foo(x, z)
```

## Invalid examples

```python
isinstance(x, y) or isinstance(x, z)

# suggested fix
isinstance(x, (y, z))
```
```python
isinstance(x, y) or isinstance(x, z) or isinstance(x, q)

# suggested fix
isinstance(x, (y, z, q))
```
