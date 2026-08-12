#!/usr/bin/env bash
# Record standalone clean-path (wheel install + golden via installed CLI) evidence.
# Writes only logs and digests under an evidence directory — not the wheel blob.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

STAMP="${EVIDENCE_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
OUT="${EVIDENCE_DIR:-$ROOT/dev/active/group-9-public-release/evidence/$STAMP}"
SMOKE_PYTHON="${SMOKE_PYTHON:-${UV_PYTHON:-3.12}}"

mkdir -p "$OUT"
WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/veriformis-clean-path.XXXXXX")"
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT

{
  echo "recorded_at_utc=$STAMP"
  echo "git_head=$(git rev-parse HEAD)"
  echo "git_describe=$(git describe --always --dirty 2>/dev/null || true)"
  echo "uname=$(uname -a)"
  echo "smoke_python=$SMOKE_PYTHON"
  uv python install "$SMOKE_PYTHON" >/dev/null
  echo "python_resolved=$(uv run --python "$SMOKE_PYTHON" python -c 'import sys; print(sys.version)')"
} | tee "$OUT/environment.txt"

echo "==> record_clean_path: build and install wheel into isolated venv"
uv python install "$SMOKE_PYTHON"
uv build --python "$SMOKE_PYTHON" --wheel --out-dir "$WORKDIR/dist"
WHEEL="$(find "$WORKDIR/dist" -name 'veriformis-*.whl' | head -n 1)"
test -f "$WHEEL"
# Record wheel identity only (sha256 + filename), not the binary.
{
  echo "wheel_path_basename=$(basename "$WHEEL")"
  # portable sha256
  if command -v shasum >/dev/null 2>&1; then
    echo "wheel_sha256=$(shasum -a 256 "$WHEEL" | awk '{print $1}')"
  else
    echo "wheel_sha256=$(sha256sum "$WHEEL" | awk '{print $1}')"
  fi
} | tee "$OUT/wheel_identity.txt"

uv venv --python "$SMOKE_PYTHON" "$WORKDIR/venv"
# shellcheck disable=SC1091
source "$WORKDIR/venv/bin/activate"
uv pip install "$WHEEL"
command -v veriformis
veriformis version | tee "$OUT/installed_version.txt"
PACKAGE_FILE="$(python -c 'import pathlib, veriformis; print(pathlib.Path(veriformis.__file__).resolve())')"
SITE_PACKAGES="$(python -c 'import pathlib, sysconfig; print(pathlib.Path(sysconfig.get_paths()["purelib"]).resolve())')"
{
  echo "veriformis.__file__=$PACKAGE_FILE"
  echo "site_packages=$SITE_PACKAGES"
} | tee "$OUT/installed_origin.txt"
case "$PACKAGE_FILE" in
  "$SITE_PACKAGES"/veriformis/*) ;;
  *)
    echo "record_clean_path: imported Veriformis outside isolated site-packages" >&2
    exit 1
    ;;
esac
uv pip list --python "$WORKDIR/venv/bin/python" | tee "$OUT/installed_packages.txt"
python -c 'import importlib.metadata as m; names={d.metadata["Name"].casefold() for d in m.distributions() if d.metadata.get("Name")}; assert "aptus" not in names, "unexpected external Aptus distribution installed"'

echo "==> record_clean_path: golden_compile via installed CLI"
export VERIFORMIS_USE_PATH=1
export GOLDEN_EVIDENCE_DIR="$OUT/golden"
mkdir -p "$GOLDEN_EVIDENCE_DIR"
bash "$ROOT/scripts/release/golden_compile.sh" 2>&1 | tee "$OUT/golden_compile.log"

{
  echo "status=PASS"
  echo "evidence_dir=$OUT"
  echo "notes=isolated wheel install; package origin verified in venv site-packages; standalone golden path used installed CLI"
} | tee "$OUT/SUMMARY.txt"

echo "record_clean_path_evidence: PASS → $OUT"
