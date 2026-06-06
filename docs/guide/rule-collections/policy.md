---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-collection-policy)=

# Policy

Configurable policy rules for architecture and naming boundaries.

Enable with:

```toml
enable = ["policy"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [forbidden-call](../rules/forbidden-call.md) | Do not call forbidden callable '{symbol}'. | Any | No |
| [forbidden-import](../rules/forbidden-import.md) | Do not import across forbidden boundary '{boundary}'. | Any | No |
| [forbidden-name](../rules/forbidden-name.md) | Do not use forbidden {kind} name '{name}'. | Any | No |
| [line-count-limit](../rules/line-count-limit.md) | {target} has {actual_lines} lines, exceeding the configured limit of {max_lines}. | Any | No |
| [no-unsafe-tempfile-factories](../rules/no-unsafe-tempfile-factories.md) | Use tempfile context managers instead of mkstemp or mkdtemp. | Any | No |
