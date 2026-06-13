# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import ast
import html
import inspect
import re
import shutil
import subprocess
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent, indent
from typing import TypeVar

from interfacy import Interfacy
from jinja2 import Template

from rattle.config import BUILTIN_RULE_COLLECTIONS, find_rules
from rattle.ftypes import Invalid, QualifiedRule, Valid
from rattle.rule import LintRule, RuleReference, RuleSetting

PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
RULES_INDEX_DOC = DOCS_DIR / "guide" / "builtins.md"
RULES_CATEGORY_DIR = DOCS_DIR / "guide" / "rule-collections"
RULES_DETAIL_DIR = DOCS_DIR / "guide" / "rules"
RULE_COUNT_DOCS = (PROJECT_ROOT / "README.md", DOCS_DIR / "index.md")
RULE_COUNT_PATTERN = re.compile(r"(?m)^- \d+ built-in lint rules$")
EXAMPLE_LINE_BUDGET = 6
T = TypeVar("T")

CATEGORY_TITLES = {
    "blank-lines": "Blank Lines",
    "exports": "Exports",
    "fixit": "Fixit",
    "fixit-extra": "Fixit Extra",
    "policy": "Policy",
    "style": "Style",
    "typing": "Typing",
}
CATEGORY_DESCRIPTIONS = {
    "blank-lines": "Whitespace and statement-separation rules.",
    "exports": "Rules for explicit module export surfaces.",
    "fixit": "Core lint rules inherited from Fixit.",
    "fixit-extra": "Additional Fixit-derived rules that can be enabled separately.",
    "policy": "Configurable policy rules for architecture and naming boundaries.",
    "style": "Rules for code style and structure.",
    "typing": "Rules for type annotations and modern typing syntax.",
}
CATEGORY_ORDER = (
    "blank-lines",
    "exports",
    "policy",
    "style",
    "typing",
    "fixit",
    "fixit-extra",
)

INDEX_TPL = Template(
    r"""
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

{% for category in categories %}
## {{ category.title }}

{{ category.description }}

Enable with:

```toml
enable = ["{{ category.collection }}"]
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

(rule-collection-{{ category.slug }})=

# {{ category.title }}

{{ category.description }}

Enable with:

```toml
enable = ["{{ category.collection }}"]
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

<p class="rule-metadata">
  <span>Collection: <code>{{ rule.collection }}</code></span>
  <span>Autofix: {{ rule.autofix }}</span>
  <span>Python: {{ rule.python_version }}</span>
</p>

{{ rule.description }}

{% if rule.message %}
## Message

{{ rule.message }}
{% endif %}

{% if rule.references %}
## References

{% for reference in rule.references -%}
- [{{ reference.label }}]({{ reference.url }})
{% endfor %}
{% endif %}

{% if rule.settings %}
## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
{% for setting in rule.settings -%}
    <tr>
      <td><span class="rule-setting-name">{{ setting.name }}</span></td>
      <td>{{ setting.description }}</td>
      <td><span class="rule-setting-type">{{ setting.value_type }}</span></td>
      <td><span class="rule-setting-default {{ setting.default_class }}">{{ setting.default }}</span></td>
    </tr>
{% endfor -%}
  </tbody>
</table>
```

{% endif %}
## Valid examples

{% if rule.valid_examples_visible %}
{% for case in rule.valid_examples_visible %}
```python
{{ case }}
```
{% endfor %}
{% if rule.valid_examples_hidden %}
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
{% for case in rule.valid_examples_hidden %}
```python
{{ case }}
```
{% endfor %}
```{raw} html
</details>
```
{% endif %}
{% else %}
No valid examples are documented.
{% endif %}

## Invalid examples

{% if rule.invalid_examples_visible %}
{% for case in rule.invalid_examples_visible %}
```{raw} html
<div class="rule-invalid-example{% if case.replacement and not loop.last %} rule-invalid-example-separated{% endif %}">
```
```python
{{ case.code }}
```
{% if case.replacement %}
<p class="rule-example-label">Suggested fix</p>

```python
{{ case.replacement }}
```
{% endif %}
```{raw} html
</div>
```
{% endfor %}
{% if rule.invalid_examples_hidden %}
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
{% for case in rule.invalid_examples_hidden %}
```{raw} html
<div class="rule-invalid-example{% if case.replacement and not loop.last %} rule-invalid-example-separated{% endif %}">
```
```python
{{ case.code }}
```
{% if case.replacement %}
<p class="rule-example-label">Suggested fix</p>

```python
{{ case.replacement }}
```
{% endif %}
```{raw} html
</div>
```
{% endfor %}
```{raw} html
</details>
```
{% endif %}
{% else %}
No invalid examples are documented.
{% endif %}
    """,
    trim_blocks=True,
    lstrip_blocks=True,
)


