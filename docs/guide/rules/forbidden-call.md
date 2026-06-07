---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-forbidden-call)=

# forbidden-call

<p class="rule-metadata">
  <span>Collection: <code>policy</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Ban calls to configured functions, constructors, and helper APIs.

## Message

Do not call forbidden callable '{symbol}'.


## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">forbidden_calls</span></td>
      <td>—</td>
      <td><span class="rule-setting-type">list</span></td>
      <td><span class="rule-setting-default rule-setting-default-plain">[]</span></td>
    </tr>
</tbody>
</table>
```

## Valid examples

No valid examples are documented.

## Invalid examples

No invalid examples are documented.
