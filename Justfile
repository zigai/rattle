set positional-arguments
set script-interpreter := ['uv', 'run', '--no-project', '--', 'python']

_:
    @just help

_require-uv:
  @uv --version > /dev/null || (echo "Please install uv: https://docs.astral.sh/uv/" && exit 1)

# install all dependency groups into the local environment
install: _require-uv
  uv sync --inexact --all-groups

# install the dev dependencies used for local testing and CI
install-dev: _require-uv
  uv sync --inexact --group dev

# install only the docs dependencies used for documentation builds
install-docs: _require-uv
  uv sync --inexact --group docs

# create or refresh the local virtual environment
venv: install
  @echo 'run `source .venv/bin/activate` to activate virtualenv'

# check code style and potential issues
lint: _require-uv
  uv run --group dev ruff check src/rattle scripts examples docs/conf.py
  uv run --group dev ruff format --check src/rattle scripts examples docs/conf.py
  uv run --group dev python -m rattle lint src/rattle

# format code
format: _require-uv
  uv run --group dev ruff format src/rattle scripts examples docs/conf.py

# fix automatically fixable linting issues
fix: _require-uv
  uv run --group dev ruff check --fix src/rattle scripts examples docs/conf.py

# run tests across all supported Python versions
[script]
test *args: _require-uv
  from pathlib import Path
  import os
  import shutil
  import subprocess
  import sys

  versions = [
      line.strip()
      for line in Path(".python-versions").read_text(encoding="utf-8").splitlines()
      if line.strip() and not line.lstrip().startswith("#")
  ]
  args = sys.argv[1:]
  if args[:1] == ["--"]:
      args = args[1:]

  def colorize(text):
      if os.environ.get("NO_COLOR"):
          return text
      if os.environ.get("FORCE_COLOR") or (sys.stdout.isatty() and os.environ.get("TERM") != "dumb"):
          return f"\033[1;36m{text}\033[0m"
      return text

  def print_separator(label):
      width = shutil.get_terminal_size(fallback=(120, 24)).columns
      text = f" {label} "
      if len(text) >= width:
          print(colorize(label), flush=True)
          return

      left = (width - len(text)) // 2
      right = width - len(text) - left
      print(colorize(f"{'─' * left}{text}{'─' * right}"), flush=True)

  for py in versions:
      print_separator(f"Python {py}")
      result = subprocess.run([
          "uv",
          "run",
          "--python",
          py,
          "--isolated",
          "--group",
          "test",
          "--",
          "pytest",
          *args,
      ])
      if result.returncode:
          raise SystemExit(result.returncode)

# build the package
build: _require-uv
  uv build

# setup or update local dev environment and install pre-commit hooks
sync: install
  uv run --group dev pre-commit install

# run tests with coverage and show a coverage report
coverage: _require-uv
  uv run --group dev coverage run -m pytest
  uv run --group dev coverage report

# build the docs and regenerate the builtins page
docs: _require-uv
  uv run --group docs python scripts/document_rules.py
  uv run --group docs sphinx-build -ab html docs html

# regenerate rule docs, commit generated changes, and build the docs
docs-commit: _require-uv
  uv run --group docs python scripts/document_rules.py --commit
  uv run --group docs sphinx-build -ab html docs html

# clean build artifacts and caches
clean:
  rm -rf .venv .pytest_cache .ruff_cache build dist html htmlcov .coverage
  find . -type d -name "__pycache__" -exec rm -r {} +

# static type check with pyright
typecheck: _require-uv
  uv run --group dev pyright

# check code for common misspellings
spell: _require-uv
  uv run --group dev codespell .

# run all quality checks
check: lint coverage typecheck spell

# run the main local workflow
all: install test lint docs

# list available recipes
help:
  @just --list

alias fmt := format
alias cov := coverage
alias html := docs
alias pyright := typecheck
