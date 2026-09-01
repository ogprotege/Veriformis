#!/usr/bin/env bash
# Build sdist and wheel, inspect metadata, and retain listings without binaries.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

OUT="${EVIDENCE_DIR:-$ROOT/dev/active/independent-product/phase-20-stable-1.0/evidence/python-artifacts}"
SMOKE_PYTHON="${SMOKE_PYTHON:-${UV_PYTHON:-3.12}}"
mkdir -p "$OUT"
WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/veriformis-inspect-artifacts.XXXXXX")"
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT

echo "==> inspect_python_artifacts: uv lock --check"
uv lock --check

echo "==> inspect_python_artifacts: build sdist and wheel"
uv python install "$SMOKE_PYTHON"
uv build --python "$SMOKE_PYTHON" --sdist --wheel --out-dir "$WORKDIR/dist"
shopt -s nullglob
wheels=("$WORKDIR/dist"/veriformis-*.whl)
sdists=("$WORKDIR/dist"/veriformis-*.tar.gz)
test "${#wheels[@]}" -eq 1
test "${#sdists[@]}" -eq 1
WHEEL="${wheels[0]}"
SDIST="${sdists[0]}"

hash_file() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    sha256sum "$1" | awk '{print $1}'
  fi
}

{
  echo "wheel_basename=$(basename "$WHEEL")"
  echo "wheel_sha256=$(hash_file "$WHEEL")"
  echo "sdist_basename=$(basename "$SDIST")"
  echo "sdist_sha256=$(hash_file "$SDIST")"
} | tee "$OUT/identities.txt"

python3 - "$WHEEL" "$SDIST" "$OUT" <<'PY'
import sys
import tarfile
import zipfile
from pathlib import Path

wheel = Path(sys.argv[1])
sdist = Path(sys.argv[2])
out = Path(sys.argv[3])

with zipfile.ZipFile(wheel) as zf:
    names = sorted(zf.namelist())
    (out / "wheel_members.txt").write_text("\n".join(names) + "\n", encoding="utf-8")
    metadata = next(name for name in names if name.endswith(".dist-info/METADATA"))
    record = next(name for name in names if name.endswith(".dist-info/RECORD"))
    entry = next(name for name in names if name.endswith(".dist-info/entry_points.txt"))
    meta_text = zf.read(metadata).decode("utf-8")
    record_text = zf.read(record).decode("utf-8")
    entry_text = zf.read(entry).decode("utf-8")
    (out / "wheel_METADATA.txt").write_text(meta_text, encoding="utf-8")
    (out / "wheel_RECORD.txt").write_text(record_text, encoding="utf-8")
    (out / "wheel_entry_points.txt").write_text(entry_text, encoding="utf-8")
    blob = "\n".join((meta_text, record_text, entry_text, "\n".join(names)))
    for forbidden in ("HF_TOKEN=", "AKIA", "ghp_"):
        if forbidden in blob:
            raise SystemExit(f"inspect_python_artifacts: found {forbidden} in wheel")
    if "Name: veriformis" not in meta_text:
        raise SystemExit("inspect_python_artifacts: wheel name is not veriformis")
    if "Version: 0.1.0" not in meta_text:
        raise SystemExit("inspect_python_artifacts: wheel version is not 0.1.0")
    if "Requires-Python: >=3.11" not in meta_text:
        raise SystemExit("inspect_python_artifacts: Requires-Python missing")
    if "veriformis = veriformis.cli:main" not in entry_text:
        raise SystemExit("inspect_python_artifacts: console script missing")
    if "veriformis/release/support-matrix-v1.json" not in names:
        raise SystemExit("inspect_python_artifacts: support matrix missing from wheel")

with tarfile.open(sdist, "r:gz") as tf:
    members = sorted(member.name for member in tf.getmembers() if member.isfile())
    (out / "sdist_members.txt").write_text("\n".join(members) + "\n", encoding="utf-8")
    if not any(name.endswith("LICENSE") for name in members):
        raise SystemExit("inspect_python_artifacts: LICENSE missing from sdist")
    if not any(name.endswith("pyproject.toml") for name in members):
        raise SystemExit("inspect_python_artifacts: pyproject.toml missing from sdist")

print("inspect_python_artifacts: metadata checks passed")
PY

{
  echo "status=PASS"
  echo "notes=sdist and wheel inspected; binaries not retained; version 0.1.0"
} | tee "$OUT/SUMMARY.txt"

echo "inspect_python_artifacts: PASS → $OUT"
