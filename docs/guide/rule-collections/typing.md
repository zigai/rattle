---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-collection-typing)=

# Typing

Rules for type annotations and modern typing syntax.

Enable with:

```toml
enable = ["typing"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [no-bare-object-annotations](../rules/no-bare-object-annotations.md) | Replace this bare `object` annotation with a type that describes the value. | Any | No |
| [use-callable-ellipsis](../rules/use-callable-ellipsis.md) | Use Callable[..., T] instead of Callable[[...], T]. | Any | Yes |
| [use-types-from-typing](../rules/use-types-from-typing.md) | Python 3.8 does not support `{builtin_type}[...]` annotations; use `typing.{correct_type}` instead. | `< 3.9` | Yes |
