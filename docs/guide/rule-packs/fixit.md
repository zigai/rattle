---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-pack-fixit)=

# Core Fixit rules

Core lint rules inherited from Fixit.

Enable with:

```toml
enable = ["fixit"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [ExplicitFrozenDataclass](../rules/explicit-frozen-dataclass.md) | Dataclass mutability must be explicit. Add `frozen=True` for immutable value objects or `frozen=False` when instances are intentionally mutable. | Any | — |
| [NoNamedTuple](../rules/no-named-tuple.md) | Instead of NamedTuple, consider using the @dataclass decorator from dataclasses instead for simplicity, efficiency and consistency. | Any | ✅ |
| [NoStaticIfCondition](../rules/no-static-if-condition.md) | Your if condition appears to evaluate to a static value (e.g. `or True`, `and False`). Please double check this logic and if it is actually temporary debug code. | Any | — |
| [SortedAttributes](../rules/sorted-attributes.md) | It appears you are using the @sorted-attributes directive and the class variables are unsorted. See the lint autofix suggestion. | Any | ✅ |
| [UseRattleIgnoreComment](../rules/use-rattle-ignore-comment.md) | noqa is deprecated. Use `rattle: ignore[RuleName]` instead. | Any | — |
| [UseTypesFromTyping](../rules/use-types-from-typing.md) | — | `< 3.10` | ✅ |
| [VariadicCallableSyntax](../rules/variadic-callable-syntax.md) | — | Any | ✅ |
