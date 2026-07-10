
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
| [blank-line-after-control-block](rules/blank-line-after-control-block.md) | Add a blank line after this multiline control-flow block. | Any | Yes |
| [blank-line-after-terminal-control-block](rules/blank-line-after-terminal-control-block.md) | Add a blank line after this early-exit control-flow block. | Any | Yes |
| [blank-line-before-branch](rules/blank-line-before-branch.md) | Add a blank line before this branch statement in a larger code block. | Any | Yes |
| [blank-line-before-unrelated-block](rules/blank-line-before-unrelated-block.md) | Add a blank line before this block; the preceding statements do not prepare values used by it. | Any | Yes |
| [no-suite-leading-trailing-blank-lines](rules/no-suite-leading-trailing-blank-lines.md) | Remove blank lines at the beginning or end of a code block. | Any | Yes |

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
| [no-str-exception-translation](rules/no-str-exception-translation.md) | Use a fixed message when translating an exception, and preserve the cause with `raise ... from exc`. | Any | No |
| [no-underscore-class](rules/no-underscore-class.md) | Class names must not start with an underscore prefix. | Any | No |
| [public-method-order](rules/public-method-order.md) | Define public methods before underscore-prefixed helper methods. | Any | No |

## Typing

Rules for type annotations and modern typing syntax.

Enable with:

```toml
enable = ["typing"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [no-bare-object-annotations](rules/no-bare-object-annotations.md) | Replace this bare `object` annotation with a type that describes the value. | Any | No |

## Fixit

Core lint rules inherited from Fixit.

Enable with:

```toml
enable = ["fixit"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [explicit-frozen-dataclass](rules/explicit-frozen-dataclass.md) | Dataclass mutability must be explicit. Add `frozen=True` for immutable value objects or `frozen=False` when instances are intentionally mutable. | Any | No |
| [no-named-tuple](rules/no-named-tuple.md) | NamedTuple can often be replaced with @dataclass, but dataclasses are not tuple-compatible; check callers before converting. | Any | No |
| [no-static-if-condition](rules/no-static-if-condition.md) | This `if` condition appears constant; verify the logic and remove any temporary debug clause. | Any | No |
| [sorted-attributes](rules/sorted-attributes.md) | Class assignments under @sorted-attributes are not sorted; sorting them can change right-hand-side side-effect order. | Any | Yes |
| [use-callable-ellipsis](rules/use-callable-ellipsis.md) | Use Callable[..., T] instead of Callable[[...], T]. | Any | Yes |
| [use-rattle-ignore-comment](rules/use-rattle-ignore-comment.md) | Use `rattle: ignore[rule-name]`; Rattle does not support `noqa`. | Any | No |
| [use-types-from-typing](rules/use-types-from-typing.md) | Python 3.8 does not support `{builtin_type}[...]` annotations; use `typing.{correct_type}` instead. | `< 3.9` | Yes |

## Fixit Extra

Additional Fixit-derived rules that can be enabled separately.

Enable with:

```toml
enable = ["fixit-extra"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
| [collapse-isinstance-checks](rules/collapse-isinstance-checks.md) | Multiple isinstance calls with the same target but different types can be collapsed into a single call with a tuple of types. | Any | Yes |
| [deprecated-unittest-asserts](rules/deprecated-unittest-asserts.md) | `{deprecated}` is deprecated; use `{replacement}` instead. | Any | Yes |
| [no-inherit-from-object](rules/no-inherit-from-object.md) | Remove the redundant `object` base class. | Any | Yes |
| [no-or-in-except](rules/no-or-in-except.md) | Use `except (ValueError, TypeError):`; `except ValueError or TypeError:` catches only `ValueError`. | Any | No |
| [no-redundant-arguments-super](rules/no-redundant-arguments-super.md) | Call `super()` without arguments. | Any | Yes |
| [no-redundant-f-string](rules/no-redundant-f-string.md) | Remove the `f` prefix; this f-string has no replacement fields. | Any | Yes |
| [no-redundant-lambda](rules/no-redundant-lambda.md) | The lambda that wraps {function} is redundant and can be replaced by the callable. | Any | Yes |
| [no-redundant-list-comprehension](rules/no-redundant-list-comprehension.md) | Unnecessary list comprehension inside {func}(). Use a generator expression instead. | Any | No |
| [no-string-type-annotation](rules/no-string-type-annotation.md) | Remove the quotes from this annotation; postponed evaluation is already enabled. | Any | Yes |
| [replace-union-with-optional](rules/replace-union-with-optional.md) | `Optional[T]` is preferred over `Union[T, None]` or `Union[None, T]`. | Any | Yes |
| [use-assert-equal](rules/use-assert-equal.md) | Use `assertEqual()` or `assertNotEqual()` instead of wrapping an equality comparison in `assertTrue()`. | Any | Yes |
| [use-assert-in](rules/use-assert-in.md) | Use `assertIn()` or `assertNotIn()` for membership checks. | Any | Yes |
| [use-assert-is-not-none](rules/use-assert-is-not-none.md) | Use `assertIsNone()` or `assertIsNotNone()` for `None` checks. | Any | Yes |
| [use-async-sleep-in-async-def](rules/use-async-sleep-in-async-def.md) | Do not call blocking time.sleep inside async functions; use asyncio.sleep or an async runtime sleep. | Any | No |
| [use-cls-in-classmethod](rules/use-cls-in-classmethod.md) | When using @classmethod, the first argument must be `cls`. | Any | Yes |
| [use-collections-abc](rules/use-collections-abc.md) | Import abstract base classes from `collections.abc`. | `>= 3.3` | Yes |
| [use-comprehension](rules/use-comprehension.md) | Replace this {func}() call with the equivalent comprehension. | Any | Yes |
| [use-eq-for-primitives](rules/use-eq-for-primitives.md) | Use `==` or `!=` for numeric and string values; `is` tests object identity. | Any | Yes |
| [use-f-string](rules/use-f-string.md) | Use an f-string instead of `%` formatting or `str.format()`. | Any | Yes |
| [use-is-for-singletons](rules/use-is-for-singletons.md) | Compare `None`, `True`, and `False` with `is` or `is not`. | Any | Yes |
| [use-literal](rules/use-literal.md) | Replace this {func}() call with the equivalent collection literal. | Any | Yes |

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
