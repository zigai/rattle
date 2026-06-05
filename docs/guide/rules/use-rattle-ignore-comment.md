---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-rattle-ignore-comment)=

# UseRattleIgnoreComment

<p class="rule-metadata">
  <span>Pack: <code>fixit</code></span>
  <span>Module: <code>rattle.rules.fixit.use_rattle_ignore_comment</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

To silence a lint warning, use ``rattle: ignore[RuleName]`` comments.
The comment may be a trailing inline comment or a standalone comment line above the code.
Rule names are optional, but explicitly listing one or more comma-separated rule names avoids
accidentally silencing unrelated warnings.
``noqa`` is deprecated and not supported because it is shared by other Python linters and can
accidentally silence warnings unexpectedly.

## Message

noqa is deprecated. Use `rattle: ignore[RuleName]` instead.

## Valid examples

```python
# rattle: ignore[UseFstringRule]
"%s" % "hi"
```
```python
'ab' 'cd'  # rattle: ignore[UsePlusForStringConcatRule]
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example">
```
```python
fn() # noqa
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
(
 1,
 2,  # noqa
)
```
```{raw} html
</div>
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
class C:
    # noqa
    ...
```
```{raw} html
</div>
```
```{raw} html
</details>
```
