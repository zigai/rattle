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
| [deprecated-unittest-asserts](../rules/deprecated-unittest-asserts.md) | {deprecated} is deprecated, use {replacement} instead | Any | Yes |
| [no-inherit-from-object](../rules/no-inherit-from-object.md) | Inheriting from object is a no-op. 'class Foo:' is just fine =) | Any | Yes |
| [no-or-in-except](../rules/no-or-in-except.md) | Avoid using 'or' in an except block. For example:'except ValueError or TypeError' only catches 'ValueError'. Instead, use parentheses, 'except (ValueError, TypeError)' | Any | No |
| [no-redundant-arguments-super](../rules/no-redundant-arguments-super.md) | Do not use arguments when calling super for the parent class. | Any | Yes |
| [no-redundant-f-string](../rules/no-redundant-f-string.md) | f-string doesn't have placeholders, remove redundant f-string. | Any | Yes |
| [no-redundant-lambda](../rules/no-redundant-lambda.md) | The lambda that is wrapping {function} is redundant. It can unwrapped safely and used purely. | Any | Yes |
| [no-redundant-list-comprehension](../rules/no-redundant-list-comprehension.md) | Unnecessary list comprehension inside {func}(). Use a generator expression instead. | Any | Yes |
| [no-string-type-annotation](../rules/no-string-type-annotation.md) | String type hints are no longer necessary in Python, use the type identifier directly. | Any | Yes |
| [replace-union-with-optional](../rules/replace-union-with-optional.md) | `Optional[T]` is preferred over `Union[T, None]` or `Union[None, T]`. | Any | Yes |
| [use-assert-equal](../rules/use-assert-equal.md) | "assertTrue" does not compare its arguments, use "assertEqual" or other appropriate functions. | Any | Yes |
| [use-assert-in](../rules/use-assert-in.md) | Use assertIn/assertNotIn instead of assertTrue/assertFalse for inclusion check. | Any | Yes |
| [use-assert-is-not-none](../rules/use-assert-is-not-none.md) | "assertTrue" and "assertFalse" are deprecated. Use "assertIsNotNone" and "assertIsNone" instead. | Any | Yes |
| [use-async-sleep-in-async-def](../rules/use-async-sleep-in-async-def.md) | Use asyncio.sleep in async function | Any | No |
| [use-cls-in-classmethod](../rules/use-cls-in-classmethod.md) | When using @classmethod, the first argument must be `cls`. | Any | Yes |
| [use-collections-abc](../rules/use-collections-abc.md) | ABCs must be imported from collections.abc | `>= 3.3` | Yes |
| [use-comprehension](../rules/use-comprehension.md) | It's unnecessary to use {func} around a generator expression, since there are equivalent comprehensions for this type. | Any | Yes |
| [use-eq-for-primitives](../rules/use-eq-for-primitives.md) | Don't use `is` or `is not` to compare primitives, as they compare references. Use == or != instead. | Any | Yes |
| [use-f-string](../rules/use-f-string.md) | Do not use printf style formatting or .format(). Use f-string instead to be more readable and efficient. | Any | Yes |
| [use-is-for-singletons](../rules/use-is-for-singletons.md) | Comparisons to singleton primitives should not be done with == or !=, as they check equality rather than identity. Use `is` or `is not` instead. | Any | Yes |
| [use-literal](../rules/use-literal.md) | It's unnecessary to use a list or tuple within a call to {func} since there is literal syntax for this type | Any | Yes |
