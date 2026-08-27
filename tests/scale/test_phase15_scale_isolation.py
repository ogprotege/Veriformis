"""Phase 15 isolation: baseline exists; no published tier or streaming API."""

from __future__ import annotations

import importlib
import json
import tomllib
from pathlib import Path

from veriformis.cli import app
from veriformis.contracts import (
    FINISHED_DATASET_SCHEMA_IDS,
    V1_FINISHED_DATASET_GATES,
)
from veriformis.exports import hugging_face_dataset as hugging_face_dataset_mod
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.scale import (
    ci_tiny_specs,
    materialize_scale_corpus,
    measurement_ladder_specs,
    run_named_tiny_baseline,
    scale_support_catalog,
)


ROOT = Path(__file__).resolve().parents[2]

_FORBIDDEN_CLI = frozenset(
    {
        "benchmark",
        "scale",
        "scale-benchmark",
        "scale-report",
        "scale-tier",
        "shard-export",
        "stream",
        "stream-compile",
    }
)
_FORBIDDEN_MCP = frozenset(
    {
        "benchmark",
        "scale",
        "scale_benchmark",
        "scale-benchmark",
        "scale_report",
        "scale_tier",
        "shard_export",
        "shard-export",
        "stream",
        "stream_compile",
        "stream-compile",
    }
)
_FORBIDDEN_SERVICE = (
    "materialize_scale_corpus",
    "optimize_measured_bottlenecks",
    "profile_hot_paths",
    "publish_scale_tiers",
    "run_benchmark",
    "scale_benchmark",
    "shard_export",
    "stream_compile",
)


def _support() -> dict[str, object]:
    return json.loads(
        (ROOT / "docs/governance/support-registry.json").read_text(encoding="utf-8")
    )


def _corpus_demand() -> dict[str, object]:
    return json.loads(
        (ROOT / "docs/governance/corpus-demand-matrix.json").read_text(
            encoding="utf-8"
        )
    )


def test_seventeen_finished_dataset_gates_are_unchanged() -> None:
    assert V1_FINISHED_DATASET_GATES == (
        "construction-replay",
        "record-lifecycle",
        "curation",
        "deduplication",
        "quality",
        "balance",
        "coverage",
        "split",
        "leakage",
        "row-binding",
        "objective",
        "schema",
        "encoding",
        "masking",
        "partition-nonempty",
        "aptus-row-shape",
        "snapshot",
    )
    assert len(V1_FINISHED_DATASET_GATES) == 17


def test_retained_scale_benchmark_gap_is_closed() -> None:
    gaps = _support()["known_current_gaps"]
    assert isinstance(gaps, list)
    assert all(
        not (isinstance(item, dict) and item.get("id") == "gap-retained-scale-benchmarks")
        for item in gaps
    )


def test_representative_scale_corpus_gap_stays_open() -> None:
    matrix = _corpus_demand()
    gap_ids = {
        item["gap_id"]
        for item in matrix["evidence_gaps"]
        if isinstance(item, dict)
    }
    assert "representative-scale" in gap_ids


def test_support_registry_publishes_no_corpus_tiers() -> None:
    support = _support()
    for key in (
        "corpus_tiers",
        "published_corpus_tiers",
        "scale_tiers",
        "support_tiers",
    ):
        assert key not in support
    product = support["product"]
    assert isinstance(product, dict)
    for key in ("corpus_tiers", "scale_tiers", "support_tiers"):
        assert key not in product
    scale = support["scale"]
    assert isinstance(scale, dict)
    assert scale["published_tiers"] == []
    assert scale["sla_claim"] is False
    assert scale["statistical_meaning"] is False


def test_canonical_json_v1_makes_no_scale_claim() -> None:
    contract = (
        ROOT / "docs/contracts/canonical-json-export-v1.md"
    ).read_text(encoding="utf-8")
    assert "V1 makes no large-scale performance or memory claim." in contract
    guide = (ROOT / "docs/generic-exports.md").read_text(encoding="utf-8")
    assert "v1 makes no scale, streaming, or memory claim" in guide


def test_hugging_face_dataset_pins_one_shard_per_split() -> None:
    source = Path(hugging_face_dataset_mod.__file__).read_text(encoding="utf-8")
    assert 'num_shards={"train": 1, "evaluation": 1}' in source


def test_cli_exposes_baseline_not_tiers() -> None:
    names = {command.name for command in app.registered_commands}
    assert "scale-baseline" in names
    assert "scale-support" in names
    assert names.isdisjoint(_FORBIDDEN_CLI)


def test_mcp_exposes_baseline_not_tiers() -> None:
    tools = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert "scale_baseline" in tools
    assert "scale_support" in tools
    assert tools.isdisjoint(_FORBIDDEN_MCP)


def test_pipeline_service_exposes_baseline_not_tiers() -> None:
    service = PipelineService()
    assert hasattr(service, "run_scale_baseline")
    assert hasattr(service, "discover_scale_support")
    for name in _FORBIDDEN_SERVICE:
        assert not hasattr(service, name)


def test_finished_dataset_schemas_have_no_scale_contract() -> None:
    assert all("scale-tier" not in schema for schema in FINISHED_DATASET_SCHEMA_IDS)
    assert all("scale-benchmark" not in schema for schema in FINISHED_DATASET_SCHEMA_IDS)


def test_scale_package_has_harness_and_no_published_tiers() -> None:
    module = importlib.import_module("veriformis.scale")
    assert hasattr(module, "materialize_scale_corpus")
    assert hasattr(module, "run_named_tiny_baseline")
    assert hasattr(module, "scale_support_discovery")
    assert materialize_scale_corpus is module.materialize_scale_corpus
    assert run_named_tiny_baseline is module.run_named_tiny_baseline
    assert ci_tiny_specs()
    assert measurement_ladder_specs()
    assert scale_support_catalog().published_tiers == ()
    assert not hasattr(module, "publish_scale_tiers")
    assert not hasattr(module, "ScaleTier")


def test_pytest_declares_excluded_scale_benchmark_marker() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    markers = config["tool"]["pytest"]["ini_options"]["markers"]
    assert any(marker.startswith("scale_benchmark:") for marker in markers)


def test_dataset_row_cli_compile_evidence_is_not_a_tier() -> None:
    packet = (
        ROOT
        / "dev/active/independent-product/phase-15-scale/baselines"
    )
    refused = json.loads(
        (packet / "2026-08-27-scale-baseline-ci-tiny-jsonl.refused.json").read_text(
            encoding="utf-8"
        )
    )
    assert refused["kind"] == "scale-baseline-refused"
    assert refused["sla_claim"] is False
    assert refused["exit"] == 2
    measured = json.loads(
        (packet / "2026-08-27-dataset-row-text-jsonl-cli.json").read_text(
            encoding="utf-8"
        )
    )
    assert measured["kind"] == "cli-compile-measured"
    assert measured["compile_path"] == "dataset-row"
    assert measured["sla_claim"] is False
    assert measured["seal_passed"] is True
    assert "schema_id" not in measured
    assert measured["rss_method"] == "max-of-per-stage-/usr/bin/time-l"
