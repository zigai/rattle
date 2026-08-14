---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-collection-modernization)=

# Modernization

Rules for safer, clearer Python constructs.

Enable with:

```toml
enable = ["modernization"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [explicit-frozen-dataclass](../rules/explicit-frozen-dataclass.md) | Dataclass mutability must be explicit. Add `frozen=True` for immutable value objects or `frozen=False` when instances are intentionally mutable. | Any | No |
| [no-named-tuple](../rules/no-named-tuple.md) | NamedTuple can often be replaced with @dataclass, but dataclasses are not tuple-compatible; check callers before converting. | Any | No |
| [no-static-if-condition](../rules/no-static-if-condition.md) | This `if` condition appears constant; verify the logic and remove any temporary debug clause. | Any | No |
| [use-rattle-ignore-comment](../rules/use-rattle-ignore-comment.md) | Use `rattle: ignore[rule-name]`; Rattle does not support `noqa`. | Any | No |
