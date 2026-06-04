---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-deprecated-a-b-c-import)=

# DeprecatedABCImport

Checks for the use of the deprecated collections ABC import. Since python 3.3,
the Collections Abstract Base Classes (ABC) have been moved to `collections.abc`.
These ABCs are import errors starting in Python 3.10.

<p class="rule-metadata">
  <span>Pack: <code>fixit_extra</code></span>
  <span>Module: <code>rattle.rules.fixit_extra.deprecated_abc_import</code></span>
  <span>Autofix: Yes</span>
  <span>Python: `>= 3.3`</span>
</p>

## Message

ABCs must be imported from collections.abc

## Valid examples

```python
from collections.abc import Container
```
```python
from collections.abc import Container, Hashable
```

## Invalid examples

```python
from collections import Container

# suggested fix
from collections.abc import Container
```
```python
from collections import Container, Hashable

# suggested fix
from collections.abc import Container, Hashable
```
