#!/usr/bin/env bash
# Compile the acceptance golden corpus through seal, external_digest verify,
# and Aptus handoff-verify for both M1.1 acceptance objectives.
# Group 9 release gate: reproducible product-path evidence from raw sources.
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

TMP="$(mktemp -d "${TMPDIR:-/tmp}/veriformis-golden-compile.XXXXXX")"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

SOURCES=()
while IFS= read -r line; do
  SOURCES+=("$line")
done < <(find "$CORPUS_DIR" -type f | LC_ALL=C sort)
test "${#SOURCES[@]}" -ge 1

compile_objective() {
  local objective="$1"
  local split_extra=()
  if [[ "$objective" == "continuation" ]]; then
    split_extra=(--split-ratio-ppm 400000)
  fi

  local ws="$TMP/ws-$objective"
  local bundle="$TMP/$objective.vfbundle"

  echo "==> golden_compile: $objective (parse → seal)"
  vf parse "${SOURCES[@]}" -o "$ws" --source-root "$CORPUS_ROOT"
  vf clean "$ws"
  vf chunk "$ws"
  vf construct "$ws" --objective "$objective" "${split_extra[@]+"${split_extra[@]}"}"
  vf curate "$ws" --allow-empty-evaluation
  vf split "$ws"
  vf format "$ws"
  vf validate "$ws"
  local seal_out
  seal_out="$(vf seal "$ws" -o "$bundle" 2>&1)"
  printf '%s\n' "$seal_out"

  local manifest
  manifest="$(printf '%s\n' "$seal_out" | awk -F': ' 'tolower($0) ~ /manifest sha-256/ {print $2; exit}')"
  test -n "$manifest"
  test -f "$bundle/manifest.json"

  local handoff="${bundle}.aptus-handoff.json"
  test -f "$handoff"

  echo "==> golden_compile: $objective external_digest verify"
  vf verify "$bundle" --manifest-sha256 "$manifest"

  # Aptus v1 backend rejects plain text rows (full_text). Continuation must
  # handoff-verify as accepted. See docs/contracts/aptus-handoff-v1.md.
  local hv_out=""
  if [[ "$objective" == "continuation" ]]; then
    echo "==> golden_compile: $objective handoff-verify (must accept)"
    hv_out="$(vf handoff-verify "$handoff" --bundle "$bundle" 2>&1)"
    printf '%s\n' "$hv_out"
    printf '%s\n' "$hv_out" | grep -q "status: accepted"
  else
    echo "==> golden_compile: $objective handoff present (Aptus rejects text schema by contract)"
    test -f "$handoff"
    hv_out="$(vf handoff-verify "$handoff" --bundle "$bundle" 2>&1 || true)"
    printf '%s\n' "$hv_out"
    printf '%s\n' "$hv_out" | grep -q "backend-rejects-row-schema:text"
  fi

  if [[ -n "${GOLDEN_EVIDENCE_DIR:-}" ]]; then
    mkdir -p "$GOLDEN_EVIDENCE_DIR"
    {
      echo "objective=$objective"
      echo "manifest_sha256=$manifest"
      echo "bundle=$bundle"
      echo "handoff=$handoff"
      printf '%s\n' "$hv_out"
    } >"$GOLDEN_EVIDENCE_DIR/${objective}.evidence.txt"
  fi

  echo "golden_compile: $objective PASS (manifest=$manifest)"
}

compile_objective full_text
compile_objective continuation

echo "golden_compile: PASS (full_text + continuation external_digest; continuation handoff accepted)"
