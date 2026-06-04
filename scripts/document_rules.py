# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import ast
import inspect
import re
import shutil
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent, indent

from jinja2 import Template

from rattle.config import BUILTIN_RULE_PACKS, find_rules
from rattle.ftypes import Invalid, QualifiedRule, Valid
from rattle.rule import LintRule, RuleSetting

DOCS_DIR = Path(__file__).parent.parent / "docs"
RULES_INDEX_DOC = DOCS_DIR / "guide" / "builtins.md"
RULES_CATEGORY_DIR = DOCS_DIR / "guide" / "rule-packs"
RULES_DETAIL_DIR = DOCS_DIR / "guide" / "rules"

CATEGORY_TITLES = {
    "blank_lines": "Blank-line rules",
    "fixit": "Core Fixit rules",
    "fixit_extra": "Additional Fixit rules",
}
CATEGORY_DESCRIPTIONS = {
    "blank_lines": "Whitespace and statement-separation rules.",
    "fixit": "Core lint rules inherited from Fixit.",
    "fixit_extra": "Additional Fixit-derived rules that can be enabled separately.",
}

INDEX_TPL = Template(
    r"""
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

{% for category in categories %}
## {{ category.title }}

{{ category.description }}

Enable with:

```toml
enable = ["{{ category.pack }}"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
{% for rule in category.rules -%}
| [{{ rule.name }}]({{ rule.path }}) | {{ rule.message_short }} | {{ rule.python_version }} | {{ rule.autofix_icon }} |
{% endfor %}

{% endfor %}
```{toctree}
:hidden:
:maxdepth: 1

{% for category in categories -%}
{{ category.toctree_path }}
{% endfor %}
```
    """,
    trim_blocks=True,
    lstrip_blocks=True,
)

CATEGORY_TPL = Template(
    """\
---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-pack-{{ category.slug }})=

# {{ category.title }}

{{ category.description }}

Enable with:

```toml
enable = ["{{ category.pack }}"]
```

| Rule | Message | Python | Autofix |
| --- | --- | --- | :---: |
{% for rule in category.rules -%}
| [{{ rule.name }}](../{{ rule.path }}) | {{ rule.message_short }} | {{ rule.python_version }} | {{ rule.autofix_icon }} |
{% endfor %}
    """,
    trim_blocks=True,
    lstrip_blocks=True,
)

DETAIL_TPL = Template(
    """\
---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-{{ rule.slug }})=

# {{ rule.name }}

{{ rule.description }}

<p class="rule-metadata">
  <span>Pack: <code>{{ rule.pack }}</code></span>
  <span>Module: <code>{{ rule.module }}</code></span>
  <span>Autofix: {{ rule.autofix }}</span>
  <span>Python: {{ rule.python_version }}</span>
  {% if rule.tags -%}<span>Tags: {{ rule.tags }}</span>{% endif %}
</p>

{% if rule.message %}
## Message

{{ rule.message }}
{% endif %}

{% if rule.settings %}
## Settings

| Setting | Type | Default |
| --- | --- | --- |
{% for setting in rule.settings -%}
| `{{ setting.name }}` | `{{ setting.value_type }}` | `{{ setting.default }}` |
{% endfor %}

{% endif %}
## Valid examples

{% for case in rule.valid_examples %}
```python
{{ case }}
```
{% endfor %}

## Invalid examples

{% for case in rule.invalid_examples %}
```python
{{ case.code }}
{% if case.replacement %}

# suggested fix
{{ case.replacement }}
{% endif %}
```
{% endfor %}
    """,
    trim_blocks=True,
    lstrip_blocks=True,
)


@dataclass(frozen=True)
class SettingDoc:
    name: str
    value_type: str
    default: str


@dataclass(frozen=True)
class InvalidExampleDoc:
    code: str
    replacement: str


@dataclass(frozen=True)
class RuleDoc:
    name: str
    slug: str
    module: str
    pack: str
    selector: str
    path: str
    toctree_path: str
    description: str
    message: str
    message_short: str
    autofix: str
    autofix_icon: str
    python_version: str
    tags: str
    settings: Sequence[SettingDoc]
    valid_examples: Sequence[str]
    invalid_examples: Sequence[InvalidExampleDoc]


@dataclass(frozen=True)
class CategoryDoc:
    pack: str
    module: str
    title: str
    description: str
    slug: str
    toctree_path: str
    rules: Sequence[RuleDoc]


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


