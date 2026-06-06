---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-collection-reliability)=

# Reliability

Rules for APIs that are easy to misuse in production code.

Enable with:

```toml
enable = ["reliability"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [no-unsafe-tempfile-factories](../rules/no-unsafe-tempfile-factories.md) | Use tempfile context managers instead of mkstemp or mkdtemp. | Any | No |
