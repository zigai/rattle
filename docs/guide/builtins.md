
<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(builtin-rules)=

# Built-in Rules

- `rattle.rules.blank_lines`
- `rattle.rules.fixit`
- `rattle.rules.fixit_extra`


## `rattle.rules.blank_lines`

```{automodule} rattle.rules.blank_lines
```

- `BlankLineAfterControlBlock`
- `BlankLineBeforeAssignment`
- `BlankLineBeforeBranchInLargeSuite`
- `BlockHeaderCuddleRelaxed`
- `NoSuiteLeadingTrailingBlankLines`

### BlankLineAfterControlBlock

Require separation after multiline control-flow block statements.

#### MESSAGE

Missing blank line after multiline control-flow block statement.

#### AUTOFIX

Yes


#### VALID

```python
def f(value: int) -> int:
    if value > 0:
        value += 1

    return value
```
```python
def f(value: int) -> int:
    if value > 0:
        value += 1
    # comment separator
    return value
```

#### INVALID

```python
def f(value: int) -> int:
    if value > 0:
        value += 1
    return value

# suggested fix
def f(value: int) -> int:
    if value > 0:
        value += 1

    return value

```
```python
def f(values: list[int]) -> int:
    total = 0
    for value in values:
        total += value
    return total

# suggested fix
def f(values: list[int]) -> int:
    total = 0
    for value in values:
        total += value

    return total

```
### BlankLineBeforeAssignment

Require separators before assignments that do not continue the local flow.

#### MESSAGE

Missing blank line before assignment statement that follows a non-assignment statement.

#### AUTOFIX

Yes


#### VALID

```python
def f() -> int:
    value = 1
    other = value + 1
    return other
```
```python
def f() -> int:
    log_start()

    value = compute()
    log_value(value)
    return value
```

#### INVALID

```python
def f(values: list[int]) -> int:
    total = 0
    if values:
        total += len(values)
    total += 1
    return total

# suggested fix
def f(values: list[int]) -> int:
    total = 0
    if values:
        total += len(values)

    total += 1
    return total

```
```python
def f(flag: bool, value: str) -> str:
    if not flag:
        return value
    normalized = value.strip()
    return normalized

# suggested fix
def f(flag: bool, value: str) -> str:
    if not flag:
        return value

    normalized = value.strip()
    return normalized

```
### BlankLineBeforeBranchInLargeSuite

Require branch statements to be visually separated in large suites.

#### MESSAGE

Missing blank line before return/raise/break/continue in a large suite.

#### AUTOFIX

Yes


#### VALID

```python
def f(value: int) -> int:
    x = value + 1
    y = x + 1

    return y
```
```python
def f(value: int) -> int:
    x = value + 1
    return x
```

#### INVALID

```python
def f(value: int) -> int:
    x = value + 1
    y = x + 1
    z = y + 1
    return z

# suggested fix
def f(value: int) -> int:
    x = value + 1
    y = x + 1
    z = y + 1

    return z

```
```python
def f(values: list[int]) -> int:
    total = 0
    message = str(total)
    flag = bool(message)
    raise RuntimeError("boom")

# suggested fix
def f(values: list[int]) -> int:
    total = 0
    message = str(total)
    flag = bool(message)

    raise RuntimeError("boom")

```
### BlockHeaderCuddleRelaxed

Allow cuddling when the setup remains part of the same control-flow step.

#### MESSAGE

Illegal cuddle before block header. The preceding setup must directly feed the upcoming block.

#### AUTOFIX

Yes


#### VALID

```python
def f(value: int) -> int:
    prepared = value + 1
    if prepared > 0:
        return prepared

    return 0
```
```python
def f(value: int) -> int:
    prepared = value + 1
    if value > 0:
        result = prepared
        return result

    return 0
```

#### INVALID

```python
def f(value: int) -> int:
    prepared = value + 1
    if value > 0:
        return value

    return 0

# suggested fix
def f(value: int) -> int:
    prepared = value + 1

    if value > 0:
        return value

    return 0

```
```python
def f(value: int) -> int:
    prepared = value + 1
    log(prepared)
    if prepared > 0:
        return prepared

    return 0

# suggested fix
def f(value: int) -> int:
    prepared = value + 1
    log(prepared)

    if prepared > 0:
        return prepared

    return 0

```
### NoSuiteLeadingTrailingBlankLines

