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
| [no-exception-message-variables](../rules/no-exception-message-variables.md) | Inline exception message strings instead of assigning throwaway variables. | Any | Yes |
| [no-str-exception-translation](../rules/no-str-exception-translation.md) | Use a fixed message when translating an exception, and preserve the cause with `raise ... from exc`. | Any | No |
| [no-underscore-class](../rules/no-underscore-class.md) | Class names must not start with an underscore prefix. | Any | No |
| [public-method-order](../rules/public-method-order.md) | Define public methods before underscore-prefixed helper methods. | Any | No |
