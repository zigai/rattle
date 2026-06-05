---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-pack-blank-lines)=

# Blank-line rules

Whitespace and statement-separation rules.

Enable with:

```toml
enable = ["blank_lines"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [BlankLineAfterControlBlock](../rules/blank-line-after-control-block.md) | Missing blank line after multiline control-flow block statement. | Any | Yes |
| [BlankLineBeforeAssignment](../rules/blank-line-before-assignment.md) | Missing blank line before assignment statement that follows a non-assignment statement. | Any | Yes |
| [BlankLineBeforeBranchInLargeSuite](../rules/blank-line-before-branch-in-large-suite.md) | Missing blank line before return/raise/break/continue in a large suite. | Any | Yes |
| [BlockHeaderCuddleRelaxed](../rules/block-header-cuddle-relaxed.md) | Illegal cuddle before block header. The preceding setup must directly feed the upcoming block. | Any | Yes |
| [NoSuiteLeadingTrailingBlankLines](../rules/no-suite-leading-trailing-blank-lines.md) | — | Any | Yes |
