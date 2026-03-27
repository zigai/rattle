(integrations)=

# Integrations

(ide_integrations)=

## IDE

Rattle can lint as you type and can also be used to format files.

To enable this, install the `lsp` extras, for example:

```console
$ pip install "rattle-lint[lsp]"
```

Then configure an LSP client to launch and connect to the Rattle LSP server.
See the {ref}`lsp_command` command reference for usage details.

Examples of client setup:

- VS Code:
  [Generic LSP Client](https://github.com/llllvvuu/vscode-glspc) via GitHub,
  which requires configuration.
- VS Code:
  [Rattle (Unofficial)](https://marketplace.visualstudio.com/items?itemName=llllvvuu.fixit-unofficial)
  via the VS Code Marketplace. This is built from Generic LSP Client with a
  preset configuration for Rattle.
- Neovim:
  [nvim-lspconfig](https://github.com/neovim/nvim-lspconfig).

```lua
require("lspconfig.configs").rattle = {
  default_config = {
    cmd = { "rattle", "lsp" },
    filetypes = { "python" },
    root_dir = require("lspconfig").util.root_pattern(
      "pyproject.toml", "setup.py", "requirements.txt", ".git",
    ),
    single_file_support = true,
  },
}

lspconfig.rattle.setup({})
```

- Other IDEs:
  [Language Server Protocol tools](https://microsoft.github.io/language-server-protocol/implementors/tools/).

## pre-commit

Rattle can be included as a hook for [pre-commit](https://pre-commit.com).

Once you have [installed pre-commit](https://pre-commit.com/#installation),
add one of Rattle's hooks to `.pre-commit-config.yaml`.

To run lint rules on commit:

```yaml
repos:
  - repo: https://github.com/zigai/rattle
    rev: 0.0.0  # replace with the Rattle version to use
    hooks:
      - id: rattle-lint
```

To run lint rules and apply autofixes:

```yaml
repos:
  - repo: https://github.com/zigai/rattle
    rev: 0.0.0  # replace with the Rattle version to use
    hooks:
      - id: rattle-fix
```

To read more about how you can customize your pre-commit configuration, see the
[pre-commit hooks documentation](https://pre-commit.com/#pre-commit-configyaml---hooks).

## VS Code

For better integration with Visual Studio Code, set `output-format = "vscode"`.
That allows VS Code to open the editor at the right position when clicking code
locations in Rattle's terminal output.
