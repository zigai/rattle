(commands)=

# Commands

```console
$ rattle [OPTIONS] COMMAND ...
```

The following options are available for all commands.

## `--debug / --quiet`

Raise or lower the level of output and logging.

## `--config-file PATH`

Override the normal hierarchical configuration and use the configuration from
the specified path, ignoring all other configuration files entirely.

## `--tags TAGS`

Select or filter the set of lint rules to apply based on their tags.

This takes a comma-separated list of tag names, optionally prefixed with `!`,
`^`, or `-`. Tags without one of those prefixes are treated as include tags.
Tags with one of those prefixes are treated as exclude tags.

Lint rules are enabled if and only if they have at least one tag in the include
list and no tags in the exclude list.

For example:

```console
$ rattle --tags "hello,world,^cats" ...
```

The command above filters the enabled lint rules to ones that have either the
`hello` or `world` tag, and excludes any rules with the `cats` tag, even if
they would otherwise have been selected.

## `--rules RULES`

Override the configured set of lint rules entirely.

This takes a comma-separated list of rule selectors, with the same accepted
forms as {attr}`enable <rattle.Config.enable>` and
{attr}`disable <rattle.Config.disable>`:

- import selectors such as `rattle.rules` or `rattle.rules:UseFstring`
- exact codes such as `RAT024`
- exact aliases such as `UseFstring`
- code prefixes such as `RAT`

For example:

```console
$ rattle --rules "RAT024" lint path/to/file.py
$ rattle --rules "RAT014,RAT024" lint path/to/file.py
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
$ rattle lint [--diff] [PATH ...]
```

### `--diff / -d`

Show suggested fixes, in unified diff format, when available.

## `fix`

Lint one or more paths and apply suggested fixes. If `-` is given as the first
path, then the second path is used for configuration lookup, the input is read
from standard input, and the fixed output is printed to standard output,
ignoring `--interactive`.

```console
$ rattle fix [--interactive | --automatic [--diff]] [PATH ...]
```

### `--interactive / -i`

Interactively prompt the user to apply or decline each available autofix.
Press `y` to apply, `n` to skip, or `q` to stop prompting and leave the
remaining fixes unapplied.

### `--automatic / -a`

Automatically apply suggested fixes for all lint errors when available.
This is the default behavior.

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
$ rattle lsp [--stdio | --tcp PORT | --ws PORT]
```

### `--stdio`

Serve LSP over stdio. This is the default.

### `--tcp`

Serve LSP over TCP on `PORT`.

### `--ws`

Serve LSP over WebSocket on `PORT`.

### `--debounce-interval`

Delay in seconds for server-side debounce. Default: `0.5`.

## `test`

Test one or more lint rules using their {attr}`~rattle.LintRule.VALID` and
{attr}`~rattle.LintRule.INVALID` test cases.

The command accepts rule selectors with the same forms as
{attr}`enable <rattle.Config.enable>` and
{attr}`disable <rattle.Config.disable>`.

Built-in rules may be referenced by import selector, exact code, exact alias,
or code prefix:

```console
$ rattle test [RULES ...]
```

Example:

```console
$ rattle test .examples.teambread.rules
test_INVALID_0 (rattle.testing.HollywoodNameRule) ... ok
test_INVALID_1 (rattle.testing.HollywoodNameRule) ... ok
test_VALID_0 (rattle.testing.HollywoodNameRule) ... ok
test_VALID_1 (rattle.testing.HollywoodNameRule) ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.024s

OK
```

```console
$ rattle test RAT024
$ rattle test UseFstring
$ rattle test RAT
```

## `debug`

Debug options for validating Rattle configuration.
This prints resolved config data, enabled and disabled rules, and resolved rule
settings.

```console
$ rattle debug [PATH ...]
```
