---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-pack-fixit-extra)=

# Additional Fixit rules

Additional Fixit-derived rules that can be enabled separately.

Enable with:

```toml
enable = ["fixit_extra"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [AvoidOrInExcept](../rules/avoid-or-in-except.md) | Avoid using 'or' in an except block. For example:'except ValueError or TypeError' only catches 'ValueError'. Instead, use parentheses, 'except (ValueError, TypeError)' | Any | No |
| [CollapseIsinstanceChecks](../rules/collapse-isinstance-checks.md) | Multiple isinstance calls with the same target but different types can be collapsed into a single call with a tuple of types. | Any | Yes |
| [ComparePrimitivesByEqual](../rules/compare-primitives-by-equal.md) | Don't use `is` or `is not` to compare primitives, as they compare references. Use == or != instead. | Any | Yes |
| [CompareSingletonPrimitivesByIs](../rules/compare-singleton-primitives-by-is.md) | Comparisons to singleton primitives should not be done with == or !=, as they check equality rather than identity. Use `is` or `is not` instead. | Any | Yes |
| [DeprecatedABCImport](../rules/deprecated-a-b-c-import.md) | ABCs must be imported from collections.abc | `>= 3.3` | Yes |
| [DeprecatedUnittestAsserts](../rules/deprecated-unittest-asserts.md) | {deprecated} is deprecated, use {replacement} instead | Any | Yes |
| [NoAssertTrueForComparisons](../rules/no-assert-true-for-comparisons.md) | "assertTrue" does not compare its arguments, use "assertEqual" or other appropriate functions. | Any | Yes |
| [NoInheritFromObject](../rules/no-inherit-from-object.md) | Inheriting from object is a no-op. 'class Foo:' is just fine =) | Any | Yes |
| [NoRedundantArgumentsSuper](../rules/no-redundant-arguments-super.md) | Do not use arguments when calling super for the parent class. See https://www.python.org/dev/peps/pep-3135/ | Any | Yes |
| [NoRedundantFString](../rules/no-redundant-f-string.md) | f-string doesn't have placeholders, remove redundant f-string. | Any | Yes |
| [NoRedundantLambda](../rules/no-redundant-lambda.md) | — | Any | Yes |
| [NoRedundantListComprehension](../rules/no-redundant-list-comprehension.md) | — | Any | Yes |
| [NoStringTypeAnnotation](../rules/no-string-type-annotation.md) | String type hints are no longer necessary in Python, use the type identifier directly. | Any | Yes |
| [ReplaceUnionWithOptional](../rules/replace-union-with-optional.md) | `Optional[T]` is preferred over `Union[T, None]` or `Union[None, T]`. Learn more: https://docs.python.org/3/library/typing.html#typing.Optional | Any | Yes |
| [RewriteToComprehension](../rules/rewrite-to-comprehension.md) | — | Any | Yes |
| [RewriteToLiteral](../rules/rewrite-to-literal.md) | — | Any | Yes |
| [UseAssertIn](../rules/use-assert-in.md) | Use assertIn/assertNotIn instead of assertTrue/assertFalse for inclusion check. See https://docs.python.org/3/library/unittest.html#unittest.TestCase.assertIn) | Any | Yes |
| [UseAssertIsNotNone](../rules/use-assert-is-not-none.md) | "assertTrue" and "assertFalse" are deprecated. Use "assertIsNotNone" and "assertIsNone" instead. See https://docs.python.org/3.8/library/unittest.html#deprecated-aliases | Any | Yes |
| [UseAsyncSleepInAsyncDef](../rules/use-async-sleep-in-async-def.md) | Use asyncio.sleep in async function | Any | No |
| [UseClsInClassmethod](../rules/use-cls-in-classmethod.md) | When using @classmethod, the first argument must be `cls`. | Any | Yes |
| [UseFstring](../rules/use-fstring.md) | Do not use printf style formatting or .format(). Use f-string instead to be more readable and efficient. See https://www.python.org/dev/peps/pep-0498/ | Any | Yes |
