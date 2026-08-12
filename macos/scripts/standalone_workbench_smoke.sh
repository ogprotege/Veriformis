#!/usr/bin/env bash
# Build the workbench, launch it with one explicitly verified Veriformis CLI,
# and prove that launch created a new app process. This is not a signing or
# notarization check.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DERIVED_DATA="${VERIFORMIS_DERIVED_DATA:-${TMPDIR:-/tmp}/veriformis-standalone-smoke-dd}"
APP="$DERIVED_DATA/Build/Products/Debug/Veriformis.app"
APP_NAME="Veriformis"

CLI="${VERIFORMIS_CLI:-$ROOT/.venv/bin/veriformis}"
if [[ "$CLI" != /* ]]; then
  CLI="$(cd "$(dirname "$CLI")" && pwd)/$(basename "$CLI")"
fi
if [[ ! -x "$CLI" ]]; then
  echo "standalone smoke requires an executable CLI at: $CLI" >&2
  echo "install Veriformis first or set VERIFORMIS_CLI to an absolute executable path" >&2
  exit 2
fi

echo "==> resolved CLI: $CLI"
"$CLI" version

echo "==> building the checked-in Debug workbench project"
cd "$ROOT/macos"
xcodebuild \
  -project Veriformis.xcodeproj \
  -scheme Veriformis \
  -configuration Debug \
  -derivedDataPath "$DERIVED_DATA" \
  build

test -x "$APP/Contents/MacOS/$APP_NAME"

before_pids="$(pgrep -x "$APP_NAME" || true)"
launched_pid=""
cleanup() {
  if [[ -n "$launched_pid" ]]; then
    kill "$launched_pid" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "==> launching the freshly built app with the resolved CLI"
/usr/bin/open -n \
  --env "VERIFORMIS_CLI=$CLI" \
  --env "VERIFORMIS_DEVELOPMENT_REPOSITORY_ROOT=$ROOT" \
  "$APP"

for _ in {1..40}; do
  while IFS= read -r candidate; do
    [[ -n "$candidate" ]] || continue
    if ! grep -qx "$candidate" <<<"$before_pids"; then
      launched_pid="$candidate"
      break 2
    fi
  done < <(pgrep -x "$APP_NAME" || true)
  sleep 0.25
done

if [[ -z "$launched_pid" ]]; then
  echo "workbench launch did not create a new $APP_NAME process" >&2
  exit 1
fi

kill -0 "$launched_pid"
echo "Standalone workbench build/launch smoke: PASS (pid $launched_pid, CLI $CLI)"
