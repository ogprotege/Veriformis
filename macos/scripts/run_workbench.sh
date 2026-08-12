#!/usr/bin/env bash
# Compatibility path; the repository root script owns build/run behavior.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec "$ROOT/script/build_and_run.sh" "$@"
