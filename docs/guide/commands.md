(commands)=

# Commands

```console
$ rattle COMMAND [OPTIONS] ...
```

The following runtime options are available on commands that lint code,
autofix code, or materialize lint configuration.

## `--debug`, `--quiet / -q`

Raise or lower the level of output and logging.

## `--config-file / -c PATH`

Override the normal hierarchical configuration and use the configuration from
the specified path, ignoring all other configuration files entirely.

## `--exclude PATTERN`

Override configured file exclusions with a glob pattern. This option may be
passed more than once. Like Ruff's `--exclude`, direct path arguments are also
excluded when they match the pattern.

```console
$ rattle lint . --exclude "generated/**"
```

## `--extend-exclude PATTERN`

Add a glob pattern to the configured file exclusions. This option may be passed
more than once. Direct path arguments are still checked unless they are excluded
by configuration with `force-exclude`.

```console
$ rattle lint . --extend-exclude "docs/_build/**"
```

## `--tags / -t TAGS`

Select or filter the set of lint rules to apply based on their tags.

This takes a comma-separated list of tag names, optionally prefixed with `!`,
`^`, or `-`. Tags without one of those prefixes are treated as include tags.
Tags with one of those prefixes are treated as exclude tags.

Lint rules are enabled if and only if they have at least one tag in the include
list and no tags in the exclude list.

For example:

```console
$ rattle lint --tags "hello,world,^cats" ...
```

The command above filters the enabled lint rules to ones that have either the
`hello` or `world` tag, and excludes any rules with the `cats` tag, even if
they would otherwise have been selected.

## `--rules / -r RULES`

Override the configured set of lint rules entirely.

This takes a comma-separated list of rule selectors, with the same accepted
forms as {attr}`enable <rattle.Config.enable>` and
{attr}`disable <rattle.Config.disable>`:

- import selectors such as `rattle.rules.fixit_extra:UseFstring`
- built-in rule packs such as `fixit` or `fixit_extra`
- exact built-in rule class names such as `UseFstring`

For example:

```console
$ rattle lint --rules "UseFstring" path/to/file.py
$ rattle lint --rules "fixit,fixit_extra" path/to/file.py
```

## `--output-format / -o FORMAT_TYPE`

Override how Rattle prints violations to the terminal.

See {attr}`output-format <rattle.Config.output_format>` for available formats.

## `--output-template TEMPLATE`

Override the Python formatting template used with `output-format = "custom"`.

## `lint`

Lint one or more paths and print a list of lint errors. If `-` is given as the
first path, then the second path is used for configuration lookup and error
messages, and the input is read from standard input.

```console
$ rattle lint [OPTIONS] [--brief] [--diff] [--stats] [PATH ...]
```

### `--brief / -b`

Print each diagnostic on one line, without source snippets or help text.

### `--diff / -d`

Show suggested fixes, in unified diff format, when available.

### `--stats`

Print violation counts grouped by containing directory.

## `fix`

Lint one or more paths and apply suggested fixes. If `-` is given as the first
path, then the second path is used for configuration lookup, the input is read
from standard input, and the fixed output is printed to standard output,
ignoring `--interactive`.

```console
$ rattle fix [OPTIONS] [--interactive | --automatic] [--brief] [--diff] [PATH ...]
```

### `--interactive / -i`

Interactively prompt the user to apply or decline each available autofix.
Press `y` to apply, `n` to skip, or `q` to stop prompting and leave the
remaining fixes unapplied.

### `--automatic / -a`

Automatically apply suggested fixes for all lint errors when available.
This is the default behavior.

### `--brief / -b`

Print each diagnostic on one line, without source snippets or help text.

### `--diff / -d`

Show applied fixes in unified diff format when applied automatically.

(lsp_command)=

## `lsp`

Start the language server providing IDE features over
[LSP](https://microsoft.github.io/language-server-protocol/).
This command is only available if Rattle is installed with the `lsp` extras,
for example `pip install "rattle-lint[lsp]"`. See {ref}`ide_integrations` for more
details.

```console
$ rattle lsp [--no-stdio] [--tcp PORT | --ws PORT]
```

### `--no-stdio / -n`

Disable the default stdio transport when serving over TCP or WebSocket.

### `--tcp`

Serve LSP over TCP on `PORT`.

### `--ws / -w`

Serve LSP over WebSocket on `PORT`.

### `--debounce-interval / -d`

Delay in seconds for server-side debounce. Default: `0.5`.

## `rules`

Display the lint rules enabled for the current configuration. Pass paths to see
the rules resolved for those files or directories.

```console
$ rattle rules [PATH ...]
```

### `--test`

Test enabled lint rules using their {attr}`~rattle.LintRule.VALID` and
{attr}`~rattle.LintRule.INVALID` test cases. Use `--rules` to select the rules
to test.

Rule selectors use the same forms as
{attr}`enable <rattle.Config.enable>` and
{attr}`disable <rattle.Config.disable>`.

Example:

```console
$ rattle rules --test -r .examples.teambread.rules
test_INVALID_0 (rattle.testing.HollywoodNameRule) ... ok
test_INVALID_1 (rattle.testing.HollywoodNameRule) ... ok
test_VALID_0 (rattle.testing.HollywoodNameRule) ... ok
test_VALID_1 (rattle.testing.HollywoodNameRule) ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.024s

OK
```

```console
$ rattle rules --test -r UseFstring
```

## `validate`

Validate config. When no path is provided, Rattle validates `pyproject.toml`
from the current directory.

```console
$ rattle validate
$ rattle validate pyproject.toml
```
