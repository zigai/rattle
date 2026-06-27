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
| [no-static-if-condition](../rules/no-static-if-condition.md) | Your if condition appears to evaluate to a static value (e.g. `or True`, `and False`). Please double check this logic and if it is actually temporary debug code. | Any | No |
| [sorted-attributes](../rules/sorted-attributes.md) | Class assignments under @sorted-attributes are not sorted; sorting them can change right-hand-side side-effect order. | Any | Yes |
| [use-callable-ellipsis](../rules/use-callable-ellipsis.md) | Use Callable[..., T] instead of Callable[[...], T]. | Any | Yes |
| [use-rattle-ignore-comment](../rules/use-rattle-ignore-comment.md) | noqa is deprecated. Use `rattle: ignore[rule-name]` instead. | Any | No |
| [use-types-from-typing](../rules/use-types-from-typing.md) | For Python < 3.9, builtins.{builtin_type} is used as a type annotation but the type system doesn't recognize it as a valid type. Use typing.{correct_type} instead. | `< 3.9` | Yes |
