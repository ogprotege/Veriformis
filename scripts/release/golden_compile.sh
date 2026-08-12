#!/usr/bin/env bash
# Compile the acceptance corpus from raw sources through seal and independent
# external-digest verification and deterministic transport packaging for both
# supported acceptance objectives.
# This core release gate has no integration dependency or generated handoff.
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
  local archive="$TMP/$objective.vfbundle.zip"

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
  test "${#manifest}" -eq 64

  # Canonical standalone bundle files must all be published.
  test -f "$bundle/manifest.json"
  test -f "$bundle/attestation.json"
  test -f "$bundle/data/train.jsonl"
  test -f "$bundle/data/evaluation.jsonl"
  test -f "$bundle/metadata/row-provenance.jsonl"
  test -f "$bundle/validation.json"

  # Default seal must not publish an automatic integration descriptor.
  local automatic_handoff="${bundle}.aptus-handoff.json"
  test ! -e "$automatic_handoff"

  echo "==> golden_compile: $objective external_digest verify"
  local verify_out
  verify_out="$(vf verify "$bundle" --manifest-sha256 "$manifest" 2>&1)"
  printf '%s\n' "$verify_out"
  printf '%s\n' "$verify_out" | grep -q "verification grade: external_digest"

  echo "==> golden_compile: $objective deterministic transport"
  local package_out
  package_out="$(vf package "$bundle" -o "$archive" --manifest-sha256 "$manifest" 2>&1)"
  printf '%s\n' "$package_out"
  test -f "$archive"
  printf '%s\n' "$package_out" | grep -q "verification grade: external_digest"
  local archive_sha256
  archive_sha256="$(printf '%s\n' "$package_out" | awk -F': ' 'tolower($0) ~ /archive sha-256/ {print $2; exit}')"
  test "${#archive_sha256}" -eq 64

  local package_verify_out
  package_verify_out="$(vf package-verify "$archive" --manifest-sha256 "$manifest" 2>&1)"
  printf '%s\n' "$package_verify_out"
  printf '%s\n' "$package_verify_out" | grep -q "transport archive status: accepted"

  if [[ -n "${GOLDEN_EVIDENCE_DIR:-}" ]]; then
    mkdir -p "$GOLDEN_EVIDENCE_DIR"
    {
      echo "objective=$objective"
      echo "manifest_sha256=$manifest"
      echo "bundle=$bundle"
      echo "canonical_bundle=present"
      echo "automatic_handoff=absent"
      echo "transport_archive=$archive"
      echo "transport_archive_sha256=$archive_sha256"
      printf '%s\n' "$verify_out"
      printf '%s\n' "$package_verify_out"
    } >"$GOLDEN_EVIDENCE_DIR/${objective}.evidence.txt"
  fi

  echo "golden_compile: $objective PASS (manifest=$manifest archive=$archive_sha256)"
}

compile_objective full_text
compile_objective continuation

echo "golden_compile: PASS (standalone compile + external_digest + transport)"
