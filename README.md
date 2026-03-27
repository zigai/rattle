# Rattle

Rattle is a Python linting framework built on [LibCST](https://libcst.readthedocs.io) with support for autofixes, custom in-repo lint rules, and hierarchical configuration.

## Install

Install the CLI from PyPI:

```bash
pip install rattle
```

Install editor/LSP support too:

```bash
pip install "rattle[lsp]"
```

## Basic Usage

Lint a file or directory:

```bash
rattle lint path/to/code
```

Apply available autofixes:

```bash
rattle fix path/to/code
```

Rattle reads configuration from `pyproject.toml` under `[tool.rattle]`.

## Example Configuration

Example `pyproject.toml` you can use as a starting point:

```toml
[tool.rattle]
root = true
python-version = "3.10"
formatter = "ufmt"
output-format = "rattle"
disable = [
    "NoStaticIfCondition",
    "UseAssertIn",
]
per-file-disable = {"tests/generated.py" = ["UseFstring"]}

[tool.rattle.options]
UseFstring = {simple_expression_max_length = 40}

[[tool.rattle.overrides]]
path = "tests"
enable = ["UseAssertIn"]

[tool.rattle.overrides.options.UseFstring]
simple_expression_max_length = 60
```

## Features

- Built-in lint rules for common Python issues
- Autofix support when a rule can safely rewrite code
- Local custom rules that can live inside your repository
- Hierarchical `pyproject.toml` configuration
- LSP support for editor integrations
- Pre-commit integration for CI and local workflows

## Documentation

See the repository documentation for the quickstart, commands, configuration,
integrations, and built-in rules.

## License

Rattle is MIT licensed. See `LICENSE` for details.