@dataclass(frozen=True)
class SettingDoc:
    name: str
    value_type: str
    default: str
    default_class: str
    description: str


@dataclass(frozen=True)
class ReferenceDoc:
    label: str
    url: str


@dataclass(frozen=True)
class InvalidExampleDoc:
    code: str
    replacement: str


@dataclass(frozen=True)
class RuleDoc:
    name: str
    slug: str
    module: str
    collection: str
    selector: str
    path: str
    toctree_path: str
    description: str
    message: str
    message_short: str
    references: Sequence[ReferenceDoc]
    autofix: str
    autofix_icon: str
    python_version: str
    tags: str
    settings: Sequence[SettingDoc]
    valid_examples_visible: Sequence[str]
    valid_examples_hidden: Sequence[str]
    invalid_examples_visible: Sequence[InvalidExampleDoc]
    invalid_examples_hidden: Sequence[InvalidExampleDoc]


@dataclass(frozen=True)
class CategoryDoc:
    collection: str
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


def code_line_count(value: str) -> int:
    return max(1, len(value.splitlines()))


def invalid_example_line_count(example: InvalidExampleDoc) -> int:
    return code_line_count(example.code) + (
        code_line_count(example.replacement) if example.replacement else 0
    )


def split_examples_by_line_budget(
    examples: Sequence[T],
    *,
    line_count: Callable[[T], int],
    budget: int = EXAMPLE_LINE_BUDGET,
) -> tuple[Sequence[T], Sequence[T]]:
    visible: list[T] = []
    used = 0

    for example in examples:
        example_lines = line_count(example)
        if visible and used + example_lines > budget:
            break
        visible.append(example)
        used += example_lines

    return visible, examples[len(visible) :]


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


def setting_default_class(default: str) -> str:
    if default in {"True", "False", "None"}:
        return "rule-setting-default-constant"
    if re.fullmatch(r"-?\d+(\.\d+)?", default):
        return "rule-setting-default-number"
    if default.startswith(("'", '"')):
        return "rule-setting-default-string"
    return "rule-setting-default-plain"


def html_text(value: str) -> str:
    return html.escape(value, quote=True)


def markdown_text(value: str) -> str:
    return re.sub(r"__(?=\w)([^\n`]*?\w)__", r"\\_\\_\1\\_\\_", value)


def reference_doc(reference: RuleReference) -> ReferenceDoc:
    if isinstance(reference, str):
        return ReferenceDoc(label=reference, url=reference)

    label, url = reference
    return ReferenceDoc(label=label, url=url)


def build_rule_doc(rule: type[LintRule], *, collection: str) -> RuleDoc:
    name = rule.name
    slug = name
    description = markdown_text(redent(rule_doc(rule)))
    message = markdown_text(redent(str(getattr(rule, "MESSAGE", ""))))
    references = tuple(reference_doc(reference) for reference in rule.REFERENCES)
    message_short = markdown_table_cell(message or "—")
    python_version = getattr(rule, "PYTHON_VERSION", "") or "Any"
    settings = []
    for setting_name, setting in sorted(rule.SETTINGS.items()):
        default = setting_default(setting)
        settings.append(
            SettingDoc(
                name=html_text(setting_name),
                value_type=html_text(type_name(setting.value_type)),
                default=html_text(default),
                default_class=setting_default_class(default),
                description=html_text(setting.description) or "—",
            )
        )
    valid_examples = [example_code(case) for case in getattr(rule, "VALID", ())]
    invalid_examples = [
        InvalidExampleDoc(
            code=example_code(case),
            replacement=expected_replacement(case),
        )
        for case in getattr(rule, "INVALID", ())
    ]
    valid_examples_visible, valid_examples_hidden = split_examples_by_line_budget(
        valid_examples,
        line_count=code_line_count,
    )
    invalid_examples_visible, invalid_examples_hidden = split_examples_by_line_budget(
        invalid_examples,
        line_count=invalid_example_line_count,
    )

    return RuleDoc(
        name=name,
        slug=slug,
        module=rule.__module__,
        collection=collection,
        selector=f"{rule.__module__}:{name}",
        path=f"rules/{slug}.md",
        toctree_path=f"rules/{slug}",
        description=description,
        message=message,
        message_short=message_short,
        references=references,
        autofix="Yes" if rule.AUTOFIX else "No",
        autofix_icon="Yes" if rule.AUTOFIX else "No",
        python_version=f"`{python_version}`" if python_version != "Any" else "Any",
        tags=", ".join(f"`{tag}`" for tag in sorted(getattr(rule, "TAGS", ()))),
        settings=settings,
        valid_examples_visible=valid_examples_visible,
        valid_examples_hidden=valid_examples_hidden,
        invalid_examples_visible=invalid_examples_visible,
        invalid_examples_hidden=invalid_examples_hidden,
    )


