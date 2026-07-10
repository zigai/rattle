---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-collection-fixit)=

# Fixit

Core lint rules inherited from Fixit.

Enable with:

```toml
enable = ["fixit"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [explicit-frozen-dataclass](../rules/explicit-frozen-dataclass.md) | Dataclass mutability must be explicit. Add `frozen=True` for immutable value objects or `frozen=False` when instances are intentionally mutable. | Any | No |
| [no-named-tuple](../rules/no-named-tuple.md) | NamedTuple can often be replaced with @dataclass, but dataclasses are not tuple-compatible; check callers before converting. | Any | No |
| [no-static-if-condition](../rules/no-static-if-condition.md) | This `if` condition appears constant; verify the logic and remove any temporary debug clause. | Any | No |
| [sorted-attributes](../rules/sorted-attributes.md) | Class assignments under @sorted-attributes are not sorted; sorting them can change right-hand-side side-effect order. | Any | Yes |
| [use-callable-ellipsis](../rules/use-callable-ellipsis.md) | Use Callable[..., T] instead of Callable[[...], T]. | Any | Yes |
| [use-rattle-ignore-comment](../rules/use-rattle-ignore-comment.md) | Use `rattle: ignore[rule-name]`; Rattle does not support `noqa`. | Any | No |
| [use-types-from-typing](../rules/use-types-from-typing.md) | Python 3.8 does not support `{builtin_type}[...]` annotations; use `typing.{correct_type}` instead. | `< 3.9` | Yes |
