set positional-arguments
set script-interpreter := ['uv', 'run', '--no-project', '--', 'python']

# Setup or update local dev environment with all dependency groups and install pre-commit hooks
setup: require-uv
    uv sync --inexact --all-groups
    uv run --group dev pre-commit install

# Install the CLI executable to ~/.local/bin
install: require-uv
    uv tool install --editable .

# Check code style and potential issues
lint: require-uv
    uv run --group dev ruff check src/rattle scripts examples docs/conf.py
    uv run --group dev ruff format --check src/rattle scripts examples docs/conf.py
    uv run --group dev python -m rattle check src/rattle

# Format code
format: require-uv
    uv run --group dev ruff format src/rattle scripts examples docs/conf.py

# Fix automatically fixable linting issues
fix: require-uv
    uv run --group dev ruff check --fix src/rattle scripts examples docs/conf.py

# Run tests across all supported Python versions
[script]
test *args: require-uv
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

# Build the package
build: require-uv
    uv build

# Measure all local test suites and print coverage
coverage: require-uv
    #!/usr/bin/env bash
    set -euo pipefail
    export COVERAGE_FILE="$PWD/.coverage"
    uv run --group dev coverage erase
    uv run --group dev coverage run -m pytest || [[ $? -eq 5 ]]
    uv run --group dev coverage combine
    uv run --group dev coverage report

# Build the docs and regenerate the builtins page
docs: require-uv
    uv run --group docs python scripts/document_rules.py
    uv run --group docs sphinx-build -ab html docs html

# Regenerate rule docs, commit generated changes, and build the docs
docs-commit: require-uv
    uv run --group docs python scripts/document_rules.py --commit
    uv run --group docs sphinx-build -ab html docs html

# Remove generated output and caches
clean: (remove ".venv" ".pytest_cache" ".ruff_cache" "build" "dist" "html" "htmlcov" ".coverage" ".coverage.*" "**/__pycache__")

# Check static types with pyrefly
typecheck: require-uv
    uv run --group dev pyrefly check --min-severity warn

# Run the commit checks
check: (run-checks "formatcheck" "lockcheck" "lint" "typecheck" "test")

# Run the main local workflow
all: setup test lint docs

# Check formatting without changing files
formatcheck:
    uv run --group dev ruff format --check src/rattle scripts examples docs/conf.py

# Synchronize dependency locks without upgrading dependencies
[no-exit-message]
lock:
    @uv lock

# Verify dependency manifests and locks without changing files
[no-exit-message]
lockcheck:
    @uv lock --check

# List available recipes
[default]
help:
    @just --list

alias fmt := format
alias cov := coverage

[private]
require-uv:
    @uv --version > /dev/null || (echo "Please install uv: https://docs.astral.sh/uv/" && exit 1)

[positional-arguments]
[private]
run-checks +steps:
    #!/usr/bin/env bash
    set -uo pipefail
    LC_NUMERIC=C
    log_dir="${XDG_CACHE_HOME:-$HOME/.cache}/just-check"
    mkdir -p "$log_dir"
    log=$(mktemp "$log_dir/step.XXXXXX")
    trap 'rm -f "$log"' EXIT
    width=0 failed=()
    for step in "$@"; do (( ${#step} > width )) && width=${#step}; done
    for step in "$@"; do
        read -ra command <<< "$step"
        printf 'check  %-*s  ' "$width" "$step"
        start=$EPOCHREALTIME
        run=(just --justfile {{ quote(justfile()) }} "${command[@]}")
        if [[ -t 1 ]]; then run=(script -qefc "${run[*]@Q}" /dev/null); fi
        if "${run[@]}" < /dev/null > "$log" 2>&1; then status=ok; else status=FAIL; failed+=("$step"); fi
        printf '%-4s  %7.1fs\n' "$status" "$(LC_NUMERIC=C awk -v a="$start" -v b="$EPOCHREALTIME" 'BEGIN { print b - a }')"
        if [[ "$status" == FAIL ]]; then sed 's/\r$//; s/^/    /' "$log"; fi
    done
    if (( ${#failed[@]} )); then printf '%d of %d failed: %s\n' "${#failed[@]}" "$#" "${failed[*]}"; exit 1; fi
    printf 'all %d passed\n' "$#"

[positional-arguments]
[private]
remove +paths:
    #!/usr/bin/env bash
    set -euo pipefail
    shopt -s nullglob globstar
    size() { LC_ALL=C numfmt --from-unit=1024 --to=iec-i --suffix=B --format=%.1f "$1"; }
    rows=() total=0
    for pattern in "$@"; do
        found=()
        for path in $pattern; do
            if [[ -e $path || -L $path ]]; then found+=("$path"); fi
        done
        if (( ${#found[@]} == 0 )); then continue; fi
        kib=$(du -sck -- "${found[@]}" | tail -n1 | cut -f1)
        rm -rf -- "${found[@]}"
        label=$pattern
        if (( ${#found[@]} > 1 )); then label+=" (${#found[@]})"; fi
        rows+=("removed  $label|$(size "$kib")")
        total=$(( total + kib ))
    done
    if [[ -n ${CLEAN_TOTAL_FILE:-} ]]; then echo "$total" >> "$CLEAN_TOTAL_FILE"; fi
    if (( ${#rows[@]} == 0 )); then echo "nothing to clean"; exit 0; fi
    printf '%s\n' "${rows[@]}" "total freed|$(size "$total")" | column -t -s '|' -R 2