Disallow leading/trailing empty lines at suite boundaries.

#### AUTOFIX

Yes


#### VALID

```python
def f() -> int:
    value = 1
    return value
```
```python
def f() -> int:
    # comment lines are separators, not blank lines
    value = 1
    return value
```

#### INVALID

```python
def f() -> int:

    value = 1
    return value

# suggested fix
def f() -> int:
    value = 1
    return value

```
```python
def f(items: list[int]) -> None:


    def emit() -> None:
        print(items)

# suggested fix
def f(items: list[int]) -> None:

    def emit() -> None:
        print(items)

```

## `rattle.rules.fixit`

```{automodule} rattle.rules.fixit
```

- `ExplicitFrozenDataclass`
- `NoNamedTuple`
- `NoStaticIfCondition`
- `SortedAttributes`
- `UseLintFixmeComment`
- `UseTypesFromTyping`
- `VariadicCallableSyntax`

### ExplicitFrozenDataclass

Requires dataclass mutability to be explicit.

#### MESSAGE

Dataclass mutability must be explicit. Add `frozen=True` for immutable value objects or `frozen=False` when instances are intentionally mutable.


#### VALID

```python
@some_other_decorator
class Cls: pass
```
```python
from dataclasses import dataclass
@dataclass(frozen=False)
class Cls: pass
```

#### INVALID

```python
from dataclasses import dataclass
@some_unrelated_decorator
@dataclass  # not called as a function
@another_unrelated_decorator
class Cls: pass
```
```python
from dataclasses import dataclass
@dataclass()  # called as a function, no kwargs
class Cls: pass
```
### NoNamedTuple

Enforce the use of ``dataclasses.dataclass`` decorator instead of ``NamedTuple`` for cleaner customization and
inheritance. It supports default value, combining fields for inheritance, and omitting optional fields at
instantiation. See `PEP 557 <https://www.python.org/dev/peps/pep-0557>`_.
``@dataclass`` is faster at reading an object's nested properties and executing its methods. (`benchmark <https://medium.com/@jacktator/dataclass-vs-namedtuple-vs-object-for-performance-optimization-in-python-691e234253b9>`_).

#### MESSAGE

Instead of NamedTuple, consider using the @dataclass decorator from dataclasses instead for simplicity, efficiency and consistency.

#### AUTOFIX

Yes


#### VALID

```python
@dataclass(frozen=True)
class Foo:
    pass
```
```python
@dataclass(frozen=False)
class Foo:
    pass
```

#### INVALID

```python
from typing import NamedTuple

class Foo(NamedTuple):
    pass

# suggested fix
import dataclasses

@dataclasses.dataclass(frozen=True)
class Foo:
    pass

```
```python
from typing import NamedTuple as NT

class Foo(NT):
    pass

# suggested fix
import dataclasses

@dataclasses.dataclass(frozen=True)
class Foo:
    pass

```
### NoStaticIfCondition

Discourages ``if`` conditions which evaluate to a static value (e.g. ``or True``, ``and False``, etc).

#### MESSAGE

Your if condition appears to evaluate to a static value (e.g. `or True`, `and False`). Please double check this logic and if it is actually temporary debug code.


#### VALID

```python
if my_func() or not else_func():
    pass
```
```python
if function_call(True):
    pass
```

#### INVALID

```python
if True:
    do_something()
```
```python
if crazy_expression or True:
    do_something()
```
### SortedAttributes

Ever wanted to sort a bunch of class attributes alphabetically?
Well now it's easy! Just add "@sorted-attributes" in the doc string of
a class definition and lint will automatically sort all attributes alphabetically.

Feel free to add other methods and such -- it should only affect class attributes.

#### MESSAGE

It appears you are using the @sorted-attributes directive and the class variables are unsorted. See the lint autofix suggestion.

#### AUTOFIX

Yes


#### VALID

