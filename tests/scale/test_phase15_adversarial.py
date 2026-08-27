"""Phase 15.9: adversarial scale checks at the measured path. No guessed preflight."""

from __future__ import annotations

from pathlib import Path

import pytest

from veriformis.cli import app
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.scale import (
    ScaleCorpusSpec,
    materialize_scale_corpus,
    scale_support_catalog,
)
from veriformis.scale.baseline import compile_document_corpus, request_scale_cancellation
from veriformis.errors import ScaleCancelled


def test_long_row_materializes_exact_length(tmp_path: Path) -> None:
    spec = ScaleCorpusSpec.create(
        corpus_id="adv-long-row",
        input_mode="document-source",
        file_count=1,
        record_count=1,
        row_length=4096,
        nesting_depth=0,
        pdf_pages=0,
        duplicate_rate_ppm=0,
        container="split-jsonl-directory",
        seed="adv-long-row",
    )
    corpus = materialize_scale_corpus(spec, tmp_path)
    body = (tmp_path / corpus.files[0].path).read_text(encoding="utf-8")
    assert corpus.files[0].size == len(body.encode("utf-8"))
    assert "adv-long-row" in body


def test_materialize_file_count_matches_spec(tmp_path: Path) -> None:
    spec = ScaleCorpusSpec.create(
        corpus_id="adv-three-files",
        input_mode="document-source",
        file_count=3,
        record_count=3,
        row_length=16,
        nesting_depth=0,
        pdf_pages=0,
        duplicate_rate_ppm=0,
        container="split-jsonl-directory",
        seed="adv-three-files",
    )
    corpus = materialize_scale_corpus(spec, tmp_path)
    assert len(corpus.files) == 3
    written = [path for path in tmp_path.rglob("*") if path.is_file()]
    assert len(written) == 3


def test_cancel_leaves_no_bundle(tmp_path: Path) -> None:
    spec = ScaleCorpusSpec.create(
        corpus_id="adv-cancel",
        input_mode="document-source",
        file_count=2,
        record_count=4,
        row_length=24,
        nesting_depth=0,
        pdf_pages=0,
        duplicate_rate_ppm=0,
        container="split-jsonl-directory",
        seed="adv-cancel",
    )
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


def test_no_guessed_disk_preflight_or_shard_surface() -> None:
    names = {command.name for command in app.registered_commands}
    assert "disk-preflight" not in names
    assert "scale-preflight" not in names
    assert "shard-export" not in names
    assert "stream-compile" not in names
    tools = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert "disk_preflight" not in tools
    assert "scale_preflight" not in tools
    service = PipelineService()
    assert not hasattr(service, "disk_preflight")
    assert not hasattr(service, "scale_preflight")


def test_unmeasured_work_stays_named() -> None:
    catalog = scale_support_catalog()
    assert catalog.published_tiers == ()
    assert "streaming-compile" in catalog.unmeasured
    assert "export-sharding-as-bottleneck" in catalog.unmeasured
    assert "document-source-above-1-mib" in catalog.unmeasured
    assert "dataset-row-at-ladder-scale" in catalog.unmeasured
