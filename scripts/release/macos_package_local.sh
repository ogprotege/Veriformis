#!/usr/bin/env bash
# Build a local macOS workbench archive for development and packaging dry-runs.
# Does NOT sign with Developer ID or notarize. Those are owner steps documented
# in docs/release.md and must leave recorded evidence — never silent skips.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "macos_package_local: requires macOS" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MACOS="$ROOT/macos"
cd "$MACOS"

CONFIGURATION="${CONFIGURATION:-Release}"
OUT_DIR="${OUT_DIR:-$ROOT/dist/macos}"
SCHEME="${SCHEME:-Veriformis}"

if ! command -v xcodegen >/dev/null 2>&1; then
  echo "macos_package_local: xcodegen is required (brew install xcodegen)" >&2
  exit 1
fi
if ! command -v xcodebuild >/dev/null 2>&1; then
  echo "macos_package_local: xcodebuild is required (install Xcode)" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
DERIVED="$OUT_DIR/DerivedData"
ARCHIVE_PATH="$OUT_DIR/Veriformis-local.xcarchive"
ZIP_PATH="$OUT_DIR/Veriformis-local-unsigned.zip"
STATE_PATH="$OUT_DIR/RELEASE_STATE.json"

echo "==> macos_package_local: xcodegen generate"
xcodegen generate

echo "==> macos_package_local: xcodebuild archive ($CONFIGURATION)"
# CODE_SIGNING_ALLOWED=NO produces a local-only product for dry-run packaging.
# Owner release builds must re-run with Developer ID signing (see docs/release.md).
xcodebuild \
  -scheme "$SCHEME" \
  -configuration "$CONFIGURATION" \
  -derivedDataPath "$DERIVED" \
  -archivePath "$ARCHIVE_PATH" \
  CODE_SIGNING_ALLOWED=NO \
  archive

APP_PATH="$(find "$ARCHIVE_PATH/Products" -name 'Veriformis.app' -type d | head -n 1 || true)"
if [[ -z "$APP_PATH" ]]; then
  # Fallback: products under DerivedData when archive layout differs
  APP_PATH="$(find "$DERIVED" -name 'Veriformis.app' -type d | head -n 1 || true)"
fi
test -n "$APP_PATH"
test -d "$APP_PATH"

echo "==> macos_package_local: zip unsigned app"
rm -f "$ZIP_PATH"
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"

python3 - <<PY
import json, hashlib, pathlib, datetime
zip_path = pathlib.Path("$ZIP_PATH")
digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
state = {
    "schema_version": 1,
    "product": "Veriformis macOS workbench",
    "package_kind": "local-unsigned-zip",
    "signing": "none",
    "notarization": "not-attempted",
    "public_release_ready": False,
    "configuration": "$CONFIGURATION",
    "archive_path": "$ARCHIVE_PATH",
    "zip_path": str(zip_path),
    "zip_sha256": digest,
    "built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "note": (
        "This artifact is for local dry-run only. Public distribution requires "
        "Developer ID signing, notarization, stapling, and recorded evidence "
        "per docs/release.md."
    ),
}
pathlib.Path("$STATE_PATH").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
print(json.dumps(state, indent=2))
PY

echo "macos_package_local: wrote $ZIP_PATH"
echo "macos_package_local: RELEASE_STATE at $STATE_PATH"
echo "macos_package_local: PASS (unsigned local archive only)"
