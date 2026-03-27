(configuration)=

# Configuration

Rattle uses [TOML](https://toml.io) configuration in `pyproject.toml`, and
supports hierarchical, cascading configuration. Values from files nearer to the
linted files take precedence over values from files further away.

When determining the configuration for a path, Rattle continues walking upward
until it reaches either the filesystem root or a configuration with
{attr}`root <rattle.Config.root>` set to `true`. It then reads each matching
configuration file from furthest to nearest and merges values as appropriate.

This makes it possible for a monorepo to define a baseline configuration while
still allowing individual projects to extend or replace it.

## `[tool.rattle]`

The main configuration table.

## `root`

Type: `bool`
Default: `false`

Marks a file as the root of the configuration hierarchy.

If set to `true`, Rattle does not visit any configuration files further up the
filesystem hierarchy.

## `enable`

Type: `list[str]`
Default: `[]`

List of selectors to enable when linting files covered by this configuration.

Rattle accepts three selector forms:

- import selectors, using Python module syntax, for packages, modules, or one
  concrete rule (`module:ClassName`)
- exact built-in or opted-in rule codes such as `RAT024`
- exact aliases such as `UseFstring`

Code selectors also support Ruff-style family prefixes. For example, `RAT`
targets every rule whose code starts with `RAT`.

For bundled rules, the rule class name is accepted as an alias. Other rules may
opt in to short-name selection by declaring {attr}`~rattle.LintRule.CODE` and,
optionally, {attr}`~rattle.LintRule.ALIASES`.

Rules bundled with Rattle, or available in the environment's `site-packages`,
can be referenced as a group by their fully-qualified package name,
individually by adding a colon and the rule name, or by a short code or alias:

```toml
enable = [
    "rattle.rules",
    "rattle.rules:UseFstring",
    "RAT024",
    "UseFstring",
    "RAT",
]
```

Local rules, available only in the repo being linted, can be referenced by
their locally-qualified package names, as if they were being imported from a
Python module relative to the configuration file specifying the rule:

```toml
# teambread/pyproject.toml
enable = [
    ".rules",
    ".rules.hollywood",
    ".rules:HollywoodNameRule",
]
```

Built-in codes and aliases are always available. For local or third-party
rules, short selectors only work once the rule is discoverable through an
import selector, and only if the rule class declares a unique
{attr}`~rattle.LintRule.CODE` or {attr}`~rattle.LintRule.ALIASES`.

`enable` overrides disabled rules from any configuration further up the
hierarchy.

Rattle enables the built-in `rattle.rules` lint rules by default.

## `disable`

Type: `list[str]`
Default: `[]`

List of rule selectors to disable when linting files covered by this
configuration.

This overrides enabled rules from the same file and from any configuration
further up the hierarchy.

See {attr}`enable <rattle.Config.enable>` for selector details.

## `enable-root-import`

Type: `bool | str`

Allow importing local rules using absolute imports relative to the project
root. This provides an alternative to using dotted rule names for enabling and
importing local rules from either the directory containing the root config
(when set to `true`) or a single optional path relative to the root config.

For example, a project `orange` using a `src/orange/` layout could use:

```toml
root = true
enable-root-import = "src"
enable = ["orange.rules"]
```

Assuming `orange` is not already in `site-packages`, `orange.rules` would then
be imported from `src/orange/rules/`, while also allowing those local rules to
import from other components in the `orange` namespace.

This option may only be specified in the root config file. Specifying it in any
other config file is treated as a configuration error. Absolute paths, or paths
containing `..` parent-relative components, are not allowed.

This option is roughly equivalent to adding the configured path, relative to
the root configuration, to `sys.path` when attempting to import and materialize
enabled lint rules.

## `python-version`

Type: `str`

Python version to target when selecting lint rules. Rules with
{attr}`~rattle.LintRule.PYTHON_VERSION` specifiers that do not match this
target version are disabled automatically during linting.

To target a minimum Python version of 3.10:

```toml
python-version = "3.10"
```

Defaults to the currently active Python version.
Set it to an empty string, `""`, to disable target version checking.

## `formatter`

Type: `str`

Optional post-fix formatting style to apply after Rattle rewrites a file.
Leave this unset if formatting should remain fully owned by the repository's
existing tooling.

Supported code styles:

- `(unset)`: no style is applied
- `"black"`: [Black](https://black.readthedocs.io/) code formatter
- `"ruff"`: [Ruff format](https://docs.astral.sh/ruff/formatter/) code formatter
- `"ufmt"`: [µfmt](https://ufmt.omnilib.dev/) code style, combining
  [µsort](https://usort.readthedocs.io/) import sorting with
  [Black](https://black.readthedocs.io/) formatting

Alternative formatting styles can be added by implementing the
{class}`~rattle.Formatter` interface.

## `output-format`

Type: `str`

Choose one of the presets for terminal output formatting.
This option is inferred based on the current working directory or from an
explicitly specified config file. Subpath overrides are ignored.

Available values:

- `custom`: specify your own format using {attr}`output-template <rattle.Config.output_template>`
- `rattle`: Rattle's default human-readable format, with Ruff-style headers,
  source snippets, and autofix help
- `vscode`: a single-line format that provides clickable paths for Visual
  Studio Code

## `output-template`

Type: `str`

Sets the format of output printed to the terminal.
Python formatting is used in the background to fill in data.
Only active when {attr}`output-format <rattle.Config.output_format>` is set to
`custom`.

This option is inferred based on the current working directory or from an
explicitly specified config file. Subpath overrides are ignored.

Supported variables:

- `message`: message emitted by the applied rule
- `path`: path to the affected file
- `result`: raw {class}`~rattle.Result` object
- `rule_name`: name of the applied rule
- `start_col`: start column of affected code
- `start_line`: start line of affected code

(rule-options)=

## `[tool.rattle.options]`

The `options` table allows setting options for individual lint rules by mapping
one concrete rule target to a dictionary of key-value pairs.

Valid keys are:

- a concrete import selector (`module:ClassName`)
- an exact code such as `RAT024`
- an exact alias such as `UseFstring`

```toml
[tool.rattle.options.UseFstring]
simple_expression_max_length = 42
```

Option keys must point to one concrete lint rule class, not a package, module,
or code prefix. Keys should be quoted when using `:` or a leading `.`.

As with {attr}`enable <rattle.Config.enable>`, built-in codes and aliases are
always available. Exact codes or aliases for local and third-party rules only
work when the rule is otherwise discoverable for the active configuration.

Option values may be TOML scalars or arrays of scalars.

For rules with a larger number of options, the rule name may instead be part of
the table name:

```toml
[tool.rattle.options."rattle.rules:ExampleRule"]
greeting = "hello world"
answer = 42
```

Inline mappings are still supported:

```toml
[tool.rattle.options]
UseFstring = {simple_expression_max_length = 42}
```

(overrides)=

## `[[tool.rattle.overrides]]`

Overrides provide a mechanism for hierarchical configuration within a single
configuration file. They are defined as an
[array of tables](https://toml.io/en/v1.0.0#array-of-tables), with each table
defining the subpath it applies to along with any values from the main table.

```toml
[[tool.rattle.overrides]]
path = "foo/bar"
disable = ["rattle.rules:ExampleRule"]
options = {"rattle.rules:Story" = {closing = "goodnight moon"}}

[[tool.rattle.overrides]]
path = "fizz/buzz"
enable = ["plugin:SomethingNeat"]
```

For example:

```toml
[tool.rattle.options.UseFstring]
simple_expression_max_length = 40

[[tool.rattle.overrides]]
path = "tests"
options = { UseFstring = { simple_expression_max_length = 60 } }
```

In that configuration, `UseFstring.simple_expression_max_length` is `40`
globally and `60` for files under `tests/`.

The expanded TOML table form is also supported when needed:

```toml
[[tool.rattle.overrides]]
path = "tests"

[tool.rattle.overrides.options.UseFstring]
simple_expression_max_length = 60
```

## `[tool.rattle.per-file-enable]` and `[tool.rattle.per-file-disable]`

Per-file tables provide Ruff-style glob matching for rule selection.
Each key is a glob pattern relative to the configuration file, and each value
is an array of rule selectors to enable or disable when the linted file matches
that pattern.

Patterns containing path separators are matched relative to the config file.
Patterns without a separator match by filename or directory name.

These tables are applied after the base config and any matching
{ref}`overrides`, with `per-file-disable` acting as the final suppression
layer.

```toml
[tool.rattle.per-file-enable]
"tests/**/*.py" = ["rattle.rules:UseFstring"]
"scripts/**/*.py" = ["RAT014"]

[tool.rattle.per-file-disable]
"tests/generated.py" = ["rattle.rules:UseFstring"]
"scripts/*.py" = ["rattle.rules"]
"fixtures/**/*.py" = ["RAT"]
```

## `inherit-ruff-files`

Set `inherit-ruff-files = true` to reuse Ruff's file-selection settings from
the `pyproject.toml` in the same directory as the active Rattle config.

This affects which files Rattle lints, not which lint rules it enables.
Only Ruff file selection is inherited: `include`, `extend-include`, `exclude`,
`extend-exclude`, and `force-exclude`.

```toml
[tool.rattle]
inherit-ruff-files = true
```
