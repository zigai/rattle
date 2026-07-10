# Rattle Configuration Reference

Read this reference when adding Rattle, wiring local rules, configuring options,
or applying path-specific scope.

- [Installation and layout](#installation-and-layout)
- [Selectors](#selectors)
- [Rule options](#rule-options)
- [Path scope](#path-scope)
- [Inspection and ignores](#inspection-and-ignores)

## Installation and layout

Install Rattle with:

```bash
pip install "rattle-lint>=2.1.0"
```

Use a local rule package relative to the root configuration:

```text
repo/
  pyproject.toml
  rules/
    __init__.py
    my_rule.py
```

Without `enable-root-import`, keep imports within the tree rooted at the config
file relative. If local rules need repository imports, configure
`enable-root-import` as `true` or as one path relative to the root config:

```toml
[tool.rattle]
root = true
enable-root-import = "src"
enable = ["myproject.rules"]
```

## Selectors

Rattle enables no rules by default. Local selectors are relative to the config
file:

- `.rules` enables a package;
- `.rules.my_rule` enables a module; and
- `.rules:my-rule` selects one concrete rule.

Displayed rule names and concrete selector suffixes are canonical kebab-case;
never use the Python class name. Set `NAME = "my-rule"` when class-name
conversion does not produce the intended public name.

Minimal configuration:

```toml
[tool.rattle]
root = true
python-version = "3.11"
enable = [".rules"]
disable = [".rules:disabled-rule"]
```

## Rule options

Target options at one concrete rule. Quote keys containing `:` or beginning
with `.`:

```toml
[tool.rattle.options.".rules:my-rule"]
max_length = 42
```

Inline mappings are also valid:

```toml
[tool.rattle.options]
".rules:my-rule" = { max_length = 42 }
```

Use `RuleSetting(..., validator=...)` for constraints beyond its declared type.
Settings without defaults must be supplied by configuration.

## Path scope

Use overrides or per-file tables instead of path checks inside rules:

```toml
[[tool.rattle.overrides]]
path = "tests"
enable = [".rules:tests-only-rule"]
options = { ".rules:tests-only-rule" = { max_length = 80 } }

[tool.rattle.per-file-disable]
"tests/generated.py" = [".rules:my-rule"]

[tool.rattle.per-file-enable]
"scripts/**/*.py" = [".rules:scripts-only-rule"]
```

`per-file-disable` is the final suppression layer after base configuration and
matching overrides.

## Inspection and ignores

Use `rattle rules <path>` to inspect enabled rules, disabled rules, and resolved
settings under configuration inheritance.

Local suppressions are:

```python
statement()  # rattle: ignore[my-rule]
statement()  # rattle: ignore
```

Omitting names suppresses every rule attached to that statement. Multiple
kebab-case names may be comma-separated. Prefer precise matching and
configuration before recommending suppressions.
