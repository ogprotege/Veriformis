"""Phase 13.7 policy detectors are findings, not certification."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from veriformis.chunkers.base import Chunk
from veriformis.chunkers.strategies import chunk_paragraph
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
from veriformis.quality import (
    DETECTOR_SET_ID,
    report_policy_detectors,
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
        producer_id="veriformis.test.quality-detectors",
        producer_version="1",
        config_digest=artifact_config_digest,
    )
    artifact = IRArtifactInput.create(
        source_id=source.id,
        artifact_id=artifact_id,
        artifact_kind="cleaned-document-ir",
        document_json=document_json,
        producer_id="veriformis.test.quality-detectors",
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
            seed="quality-detectors-v1",
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


def _report(case: QualityCase):
    return report_policy_detectors(
        recipe=case.recipe,
        construction=case.construction,
        curation=case.curation,
        split=case.split,
    )


def test_clean_text_has_no_detector_hits(tmp_path: Path) -> None:
    case = _finished(
        tmp_path,
        (
            ("a.txt", "Alpha exact kept text for source one."),
            ("b.txt", "Beta completely different omega text."),
        ),
    )
    report = _report(case)
    require_quality_report_not_enforcing(report)
    assert _json(report, "detector-set-id") == DETECTOR_SET_ID
    assert _fact(report, "detector-pii-hit-count").integer_value == 0
    assert _fact(report, "detector-secret-hit-count").integer_value == 0
    assert _fact(report, "detector-unsafe-hit-count").integer_value == 0
    assert _fact(report, "detector-license-hit-count").integer_value == 0
    assert _json(report, "detector-hits") == []
    assert "detector-findings-not-certification" in {
        item.name for item in report.policy_decisions
    }


def test_named_detectors_record_findings_not_certification(tmp_path: Path) -> None:
    case = _finished(
        tmp_path,
        (
            ("a.txt", "Contact alpha@example.test for the first source."),
            ("b.txt", "Key AKIAIOSFODNN7EXAMPLE stays a finding only."),
        ),
    )
    report = _report(case)
    assert _fact(report, "detector-pii-hit-count").integer_value == 1
    assert _fact(report, "detector-secret-hit-count").integer_value == 1
    families = {item["family"] for item in _json(report, "detector-hits")}
    assert families == {"pii", "secret"}
    assert report.enforcing is False
