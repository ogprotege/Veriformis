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
uv run --python "$PYTHON" pytest -q
bash "$ROOT/scripts/release/smoke_install.sh"
bash "$ROOT/scripts/release/golden_compile.sh"

echo "check_local: PASS (local automated gates; full matrix remains on GitHub)"
