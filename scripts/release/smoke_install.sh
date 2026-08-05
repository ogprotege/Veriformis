#!/usr/bin/env bash
# Build a wheel, install it into a clean virtualenv, and smoke-test the CLI.
# Group 9 release gate: proves the package is installable without the repo src tree.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/veriformis-smoke-install.XXXXXX")"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

echo "==> smoke_install: uv lock --check"
uv lock --check

echo "==> smoke_install: build wheel"
rm -rf "$ROOT/dist"
uv build --wheel --out-dir "$TMP/dist"
WHEEL="$(find "$TMP/dist" -name 'veriformis-*.whl' | head -n 1)"
test -n "$WHEEL"
test -f "$WHEEL"
echo "wheel: $WHEEL"

echo "==> smoke_install: clean venv install"
python3 -m venv "$TMP/venv"
# shellcheck disable=SC1091
source "$TMP/venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install "$WHEEL"

echo "==> smoke_install: CLI smoke"
command -v veriformis >/dev/null
veriformis version
veriformis --help >/dev/null
veriformis list-recipes | head -n 5

echo "smoke_install: PASS"
