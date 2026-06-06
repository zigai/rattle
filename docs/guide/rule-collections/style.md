---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-collection-style)=

# Style

Opinionated style rules that are not inherited from Fixit.

Enable with:

```toml
enable = ["style"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [no-annotated-self](../rules/no-annotated-self.md) | Do not annotate self in instance methods. | Any | Yes |
| [public-method-order](../rules/public-method-order.md) | Define public methods before private helpers in behavior classes. | Any | No |
