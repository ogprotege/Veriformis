#!/usr/bin/env bash
# Build the Debug workbench and open THAT binary (not an old Xcode DerivedData copy).
# GUI apps do not inherit a normal shell PATH; this script also passes env via open --env.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "==> repo: $ROOT"
if [[ ! -x "$ROOT/.venv/bin/veriformis" ]]; then
  echo "==> uv sync (creating .venv/bin/veriformis)"
  uv sync
fi
test -x "$ROOT/.venv/bin/veriformis"
"$ROOT/.venv/bin/veriformis" version

DD="${VERIFORMIS_DERIVED_DATA:-/tmp/veriformis-dd}"
APP="$DD/Build/Products/Debug/Veriformis.app"

echo "==> xcodegen + xcodebuild (DerivedData: $DD)"
cd "$ROOT/macos"
xcodegen generate
xcodebuild -scheme Veriformis -configuration Debug -derivedDataPath "$DD" build

test -d "$APP"
echo "==> Info.plist repo root:"
plutil -p "$APP/Contents/Info.plist" | grep VERIFORMIS || true

# Prefer the venv console script — no PATH required inside the app.
CLI="${VERIFORMIS_CLI:-$ROOT/.venv/bin/veriformis}"
test -x "$CLI"

echo "==> quitting any running Veriformis instances"
killall Veriformis 2>/dev/null || true
sleep 0.3

echo "==> opening $APP"
# `open` does NOT pass exported shell env unless you use --env (macOS open(1)).
open \
  --env "VERIFORMIS_CLI=$CLI" \
  --env "VERIFORMIS_DEVELOPMENT_REPOSITORY_ROOT=$ROOT" \
  "$APP"

echo "==> expected log line: CLI ready: $CLI"
echo "    If you still see missing CLI, check the log panel for 'Workbench bootstrap' diagnostics."
