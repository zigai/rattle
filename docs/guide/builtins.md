
<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(builtin-rules)=
(rules)=

# Rules

Rattle's built-in rules are grouped by collection. Enable a collection by adding
its name to {attr}`enable <rattle.Config.enable>`, or enable a single rule by its
kebab-case name.

## Blank-line rules

Whitespace and statement-separation rules.

Enable with:

```toml
enable = ["blank-lines"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [blank-line-after-control-block](rules/blank-line-after-control-block.md) | Missing blank line after multiline control-flow block statement. | Any | Yes |
| [blank-line-before-assignment](rules/blank-line-before-assignment.md) | Missing blank line before assignment statement that follows a non-assignment statement. | Any | Yes |
| [blank-line-before-branch-in-large-suite](rules/blank-line-before-branch-in-large-suite.md) | Missing blank line before return/raise/break/continue in a large suite. | Any | Yes |
| [block-header-cuddle-relaxed](rules/block-header-cuddle-relaxed.md) | Illegal cuddle before block header. The preceding setup must directly feed the upcoming block. | Any | Yes |
| [no-suite-leading-trailing-blank-lines](rules/no-suite-leading-trailing-blank-lines.md) | — | Any | Yes |

## Core Fixit rules

Core lint rules inherited from Fixit.

Enable with:

```toml
enable = ["fixit"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [explicit-frozen-dataclass](rules/explicit-frozen-dataclass.md) | Dataclass mutability must be explicit. Add `frozen=True` for immutable value objects or `frozen=False` when instances are intentionally mutable. | Any | No |
| [no-named-tuple](rules/no-named-tuple.md) | Instead of NamedTuple, consider using the @dataclass decorator from dataclasses instead for simplicity, efficiency and consistency. | Any | Yes |
| [no-static-if-condition](rules/no-static-if-condition.md) | Your if condition appears to evaluate to a static value (e.g. `or True`, `and False`). Please double check this logic and if it is actually temporary debug code. | Any | No |
| [sorted-attributes](rules/sorted-attributes.md) | It appears you are using the @sorted-attributes directive and the class variables are unsorted. See the lint autofix suggestion. | Any | Yes |
| [use-rattle-ignore-comment](rules/use-rattle-ignore-comment.md) | noqa is deprecated. Use `rattle: ignore[rule-name]` instead. | Any | No |
| [use-types-from-typing](rules/use-types-from-typing.md) | — | `< 3.10` | Yes |
| [variadic-callable-syntax](rules/variadic-callable-syntax.md) | — | Any | Yes |

## Additional Fixit rules

Additional Fixit-derived rules that can be enabled separately.

Enable with:

```toml
enable = ["fixit-extra"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [avoid-or-in-except](rules/avoid-or-in-except.md) | Avoid using 'or' in an except block. For example:'except ValueError or TypeError' only catches 'ValueError'. Instead, use parentheses, 'except (ValueError, TypeError)' | Any | No |
| [collapse-isinstance-checks](rules/collapse-isinstance-checks.md) | Multiple isinstance calls with the same target but different types can be collapsed into a single call with a tuple of types. | Any | Yes |
| [compare-primitives-by-equal](rules/compare-primitives-by-equal.md) | Don't use `is` or `is not` to compare primitives, as they compare references. Use == or != instead. | Any | Yes |
| [compare-singleton-primitives-by-is](rules/compare-singleton-primitives-by-is.md) | Comparisons to singleton primitives should not be done with == or !=, as they check equality rather than identity. Use `is` or `is not` instead. | Any | Yes |
| [deprecated-a-b-c-import](rules/deprecated-a-b-c-import.md) | ABCs must be imported from collections.abc | `>= 3.3` | Yes |
| [deprecated-unittest-asserts](rules/deprecated-unittest-asserts.md) | {deprecated} is deprecated, use {replacement} instead | Any | Yes |
| [no-assert-true-for-comparisons](rules/no-assert-true-for-comparisons.md) | "assertTrue" does not compare its arguments, use "assertEqual" or other appropriate functions. | Any | Yes |
| [no-inherit-from-object](rules/no-inherit-from-object.md) | Inheriting from object is a no-op. 'class Foo:' is just fine =) | Any | Yes |
| [no-redundant-arguments-super](rules/no-redundant-arguments-super.md) | Do not use arguments when calling super for the parent class. See https://www.python.org/dev/peps/pep-3135/ | Any | Yes |
| [no-redundant-f-string](rules/no-redundant-f-string.md) | f-string doesn't have placeholders, remove redundant f-string. | Any | Yes |
| [no-redundant-lambda](rules/no-redundant-lambda.md) | — | Any | Yes |
| [no-redundant-list-comprehension](rules/no-redundant-list-comprehension.md) | — | Any | Yes |
| [no-string-type-annotation](rules/no-string-type-annotation.md) | String type hints are no longer necessary in Python, use the type identifier directly. | Any | Yes |
| [replace-union-with-optional](rules/replace-union-with-optional.md) | `Optional[T]` is preferred over `Union[T, None]` or `Union[None, T]`. Learn more: https://docs.python.org/3/library/typing.html#typing.Optional | Any | Yes |
| [rewrite-to-comprehension](rules/rewrite-to-comprehension.md) | — | Any | Yes |
| [rewrite-to-literal](rules/rewrite-to-literal.md) | — | Any | Yes |
| [use-assert-in](rules/use-assert-in.md) | Use assertIn/assertNotIn instead of assertTrue/assertFalse for inclusion check. See https://docs.python.org/3/library/unittest.html#unittest.TestCase.assertIn) | Any | Yes |
| [use-assert-is-not-none](rules/use-assert-is-not-none.md) | "assertTrue" and "assertFalse" are deprecated. Use "assertIsNotNone" and "assertIsNone" instead. See https://docs.python.org/3.8/library/unittest.html#deprecated-aliases | Any | Yes |
| [use-async-sleep-in-async-def](rules/use-async-sleep-in-async-def.md) | Use asyncio.sleep in async function | Any | No |
| [use-cls-in-classmethod](rules/use-cls-in-classmethod.md) | When using @classmethod, the first argument must be `cls`. | Any | Yes |
| [use-fstring](rules/use-fstring.md) | Do not use printf style formatting or .format(). Use f-string instead to be more readable and efficient. See https://www.python.org/dev/peps/pep-0498/ | Any | Yes |

```{toctree}
:hidden:
:maxdepth: 1

rule-collections/blank-lines
rule-collections/fixit
rule-collections/fixit-extra
```
