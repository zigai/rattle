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
| [blank-line-after-control-block](../rules/blank-line-after-control-block.md) | Add a blank line after this multiline control-flow block. | Any | Yes |
| [blank-line-after-terminal-control-block](../rules/blank-line-after-terminal-control-block.md) | Add a blank line after this early-exit control-flow block. | Any | Yes |
| [blank-line-before-branch](../rules/blank-line-before-branch.md) | Add a blank line before this branch statement in a larger code block. | Any | Yes |
| [blank-line-before-unrelated-block](../rules/blank-line-before-unrelated-block.md) | Add a blank line before this block; the preceding statements do not prepare values used by it. | Any | Yes |
| [no-suite-leading-trailing-blank-lines](../rules/no-suite-leading-trailing-blank-lines.md) | Remove blank lines at the beginning or end of a code block. | Any | Yes |
