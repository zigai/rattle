---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-forbidden-name)=

# forbidden-name

<p class="rule-metadata">
  <span>Collection: <code>policy</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

Ban configured names by identifier kind and pattern.

## Message template

Do not use forbidden {kind} name '{name}'.

Placeholder values are filled in when the violation is reported.


## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">forbidden_names</span></td>
      <td>Names to forbid. Each entry has the form kind:pattern[|message], where kind is any, variable, parameter, function, class, attribute, import, or alias. Patterns support shell-style wildcards; for example, &#x27;class:*Manager|Use a specific role name&#x27;.</td>
      <td><span class="rule-setting-type">list</span></td>
      <td><span class="rule-setting-default rule-setting-default-plain">[]</span></td>
    </tr>
</tbody>
</table>
```
