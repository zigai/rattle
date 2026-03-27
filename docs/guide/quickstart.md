(quickstart)=

# Quick Start

## Setup

Install Rattle from PyPI:

```console
$ pip install rattle-lint
```

By default, Rattle enables the lint rules that ship with Rattle, all of which
are part of `rattle.rules`.

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
# custom_object.py

class Foo(object):
    def bar(self, value: str) -> str:
        return "value is {}".format(value)
```

Running Rattle shows two separate lint errors:

```console
$ rattle lint custom_object.py
NoInheritFromObject [*] Inheriting from object is a no-op.  'class Foo:' is just fine =)
 --> custom_object.py:1:1
  |
1 | class Foo(object):
  | ^^^^^^^^^^^^^^^^^^
2 |     def bar(self, value: str) -> str:
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
3 |         return "value is {}".format(value)
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |
help: Apply the available autofix

UseFstring Do not use printf style formatting or .format(). Use f-string instead to be more readable and efficient. See https://www.python.org/dev/peps/pep-0498/
 --> custom_object.py:3:16
  |
2 |     def bar(self, value: str) -> str:
3 |         return "value is {}".format(value)
  |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |
```

You can also see suggested changes by passing `--diff`:

```console
$ rattle lint --diff custom_object.py
NoInheritFromObject [*] Inheriting from object is a no-op.  'class Foo:' is just fine =)
 --> custom_object.py:1:1
  |
1 | class Foo(object):
  | ^^^^^^^^^^^^^^^^^^
2 |     def bar(self, value: str) -> str:
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
3 |         return "value is {}".format(value)
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |
help: Apply the available autofix
--- a/custom_object.py
+++ b/custom_object.py
@@ -1,2 +1,2 @@
-class Foo(object):
+class Foo:
     def bar(self, value: str) -> str:

UseFstring Do not use printf style formatting or .format(). Use f-string instead to be more readable and efficient. See https://www.python.org/dev/peps/pep-0498/
 --> custom_object.py:3:16
  |
2 |     def bar(self, value: str) -> str:
3 |         return "value is {}".format(value)
  |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |
```

(suppressions)=

## Silencing Errors

For lint rules without autofixes, it may still be useful to silence individual
errors. A simple `# lint-ignore` or `# lint-fixme` comment, either as a
trailing inline comment or as a dedicated comment line above the code, will
silence the matching violation:

```python
class Foo(object):  # lint-fixme: NoInheritFromObject
    ...

# lint-ignore: NoInheritFromObject
class Bar(object):
    ...
```

By providing one or more rule names, separated by commas, Rattle can still
report issues triggered by other rules that have not been listed in the
comment, but this is not required.

If no rule name is listed, Rattle will silence all rules associated with that
comment:

```python
class Foo(object):  # lint-ignore
    ...
```

### "ignore" vs "fixme"

Both comment directives achieve the same result: silencing errors for a
particular statement of code. The choice between them is left to the user, but
they are intended to carry different meanings:

- `# lint-fixme` is for errors that need to be corrected or reviewed later,
  but should be silenced temporarily for CI or similar circumstances.
- `# lint-ignore` is for false positives or intentionally structured code where
  the lint error cannot be avoided.

Future versions of Rattle may offer reporting or similar tools that treat
`fixme` directives differently from `ignore` directives.

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
HollywoodName [*] It's underproved!
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
$ rattle fix --automatic sourdough/baker.py
HollywoodName [*] It's underproved!
 --> sourdough/baker.py:2:12
  |
1 | def main():
2 |     name = "Paul"
  |            ^^^^^^
3 |     print(f"hello {name}")
  |
help: Apply the available autofix
1 file checked, 1 file with errors, 1 auto-fix available, 1 fix applied
```

By default, the `fix` command prompts interactively for each available change,
and lets the user accept or decline it.

Now that the suggested changes have been applied, the codebase is clean:

```console
$ rattle lint sourdough/baker.py
1 file clean
```
