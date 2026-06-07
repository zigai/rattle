
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

## Blank Lines

Whitespace and statement-separation rules.

Enable with:

```toml
enable = ["blank-lines"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [blank-line-after-control-block](rules/blank-line-after-control-block.md) | Missing blank line after multiline control-flow block statement. | Any | Yes |
| [blank-line-before-assignment](rules/blank-line-before-assignment.md) | Missing blank line before assignment statement that follows a non-assignment statement. | Any | Yes |
| [blank-line-before-branch](rules/blank-line-before-branch.md) | Missing blank line before return/raise/break/continue in a large suite. | Any | Yes |
| [blank-line-before-unrelated-block](rules/blank-line-before-unrelated-block.md) | Illegal cuddle before block header. The preceding setup must directly feed the upcoming block. | Any | Yes |
| [no-suite-leading-trailing-blank-lines](rules/no-suite-leading-trailing-blank-lines.md) | Leading or trailing blank lines in a suite are not allowed. | Any | Yes |

## Exports

Rules for explicit module export surfaces.

Enable with:

```toml
enable = ["exports"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [module-all-at-bottom](rules/module-all-at-bottom.md) | Define module \_\_all\_\_ at the bottom of the file. | Any | Yes |
| [no-underscore-all-exports](rules/no-underscore-all-exports.md) | Do not export underscore-prefixed symbols in \_\_all\_\_. Either remove them from \_\_all\_\_ or rename them to be public. | Any | No |

## Policy

Configurable policy rules for architecture and naming boundaries.

Enable with:

```toml
enable = ["policy"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [forbidden-call](rules/forbidden-call.md) | Do not call forbidden callable '{symbol}'. | Any | No |
| [forbidden-import](rules/forbidden-import.md) | Do not import across forbidden boundary '{boundary}'. | Any | No |
| [forbidden-name](rules/forbidden-name.md) | Do not use forbidden {kind} name '{name}'. | Any | No |
| [line-count-limit](rules/line-count-limit.md) | {target} has {actual_lines} lines, exceeding the configured limit of {max_lines}. | Any | No |
| [no-relative-imports](rules/no-relative-imports.md) | Use absolute imports instead of relative imports. | Any | No |
| [no-underscore-import-aliases](rules/no-underscore-import-aliases.md) | Import aliases must not start with an underscore. | Any | No |
| [no-unsafe-tempfile-factories](rules/no-unsafe-tempfile-factories.md) | Use tempfile context managers instead of mkstemp or mkdtemp. | Any | No |

## Style

Rules for code style and structure.

Enable with:

```toml
enable = ["style"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [no-annotated-self](rules/no-annotated-self.md) | Do not annotate self in instance methods. | Any | Yes |
| [no-exception-message-variables](rules/no-exception-message-variables.md) | Inline exception message strings instead of assigning throwaway variables. | Any | Yes |
| [no-str-exception-translation](rules/no-str-exception-translation.md) | Do not translate exceptions by passing str(exc); use a stable message and chain the cause. | Any | No |
| [no-underscore-class](rules/no-underscore-class.md) | Class names must not start with an underscore prefix. | Any | No |
| [public-method-order](rules/public-method-order.md) | Define public methods before private helpers in behavior classes. | Any | No |

## Typing

Rules for type annotations and modern typing syntax.

Enable with:

```toml
enable = ["typing"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [no-bare-object-annotations](rules/no-bare-object-annotations.md) | Use a narrower type than bare object in annotations. | Any | No |

## Fixit

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
| [use-callable-ellipsis](rules/use-callable-ellipsis.md) | Use Callable[..., T] instead of Callable[[...], T]. | Any | Yes |
| [use-rattle-ignore-comment](rules/use-rattle-ignore-comment.md) | noqa is deprecated. Use `rattle: ignore[rule-name]` instead. | Any | No |
| [use-types-from-typing](rules/use-types-from-typing.md) | You are using builtins.{builtin_type} as a type annotation but the type system doesn't recognize it as a valid type. Use typing.{correct_type} instead. | `< 3.10` | Yes |

## Fixit Extra

Additional Fixit-derived rules that can be enabled separately.

Enable with:

```toml
enable = ["fixit-extra"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [collapse-isinstance-checks](rules/collapse-isinstance-checks.md) | Multiple isinstance calls with the same target but different types can be collapsed into a single call with a tuple of types. | Any | Yes |
| [deprecated-unittest-asserts](rules/deprecated-unittest-asserts.md) | {deprecated} is deprecated, use {replacement} instead | Any | Yes |
| [no-inherit-from-object](rules/no-inherit-from-object.md) | Inheriting from object is a no-op. 'class Foo:' is just fine =) | Any | Yes |
| [no-or-in-except](rules/no-or-in-except.md) | Avoid using 'or' in an except block. For example:'except ValueError or TypeError' only catches 'ValueError'. Instead, use parentheses, 'except (ValueError, TypeError)' | Any | No |
| [no-redundant-arguments-super](rules/no-redundant-arguments-super.md) | Do not use arguments when calling super for the parent class. | Any | Yes |
| [no-redundant-f-string](rules/no-redundant-f-string.md) | f-string doesn't have placeholders, remove redundant f-string. | Any | Yes |
| [no-redundant-lambda](rules/no-redundant-lambda.md) | The lambda that is wrapping {function} is redundant. It can unwrapped safely and used purely. | Any | Yes |
| [no-redundant-list-comprehension](rules/no-redundant-list-comprehension.md) | Unnecessary list comprehension inside {func}(). Use a generator expression instead. | Any | Yes |
| [no-string-type-annotation](rules/no-string-type-annotation.md) | String type hints are no longer necessary in Python, use the type identifier directly. | Any | Yes |
| [replace-union-with-optional](rules/replace-union-with-optional.md) | `Optional[T]` is preferred over `Union[T, None]` or `Union[None, T]`. | Any | Yes |
| [use-assert-equal](rules/use-assert-equal.md) | "assertTrue" does not compare its arguments, use "assertEqual" or other appropriate functions. | Any | Yes |
| [use-assert-in](rules/use-assert-in.md) | Use assertIn/assertNotIn instead of assertTrue/assertFalse for inclusion check. | Any | Yes |
| [use-assert-is-not-none](rules/use-assert-is-not-none.md) | "assertTrue" and "assertFalse" are deprecated. Use "assertIsNotNone" and "assertIsNone" instead. | Any | Yes |
| [use-async-sleep-in-async-def](rules/use-async-sleep-in-async-def.md) | Use asyncio.sleep in async function | Any | No |
| [use-cls-in-classmethod](rules/use-cls-in-classmethod.md) | When using @classmethod, the first argument must be `cls`. | Any | Yes |
| [use-collections-abc](rules/use-collections-abc.md) | ABCs must be imported from collections.abc | `>= 3.3` | Yes |
| [use-comprehension](rules/use-comprehension.md) | It's unnecessary to use {func} around a generator expression, since there are equivalent comprehensions for this type. | Any | Yes |
| [use-eq-for-primitives](rules/use-eq-for-primitives.md) | Don't use `is` or `is not` to compare primitives, as they compare references. Use == or != instead. | Any | Yes |
| [use-f-string](rules/use-f-string.md) | Do not use printf style formatting or .format(). Use f-string instead to be more readable and efficient. | Any | Yes |
| [use-is-for-singletons](rules/use-is-for-singletons.md) | Comparisons to singleton primitives should not be done with == or !=, as they check equality rather than identity. Use `is` or `is not` instead. | Any | Yes |
| [use-literal](rules/use-literal.md) | It's unnecessary to use a list or tuple within a call to {func} since there is literal syntax for this type | Any | Yes |

```{toctree}
:hidden:
:maxdepth: 1

rule-collections/blank-lines
rule-collections/exports
rule-collections/policy
rule-collections/style
rule-collections/typing
rule-collections/fixit
rule-collections/fixit-extra
```
