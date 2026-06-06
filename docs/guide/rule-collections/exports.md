---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-collection-exports)=

# Exports

Rules for explicit module export surfaces.

Enable with:

```toml
enable = ["exports"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [module-all-at-bottom](../rules/module-all-at-bottom.md) | Define module __all__ at the bottom of the file. | Any | Yes |
| [no-underscore-all-exports](../rules/no-underscore-all-exports.md) | Do not export underscore-prefixed symbols in __all__. Either remove them from __all__ or rename them to be public. | Any | No |
