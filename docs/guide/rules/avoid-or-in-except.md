---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-avoid-or-in-except)=

# AvoidOrInExcept

Discourages use of ``or`` in except clauses. If an except clause needs to catch multiple exceptions,
they must be expressed as a parenthesized tuple, for example:
``except (ValueError, TypeError)``
(https://docs.python.org/3/tutorial/errors.html#handling-exceptions).

When ``or`` is used, only the first operand exception type of the conditional statement will be caught.
For example::

    In [1]: class Exc1(Exception):
        ...:     pass
        ...:

    In [2]: class Exc2(Exception):
        ...:     pass
        ...:

    In [3]: try:
        ...:     raise Exception()
        ...: except Exc1 or Exc2:
        ...:     print("caught!")
        ...:
    ---------------------------------------------------------------------------
    Exception                                 Traceback (most recent call last)
    <ipython-input-3-3340d66a006c> in <module>
        1 try:
    ----> 2     raise Exception()
        3 except Exc1 or Exc2:
        4     print("caught!")
        5

    Exception:

    In [4]: try:
        ...:     raise Exc1()
        ...: except Exc1 or Exc2:
        ...:     print("caught!")
        ...:
        caught!

    In [5]: try:
        ...:     raise Exc2()
        ...: except Exc1 or Exc2:
        ...:     print("caught!")
        ...:
    ---------------------------------------------------------------------------
    Exc2                                      Traceback (most recent call last)
    <ipython-input-5-5d29c1589cc0> in <module>
        1 try:
    ----> 2     raise Exc2()
        3 except Exc1 or Exc2:
        4     print("caught!")
        5

    Exc2:

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.avoid_or_in_except</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

## Message

Avoid using 'or' in an except block. For example:'except ValueError or TypeError' only catches 'ValueError'. Instead, use parentheses, 'except (ValueError, TypeError)'

## Valid examples

```python
try:
    print()
except (ValueError, TypeError) as err:
    pass
```

## Invalid examples

```python
try:
    print()
except ValueError or TypeError:
    pass
```
