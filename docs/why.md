# Historical Context

This page is retained as historical context from the upstream
[Fixit](https://github.com/Instagram/Fixit) project that Rattle was forked
from. It describes the original motivation behind the tool's design.

## Original motivation

There are many Python linter tools, but in large codebases too many lint
suggestions can slow teams down. Developers can end up spending more time
cleaning up warnings than moving work forward, and eventually they start
ignoring even the useful suggestions.

The upstream project was built around **autofix**. Many linters analyze source
code as an [AST](https://docs.python.org/3/library/ast.html), which does not
preserve formatting and comments well enough for high-quality rewrites. Using
[LibCST](https://libcst.readthedocs.io), rules can find problematic code and
transform it while keeping formatting intact.

## Learning from building a Flake8 plugin

Many older lint rules were implemented in a monolithic
[Flake8 plugin](https://flake8.pycqa.org/en/latest/plugin-development/index.html).
That model provided flexibility, but it also led to performance and reliability
problems:

- Rules were highly coupled and shared too much state.
- Small changes in one rule could break others.
- Rules were hard to run in isolation for benchmarking and testing.
- Visitors had to recurse manually, which made coverage easier to break.
- Multiple AST traversals slowed linting down.

The result was a large pile of helper functions and visitors that was hard to
extend safely.

## Original design principles

The original project emphasized the following principles:

- **Autofix.** Rules should provide autofix whenever possible.
- **Modular.** Each lint rule should be a standalone class with isolated logic.
- **Fast.** Rules should run in a single traversal and share metadata efficiently.
- **Configurable.** Rules should be configurable and fully disable-able.
- **Testable.** Rule examples should double as documentation and tests.