def slugify(value: str) -> str:
    words = re.sub(r"(?<!^)(?=[A-Z])", "-", value).lower()
    return re.sub(r"[^a-z0-9]+", "-", words).strip("-")


def markdown_table_cell(value: str) -> str:
    return " ".join(value.split()).replace("|", "\\|")


def example_code(case: str | Valid | Invalid) -> str:
    if isinstance(case, (Valid, Invalid)):
        return redent(case.code)
    return redent(case)


def expected_replacement(case: str | Invalid) -> str:
    if isinstance(case, Invalid) and case.expected_replacement:
        return redent(case.expected_replacement)
    return ""


def type_name(value: object) -> str:
    name = getattr(value, "__name__", None)
    if name is not None:
        return name
    return repr(value)


def setting_default(setting: RuleSetting) -> str:
    default = setting.default
    if type(default) is object:
        return "required"
    return repr(default)


def build_rule_doc(rule: type[LintRule], *, pack: str) -> RuleDoc:
    name = rule.__name__
    slug = slugify(name)
    description = redent(rule_doc(rule))
    message = redent(str(getattr(rule, "MESSAGE", "")))
    message_short = markdown_table_cell(message or "—")
    python_version = getattr(rule, "PYTHON_VERSION", "") or "Any"
    settings = [
        SettingDoc(
            name=name,
            value_type=type_name(setting.value_type),
            default=setting_default(setting),
        )
        for name, setting in sorted(rule.SETTINGS.items())
    ]
    valid_examples = [example_code(case) for case in getattr(rule, "VALID", ())[:2]]
    invalid_examples = [
        InvalidExampleDoc(
            code=example_code(case),
            replacement=expected_replacement(case),
        )
        for case in getattr(rule, "INVALID", ())[:2]
    ]

    return RuleDoc(
        name=name,
        slug=slug,
        module=rule.__module__,
        pack=pack,
        selector=f"{rule.__module__}:{name}",
        path=f"rules/{slug}.md",
        toctree_path=f"rules/{slug}",
        description=description,
        message=message,
        message_short=message_short,
        autofix="Yes" if rule.AUTOFIX else "No",
        autofix_icon="✅" if rule.AUTOFIX else "—",
        python_version=f"`{python_version}`" if python_version != "Any" else "Any",
        tags=", ".join(f"`{tag}`" for tag in sorted(getattr(rule, "TAGS", ()))),
        settings=settings,
        valid_examples=valid_examples,
        invalid_examples=invalid_examples,
    )


def build_categories() -> list[CategoryDoc]:
    categories: list[CategoryDoc] = []
    for pack, module in BUILTIN_RULE_PACKS.items():
        rules = sorted(
            (build_rule_doc(rule, pack=pack) for rule in find_rules(QualifiedRule(module))),
            key=lambda rule: rule.name,
        )
        title = CATEGORY_TITLES.get(pack, pack.replace("_", " ").title())
        slug = slugify(pack)
        categories.append(
            CategoryDoc(
                pack=pack,
                module=module,
                title=title,
                description=CATEGORY_DESCRIPTIONS.get(pack, "Built-in Rattle rules."),
                slug=slug,
                toctree_path=f"rule-packs/{slug}",
                rules=rules,
            )
        )
    return categories


def render_rule_categories(categories: Iterable[CategoryDoc]) -> None:
    if RULES_CATEGORY_DIR.exists():
        shutil.rmtree(RULES_CATEGORY_DIR)
    RULES_CATEGORY_DIR.mkdir(parents=True)

    for category in categories:
        rendered = CATEGORY_TPL.render(category=category)
        (RULES_CATEGORY_DIR / f"{category.slug}.md").write_text(rendered.rstrip() + "\n")


def render_rule_details(rules: Iterable[RuleDoc]) -> None:
    if RULES_DETAIL_DIR.exists():
        shutil.rmtree(RULES_DETAIL_DIR)
    RULES_DETAIL_DIR.mkdir(parents=True)

    for rule in rules:
        rendered = DETAIL_TPL.render(rule=rule)
        (RULES_DETAIL_DIR / f"{rule.slug}.md").write_text(rendered.rstrip() + "\n")


def main() -> None:
    categories = build_categories()
    render_rule_categories(categories)
    render_rule_details(rule for category in categories for rule in category.rules)
    rendered = INDEX_TPL.render(categories=categories)
    RULES_INDEX_DOC.write_text(rendered.rstrip() + "\n")


if __name__ == "__main__":
    main()
