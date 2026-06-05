
<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(builtin-rules)=
(rules)=

# Rules

Rattle's built-in rules are grouped by rule pack. Enable a pack by adding its
name to {attr}`enable <rattle.Config.enable>`, or enable a single rule by its
class name.

## Blank-line rules

Whitespace and statement-separation rules.

Enable with:

```toml
enable = ["blank_lines"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [BlankLineAfterControlBlock](rules/blank-line-after-control-block.md) | Missing blank line after multiline control-flow block statement. | Any | Yes |
| [BlankLineBeforeAssignment](rules/blank-line-before-assignment.md) | Missing blank line before assignment statement that follows a non-assignment statement. | Any | Yes |
| [BlankLineBeforeBranchInLargeSuite](rules/blank-line-before-branch-in-large-suite.md) | Missing blank line before return/raise/break/continue in a large suite. | Any | Yes |
| [BlockHeaderCuddleRelaxed](rules/block-header-cuddle-relaxed.md) | Illegal cuddle before block header. The preceding setup must directly feed the upcoming block. | Any | Yes |
| [NoSuiteLeadingTrailingBlankLines](rules/no-suite-leading-trailing-blank-lines.md) | — | Any | Yes |

## Core Fixit rules

Core lint rules inherited from Fixit.

Enable with:

```toml
enable = ["fixit"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [ExplicitFrozenDataclass](rules/explicit-frozen-dataclass.md) | Dataclass mutability must be explicit. Add `frozen=True` for immutable value objects or `frozen=False` when instances are intentionally mutable. | Any | No |
| [NoNamedTuple](rules/no-named-tuple.md) | Instead of NamedTuple, consider using the @dataclass decorator from dataclasses instead for simplicity, efficiency and consistency. | Any | Yes |
| [NoStaticIfCondition](rules/no-static-if-condition.md) | Your if condition appears to evaluate to a static value (e.g. `or True`, `and False`). Please double check this logic and if it is actually temporary debug code. | Any | No |
| [SortedAttributes](rules/sorted-attributes.md) | It appears you are using the @sorted-attributes directive and the class variables are unsorted. See the lint autofix suggestion. | Any | Yes |
| [UseRattleIgnoreComment](rules/use-rattle-ignore-comment.md) | noqa is deprecated. Use `rattle: ignore[RuleName]` instead. | Any | No |
| [UseTypesFromTyping](rules/use-types-from-typing.md) | — | `< 3.10` | Yes |
| [VariadicCallableSyntax](rules/variadic-callable-syntax.md) | — | Any | Yes |

## Additional Fixit rules

Additional Fixit-derived rules that can be enabled separately.

Enable with:

```toml
enable = ["fixit_extra"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [AvoidOrInExcept](rules/avoid-or-in-except.md) | Avoid using 'or' in an except block. For example:'except ValueError or TypeError' only catches 'ValueError'. Instead, use parentheses, 'except (ValueError, TypeError)' | Any | No |
| [CollapseIsinstanceChecks](rules/collapse-isinstance-checks.md) | Multiple isinstance calls with the same target but different types can be collapsed into a single call with a tuple of types. | Any | Yes |
| [ComparePrimitivesByEqual](rules/compare-primitives-by-equal.md) | Don't use `is` or `is not` to compare primitives, as they compare references. Use == or != instead. | Any | Yes |
| [CompareSingletonPrimitivesByIs](rules/compare-singleton-primitives-by-is.md) | Comparisons to singleton primitives should not be done with == or !=, as they check equality rather than identity. Use `is` or `is not` instead. | Any | Yes |
| [DeprecatedABCImport](rules/deprecated-a-b-c-import.md) | ABCs must be imported from collections.abc | `>= 3.3` | Yes |
| [DeprecatedUnittestAsserts](rules/deprecated-unittest-asserts.md) | {deprecated} is deprecated, use {replacement} instead | Any | Yes |
| [NoAssertTrueForComparisons](rules/no-assert-true-for-comparisons.md) | "assertTrue" does not compare its arguments, use "assertEqual" or other appropriate functions. | Any | Yes |
| [NoInheritFromObject](rules/no-inherit-from-object.md) | Inheriting from object is a no-op. 'class Foo:' is just fine =) | Any | Yes |
| [NoRedundantArgumentsSuper](rules/no-redundant-arguments-super.md) | Do not use arguments when calling super for the parent class. See https://www.python.org/dev/peps/pep-3135/ | Any | Yes |
| [NoRedundantFString](rules/no-redundant-f-string.md) | f-string doesn't have placeholders, remove redundant f-string. | Any | Yes |
| [NoRedundantLambda](rules/no-redundant-lambda.md) | — | Any | Yes |
| [NoRedundantListComprehension](rules/no-redundant-list-comprehension.md) | — | Any | Yes |
| [NoStringTypeAnnotation](rules/no-string-type-annotation.md) | String type hints are no longer necessary in Python, use the type identifier directly. | Any | Yes |
| [ReplaceUnionWithOptional](rules/replace-union-with-optional.md) | `Optional[T]` is preferred over `Union[T, None]` or `Union[None, T]`. Learn more: https://docs.python.org/3/library/typing.html#typing.Optional | Any | Yes |
| [RewriteToComprehension](rules/rewrite-to-comprehension.md) | — | Any | Yes |
| [RewriteToLiteral](rules/rewrite-to-literal.md) | — | Any | Yes |
| [UseAssertIn](rules/use-assert-in.md) | Use assertIn/assertNotIn instead of assertTrue/assertFalse for inclusion check. See https://docs.python.org/3/library/unittest.html#unittest.TestCase.assertIn) | Any | Yes |
| [UseAssertIsNotNone](rules/use-assert-is-not-none.md) | "assertTrue" and "assertFalse" are deprecated. Use "assertIsNotNone" and "assertIsNone" instead. See https://docs.python.org/3.8/library/unittest.html#deprecated-aliases | Any | Yes |
| [UseAsyncSleepInAsyncDef](rules/use-async-sleep-in-async-def.md) | Use asyncio.sleep in async function | Any | No |
| [UseClsInClassmethod](rules/use-cls-in-classmethod.md) | When using @classmethod, the first argument must be `cls`. | Any | Yes |
| [UseFstring](rules/use-fstring.md) | Do not use printf style formatting or .format(). Use f-string instead to be more readable and efficient. See https://www.python.org/dev/peps/pep-0498/ | Any | Yes |

```{toctree}
:hidden:
:maxdepth: 1

rule-packs/blank-lines
rule-packs/fixit
rule-packs/fixit-extra
```
