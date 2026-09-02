#!/usr/bin/env bash
# Unsigned Debug xcodebuild for the same scheme ./script/build_and_run.sh uses.
# GitHub may run this with continue-on-error. This is not a public Mac claim.
# No signing secrets. No notarize. No staple.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "xcodebuild_debug: requires macOS" >&2
  exit 1
fi
if ! command -v xcodebuild >/dev/null 2>&1; then
  echo "xcodebuild_debug: xcodebuild is required (install Xcode)" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DERIVED_DATA="${VERIFORMIS_DERIVED_DATA:-${TMPDIR:-/tmp}/veriformis-xcodebuild-debug-dd}"

echo "==> unsigned Debug xcodebuild test (scheme Veriformis)"
echo "==> derivedDataPath=$DERIVED_DATA"

xcodebuild \
  -project "$ROOT/macos/Veriformis.xcodeproj" \
  -scheme Veriformis \
  -configuration Debug \
  -destination "platform=macOS" \
  -derivedDataPath "$DERIVED_DATA" \
  test \
  CODE_SIGNING_ALLOWED=NO
