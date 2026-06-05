---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-collection-blank-lines)=

# Blank-line rules

Whitespace and statement-separation rules.

Enable with:

```toml
enable = ["blank-lines"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [blank-line-after-control-block](../rules/blank-line-after-control-block.md) | Missing blank line after multiline control-flow block statement. | Any | Yes |
| [blank-line-before-assignment](../rules/blank-line-before-assignment.md) | Missing blank line before assignment statement that follows a non-assignment statement. | Any | Yes |
| [blank-line-before-branch-in-large-suite](../rules/blank-line-before-branch-in-large-suite.md) | Missing blank line before return/raise/break/continue in a large suite. | Any | Yes |
| [block-header-cuddle-relaxed](../rules/block-header-cuddle-relaxed.md) | Illegal cuddle before block header. The preceding setup must directly feed the upcoming block. | Any | Yes |
| [no-suite-leading-trailing-blank-lines](../rules/no-suite-leading-trailing-blank-lines.md) | — | Any | Yes |
