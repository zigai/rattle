(quickstart)=

# Quick Start

## Setup

Install Rattle from PyPI:

```console
$ pip install rattle-lint
```

By default, Rattle runs with no enabled lint rules. Enable rule collections in
`pyproject.toml`:

```toml
[tool.rattle]
enable = ["fixit"]
```

If you want to customize the enabled rules, add new rules, or disable specific
ones, see the {ref}`configuration` guide.

Rattle also supports editor integrations, LSP, and pre-commit. See the
{ref}`integrations` guide for details.

## Usage

See lints and suggested changes for a set of source files:

```console
$ rattle lint <path>
```

Apply suggested changes on those same files automatically:

```console
$ rattle fix <path>
```

If given directories, Rattle will recurse them automatically, finding `.py`
files while obeying the repo's global `.gitignore`.

See the {ref}`commands` reference for more details.

## Example

Given the following code:

```python
# handlers.py

from typing import Callable


handler: Callable[[...], int]
```

With `fixit` enabled, running Rattle shows the rule violation:

```console
$ rattle lint handlers.py
use-callable-ellipsis [*] Use Callable[..., T] instead of Callable[[...], T].
 --> handlers.py:4:10
  |
3 |
4 | handler: Callable[[...], int]
  |          ^^^^^^^^^^^^^^^^^^^^
  |
help: Apply the available autofix
```

You can also see suggested changes by passing `--diff`:

```console
$ rattle lint --diff handlers.py
use-callable-ellipsis [*] Use Callable[..., T] instead of Callable[[...], T].
 --> handlers.py:4:10
  |
3 |
4 | handler: Callable[[...], int]
  |          ^^^^^^^^^^^^^^^^^^^^
  |
help: Apply the available autofix
--- a/handlers.py
+++ b/handlers.py
@@ -3,2 +3,2 @@

-handler: Callable[[...], int]
+handler: Callable[..., int]
```

(suppressions)=

## Silencing Errors

For lint rules without autofixes, it may still be useful to silence individual
errors. A `# rattle: ignore[...]` comment, either as a trailing inline comment
or as a dedicated comment line above the code, will silence the matching
violation:

```python
class Foo(NamedTuple):  # rattle: ignore[no-named-tuple]
    ...

# rattle: ignore[no-named-tuple]
class Bar(NamedTuple):
    ...
```

By providing one or more rule names, separated by commas, Rattle can still
report issues triggered by other rules that have not been listed in the
comment, but this is not required.

If no rule name is listed, Rattle will silence all rules associated with that
comment:

```python
class Foo(object):  # rattle: ignore
    ...
```

## Custom Rules

Rattle makes it easy to write and enable new lint rules directly in your
existing codebase alongside the code they lint.

Lint rules in Rattle are built on top of
[LibCST](https://libcst.readthedocs.io/), using a {class}`~rattle.LintRule`
to combine visitors and tests together in a single unit. A simple rule looks
like this:

```python
# teambread/rules/hollywood.py

import libcst

from rattle import Invalid, LintRule, RuleSetting, Valid


class HollywoodNameRule(LintRule):
    SETTINGS = {
        "preferred_name": RuleSetting(str, default="Mary"),
    }

    VALID = [
        Valid('name = "Susan"'),
    ]
    INVALID = [
        Invalid('name = "Paul"'),
    ]

    def visit_SimpleString(self, node: libcst.SimpleString) -> None:
        if node.value in ('"Paul"', "'Paul'"):
            preferred_name = self.settings["preferred_name"]
            self.report(node, f'Use "{preferred_name}" instead')
```

Rules can suggest autofixes by including a replacement CST node when reporting
an error:

```python
def visit_SimpleString(self, node: libcst.SimpleString) -> None:
    if node.value in ('"Paul"', "'Paul'"):
        new_node = libcst.SimpleString('"Mary"')
        self.report(node, "It's underproved!", replacement=new_node)
```

### Optional AST analysis

Rules that need Python's compiler-normalized syntax can request a cached AST
through {class}`~rattle.AstProvider`. LibCST remains responsible for traversal,
reporting, ignore comments, and autofixes:

```python
import ast

import libcst
from libcst.metadata import PositionProvider

from rattle import AstContext, AstProvider, CodeRange, LintRule


class LargeIntegerRule(LintRule):
    METADATA_DEPENDENCIES = (AstProvider, PositionProvider)

    def __init__(self) -> None:
        super().__init__()
        self.large_integer_ranges: set[CodeRange] = set()

    def visit_Module(self, node: libcst.Module) -> None:
        context = self.get_metadata(AstProvider, node, None)
        assert isinstance(context, AstContext)
        self.large_integer_ranges = {
            context.code_range(ast_node)
            for ast_node in ast.walk(context.tree)
            if isinstance(ast_node, ast.Constant)
            and isinstance(ast_node.value, int)
            and ast_node.value > 1_000
        }

    def visit_Integer(self, node: libcst.Integer) -> None:
        if self.get_metadata(PositionProvider, node) in self.large_integer_ranges:
            self.report(node, "Avoid large integer literals")
```

{class}`~rattle.AstContext.code_range` converts CPython AST byte offsets into
Rattle character-based ranges, including for non-ASCII source. Reporting still
uses a CST node so local `# rattle: ignore` directives and CST replacements keep
their existing behavior. Rattle does not automatically map AST nodes to CST
nodes.

AST parsing uses the Python interpreter running Rattle and includes legacy
`# type:` comments. If that interpreter cannot parse the source, or a type
comment is misplaced, Rattle reports an {class}`~rattle.AstParseError`. This can
happen even when LibCST supports the target syntax, so AST analysis should only
be requested by rules that need it.

The best lint rules provide a clear error message, a suggested replacement, and
multiple valid and invalid test cases that exercise important edge cases.

Once written, the rule can be enabled by adding it to the project's
{ref}`configuration`:

```toml
# teambread/pyproject.toml

[tool.rattle]
enable = [
    ".rules.hollywood",
    ".rules",
]
```

```{note}
The leading `.` is required when using in-repo, or "local", lint rules with a
module path relative to the directory containing the config file. This allows
Rattle to locate and import the rule without installing a plugin into the
environment.

If your custom rule imports other libraries from the repo, those imports must
be relative imports, and they must stay within the same directory tree as the
configuration file.
```

Once enabled, Rattle can run the new rule against the codebase:

```python
# teambread/sourdough/baker.py

def main():
    name = "Paul"
    print(f"hello {name}")
```

```console
$ rattle lint --diff sourdough/baker.py
hollywood-name-rule [*] It's underproved!
 --> sourdough/baker.py:2:12
  |
1 | def main():
2 |     name = "Paul"
  |            ^^^^^^
3 |     print(f"hello {name}")
  |
help: Apply the available autofix
--- a/baker.py
+++ b/baker.py
@@ -1,3 +1,3 @@
 def main():
-    name = "Paul"
+    name = "Mary"
     print(f"hello {name}")
```

Note that the `lint` command only shows lint errors and suggested changes.
The `fix` command applies those changes to the codebase:

```console
$ rattle fix sourdough/baker.py
1 file checked, 1 fix applied
```

Pass `--interactive` to confirm each available autofix one at a time.

Now that the suggested changes have been applied, the codebase is clean:

```console
$ rattle lint sourdough/baker.py
1 file clean
```
