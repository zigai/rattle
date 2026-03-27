# Contributing to Rattle

## Setup

Rattle requires Python 3.10 or newer. We recommend using [uv][] to install Python:

```shell-session
$ uv python install 3.13

$ uv python pin 3.13
```

You can then sync a local development environment with `just`:

```shell-session
$ just sync
```

This installs all project extras into `.venv` and sets up the local
`pre-commit` hooks. Once created, activate the environment:

```shell-session
$ source .venv/bin/activate

(rattle) $
```

## Developing

Once activated, Rattle can be run locally:

```shell-session
(rattle) $ rattle [args]
```

To run the test suite, type checker, and linters:

```shell-session
$ just test

$ just lint

$ just typecheck
```

To format code, sort imports, and apply automatic lint fixes:

```shell-session
$ just fix

$ just format
```

Documentation is built using sphinx. You can generate and view the documentation
locally in your browser:

```shell-session
$ just docs

$ open html/index.html
```

To run the full test, lint, typecheck, spell-check, and header-check suite:

```shell-session
$ just check
```


## Submitting PRs

Before submitting PRs, please address the following items:

- Add tests exercising any fixed bugs or new functionality
- Document any changes to configuration or behavior
- Apply formatting, regenerate documentation, and run the test suite (see above)
- Summarize the high level features or behavior changes in your commit message

For most developers, we recommend using the [github cli][gh] to submit pull
requests:

```shell-session
$ gh pr create
```

## Code style

You can ensure your changes are well formatted, and imports are sorted:

```shell-session
$ just format
```

If you are using VS Code as your editor, enable Ruff for formatting and linting
to match the project workflow.


## VS Code

Make sure you've created an environment for Rattle:

```shell-session
$ just sync
```

Now, the VS Code Python module should be able to find and offer the local
`.venv` path as an option for your active Python environment, and should then
be aware of what libraries are available, and enable "Go To Definition" for
those packages.


## git-branchless

[git-branchless](https://github.com/arxanas/git-branchless) is a useful tool
for improving your local git CLI workflow, especially within a stack of commits.
It provides a "smartlog" command (`git sl`) to help visual the hierarchy of
commits and branches in your checkout, as well as `next`/`prev` commands to
make moving through your stacks even easier:

```shell-session
amethyst@luxray ~/workspace/Rattle docs  » git sl
⋮
◇ a80603c 226d (0.x) Update 'master' (branch) references to 'main' (#220)
⋮
◆ c3f8ff9 52d (main, ᐅ docs) Include scripts dir in linters
┃
◯ 33863f4 52d (local-rules) Simple example of local rule for copyright headers
```

git-branchless is a Rust package, and can be installed with cargo:

```shell-session
$ cargo install --locked git-branchless
```

Once installed to your system, it must be enabled on each git repo that you
want to use it with, so that it can install hooks and new commands:

```shell-session
$ git branchless init
```

[gh]: https://cli.github.com/
[uv]: https://docs.astral.sh/uv/