```python
class MyConstants:
    """
    @sorted-attributes
    """
    A = 'zzz123'
    B = 'aaa234'

class MyUnsortedConstants:
    B = 'aaa234'
    A = 'zzz123'
```

#### INVALID

```python
class MyUnsortedConstants:
    """
    @sorted-attributes
    """
    z = "hehehe"
    B = 'aaa234'
    A = 'zzz123'
    cab = "foo bar"
    Daaa = "banana"

    @classmethod
    def get_foo(cls) -> str:
        return "some random thing"

# suggested fix
class MyUnsortedConstants:
    """
    @sorted-attributes
    """
    A = 'zzz123'
    B = 'aaa234'
    Daaa = "banana"
    cab = "foo bar"
    z = "hehehe"

    @classmethod
    def get_foo(cls) -> str:
        return "some random thing"

```
### UseLintFixmeComment

To silence a lint warning, use ``lint-fixme`` (when plans to fix the issue later) or ``lint-ignore``
(when the lint warning is not valid) comments.
The comment requires to be in a standalone comment line and follows the format ``lint-fixme: RULE_NAMES EXTRA_COMMENTS``.
It suppresses the lint warning with the RULE_NAMES in the next line.
RULE_NAMES can be one or more lint rule names separated by comma.
``noqa`` is deprecated and not supported because explicitly providing lint rule names to be suppressed
in lint-fixme comment is preferred over implicit noqa comments. Implicit noqa suppression comments
sometimes accidentally silence warnings unexpectedly.

#### MESSAGE

noqa is deprecated. Use `lint-fixme` or `lint-ignore` instead.


#### VALID

```python
# lint-fixme: UseFstringRule
"%s" % "hi"
```
```python
# lint-ignore: UsePlusForStringConcatRule
'ab' 'cd'
```

#### INVALID

```python
fn() # noqa
```
```python
(
 1,
 2,  # noqa
)
```
### UseTypesFromTyping

Enforces the use of types from the ``typing`` module in type annotations in place
of ``builtins.{builtin_type}`` since the type system doesn't recognize the latter
as a valid type before Python ``3.10``.

#### AUTOFIX

Yes

#### PYTHON_VERSION

`'< 3.10'`

#### VALID

```python
def function(list: List[str]) -> None:
    pass
```
```python
def function() -> None:
    thing: Dict[str, str] = {}
```

#### INVALID

```python
from typing import List
def whatever(list: list[str]) -> None:
    pass

# suggested fix
from typing import List
def whatever(list: List[str]) -> None:
    pass

```
```python
def function(list: list[str]) -> None:
    pass
```
### VariadicCallableSyntax

Callable types with arbitrary parameters should be written as `Callable[..., T]`.

#### AUTOFIX

Yes


#### VALID

```python
from typing import Callable
x: Callable[[int], int]
```
```python
from typing import Callable
x: Callable[[int, int, ...], int]
```

#### INVALID

```python
from typing import Callable
x: Callable[[...], int] = ...

# suggested fix
from typing import Callable
x: Callable[..., int] = ...

```
```python
import typing as t
x: t.Callable[[...], int] = ...

# suggested fix
import typing as t
x: t.Callable[..., int] = ...

```

## `rattle.rules.fixit_extra`

```{automodule} rattle.rules.fixit_extra
```

- `AvoidOrInExcept`
- `CollapseIsinstanceChecks`
- `ComparePrimitivesByEqual`
- `CompareSingletonPrimitivesByIs`
- `DeprecatedABCImport`
- `DeprecatedUnittestAsserts`
- `NoAssertTrueForComparisons`
- `NoInheritFromObject`
- `NoRedundantArgumentsSuper`
- `NoRedundantFString`
- `NoRedundantLambda`
- `NoRedundantListComprehension`
- `NoStringTypeAnnotation`
- `ReplaceUnionWithOptional`
- `RewriteToComprehension`
- `RewriteToLiteral`
- `UseAssertIn`
- `UseAssertIsNotNone`
- `UseAsyncSleepInAsyncDef`
- `UseClsInClassmethod`
- `UseFstring`

### AvoidOrInExcept

