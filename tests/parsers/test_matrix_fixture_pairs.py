"""Matrix fixture pairs: parse accepts two independent sources per family."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app

ROOT = Path(__file__).resolve().parents[2]
RUNNER = CliRunner()

PAIRS = (
    pytest.param(
        ROOT / "tests/fixtures/acceptance/v1/raw/corpus/code/sample.py",
        ROOT / "tests/fixtures/matrix/code/second.py",
        id="source-code",
    ),
    pytest.param(
        ROOT / "tests/fixtures/matrix/tables/alpha.csv",
        ROOT / "tests/fixtures/matrix/tables/beta.csv",
        id="delimited-table",
    ),
    pytest.param(
        ROOT / "tests/fixtures/matrix/json/alpha.json",
        ROOT / "tests/fixtures/matrix/json/beta.jsonl",
        id="document-json-records",
    ),
)


@pytest.mark.parametrize("first,second", PAIRS)
def test_parse_accepts_two_independent_matrix_sources(
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
        ],
    )
    assert result.exit_code == 0, result.output
