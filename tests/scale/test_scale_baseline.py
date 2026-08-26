"""Phase 15.3: named-hardware baseline harness. Reports are not SLAs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.contracts import SCALE_BASELINE_REPORT_SCHEMA_ID
from veriformis.errors import ScaleCancelled, ScaleError
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.scale import (
    BASELINE_LIMITATIONS,
    BASELINE_STAGES,
    compile_document_corpus,
    materialize_scale_corpus,
    request_scale_cancellation,
    run_named_tiny_baseline,
    spec_by_corpus_id,
)
from veriformis.scale.models import ScaleBaselineReport


RUNNER = CliRunner()


def test_tiny_markdown_baseline_is_evidence_not_an_sla(tmp_path: Path) -> None:
    report = run_named_tiny_baseline("ci-tiny-markdown", tmp_path / "run")
    assert report.schema_id == SCALE_BASELINE_REPORT_SCHEMA_ID
    assert report.sla_claim is False
    assert report.statistical_meaning is False
    assert report.operation == "compile-document"
    assert report.stages == BASELINE_STAGES
    assert report.limitations == BASELINE_LIMITATIONS
    assert report.metrics.wall_ns >= 1
    assert report.metrics.peak_rss_bytes >= 1
    assert report.metrics.source_bytes >= 1
    assert report.metrics.object_count >= 1
    assert report.metrics.cancel_observed is True
    assert report.metrics.resume_observed is True
    assert report.metrics.disk_amplification_ppm == (
        (report.metrics.workspace_bytes + report.metrics.bundle_bytes) * 1_000_000
    ) // report.metrics.source_bytes
    replay = ScaleBaselineReport.model_validate(report.model_dump(mode="json"))
    assert replay == report


def test_dataset_row_baseline_fails_closed(tmp_path: Path) -> None:
    spec = spec_by_corpus_id("ci-tiny-jsonl")
    with pytest.raises(ScaleError, match="document-source"):
        run_named_tiny_baseline(spec.corpus_id, tmp_path)


def test_unknown_corpus_id_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ScaleError, match="unknown scale corpus id"):
        run_named_tiny_baseline("not-a-corpus", tmp_path)


def test_non_empty_work_root_fails_closed(tmp_path: Path) -> None:
    dest = tmp_path / "used"
    dest.mkdir()
    (dest / "stale.txt").write_text("no", encoding="utf-8")
    with pytest.raises(ScaleError, match="empty"):
        run_named_tiny_baseline("ci-tiny-markdown", dest)


def test_between_stage_cancel_stops_after_parse(tmp_path: Path) -> None:
    spec = spec_by_corpus_id("ci-tiny-markdown")
    corpus_dir = tmp_path / "corpus"
    corpus = materialize_scale_corpus(spec, corpus_dir)
    paths = tuple(corpus_dir / item.path for item in corpus.files)
    workspace = tmp_path / "workspace"
    bundle = tmp_path / "bundle"
    with pytest.raises(ScaleCancelled, match="cancelled after parse"):
        compile_document_corpus(
            PipelineService(),
            paths,
            workspace=workspace,
            bundle=bundle,
            source_root=corpus_dir,
            cancellation_check=request_scale_cancellation(),
        )
    assert workspace.is_dir()
    assert not bundle.exists()


def test_python_cli_and_mcp_agree_on_baseline(tmp_path: Path) -> None:
    service = PipelineService()
    python_report = service.run_scale_baseline(
        "ci-tiny-markdown",
        tmp_path / "py",
    )
    cli = RUNNER.invoke(
        app,
        [
            "scale-baseline",
            "--corpus-id",
            "ci-tiny-markdown",
            "--work-root",
            str(tmp_path / "cli"),
        ],
    )
    assert cli.exit_code == 0, cli.output
    cli_report = json.loads(cli.output)
    tools = {
        tool.name: tool.fn
        for tool in create_mcp_server(service)._tool_manager.list_tools()
    }
    mcp_report = json.loads(
        tools["scale_baseline"]("ci-tiny-markdown", str(tmp_path / "mcp"))
    )
    for report in (python_report, cli_report, mcp_report):
        assert report["sla_claim"] is False
        assert report["statistical_meaning"] is False
        assert report["schema_id"] == SCALE_BASELINE_REPORT_SCHEMA_ID
        assert report["spec_id"] == python_report["spec_id"]
        assert report["corpus_id"] == python_report["corpus_id"]


@pytest.mark.scale_benchmark
def test_named_hardware_tiny_baseline_writes_report(tmp_path: Path) -> None:
    report = run_named_tiny_baseline("ci-tiny-markdown", tmp_path)
    path = tmp_path / "baseline.json"
    path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["sla_claim"] is False
    assert loaded["metrics"]["wall_ns"] >= 1
