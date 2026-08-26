"""Phase 13.9 previewable quality gates and labeled fixtures."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from veriformis.chunkers.base import Chunk
from veriformis.chunkers.strategies import chunk_paragraph
from veriformis.cli import app
from veriformis.construction import (
    ConstructionInputs,
    ConstructionPass,
    ConstructionResult,
    DatasetRecipe,
    IRArtifactInput,
    SegmentationPolicy,
    TrainingObjective,
    construct_dataset,
)
from veriformis.datasets.curation import curate_dataset
from veriformis.datasets.models import CurationPolicy, CurationResult
from veriformis.datasets.plan import FinishedDatasetPlan
from veriformis.datasets.serialization import SerializationPlan
from veriformis.datasets.splitting import SplitPolicy, SplitResult, split_dataset
from veriformis.errors import QualityReportError
from veriformis.identity import (
    canonical_digest,
    derive_artifact_id,
    lossless_json_bytes,
    sha256_digest,
)
from veriformis.ir import Block, Document, Paragraph, Text, attach_canonical_provenance
from veriformis.ir.serde import document_to_dict
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.quality import (
    LABELED_FIXTURE_SET_ID,
    LABELED_FIXTURES,
    QUALITY_GATE_POLICY_ID,
    V1_QUALITY_GATES,
    QualityGateSpec,
    preview_quality_gates,
    require_quality_report_not_enforcing,
)
from veriformis.sources import SourceRef, register_source


@dataclass(frozen=True)
class SourceBundle:
    source: SourceRef
    document: Document
    chunks: tuple[Chunk, ...]
    artifact: IRArtifactInput


@dataclass(frozen=True)
class QualityCase:
    recipe: DatasetRecipe
    construction: ConstructionResult
    curation: CurationResult
    split: SplitResult


def source_bundle(
    tmp_path: Path,
    *,
    logical_path: str,
    blocks: Sequence[Block],
) -> SourceBundle:
    document = Document(children=list(blocks))
    stream = attach_canonical_provenance(document)
    source = register_source(
        tmp_path / logical_path,
        "fixture",
        stream,
        logical_path=logical_path,
        raw_bytes=stream.encode("utf-8"),
    )
    document.source_id = source.id
    chunks = chunk_paragraph(
        document.children,
        max_size=1_000,
        source=source,
        transformed=set(),
        block_derivations={},
        region_id="body",
    )
    document_json = lossless_json_bytes(document_to_dict(document))
    artifact_config_digest = canonical_digest({"fixture": logical_path})
    artifact_id = derive_artifact_id(
        kind="cleaned-document-ir",
        content_sha256=sha256_digest(document_json),
        source_ids=(source.id,),
        producer_id="veriformis.test.quality-gates",
        producer_version="1",
        config_digest=artifact_config_digest,
    )
    artifact = IRArtifactInput.create(
        source_id=source.id,
        artifact_id=artifact_id,
        artifact_kind="cleaned-document-ir",
        document_json=document_json,
        producer_id="veriformis.test.quality-gates",
        producer_version="1",
        config_digest=artifact_config_digest,
    )
    return SourceBundle(source, document, tuple(chunks), artifact)


def _finished(tmp_path: Path, texts: tuple[tuple[str, str], ...]) -> QualityCase:
    bundles = tuple(
        source_bundle(
            tmp_path,
            logical_path=logical_path,
            blocks=[Paragraph(children=[Text(text)])],
        )
        for logical_path, text in texts
    )
    recipe = DatasetRecipe.create(
        objective=TrainingObjective.create("full_text"),
        source_ids=tuple(item.source.id for item in bundles),
        cleaning_config_digest=canonical_digest({"cleaning": "fixture-v1"}),
        segmentation=SegmentationPolicy(
            schema_version="veriformis.segmentation-policy/v1",
            strategy="paragraph",
            size=1_000,
            overlap=100,
        ),
        passes=(ConstructionPass.create(sequence=1, objective_kind="full_text"),),
        target_row_schema="text",
    )
    inputs = ConstructionInputs.create(
        cleaning_config_digest=canonical_digest({"cleaning": "fixture-v1"}),
        sources=tuple(bundle.source for bundle in bundles),
        chunks=tuple(chunk for bundle in bundles for chunk in bundle.chunks),
        transforms=(),
        ir_artifacts=tuple(bundle.artifact for bundle in bundles),
    )
    construction = construct_dataset(recipe, inputs)
    finished_plan = FinishedDatasetPlan.create(
        recipe_id=recipe.recipe_id,
        construction_result_id=construction.result_id,
        curation_policy=CurationPolicy.create(minimum_target_characters=1),
        split_policy=SplitPolicy.create(
            evaluation_ratio_ppm=500_000,
            evaluation_required=True,
            seed="quality-gates-v1",
        ),
        serialization_plan=SerializationPlan.create(row_schema="text"),
    )
    curation = curate_dataset(finished_plan, recipe, inputs, construction)
    split = split_dataset(
        finished_plan,
        construction,
        curation,
        {bundle.source.id: bundle.source.sha256 for bundle in bundles},
    )
    return QualityCase(recipe, construction, curation, split)


def _fact(report, name: str):
    return next(item for item in report.facts if item.name == name)


def _json(report, name: str):
    return json.loads(_fact(report, name).text_value)


def _preview(case: QualityCase, **kwargs):
    return preview_quality_gates(
        recipe=case.recipe,
        construction=case.construction,
        curation=case.curation,
        split=case.split,
        **kwargs,
    )


def test_clean_labeled_negative_preview_does_not_block(tmp_path: Path) -> None:
    case = _finished(
        tmp_path,
        (
            ("a.txt", "Alpha exact kept text for source one."),
            ("b.txt", "Beta completely different omega text."),
        ),
    )
    report = _preview(case)
    require_quality_report_not_enforcing(report)
    assert _json(report, "quality-gate-policy-id") == QUALITY_GATE_POLICY_ID
    assert _json(report, "quality-labeled-fixture-set-id") == LABELED_FIXTURE_SET_ID
    assert _json(report, "quality-gate-plan-id") == case.curation.plan_id
    assert _fact(report, "quality-admitted-blocking-count").integer_value == 0
    assert _fact(report, "quality-gate-would-block-count").integer_value == 0
    assert _fact(report, "quality-labeled-fixture-count").integer_value == len(
        LABELED_FIXTURES
    )
    preview = _json(report, "quality-gate-preview")
    assert [row["gate-id"] for row in preview] == sorted(row["gate-id"] for row in preview)
    assert all(row["admitted-to-block"] is False for row in preview)
    assert all(row["would-block"] is False for row in preview)
    policy = {item.name for item in report.policy_decisions}
    assert "quality-gates-preview-only" in policy
    assert "quality-no-heuristic-admitted-to-block" in policy


def test_labeled_detector_positives_would_block_without_admitting(
    tmp_path: Path,
) -> None:
    case = _finished(
        tmp_path,
        (
            ("a.txt", "Contact alpha@example.test for the first source."),
            ("b.txt", "Key AKIAIOSFODNN7EXAMPLE stays a finding only."),
        ),
    )
    report = _preview(case)
    require_quality_report_not_enforcing(report)
    assert _fact(report, "detector-pii-hit-count").integer_value == 1
    assert _fact(report, "detector-secret-hit-count").integer_value == 1
    assert _fact(report, "quality-gate-would-block-count").integer_value == 2
    assert _fact(report, "quality-admitted-blocking-count").integer_value == 0
    blocked = {
        row["gate-id"]
        for row in _json(report, "quality-gate-preview")
        if row["would-block"]
    }
    assert blocked == {"preview-detector-pii", "preview-detector-secret"}


def test_labeled_near_duplicate_positive_would_block(tmp_path: Path) -> None:
    case = _finished(
        tmp_path,
        (
            ("near-a.txt", "The quick brown fox jumps over the lazy dog."),
            ("near-b.txt", "The quick brown fox jumps over the lazy dog!"),
            ("other.txt", "Omega zeta unrelated material for the third source."),
        ),
    )
    report = _preview(case)
    require_quality_report_not_enforcing(report)
    assert _fact(report, "near-duplicate-member-count").integer_value == 2
    preview = {row["gate-id"]: row for row in _json(report, "quality-gate-preview")}
    assert preview["preview-near-duplicate-members"]["would-block"] is True
    assert preview["preview-near-duplicate-members"]["admitted-to-block"] is False
    assert report.enforcing is False


def test_custom_preview_gate_is_configurable(tmp_path: Path) -> None:
    case = _finished(
        tmp_path,
        (
            ("a.txt", "Alpha exact kept text for source one."),
            ("b.txt", "Beta completely different omega text."),
        ),
    )
    report = _preview(
        case,
        gates=(
            QualityGateSpec(
                gate_id="preview-split-empty-target",
                fact_name="split-empty-target-count",
                threshold=1,
                admitted_to_block=False,
            ),
        ),
    )
    require_quality_report_not_enforcing(report)
    preview = _json(report, "quality-gate-preview")
    assert preview == [
        {
            "admitted-to-block": False,
            "fact": "split-empty-target-count",
            "gate-id": "preview-split-empty-target",
            "observed": 0,
            "threshold": 1,
            "would-block": False,
        }
    ]
    assert _fact(report, "quality-gate-would-block-count").integer_value == 0


def test_invalid_threshold_duplicate_and_missing_fact_fail_closed(
    tmp_path: Path,
) -> None:
    case = _finished(
        tmp_path,
        (
            ("a.txt", "Alpha exact kept text for source one."),
            ("b.txt", "Beta completely different omega text."),
        ),
    )
    empty = QualityGateSpec(
        gate_id="preview-split-empty-target",
        fact_name="split-empty-target-count",
        threshold=1,
        admitted_to_block=False,
    )
    with pytest.raises(QualityReportError, match="positive integer"):
        _preview(
            case,
            gates=(
                QualityGateSpec(
                    gate_id="preview-split-empty-target",
                    fact_name="split-empty-target-count",
                    threshold=0,
                    admitted_to_block=False,
                ),
            ),
        )
    with pytest.raises(QualityReportError, match="must be unique"):
        _preview(case, gates=(empty, empty))
    with pytest.raises(QualityReportError, match="requires integer fact"):
        _preview(
            case,
            gates=(
                QualityGateSpec(
                    gate_id="preview-missing-fact",
                    fact_name="not-a-quality-fact",
                    threshold=1,
                    admitted_to_block=False,
                ),
            ),
        )


def test_admitted_gate_fails_closed_without_fixture_admission(tmp_path: Path) -> None:
    case = _finished(
        tmp_path,
        (
            ("a.txt", "Alpha exact kept text for source one."),
            ("b.txt", "Beta completely different omega text."),
        ),
    )
    with pytest.raises(QualityReportError, match="cannot block seal"):
        _preview(
            case,
            gates=(
                QualityGateSpec(
                    gate_id="preview-split-empty-target",
                    fact_name="split-empty-target-count",
                    threshold=1,
                    admitted_to_block=True,
                ),
            ),
        )


def test_labeled_fixture_catalog_is_closed_and_sorted() -> None:
    ids = tuple(item.fixture_id for item in LABELED_FIXTURES)
    assert ids == tuple(sorted(ids))
    assert {item.label for item in LABELED_FIXTURES} <= {"positive", "negative"}
    assert all(item.heuristic for item in LABELED_FIXTURES)
    gate_ids = tuple(item.gate_id for item in V1_QUALITY_GATES)
    assert gate_ids == tuple(sorted(gate_ids))
    assert all(item.admitted_to_block is False for item in V1_QUALITY_GATES)


def test_cli_and_service_still_have_no_quality_report_command() -> None:
    names = {command.name for command in app.registered_commands}
    assert "quality-report" not in names
    assert not hasattr(PipelineService(), "quality_report")
    assert not hasattr(PipelineService(), "quality_preview")
    tools = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert "quality_report" not in tools
    assert "quality-report" not in tools
