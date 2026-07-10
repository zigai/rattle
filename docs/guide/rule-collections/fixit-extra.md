---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-collection-fixit-extra)=

# Fixit Extra

Additional Fixit-derived rules that can be enabled separately.

Enable with:

```toml
enable = ["fixit-extra"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [collapse-isinstance-checks](../rules/collapse-isinstance-checks.md) | Multiple isinstance calls with the same target but different types can be collapsed into a single call with a tuple of types. | Any | Yes |
| [deprecated-unittest-asserts](../rules/deprecated-unittest-asserts.md) | `{deprecated}` is deprecated; use `{replacement}` instead. | Any | Yes |
| [no-inherit-from-object](../rules/no-inherit-from-object.md) | Remove the redundant `object` base class. | Any | Yes |
| [no-or-in-except](../rules/no-or-in-except.md) | Use `except (ValueError, TypeError):`; `except ValueError or TypeError:` catches only `ValueError`. | Any | No |
| [no-redundant-arguments-super](../rules/no-redundant-arguments-super.md) | Call `super()` without arguments. | Any | Yes |
| [no-redundant-f-string](../rules/no-redundant-f-string.md) | Remove the `f` prefix; this f-string has no replacement fields. | Any | Yes |
| [no-redundant-lambda](../rules/no-redundant-lambda.md) | The lambda that wraps {function} is redundant and can be replaced by the callable. | Any | Yes |
| [no-redundant-list-comprehension](../rules/no-redundant-list-comprehension.md) | Unnecessary list comprehension inside {func}(). Use a generator expression instead. | Any | No |
| [no-string-type-annotation](../rules/no-string-type-annotation.md) | Remove the quotes from this annotation; postponed evaluation is already enabled. | Any | Yes |
| [replace-union-with-optional](../rules/replace-union-with-optional.md) | `Optional[T]` is preferred over `Union[T, None]` or `Union[None, T]`. | Any | Yes |
| [use-assert-equal](../rules/use-assert-equal.md) | Use `assertEqual()` or `assertNotEqual()` instead of wrapping an equality comparison in `assertTrue()`. | Any | Yes |
| [use-assert-in](../rules/use-assert-in.md) | Use `assertIn()` or `assertNotIn()` for membership checks. | Any | Yes |
| [use-assert-is-not-none](../rules/use-assert-is-not-none.md) | Use `assertIsNone()` or `assertIsNotNone()` for `None` checks. | Any | Yes |
| [use-async-sleep-in-async-def](../rules/use-async-sleep-in-async-def.md) | Do not call blocking time.sleep inside async functions; use asyncio.sleep or an async runtime sleep. | Any | No |
| [use-cls-in-classmethod](../rules/use-cls-in-classmethod.md) | When using @classmethod, the first argument must be `cls`. | Any | Yes |
| [use-collections-abc](../rules/use-collections-abc.md) | Import abstract base classes from `collections.abc`. | `>= 3.3` | Yes |
| [use-comprehension](../rules/use-comprehension.md) | Replace this {func}() call with the equivalent comprehension. | Any | Yes |
| [use-eq-for-primitives](../rules/use-eq-for-primitives.md) | Use `==` or `!=` for numeric and string values; `is` tests object identity. | Any | Yes |
| [use-f-string](../rules/use-f-string.md) | Use an f-string instead of `%` formatting or `str.format()`. | Any | Yes |
| [use-is-for-singletons](../rules/use-is-for-singletons.md) | Compare `None`, `True`, and `False` with `is` or `is not`. | Any | Yes |
| [use-literal](../rules/use-literal.md) | Replace this {func}() call with the equivalent collection literal. | Any | Yes |
