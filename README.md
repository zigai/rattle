# Rattle

Rattle is a Python linting framework built on [LibCST](https://libcst.readthedocs.io) with support for autofixes, custom in-repo lint rules, and hierarchical configuration.

Rattle is a long-lived fork of [Fixit](https://github.com/Instagram/Fixit) and is maintained independently.

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
