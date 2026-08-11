#!/usr/bin/env bash
# Prove two standalone workbench-equivalent CLI sequences produce the same
# canonical bundle identity, without relying on any optional integration.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/veriformis-g7-parity.XXXXXX")"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT
export UV_CACHE_DIR="${UV_CACHE_DIR:-$TMP/uv-cache}"

RAW="$TMP/raw"
mkdir -p "$RAW"
cat >"$RAW/doc.txt" <<'EOF'
First paragraph of workbench parity source material.

Second paragraph keeps multi-block construction available for continuation.
EOF

run_sequence() {
  local label="$1"
  local ws="$TMP/ws-$label"
  local bundle="$TMP/bundle-$label.vfbundle"

  uv run veriformis parse "$RAW/doc.txt" -o "$ws" --source-root "$RAW" >/dev/null
  uv run veriformis clean "$ws" >/dev/null
  uv run veriformis chunk "$ws" >/dev/null
  uv run veriformis construct "$ws" --objective continuation --split-ratio-ppm 400000 >/dev/null
  uv run veriformis curate "$ws" --allow-empty-evaluation >/dev/null
  uv run veriformis split "$ws" >/dev/null
  uv run veriformis format "$ws" >/dev/null
  uv run veriformis validate "$ws" >/dev/null
  local seal_out
  seal_out="$(uv run veriformis seal "$ws" -o "$bundle" 2>&1)"
  local advertised_manifest
  advertised_manifest="$(printf '%s\n' "$seal_out" | awk -F': ' 'tolower($0) ~ /manifest sha-256/ {print $2; exit}')"
  test -n "$advertised_manifest"
  test -f "$bundle/manifest.json"
  test ! -e "${bundle}.aptus-handoff.json"

  local manifest_sha256
  manifest_sha256="$(shasum -a 256 "$bundle/manifest.json" | awk '{print $1}')"
  test "$advertised_manifest" = "$manifest_sha256"
  uv run veriformis verify "$bundle" --manifest-sha256 "$manifest_sha256" >/dev/null

  python3 - "$bundle" "$manifest_sha256" <<'PY'
import json
import pathlib
import sys

bundle = pathlib.Path(sys.argv[1])
manifest_sha256 = sys.argv[2]
manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
facts = {
    "manifest_sha256": manifest_sha256,
    "bundle_id": manifest["bundle_id"],
    "content_root_sha256": manifest["content_root_sha256"],
    "dataset_snapshot_id": manifest["dataset_snapshot_id"],
    "validation_report_id": manifest["validation_report_id"],
    "file_bindings": [
        {
            key: item[key]
            for key in (
                "file_id",
                "path",
                "role",
                "media_type",
                "size",
                "sha256",
                "record_count",
            )
        }
        for item in manifest["files"]
    ],
}
print(json.dumps(facts, sort_keys=True, separators=(",", ":")))
PY
}

echo "Running pure CLI sequence A"
A_OUT="$(run_sequence a)"
echo "Running workbench-equivalent sequence B"
B_OUT="$(run_sequence b)"

echo "A:"
echo "$A_OUT"
echo "B:"
echo "$B_OUT"

test "$A_OUT" = "$B_OUT"

echo "Standalone workbench CLI sequence parity: PASS"
