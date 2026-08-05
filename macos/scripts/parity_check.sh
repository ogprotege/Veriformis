#!/usr/bin/env bash
# Prove the workbench stage sequence matches a pure CLI compile digests-wise.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/veriformis-g7-parity.XXXXXX")"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

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

  uv run veriformis parse "$RAW/doc.txt" -o "$ws" --source-root "$RAW"
  uv run veriformis clean "$ws"
  uv run veriformis chunk "$ws"
  uv run veriformis construct "$ws" --objective continuation --split-ratio-ppm 400000
  uv run veriformis curate "$ws" --allow-empty-evaluation
  uv run veriformis split "$ws"
  uv run veriformis format "$ws"
  uv run veriformis validate "$ws"
  local seal_out
  seal_out="$(uv run veriformis seal "$ws" -o "$bundle" 2>&1)"
  echo "$seal_out"
  local manifest
  manifest="$(printf '%s\n' "$seal_out" | awk -F': ' 'tolower($0) ~ /manifest sha-256/ {print $2; exit}')"
  test -n "$manifest"
  test -f "$bundle/manifest.json"
  test -f "${bundle}.aptus-handoff.json"
  # content root is in the handoff / verification path
  python3 - <<PY
import json, pathlib
bundle = pathlib.Path("$bundle")
handoff = json.loads(pathlib.Path(str(bundle) + ".aptus-handoff.json").read_text())
print(handoff["content_root_sha256"])
print(handoff["assignment_digest"])
print(handoff["train"]["sha256"])
print(handoff["evaluation"]["sha256"])
print("$manifest")
PY
}

echo "Running pure CLI sequence A"
A_OUT="$(run_sequence a | tail -n 5)"
echo "Running workbench-equivalent sequence B"
B_OUT="$(run_sequence b | tail -n 5)"

echo "A:"
echo "$A_OUT"
echo "B:"
echo "$B_OUT"

test "$A_OUT" = "$B_OUT"

echo "Group 7 workbench CLI sequence parity: PASS"
