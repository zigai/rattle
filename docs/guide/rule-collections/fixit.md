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
| [no-named-tuple](../rules/no-named-tuple.md) | Instead of NamedTuple, consider using the @dataclass decorator from dataclasses instead for simplicity, efficiency and consistency. | Any | Yes |
| [no-static-if-condition](../rules/no-static-if-condition.md) | Your if condition appears to evaluate to a static value (e.g. `or True`, `and False`). Please double check this logic and if it is actually temporary debug code. | Any | No |
| [sorted-attributes](../rules/sorted-attributes.md) | It appears you are using the @sorted-attributes directive and the class variables are unsorted. See the lint autofix suggestion. | Any | Yes |
| [use-callable-ellipsis](../rules/use-callable-ellipsis.md) | Use Callable[..., T] instead of Callable[[...], T]. | Any | Yes |
| [use-rattle-ignore-comment](../rules/use-rattle-ignore-comment.md) | noqa is deprecated. Use `rattle: ignore[rule-name]` instead. | Any | No |
| [use-types-from-typing](../rules/use-types-from-typing.md) | You are using builtins.{builtin_type} as a type annotation but the type system doesn't recognize it as a valid type. Use typing.{correct_type} instead. | `< 3.10` | Yes |
