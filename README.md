# Rattle

[![Tests](https://github.com/zigai/rattle/actions/workflows/tests.yml/badge.svg)](https://github.com/zigai/rattle/actions/workflows/tests.yml)
[![Documentation Status](https://readthedocs.org/projects/rattle/badge/?version=latest)](https://rattle.readthedocs.io/en/latest/?badge=latest)
[![PyPI version](https://badge.fury.io/py/rattle-lint.svg)](https://badge.fury.io/py/rattle-lint)
![Supported versions](https://img.shields.io/badge/python-3.10+-blue.svg)
[![Downloads](https://static.pepy.tech/badge/rattle-lint)](https://pepy.tech/project/rattle-lint)
[![License: MIT](https://img.shields.io/badge/license-MIT-4b5563.svg)](https://github.com/zigai/rattle/blob/main/LICENSE)

Rattle is a Python linting framework built on [LibCST](https://libcst.readthedocs.io) with support for autofixes, custom in-repo lint rules, and hierarchical configuration.

Rattle is a fork of [Fixit](https://github.com/Instagram/Fixit).

## Features

- 48 built-in lint rules
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

Rattle runs with no enabled rules until a project enables them in
`pyproject.toml`:

```toml
[tool.rattle]
enable = ["fixit"]
```

```bash
rattle lint
```

Apply available autofixes:

```bash
rattle fix
```

Explain rule metadata, examples, and settings:

```bash
rattle explain use-f-string
rattle explain --json use-f-string
```

## Example Configuration


```toml
[tool.rattle]
root = true
enable = ["fixit"]
python-version = "3.10"
disable = [
    "no-static-if-condition",
    "use-rattle-ignore-comment",
]
per-file-disable = {"tests/generated.py" = ["no-named-tuple"]}

# Apply extra rules only under the src/ directory.
[[tool.rattle.overrides]]
path = "src"
enable = ["fixit-extra"]

[[tool.rattle.overrides]]
path = "tests"
enable = ["no-named-tuple"]
```

## License

[MIT](LICENSE)
