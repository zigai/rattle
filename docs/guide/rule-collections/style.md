---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-collection-style)=

# Style

Rules for code style and structure.

Enable with:

```toml
enable = ["style"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [no-annotated-self](../rules/no-annotated-self.md) | Do not annotate self in instance methods. | Any | Yes |
| [public-method-order](../rules/public-method-order.md) | Define public methods before private helpers in behavior classes. | Any | No |
