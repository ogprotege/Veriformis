#!/usr/bin/env bash
# Build a wheel, install it into a clean virtualenv, and smoke-test the CLI.
# Group 9 release gate: proves the package is installable without the repo src tree.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# Prefer an explicit interpreter for reproducible CI/local smoke (default 3.12).
SMOKE_PYTHON="${SMOKE_PYTHON:-${UV_PYTHON:-3.12}}"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/veriformis-smoke-install.XXXXXX")"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

echo "==> smoke_install: uv lock --check"
uv lock --check

echo "==> smoke_install: ensure Python $SMOKE_PYTHON"
uv python install "$SMOKE_PYTHON"

echo "==> smoke_install: build wheel"
uv build --python "$SMOKE_PYTHON" --wheel --out-dir "$TMP/dist"
WHEEL="$(find "$TMP/dist" -name 'veriformis-*.whl' | head -n 1)"
test -n "$WHEEL"
test -f "$WHEEL"
echo "wheel: $WHEEL"

echo "==> smoke_install: clean venv install (Python $SMOKE_PYTHON)"
uv venv --python "$SMOKE_PYTHON" "$TMP/venv"
# shellcheck disable=SC1091
source "$TMP/venv/bin/activate"
uv pip install "$WHEEL"

echo "==> smoke_install: CLI smoke"
command -v veriformis >/dev/null
veriformis version
veriformis --help >/dev/null
veriformis list-recipes | head -n 5

echo "smoke_install: PASS"
