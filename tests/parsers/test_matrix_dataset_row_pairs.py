"""Matrix dataset-row pairs: parse accepts two independent imported sources."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app

ROOT = Path(__file__).resolve().parents[2]
RUNNER = CliRunner()

PAIRS = (
    pytest.param(
        ROOT / "tests/fixtures/matrix/dataset-row/preference-a.jsonl",
        ROOT / "tests/fixtures/matrix/dataset-row/preference-b.jsonl",
        id="preference-pair",
    ),
    pytest.param(
        ROOT / "tests/fixtures/matrix/dataset-row/labels-a.jsonl",
        ROOT / "tests/fixtures/matrix/dataset-row/labels-b.jsonl",
        id="label-classification",
    ),
)


@pytest.mark.parametrize("first,second", PAIRS)
def test_dataset_row_parse_accepts_two_independent_sources(
    tmp_path: Path, first: Path, second: Path
) -> None:
    workspace = tmp_path / "workspace"
    result = RUNNER.invoke(
        app,
        [
            "parse",
            str(first),
            str(second),
            "-o",
            str(workspace),
            "--source-root",
            str(ROOT),
            "--mode",
            "dataset-row",
        ],
    )
    assert result.exit_code == 0, result.output
