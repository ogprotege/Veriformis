#!/usr/bin/env bash
# Local parity with the automated Group 9 CI jobs (single Python, not full matrix).
# Run before push. Does not replace the GitHub matrix.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

PYTHON="${CHECK_PYTHON:-3.12}"

echo "==> check_local: Python $PYTHON"
uv python install "$PYTHON"
uv lock --check
uv sync --python "$PYTHON" --extra test
uv run --python "$PYTHON" ruff check src tests
uv run --python "$PYTHON" pytest -q --ignore=tests/handoff -m "not aptus_integration and not profile_integration and not columnar_integration and not scale_benchmark"
# The clean-wheel smoke includes the complete standalone golden compile using
# the installed CLI, so a second source-tree golden run would duplicate work.
bash "$ROOT/scripts/release/smoke_install.sh"

echo "check_local: PASS (standalone core gates; optional integrations are separate)"