Discourages use of ``or`` in except clauses. If an except clause needs to catch multiple exceptions,
they must be expressed as a parenthesized tuple, for example:
``except (ValueError, TypeError)``
(https://docs.python.org/3/tutorial/errors.html#handling-exceptions).

When ``or`` is used, only the first operand exception type of the conditional statement will be caught.
For example::

    In [1]: class Exc1(Exception):
        ...:     pass
        ...:

    In [2]: class Exc2(Exception):
        ...:     pass
        ...:

    In [3]: try:
        ...:     raise Exception()
        ...: except Exc1 or Exc2:
        ...:     print("caught!")
        ...:
    ---------------------------------------------------------------------------
    Exception                                 Traceback (most recent call last)
    <ipython-input-3-3340d66a006c> in <module>
        1 try:
    ----> 2     raise Exception()
        3 except Exc1 or Exc2:
        4     print("caught!")
        5

    Exception:

    In [4]: try:
        ...:     raise Exc1()
        ...: except Exc1 or Exc2:
        ...:     print("caught!")
        ...:
        caught!

    In [5]: try:
        ...:     raise Exc2()
        ...: except Exc1 or Exc2:
        ...:     print("caught!")
        ...:
    ---------------------------------------------------------------------------
    Exc2                                      Traceback (most recent call last)
    <ipython-input-5-5d29c1589cc0> in <module>
        1 try:
    ----> 2     raise Exc2()
        3 except Exc1 or Exc2:
        4     print("caught!")
        5

    Exc2:

#### MESSAGE

Avoid using 'or' in an except block. For example:'except ValueError or TypeError' only catches 'ValueError'. Instead, use parentheses, 'except (ValueError, TypeError)'


#### VALID

```python
try:
    print()
except (ValueError, TypeError) as err:
    pass
```

#### INVALID

```python
try:
    print()
except ValueError or TypeError:
    pass
```
### CollapseIsinstanceChecks

The built-in ``isinstance`` function, instead of a single type,
can take a tuple of types and check whether given target suits
any of them. Rather than chaining multiple ``isinstance`` calls
with a boolean-or operation, a single ``isinstance`` call where
the second argument is a tuple of all types can be used.

#### MESSAGE

Multiple isinstance calls with the same target but different types can be collapsed into a single call with a tuple of types.

#### AUTOFIX

Yes


#### VALID

```python
foo() or foo()
```
```python
foo(x, y) or foo(x, z)
```

#### INVALID

```python
isinstance(x, y) or isinstance(x, z)

# suggested fix
isinstance(x, (y, z))

```
```python
isinstance(x, y) or isinstance(x, z) or isinstance(x, q)

# suggested fix
isinstance(x, (y, z, q))

```
### ComparePrimitivesByEqual

Enforces the use of ``==`` and ``!=`` in comparisons to primitives rather than ``is`` and ``is not``.
The ``==`` operator checks equality (https://docs.python.org/3/reference/datamodel.html#object.__eq__),
while ``is`` checks identity (https://docs.python.org/3/reference/expressions.html#is).

#### MESSAGE

Don't use `is` or `is not` to compare primitives, as they compare references. Use == or != instead.

#### AUTOFIX

Yes


#### VALID

```python
a == 1
```
```python
a == '1'
```

#### INVALID

```python
a is 1

# suggested fix
a == 1

```
```python
a is '1'

# suggested fix
a == '1'

```
### CompareSingletonPrimitivesByIs

Enforces the use of `is` and `is not` in comparisons to singleton primitives (None, True, False) rather than == and !=.
The == operator checks equality, when in this scenario, we want to check identity.
See Flake8 rules E711 (https://www.flake8rules.com/rules/E711.html) and E712 (https://www.flake8rules.com/rules/E712.html).

#### MESSAGE

Comparisons to singleton primitives should not be done with == or !=, as they check equality rather than identity. Use `is` or `is not` instead.

#### AUTOFIX

Yes


#### VALID

```python
if x: pass
```
```python
if not x: pass
```

#### INVALID

```python
x != True

# suggested fix
x is not True

```
```python
x != False

# suggested fix
x is not False

```
### DeprecatedABCImport

Checks for the use of the deprecated collections ABC import. Since python 3.3,
the Collections Abstract Base Classes (ABC) have been moved to `collections.abc`.
These ABCs are import errors starting in Python 3.10.

#### MESSAGE

ABCs must be imported from collections.abc

#### AUTOFIX

Yes

#### PYTHON_VERSION

`'>= 3.3'`

#### VALID

```python
from collections.abc import Container
```
```python
from collections.abc import Container, Hashable
```

#### INVALID

```python
from collections import Container

# suggested fix
from collections.abc import Container

```
```python
from collections import Container, Hashable

# suggested fix
from collections.abc import Container, Hashable

```
### DeprecatedUnittestAsserts

Discourages the use of various deprecated unittest.TestCase functions.

See https://docs.python.org/3/library/unittest.html#deprecated-aliases

#### MESSAGE

{deprecated} is deprecated, use {replacement} instead

#### AUTOFIX

Yes


#### VALID

```python
self.assertEqual(a, b)
```
```python
self.assertNotEqual(a, b)
```

#### INVALID

```python
self.assertEquals(a, b)

# suggested fix
self.assertEqual(a, b)

```
```python
self.assertNotEquals(a, b)

# suggested fix
self.assertNotEqual(a, b)

```
### NoAssertTrueForComparisons

Finds incorrect use of ``assertTrue`` when the intention is to compare two values.
These calls are replaced with ``assertEqual``.
Comparisons with True, False and None are replaced with one-argument
calls to ``assertTrue``, ``assertFalse`` and ``assertIsNone``.

#### MESSAGE

"assertTrue" does not compare its arguments, use "assertEqual" or other appropriate functions.

#### AUTOFIX

Yes


#### VALID

```python
self.assertTrue(a == b)
```
```python
self.assertTrue(data.is_valid(), "is_valid() method")
```

#### INVALID

```python
self.assertTrue(a, 3)

# suggested fix
self.assertEqual(a, 3)

```
```python
self.assertTrue(hash(s[:4]), 0x1234)

# suggested fix
self.assertEqual(hash(s[:4]), 0x1234)

```
### NoInheritFromObject

In Python 3, a class is inherited from ``object`` by default.
Explicitly inheriting from ``object`` is redundant, so removing it keeps the code simpler.

#### MESSAGE

Inheriting from object is a no-op.  'class Foo:' is just fine =)

#### AUTOFIX

Yes


#### VALID

```python
class A(something):    pass
```
```python
class A:
    pass
```

#### INVALID

```python
class B(object):
    pass

# suggested fix
class B:
    pass

```
```python
class B(object, A):
    pass

# suggested fix
class B(A):
    pass

```
### NoRedundantArgumentsSuper

Remove redundant arguments when using super for readability.

#### MESSAGE

Do not use arguments when calling super for the parent class. See https://www.python.org/dev/peps/pep-3135/

#### AUTOFIX

Yes


#### VALID

```python
class Foo(Bar):
    def foo(self, bar):
        super().foo(bar)
```
```python
class Foo(Bar):
    def foo(self, bar):
        super(Bar, self).foo(bar)
```

#### INVALID

```python
class Foo(Bar):
    def foo(self, bar):
        super(Foo, self).foo(bar)

# suggested fix
class Foo(Bar):
    def foo(self, bar):
        super().foo(bar)

```
```python
class Foo(Bar):
    @classmethod
    def foo(cls, bar):
        super(Foo, cls).foo(bar)

# suggested fix
class Foo(Bar):
    @classmethod
    def foo(cls, bar):
        super().foo(bar)

```
### NoRedundantFString

Remove redundant f-string without placeholders.

#### MESSAGE

f-string doesn't have placeholders, remove redundant f-string.

#### AUTOFIX

Yes


#### VALID

```python
good: str = "good"
```
```python
good: str = f"with_arg{arg}"
```

#### INVALID

```python
bad: str = f"bad" + "bad"

# suggested fix
bad: str = "bad" + "bad"

```
```python
bad: str = f'bad'

# suggested fix
bad: str = 'bad'

```
### NoRedundantLambda

A lambda function which has a single objective of
passing all it is arguments to another callable can
be safely replaced by that callable.

#### AUTOFIX

Yes


#### VALID

```python
lambda x: foo(y)
```
```python
lambda x: foo(x, y)
```

#### INVALID

```python
lambda: self.func()

# suggested fix
self.func

```
```python
lambda x: foo(x)

# suggested fix
foo

```
### NoRedundantListComprehension

A derivative of flake8-comprehensions's C407 rule.

#### AUTOFIX

Yes


#### VALID

```python
any(val for val in iterable)
```
```python
all(val for val in iterable)
```

#### INVALID

```python
any([val for val in iterable])

# suggested fix
any(val for val in iterable)

```
```python
all([val for val in iterable])

# suggested fix
all(val for val in iterable)

```
### NoStringTypeAnnotation

Enforce the use of type identifier instead of using string type hints for simplicity and better syntax highlighting.
Starting in Python 3.7, ``from __future__ import annotations`` can postpone evaluation of type annotations
`PEP 563 <https://www.python.org/dev/peps/pep-0563/#forward-references>`_
and thus forward references no longer need to use string annotation style.

#### MESSAGE

String type hints are no longer necessary in Python, use the type identifier directly.

#### AUTOFIX

Yes


#### VALID

```python
from a.b import Class

def foo() -> Class:
    return Class()
```
```python
import typing
from a.b import Class

def foo() -> typing.Type[Class]:
    return Class
```

#### INVALID

```python
from __future__ import annotations

from a.b import Class

def foo() -> "Class":
    return Class()

# suggested fix
from __future__ import annotations

from a.b import Class

def foo() -> Class:
    return Class()

```
```python
from __future__ import annotations

from a.b import Class

async def foo() -> "Class":
    return await Class()

# suggested fix
from __future__ import annotations

from a.b import Class

async def foo() -> Class:
    return await Class()

```
### ReplaceUnionWithOptional

Enforces the use of ``Optional[T]`` over ``Union[T, None]`` and ``Union[None, T]``.
See https://docs.python.org/3/library/typing.html#typing.Optional to learn more about Optionals.

#### MESSAGE

`Optional[T]` is preferred over `Union[T, None]` or `Union[None, T]`. Learn more: https://docs.python.org/3/library/typing.html#typing.Optional

#### AUTOFIX

Yes


#### VALID

```python
def func() -> Optional[str]:
    pass
```
```python
def func() -> Optional[Dict]:
    pass
```

#### INVALID

```python
def func() -> Union[str, None]:
    pass
```
```python
from typing import Optional
def func() -> Union[Dict[str, int], None]:
    pass

# suggested fix
from typing import Optional
def func() -> Optional[Dict[str, int]]:
    pass

```
### RewriteToComprehension

A derivative of flake8-comprehensions's C400-C402 and C403-C404.
Comprehensions are more efficient than functions calls. This C400-C402
suggest to use `dict/set/list` comprehensions rather than respective
function calls whenever possible. C403-C404 suggest to remove unnecessary
list comprehension in a set/dict call, and replace it with set/dict
comprehension.

#### AUTOFIX

Yes


#### VALID

```python
[val for val in iterable]
```
```python
{val for val in iterable}
```

#### INVALID

```python
list(val for val in iterable)

# suggested fix
[val for val in iterable]

```
```python
list(val for row in matrix for val in row)

# suggested fix
[val for row in matrix for val in row]

```
### RewriteToLiteral

A derivative of flake8-comprehensions' C405-C406 and C409-C410. It's
unnecessary to use a list or tuple literal within a call to tuple, list,
set, or dict since there is literal syntax for these types.

#### AUTOFIX

Yes


#### VALID

```python
(1, 2)
```
```python
()
```

#### INVALID

```python
tuple([1, 2])

# suggested fix
(1, 2)

```
```python
tuple((1, 2))

# suggested fix
(1, 2)

```
### UseAssertIn

Discourages use of ``assertTrue(x in y)`` and ``assertFalse(x in y)``
as it is deprecated (https://docs.python.org/3.8/library/unittest.html#deprecated-aliases).
Use ``assertIn(x, y)`` and ``assertNotIn(x, y)``) instead.

#### MESSAGE

Use assertIn/assertNotIn instead of assertTrue/assertFalse for inclusion check.
See https://docs.python.org/3/library/unittest.html#unittest.TestCase.assertIn)

#### AUTOFIX

Yes


#### VALID

```python
self.assertIn(a, b)
```
```python
self.assertIn(f(), b)
```

#### INVALID

```python
self.assertTrue(a in b)

# suggested fix
self.assertIn(a, b)

```
```python
self.assertTrue(f() in b)

# suggested fix
self.assertIn(f(), b)

```
### UseAssertIsNotNone

Discourages use of ``assertTrue(x is not None)`` and ``assertFalse(x is not None)`` as it is deprecated (https://docs.python.org/3.8/library/unittest.html#deprecated-aliases).
Use ``assertIsNotNone(x)`` and ``assertIsNone(x)``) instead.

#### MESSAGE

"assertTrue" and "assertFalse" are deprecated. Use "assertIsNotNone" and "assertIsNone" instead.
See https://docs.python.org/3.8/library/unittest.html#deprecated-aliases

#### AUTOFIX

Yes


#### VALID

```python
self.assertIsNotNone(x)
```
```python
self.assertIsNone(x)
```

#### INVALID

```python
self.assertTrue(a is not None)

# suggested fix
self.assertIsNotNone(a)

```
```python
self.assertTrue(not x is None)

# suggested fix
self.assertIsNotNone(x)

```
### UseAsyncSleepInAsyncDef

Detect if asyncio.sleep is used in an async function.

#### MESSAGE

Use asyncio.sleep in async function


#### VALID

```python
import time
def func():
    time.sleep(1)
```
```python
from time import sleep
def func():
    sleep(1)
```

#### INVALID

```python
import time
async def func():
    time.sleep(1)
```
```python
from time import sleep
async def func():
    sleep(1)
```
### UseClsInClassmethod

Enforces using ``cls`` as the first argument in a ``@classmethod``.

#### MESSAGE

When using @classmethod, the first argument must be `cls`.

#### AUTOFIX

Yes


#### VALID

```python
class foo:
    # classmethod with cls first arg.
    @classmethod
    def cm(cls, a, b, c):
        pass
```
```python
class foo:
    # non-classmethod with non-cls first arg.
    def nm(self, a, b, c):
        pass
```

#### INVALID

```python
class foo:
    # No args at all.
    @classmethod
    def cm():
        pass

# suggested fix
class foo:
    # No args at all.
    @classmethod
    def cm(cls):
        pass

```
```python
class foo:
    # Single arg + reference.
    @classmethod
    def cm(a):
        return a

# suggested fix
class foo:
    # Single arg + reference.
    @classmethod
    def cm(cls):
        return cls

```
### UseFstring

Encourages the use of f-string instead of %-formatting or .format() for high code quality and efficiency.

Following two cases not covered:

1. arguments length greater than 30 characters: for better readability reason
    For example:

    1: this is the answer: %d" % (a_long_function_call() + b_another_long_function_call())
    2: f"this is the answer: {a_long_function_call() + b_another_long_function_call()}"
    3: result = a_long_function_call() + b_another_long_function_call()
    f"this is the answer: {result}"

    Line 1 is more readable than line 2. Ideally, we'd like developers to manually fix this case to line 3

2. only %s placeholders are linted against for now. We leave it as future work to support other placeholders.
    For example, %d raises TypeError for non-numeric objects, whereas f"{x:d}" raises ValueError.
    This discrepancy in the type of exception raised could potentially break the logic in the code where the exception is handled

#### MESSAGE

Do not use printf style formatting or .format(). Use f-string instead to be more readable and efficient. See https://www.python.org/dev/peps/pep-0498/

#### AUTOFIX

Yes


#### VALID

```python
somebody='you'; f"Hey, {somebody}."
```
```python
"hey"
```

#### INVALID

```python
"Hey, {somebody}.".format(somebody="you")
```
```python
"%s" % "hi"

# suggested fix
f"{'hi'}"

```
