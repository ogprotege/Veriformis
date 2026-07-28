# tests/test_cli.py
import json

from typer.testing import CliRunner

from veriformis.cli import app

runner = CliRunner()


def test_full_pipeline_on_text_file(tmp_path):
    src = tmp_path / "notes.txt"
    src.write_text("First paragraph here.\n\n37\n\nSecond paragraph here.", encoding="utf-8")
    ws = tmp_path / "ws"

    result = runner.invoke(app, ["parse", str(src), "-o", str(ws)])
    assert result.exit_code == 0, result.output
    assert (ws / "notes.ir.json").exists()

    result = runner.invoke(app, ["clean", str(ws)])
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["chunk", str(ws), "--strategy", "paragraph"])
    assert result.exit_code == 0, result.output
    chunks = json.loads((ws / "chunks.json").read_text())
    assert len(chunks) >= 1

    result = runner.invoke(app, ["format", str(ws), "--format", "completion"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["validate", str(ws), "--format", "completion"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["seal", str(ws), "-o", str(tmp_path / "out.vfbundle")])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "out.vfbundle" / "manifest.json").exists()


def test_parse_rejects_unknown_extension(tmp_path):
    bad = tmp_path / "data.xyz"
    bad.write_text("x")
    result = runner.invoke(app, ["parse", str(bad), "-o", str(tmp_path / "ws2")])
    assert result.exit_code == 2
    assert "unsupported" in result.output.lower()


def test_preview_writes_nothing(tmp_path):
    src = tmp_path / "doc.txt"
    src.write_text("line\n\n42\n\nmore")
    result = runner.invoke(app, ["preview", str(src)])
    assert result.exit_code == 0
    assert "page-numbers" in result.output
    assert list(tmp_path.iterdir()) == [src]


def test_preview_covers_all_blocks(tmp_path):
    src = tmp_path / "doc.txt"
    src.write_text("line\n\n42\n\nmore")
    result = runner.invoke(app, ["preview", str(src)])
    assert result.exit_code == 0
    after = result.output.split("--- after ---")[-1]
    assert "42" not in after  # whole-file dry run, not just the first block


def test_validate_rejects_unknown_format(tmp_path):
    result = runner.invoke(app, ["validate", str(tmp_path), "--format", "bogus"])
    assert result.exit_code == 2
    assert "unknown format" in result.output.lower()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0 and "0.1.0" in result.output
