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

## Message template

Do not call forbidden callable '{symbol}'.

Placeholder values are filled in when the violation is reported.


## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">forbidden_calls</span></td>
      <td>Callable symbols to forbid. Each entry has the form symbol[|message[|recommended_callable]], for example &#x27;os.system|Use subprocess.run|subprocess.run&#x27;.</td>
      <td><span class="rule-setting-type">list</span></td>
      <td><span class="rule-setting-default rule-setting-default-plain">[]</span></td>
    </tr>
</tbody>
</table>
```
