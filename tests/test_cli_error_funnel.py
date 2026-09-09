"""Post-20 defect D-09: operator-input failures are error[code], never tracebacks."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.parsers.structured import parse_csv_file, parse_json_file

runner = CliRunner()


def test_map_missing_plan_file_is_a_typed_error(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "map",
            str(tmp_path / "ws"),
            "--goal",
            "learn-the-text",
            "--representation",
            "whole-text",
            "--plan",
            str(tmp_path / "missing-plan.json"),
        ],
    )
    assert result.exit_code == 2, result.output
    assert "Traceback" not in result.output
    assert "error[" in result.output


def test_map_malformed_plan_file_is_a_typed_error(tmp_path: Path) -> None:
    plan = tmp_path / "plan.json"
    plan.write_text("{not json", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "map",
            str(tmp_path / "ws"),
            "--goal",
            "learn-the-text",
            "--representation",
            "whole-text",
            "--plan",
            str(plan),
        ],
    )
    assert result.exit_code == 2, result.output
    assert "Traceback" not in result.output
    assert "error[" in result.output


def test_mapping_rejections_missing_plan_is_a_typed_error(tmp_path: Path) -> None:
    rows = tmp_path / "rows.jsonl"
    rows.write_text('{"text": "a"}\n', encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "mapping-rejections",
            str(rows),
            "--plan",
            str(tmp_path / "missing-plan.json"),
            "--output",
            str(tmp_path / "out"),
        ],
    )
    assert result.exit_code == 2, result.output
    assert "Traceback" not in result.output
    assert "error[" in result.output


def test_seal_missing_workspace_is_a_typed_error(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["seal", str(tmp_path / "missing-ws"), "-o", str(tmp_path / "out.vfbundle")],
    )
    assert result.exit_code == 1, result.output
    assert "Traceback" not in result.output
    assert "error[" in result.output


def test_csv_oversized_field_is_a_typed_refusal(tmp_path: Path) -> None:
    path = tmp_path / "wide.csv"
    path.write_text("a,b\n" + "x" * 200_000 + ",1\n", encoding="utf-8")
    result = parse_csv_file(path, logical_path=path.name)
    assert result.diagnostics.status == "refused"
    codes = {item.code for item in result.diagnostics.diagnostics}
    assert "csv.invalid" in codes


def test_csv_oversized_field_through_the_cli_is_not_a_traceback(tmp_path: Path) -> None:
    path = tmp_path / "wide.csv"
    path.write_text("a,b\n" + "x" * 200_000 + ",1\n", encoding="utf-8")
    result = runner.invoke(
        app, ["parse", str(path), "-o", str(tmp_path / "ws"), "--source-root", str(tmp_path)]
    )
    assert "Traceback" not in result.output
    assert result.exit_code != 0


def test_json_deep_nesting_is_a_typed_refusal(tmp_path: Path) -> None:
    path = tmp_path / "deep.json"
    path.write_text("[" * 100_000 + "]" * 100_000, encoding="utf-8")
    result = parse_json_file(path, logical_path=path.name)
    assert result.diagnostics.status == "refused"
    refusal = next(
        item for item in result.diagnostics.diagnostics if item.code == "json.invalid"
    )
    assert "depth" in refusal.message


def test_json_oversized_integer_is_a_typed_refusal(tmp_path: Path) -> None:
    path = tmp_path / "big.json"
    path.write_text("{\"n\": " + "9" * 10_000 + "}", encoding="utf-8")
    result = parse_json_file(path, logical_path=path.name)
    assert result.diagnostics.status == "refused"
    assert "json.invalid" in {item.code for item in result.diagnostics.diagnostics}