def build_categories() -> list[CategoryDoc]:
    categories: list[CategoryDoc] = []
    ordered_collections = [
        collection for collection in CATEGORY_ORDER if collection in BUILTIN_RULE_COLLECTIONS
    ]
    ordered_collections.extend(
        collection for collection in BUILTIN_RULE_COLLECTIONS if collection not in CATEGORY_ORDER
    )
    for collection in ordered_collections:
        module = BUILTIN_RULE_COLLECTIONS[collection]
        rules = sorted(
            (
                build_rule_doc(rule, collection=collection)
                for rule in find_rules(QualifiedRule(module))
            ),
            key=lambda rule: rule.name,
        )
        title = CATEGORY_TITLES.get(collection, collection.replace("-", " ").title())
        slug = slugify(collection)
        categories.append(
            CategoryDoc(
                collection=collection,
                module=module,
                title=title,
                description=CATEGORY_DESCRIPTIONS.get(collection, "Built-in Rattle rules."),
                slug=slug,
                toctree_path=f"rule-collections/{slug}",
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


def update_rule_count_docs(rule_count: int) -> None:
    replacement = f"- {rule_count} built-in lint rules"
    for path in RULE_COUNT_DOCS:
        content = path.read_text()
        updated, replacements = RULE_COUNT_PATTERN.subn(replacement, content, count=1)
        if replacements != 1:
            raise RuntimeError(f"Could not update built-in rule count in {path}")
        path.write_text(updated)


def generated_paths() -> tuple[Path, ...]:
    return (RULES_INDEX_DOC, RULES_CATEGORY_DIR, RULES_DETAIL_DIR, *RULE_COUNT_DOCS)


def git_path(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def git_executable() -> str:
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("git executable not found")
    return git


def commit_generated_docs(message: str) -> None:
    git = git_executable()
    paths = [git_path(path) for path in generated_paths()]
    subprocess.run([git, "add", "--", *paths], cwd=PROJECT_ROOT, check=True)  # noqa: S603
    diff = subprocess.run(  # noqa: S603
        [git, "diff", "--cached", "--quiet", "--", *paths],
        cwd=PROJECT_ROOT,
        check=False,
    )
    if diff.returncode == 0:
        return
    if diff.returncode != 1:
        raise subprocess.CalledProcessError(diff.returncode, diff.args)

    subprocess.run(  # noqa: S603
        [git, "commit", "-m", message, "--", *paths], cwd=PROJECT_ROOT, check=True
    )


def generate_rule_docs(
    *,
    commit: bool = False,
    message: str = "docs: regenerate rule documentation",
) -> None:
    """Generate rule documentation.

    Args:
        commit: Commit generated documentation changes with a Conventional Commit message.
        message: Commit message to use when commit is enabled.
    """
    categories = build_categories()
    render_rule_categories(categories)
    render_rule_details(rule for category in categories for rule in category.rules)
    rendered = INDEX_TPL.render(categories=categories)
    RULES_INDEX_DOC.write_text(rendered.rstrip() + "\n")
    update_rule_count_docs(sum(len(category.rules) for category in categories))
    if commit:
        commit_generated_docs(message)


def main(args: list[str] | None = None, *, sys_exit_enabled: bool = True) -> object:
    return Interfacy(sys_exit_enabled=sys_exit_enabled).run(generate_rule_docs, args=args)


if __name__ == "__main__":
    main()
