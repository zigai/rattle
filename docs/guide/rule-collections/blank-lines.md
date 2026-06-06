---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-collection-blank-lines)=

# Blank Lines

Whitespace and statement-separation rules.

Enable with:

```toml
enable = ["blank-lines"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [blank-line-after-control-block](../rules/blank-line-after-control-block.md) | Missing blank line after multiline control-flow block statement. | Any | Yes |
| [blank-line-before-assignment](../rules/blank-line-before-assignment.md) | Missing blank line before assignment statement that follows a non-assignment statement. | Any | Yes |
| [blank-line-before-branch](../rules/blank-line-before-branch.md) | Missing blank line before return/raise/break/continue in a large suite. | Any | Yes |
| [blank-line-before-unrelated-block](../rules/blank-line-before-unrelated-block.md) | Illegal cuddle before block header. The preceding setup must directly feed the upcoming block. | Any | Yes |
| [no-suite-leading-trailing-blank-lines](../rules/no-suite-leading-trailing-blank-lines.md) | Leading or trailing blank lines in a suite are not allowed. | Any | Yes |
