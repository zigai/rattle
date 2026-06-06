(commands)=

# Commands

```console
$ rattle COMMAND [OPTIONS] ...
```

Use `-h` or `--help` on any command to print its supported options.

## Shared lint/fix options

The following options are available on commands that check or fix code.

### `--config / -c CONFIG`

Use a specific config file instead of discovered configuration.

### `--exclude / -e PATTERN`

Replace configured exclude patterns. This option may be passed more than once.
Like Ruff's `--exclude`, direct path arguments are also excluded when they match
the pattern.

```console
$ rattle lint . --exclude "generated/**"
```

### `--extend-exclude PATTERN`

Add exclude patterns. This option may be passed more than once. Direct path
arguments are still checked unless they are excluded by configuration with
`force-exclude`.

```console
$ rattle lint . --extend-exclude "docs/_build/**"
```

### `--rules / -r RULES`

Run only the given rules or rule collections.

This takes a comma-separated list of rule selectors, with the same accepted
forms as {attr}`enable <rattle.Config.enable>` and
{attr}`disable <rattle.Config.disable>`:

- import selectors such as `rattle.rules.fixit_extra:use-f-string`
- built-in rule collections such as `blank-lines`, `policy`, or `style`
- exact built-in rule names such as `use-f-string`
- exact local rule names such as `my-custom-rule`, when the local rule module is
  already configured for the target path

For example:

```console
$ rattle lint --rules "use-f-string" path/to/file.py
$ rattle lint --rules "my-custom-rule" path/to/file.py
$ rattle lint --rules "fixit,fixit-extra" path/to/file.py
```

### `--jobs / -j JOBS`

Number of worker processes to use when checking multiple files.

### `--compact`

Print compact diagnostics.

### `--quiet / -q`

Print only the final summary. `--quiet` cannot be used with `--diff`, `--stats`,
or `fix --interactive`.

### `--diff / -d`

Show fixes as unified diffs.

### `--stats`

Print violation counts by rule.

## `lint`

Check files for Rattle violations. Use `- PATH` to check code from standard
input as `PATH`.

```console
$ rattle lint [OPTIONS] [PATH ...]
```

## `fix`

Apply available autofixes to files. Use `- PATH` to fix code from standard
input as `PATH` and write the fixed code to standard output.

```console
$ rattle fix [OPTIONS] [--interactive] [PATH ...]
```

### `--interactive / -i`

Prompt before applying each autofix. Press `y` to apply, `n` to skip, or `q` to
stop prompting and leave the remaining fixes unapplied. This option cannot be
used with standard input.

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

### `--config / -c CONFIG`

Use a specific config file instead of discovered configuration.

### `--no-stdio`

Disable the default stdio transport when serving over TCP or WebSocket.

### `--tcp PORT`

Serve LSP over TCP on `PORT`.

### `--ws PORT`

Serve LSP over WebSocket on `PORT`.

### `--debounce-interval SECONDS`

Delay diagnostics after document changes, in seconds. Default: `0.5`.

## `rules`

Display the lint rules enabled for the current configuration. Pass paths to see
the rules resolved for those files or directories.

```console
$ rattle rules [OPTIONS] [PATH ...]
```

### `--config / -c CONFIG`

Use a specific config file instead of discovered configuration.

### `--test`

Test enabled lint rules using their {attr}`~rattle.LintRule.VALID` and
{attr}`~rattle.LintRule.INVALID` test cases.

## `explain`

Display detailed information about one lint rule.

```console
$ rattle explain [OPTIONS] RULE
```

### `--config / -c CONFIG`

Use a specific config file instead of discovered configuration.

### `--json`

Print rule information as JSON.

## `validate`

Validate Rattle configuration. When no path is provided, Rattle validates
`pyproject.toml` from the current directory.

```console
$ rattle validate
$ rattle validate pyproject.toml
```

## Environment variables

### `RATTLE_DEBUG=1`

Enable debug logging.

### `RATTLE_METRICS=1`

Print internal run metrics for `lint` and `fix`.
