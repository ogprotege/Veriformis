"""Phase 13.8 split-comparability and rare-shape findings."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

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
    DETECTOR_SET_ID,
    report_split_findings,
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
        producer_id="veriformis.test.quality-split-findings",
        producer_version="1",
        config_digest=artifact_config_digest,
    )
    artifact = IRArtifactInput.create(
        source_id=source.id,
        artifact_id=artifact_id,
        artifact_kind="cleaned-document-ir",
        document_json=document_json,
        producer_id="veriformis.test.quality-split-findings",
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
            seed="quality-split-findings-v1",
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


def test_balanced_full_text_split_has_zero_rare_shapes(tmp_path: Path) -> None:
    case = _finished(
        tmp_path,
        (
            ("a.txt", "Alpha exact kept text for source one."),
            ("b.txt", "Beta completely different omega text."),
        ),
    )
    report = report_split_findings(
        recipe=case.recipe,
        construction=case.construction,
        curation=case.curation,
        split=case.split,
    )
    require_quality_report_not_enforcing(report)
    assert _fact(report, "split-empty-target-count").integer_value == 0
    assert _fact(report, "split-empty-context-count").integer_value == 0
    assert _fact(report, "split-malformed-role-count").integer_value == 0
    assert _fact(report, "split-rare-shape-count").integer_value == 0
    assert _json(report, "split-rare-shapes") == []
    assert _fact(report, "split-imbalance-ppm").integer_value == 0
    comparability = _json(report, "split-source-comparability")
    assert len(comparability) == 2
    for entry in comparability.values():
        assert entry["train"] + entry["evaluation"] == 1
    assert _json(report, "detector-set-id") == DETECTOR_SET_ID
    assert "split-findings-record-only" in {
        item.name for item in report.policy_decisions
    }


def test_three_source_split_records_integer_imbalance_ppm(tmp_path: Path) -> None:
    case = _finished(
        tmp_path,
        (
            ("a.txt", "Alpha exact kept text for source one."),
            ("b.txt", "Beta completely different omega text."),
            ("c.txt", "Gamma third independent source text."),
        ),
    )
    report = report_split_findings(
        recipe=case.recipe,
        construction=case.construction,
        curation=case.curation,
        split=case.split,
    )
    require_quality_report_not_enforcing(report)
    train = case.split.realized_train_record_count
    evaluation = case.split.realized_evaluation_record_count
    total = train + evaluation
    assert total == 3
    assert abs(train - evaluation) == 1
    assert _fact(report, "split-imbalance-ppm").integer_value == 333_333
    assert _fact(report, "split-rare-shape-count").integer_value == 0
    assert _fact(report, "split-empty-target-count").integer_value == 0
    assert _fact(report, "split-malformed-role-count").integer_value == 0


def test_cli_and_service_still_have_no_quality_report_command() -> None:
    names = {command.name for command in app.registered_commands}
    assert "quality-report" not in names
    assert not hasattr(PipelineService(), "quality_report")
    tools = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert "quality_report" not in tools
    assert "quality-report" not in tools
