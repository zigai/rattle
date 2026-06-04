# Rattle

[![Documentation Status](https://readthedocs.org/projects/rattle/badge/?version=latest)](https://rattle.readthedocs.io/en/latest/?badge=latest)
[![PyPI version](https://img.shields.io/pypi/v/rattle-lint.svg)](https://pypi.org/project/rattle-lint/)
[![License: MIT](https://img.shields.io/badge/license-MIT-4b5563.svg)](https://github.com/zigai/rattle/blob/main/LICENSE)

Rattle is a Python linting framework built on [LibCST](https://libcst.readthedocs.io) with support for autofixes, custom in-repo lint rules, and hierarchical configuration.

Rattle is a fork of [Fixit](https://github.com/Instagram/Fixit).

## Features

- Built-in lint rules for common Python issues
- Autofix support when a rule can safely rewrite code
- Local custom rules that can live inside your repository
- Hierarchical `pyproject.toml` configuration
- Pre-commit integration for CI and local workflows
- LSP support

## Install

Install the CLI from PyPI:

```bash
pip install rattle-lint
```

Install editor/LSP support too:

```bash
pip install "rattle-lint[lsp]"
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

## Example Configuration

```toml
[tool.rattle]
root = true
enable = ["fixit"]
python-version = "3.10"
output-format = "rattle"
disable = [
    "NoStaticIfCondition",
    "UseRattleIgnoreComment",
]
per-file-disable = {"tests/generated.py" = ["NoNamedTuple"]}

[[tool.rattle.overrides]]
path = "legacy"
enable = ["fixit_extra"]

[[tool.rattle.overrides]]
path = "tests"
enable = ["NoNamedTuple"]
```

## Documentation

- [Quickstart](guide/quickstart.md)
- [Commands](guide/commands.md)
- [Configuration](guide/configuration.md)
- [Integrations](guide/integrations.md)
- [Rules](guide/builtins.md)
- [API reference](api.rst)

## License

MIT

```{toctree}
:hidden:
:caption: User Guide
:maxdepth: 1

guide/quickstart
guide/commands
guide/configuration
guide/integrations
guide/builtins
```

```{toctree}
:hidden:
:caption: Reference
:maxdepth: 1

api
contributing
```

```{toctree}
:hidden:
:caption: Links
:maxdepth: 1

PyPI <https://pypi.org/project/rattle-lint/>
GitHub <https://github.com/zigai/rattle>
Issues <https://github.com/zigai/rattle/issues>
```
