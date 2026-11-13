# Rattle

[![tests](https://img.shields.io/github/actions/workflow/status/zigai/rattle/tests.yml?branch=main&label=tests&labelColor=30363d)](https://github.com/zigai/rattle/actions/workflows/tests.yml)
[![docs](https://img.shields.io/readthedocs/rattle?label=docs&logo=readthedocs&logoColor=white&labelColor=30363d)](https://rattle.readthedocs.io/en/latest/)
[![PyPI](https://img.shields.io/pypi/v/rattle-lint?label=PyPI&color=blue&logo=pypi&logoColor=white&labelColor=30363d)](https://pypi.org/project/rattle-lint/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white&labelColor=30363d)](pyproject.toml)
[![downloads](https://img.shields.io/pypi/dm/rattle-lint?label=downloads&color=blue&labelColor=30363d)](https://pepy.tech/projects/rattle-lint)
[![downloads](https://img.shields.io/pepy/dt/rattle-lint?label=downloads&color=blue&labelColor=30363d)](https://pepy.tech/projects/rattle-lint)
[![license](https://img.shields.io/github/license/zigai/rattle?label=license&labelColor=30363d)](LICENSE)

Rattle is a Python linting framework built on [LibCST](https://libcst.readthedocs.io) with support for autofixes, custom in-repo lint rules, and hierarchical configuration.

Rattle is a fork of [Fixit](https://github.com/Instagram/Fixit) designed to complement [Ruff](https://docs.astral.sh/ruff/). It intentionally omits rules that duplicate Ruff checks, so pair it with a comprehensive Ruff configuration; Ruff is considerably faster for those checks.

For migration from Fixit, overlapping Fixit-derived rules remain available in the opt-in `legacy` collection. This collection is not recommended for new configurations.

## Features

- 52 built-in lint rules
- Autofix support when a rule can safely rewrite code
- Local custom rules that can live inside your repository
- Hierarchical `pyproject.toml` configuration
- Pre-commit integration for CI and local workflows
- LSP support

## Install

### From PyPI

```bash
uv tool install rattle-lint
```

```bash
pip install rattle-lint
```

### With editor/LSP support

```bash
uv tool install "rattle-lint[lsp]"
```

```bash
pip install "rattle-lint[lsp]"
```

## Agent Skill

The official AI agent skill can be installed from this repo.

```bash
npx skills add https://github.com/zigai/rattle/tree/main/src/rattle/.agents/skills/create-rattle-lint-rules
```

or

```bash
uvx library-skills
```

## Basic Usage

Rattle enables no rules by default. A practical baseline for a typical typed
Python project is:

```toml
[tool.rattle]
root = true
enable = [
    "blank-line-after-control-block",
    "blank-line-after-terminal-control-block",
    "blank-line-before-branch",
    "blank-line-before-unrelated-block",
    "no-suite-leading-trailing-blank-lines",
    "module-all-at-bottom",
    "no-underscore-all-exports",
    "forbidden-call",
    "no-relative-imports",
    "no-underscore-import-aliases",
    "no-unsafe-tempfile-factories",
    "no-annotated-self",
    "no-exception-message-variables",
    "no-str-exception-translation",
    "no-underscore-class",
    "public-method-order",
    "no-bare-object-annotations",
    "no-named-tuple",
    "no-static-if-condition",
    "sorted-attributes",
    "use-callable-ellipsis",
]

[tool.rattle.options."forbidden-call"]
forbidden_calls = ["typing.cast"]
```

Adjust the list to match the project, then check the repository. Rattle uses
the invoked Python environment; install custom-rule dependencies there. For a
uv-managed project, install Rattle as a project dependency and use
`uv run python -m rattle check .`.

```bash
rattle check .
```

Apply available autofixes:

```bash
rattle check --fix .
```

Explain rule metadata, examples, and settings:

```bash
rattle explain no-bare-object-annotations
rattle explain --json no-bare-object-annotations
```

## License

[MIT](LICENSE)
