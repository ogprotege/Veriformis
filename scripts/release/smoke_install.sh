#!/usr/bin/env bash
# Build a wheel, install it into a clean virtualenv, and run the complete
# standalone golden path through that installed CLI.
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
shopt -s nullglob
wheels=("$TMP/dist"/veriformis-*.whl)
test "${#wheels[@]}" -eq 1
WHEEL="${wheels[0]}"
test -f "$WHEEL"
echo "wheel: $WHEEL"

echo "==> smoke_install: clean venv install (Python $SMOKE_PYTHON)"
uv venv --python "$SMOKE_PYTHON" "$TMP/venv"
# shellcheck disable=SC1091
source "$TMP/venv/bin/activate"
uv pip install "$WHEEL"

echo "==> smoke_install: installed package provenance"
PACKAGE_FILE="$(python -c 'import pathlib, veriformis; print(pathlib.Path(veriformis.__file__).resolve())')"
SITE_PACKAGES="$(python -c 'import pathlib, sysconfig; print(pathlib.Path(sysconfig.get_paths()["purelib"]).resolve())')"
echo "veriformis.__file__=$PACKAGE_FILE"
echo "site_packages=$SITE_PACKAGES"
case "$PACKAGE_FILE" in
  "$SITE_PACKAGES"/veriformis/*) ;;
  *)
    echo "smoke_install: imported Veriformis outside the clean venv site-packages" >&2
    exit 1
    ;;
esac

echo "==> smoke_install: installed package list"
uv pip list --python "$TMP/venv/bin/python"
python -c 'import importlib.metadata as m; names={d.metadata["Name"].casefold() for d in m.distributions() if d.metadata.get("Name")}; assert "aptus" not in names, "unexpected external Aptus distribution installed"'

echo "==> smoke_install: installed CLI smoke"
command -v veriformis >/dev/null
veriformis version
veriformis --help >/dev/null
# Capture the full listing first. Piping the CLI to `head` under `pipefail`
# exits 1 from SIGPIPE once five lines have been printed.
veriformis list-recipes > "$TMP/list-recipes.txt"
test -s "$TMP/list-recipes.txt"
head -n 5 "$TMP/list-recipes.txt"

echo "==> smoke_install: standalone golden compile via installed CLI"
VERIFORMIS_USE_PATH=1 bash "$ROOT/scripts/release/golden_compile.sh"

echo "smoke_install: PASS (clean wheel + standalone golden compile)"
