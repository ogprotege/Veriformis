#!/usr/bin/env bash
# Compile the retained project-spec example and compare committed fingerprints.
# Does not replace golden-compile. Does not upload.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

EXAMPLE="$ROOT/examples/project-spec"
test -f "$EXAMPLE/spec.json"
test -f "$EXAMPLE/expected-fingerprint.json"

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

TMP="$(mktemp -d "${TMPDIR:-/tmp}/veriformis-project-spec-example.XXXXXX")"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

cp -R "$EXAMPLE" "$TMP/example"
SPEC="$TMP/example/spec.json"

echo "==> project_spec_example: dry-run writes nothing"
before="$(find "$TMP/example" -type f | LC_ALL=C sort)"
vf spec-dry-run "$SPEC" >/dev/null
after="$(find "$TMP/example" -type f | LC_ALL=C sort)"
test "$before" = "$after"

echo "==> project_spec_example: spec-run"
out="$(vf spec-run "$SPEC")"
printf '%s\n' "$out"
bundle="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["bundle"])' <<<"$out")"
test -f "$bundle/manifest.json"

echo "==> project_spec_example: compare fingerprints"
python3 - "$EXAMPLE/expected-fingerprint.json" "$SPEC" "$bundle" "$EXAMPLE/spec.lock.json" <<'PY'
import hashlib, json, sys
from pathlib import Path

expected = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
spec = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
bundle = Path(sys.argv[3])
lock = json.loads(Path(sys.argv[4]).read_text(encoding="utf-8"))
manifest = hashlib.sha256((bundle / "manifest.json").read_bytes()).hexdigest()
assert spec["spec_id"] == expected["spec_id"], spec["spec_id"]
assert lock["spec_id"] == expected["spec_id"]
assert lock["spec_digest"] == expected["spec_digest"]
assert manifest == expected["manifest_sha256"], manifest
assert "HF_TOKEN" not in json.dumps(spec)
assert "HF_TOKEN" not in json.dumps(lock)
print(f"project_spec_example: PASS (manifest={manifest})")
PY
