#!/usr/bin/env bash
# Optional Aptus adapter self-conformance proof. This is intentionally separate
# from all standalone release gates, constructs the handoff only when invoked,
# and does not claim compatibility with a live named Aptus build.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

CORPUS_ROOT="$ROOT/tests/fixtures/acceptance/v1"
CORPUS_DIR="$CORPUS_ROOT/raw/corpus"
test -d "$CORPUS_DIR"

vf() {
  if [[ -n "${VERIFORMIS_CMD:-}" ]]; then
    # shellcheck disable=SC2086
    eval "$VERIFORMIS_CMD" "$@"
  elif [[ "${VERIFORMIS_USE_PATH:-}" == "1" ]]; then
    veriformis "$@"
  else
    uv run veriformis "$@"
  fi
}

TMP="$(mktemp -d "${TMPDIR:-/tmp}/veriformis-aptus-integration.XXXXXX")"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

SOURCES=()
while IFS= read -r line; do
  SOURCES+=("$line")
done < <(find "$CORPUS_DIR" -type f | LC_ALL=C sort)
test "${#SOURCES[@]}" -ge 1

WS="$TMP/ws-continuation"
BUNDLE="$TMP/continuation.vfbundle"
HANDOFF="$TMP/continuation.aptus-handoff.json"

echo "==> aptus_integration: compile and seal canonical continuation bundle"
vf parse "${SOURCES[@]}" -o "$WS" --source-root "$CORPUS_ROOT"
vf clean "$WS"
vf chunk "$WS"
vf construct "$WS" --objective continuation --split-ratio-ppm 400000
vf curate "$WS" --allow-empty-evaluation
vf split "$WS"
vf format "$WS"
vf validate "$WS"
SEAL_OUT="$(vf seal "$WS" -o "$BUNDLE" 2>&1)"
printf '%s\n' "$SEAL_OUT"

MANIFEST="$(printf '%s\n' "$SEAL_OUT" | awk -F': ' 'tolower($0) ~ /manifest sha-256/ {print $2; exit}')"
test "${#MANIFEST}" -eq 64
test -f "$BUNDLE/manifest.json"
test ! -e "${BUNDLE}.aptus-handoff.json"

echo "==> aptus_integration: explicitly construct handoff"
vf handoff "$BUNDLE" --manifest-sha256 "$MANIFEST" -o "$HANDOFF"
test -f "$HANDOFF"

echo "==> aptus_integration: verify continuation acceptance"
VERIFY_OUT="$(vf handoff-verify "$HANDOFF" --bundle "$BUNDLE" 2>&1)"
printf '%s\n' "$VERIFY_OUT"
printf '%s\n' "$VERIFY_OUT" | grep -q "status: accepted"
printf '%s\n' "$VERIFY_OUT" | grep -q "verification grade: external_digest"

if [[ -n "${APTUS_EVIDENCE_DIR:-}" ]]; then
  mkdir -p "$APTUS_EVIDENCE_DIR"
  {
    echo "objective=continuation"
    echo "manifest_sha256=$MANIFEST"
    echo "handoff_construction=explicit"
    printf '%s\n' "$VERIFY_OUT"
  } >"$APTUS_EVIDENCE_DIR/continuation.evidence.txt"
fi

echo "aptus_integration: PASS (explicit continuation adapter self-conformance)"
