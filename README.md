# Rattle

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
python-version = "3.10"
output-format = "rattle"
disable = [
    "NoStaticIfCondition",
    "UseAssertIn",
]
per-file-disable = {"tests/generated.py" = ["UseFstring"]}

[tool.rattle.options.UseFstring]
simple_expression_max_length = 40

[[tool.rattle.overrides]]
path = "tests"
enable = ["UseAssertIn"]
options = { UseFstring = { simple_expression_max_length = 60 } }
```

## License

MIT
