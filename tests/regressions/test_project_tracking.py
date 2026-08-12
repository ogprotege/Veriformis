from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_project_tracking_records_match_code_and_each_other() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_project_tracking.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Project tracking check: PASS" in result.stdout
