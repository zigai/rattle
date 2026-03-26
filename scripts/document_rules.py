# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import ast
import inspect
from pathlib import Path
from textwrap import dedent, indent

from jinja2 import Template

from rattle.config import BUILTIN_RULE_MODULES, find_rules
from rattle.ftypes import QualifiedRule

RULES_DOC = Path(__file__).parent.parent / "docs" / "guide" / "builtins.md"

PAGE_TPL = Template(
    r"""
<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(builtin-rules)=

# Built-in Rules

{% for pkg in packages %}
- `{{ pkg.module }}`
{% endfor %}

{% for pkg, rules in packages.items() %}

## `{{ pkg.module }}`

```{automodule} {{ pkg.module }}
```

{% for rule in rules %}
- `{{ rule.__name__ }}`
{% endfor %}

{% for rule in rules %}
### {{ rule.__name__ }}

{{ redent(rule_doc(rule), "") }}

{% if rule.CODE %}
#### CODE

`{{ rule.CODE }}`

{% endif %}
{% if rule.ALIASES %}
#### ALIASES

{% for alias in rule.ALIASES %}
- `{{ alias }}`
{% endfor %}

{% endif %}
{% if rule.MESSAGE %}
#### MESSAGE

{{ redent(rule.MESSAGE, "") }}

{% endif %}
{% if rule.AUTOFIX %}
#### AUTOFIX

Yes

{% endif %}
{% if rule.PYTHON_VERSION %}
#### PYTHON_VERSION

`{{ repr(rule.PYTHON_VERSION) }}`
{% endif %}

#### VALID

{% for case in rule.VALID[:2] %}
```python
{{ redent(case.code, "") }}
```
{% endfor %}

#### INVALID

{% for case in rule.INVALID[:2] %}
```python
{{ redent(case.code, "") }}
{% if case.expected_replacement %}

# suggested fix
{{ redent(case.expected_replacement, "") }}

{% endif %}
```
{% endfor %}
{% endfor %}
{% endfor %}
    """,
    trim_blocks=True,
    lstrip_blocks=True,
)


def redent(value: str, prefix: str = "") -> str:
    return indent(dedent(value).strip("\n"), prefix).rstrip()


def rule_doc(rule: type[object]) -> str:
    if rule.__doc__:
        return rule.__doc__

    source = inspect.getsource(rule)
    module = ast.parse(source)
    class_def = module.body[0]
    assert isinstance(class_def, ast.ClassDef)

    for statement in class_def.body:
        if (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        ):
            return statement.value.value

    return ""


def main() -> None:
    qrules = sorted(QualifiedRule(r) for r in BUILTIN_RULE_MODULES)
    packages = {qrule: list(find_rules(qrule)) for qrule in qrules}

    rendered = PAGE_TPL.render(
        dedent=dedent,
        indent=indent,
        redent=redent,
        rule_doc=rule_doc,
        hasattr=hasattr,
        len=len,
        repr=repr,
        packages=packages,
    )
    RULES_DOC.write_text(rendered.rstrip() + "\n")


if __name__ == "__main__":
    main()
