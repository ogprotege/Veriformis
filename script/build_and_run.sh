#!/usr/bin/env bash
# Single checked-in build/run entrypoint for the macOS workbench.
set -euo pipefail

MODE="${1:-run}"
APP_NAME="Veriformis"
BUNDLE_ID="com.veriformis.workbench"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DERIVED_DATA="${VERIFORMIS_DERIVED_DATA:-${TMPDIR:-/tmp}/veriformis-workbench-dd}"
APP_BUNDLE="$DERIVED_DATA/Build/Products/Debug/$APP_NAME.app"
APP_BINARY="$APP_BUNDLE/Contents/MacOS/$APP_NAME"
CLI="${VERIFORMIS_CLI:-$ROOT_DIR/.venv/bin/veriformis}"

if [[ "$CLI" != /* ]]; then
  CLI="$(cd "$(dirname "$CLI")" && pwd)/$(basename "$CLI")"
fi
if [[ ! -x "$CLI" ]]; then
  echo "Veriformis CLI is not executable: $CLI" >&2
  echo "Run 'uv sync' or set VERIFORMIS_CLI to an installed standalone CLI." >&2
  exit 2
fi

case "$MODE" in
  run|--debug|debug|--logs|logs|--telemetry|telemetry|--verify|verify) ;;
  *)
    echo "usage: $0 [run|--debug|--logs|--telemetry|--verify]" >&2
    exit 2
    ;;
esac

echo "==> CLI: $CLI"
"$CLI" version

echo "==> stopping existing $APP_NAME process"
pkill -x "$APP_NAME" >/dev/null 2>&1 || true

echo "==> building checked-in Xcode project"
xcodebuild \
  -project "$ROOT_DIR/macos/Veriformis.xcodeproj" \
  -scheme Veriformis \
  -configuration Debug \
  -derivedDataPath "$DERIVED_DATA" \
  build
test -x "$APP_BINARY"

open_app() {
  /usr/bin/open -n \
    --env "VERIFORMIS_CLI=$CLI" \
    --env "VERIFORMIS_DEVELOPMENT_REPOSITORY_ROOT=$ROOT_DIR" \
    "$APP_BUNDLE"
}

case "$MODE" in
  run)
    open_app
    ;;
  --debug|debug)
    VERIFORMIS_CLI="$CLI" \
      VERIFORMIS_DEVELOPMENT_REPOSITORY_ROOT="$ROOT_DIR" \
      lldb -- "$APP_BINARY"
    ;;
  --logs|logs)
    open_app
    /usr/bin/log stream --info --style compact --predicate "process == \"$APP_NAME\""
    ;;
  --telemetry|telemetry)
    open_app
    /usr/bin/log stream --info --style compact --predicate "subsystem == \"$BUNDLE_ID\""
    ;;
  --verify|verify)
    open_app
    launched_pid=""
    for _ in {1..40}; do
      launched_pid="$(pgrep -x "$APP_NAME" | head -n 1 || true)"
      if [[ -n "$launched_pid" ]]; then
        break
      fi
      sleep 0.25
    done
    if [[ -z "$launched_pid" ]]; then
      echo "$APP_NAME did not launch from $APP_BUNDLE" >&2
      exit 1
    fi
    kill -0 "$launched_pid"
    echo "Workbench build/launch verification: PASS (pid $launched_pid)"
    ;;
esac
