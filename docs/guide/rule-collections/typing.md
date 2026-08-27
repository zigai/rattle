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
| [no-any-container-annotations](../rules/no-any-container-annotations.md) | Replace `Any` in this container annotation with concrete element, key, or value types. | Any | No |
| [no-any-type-aliases](../rules/no-any-type-aliases.md) | Do not hide `Any` behind a type alias; use a concrete owner type. | Any | No |
| [no-bare-object-annotations](../rules/no-bare-object-annotations.md) | Replace this bare `object` annotation with a type that describes the value. | Any | No |
| [no-casts-to-never](../rules/no-casts-to-never.md) | Do not cast a value to `Never` or `NoReturn`; prove exhaustiveness through control flow. | Any | No |
| [no-chained-casts](../rules/no-chained-casts.md) | This cast chain discards type evidence. Keep the original precise type or validate the value once. | Any | No |
| [no-known-value-to-any](../rules/no-known-value-to-any.md) | This explicit `Any` annotation discards known type evidence. Keep inference or use a concrete owner contract. | Any | No |
| [no-object-mapping-values](../rules/no-object-mapping-values.md) | Replace this broad `object` mapping value with a concrete value type or parsed owner type. | Any | No |
| [no-widen-then-cast](../rules/no-widen-then-cast.md) | This value was widened and then cast back to a narrower type. Preserve its original type evidence. | Any | No |
| [require-safety-comment-for-cast](../rules/require-safety-comment-for-cast.md) | This cast has no `SAFETY:` justification. State the invariant immediately before the cast or its containing statement. | Any | No |
| [use-callable-ellipsis](../rules/use-callable-ellipsis.md) | Use Callable[..., T] instead of Callable[[...], T]. | Any | Yes |
| [use-types-from-typing](../rules/use-types-from-typing.md) | Python 3.8 does not support `{builtin_type}[...]` annotations; use `typing.{correct_type}` instead. | `< 3.9` | Yes |
