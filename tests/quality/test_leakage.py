"""Phase 13.5 leakage facts: imported partitions and digest-bound corpora."""

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
    LEAKAGE_FACT_NAMES,
    UNBOUND_REFERENCE_CORPUS,
    bound_reference_corpus,
    report_leakage_checks,
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
        producer_id="veriformis.test.quality-leakage",
        producer_version="1",
        config_digest=artifact_config_digest,
    )
    artifact = IRArtifactInput.create(
        source_id=source.id,
        artifact_id=artifact_id,
        artifact_kind="cleaned-document-ir",
        document_json=document_json,
        producer_id="veriformis.test.quality-leakage",
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
            seed="quality-leakage-v1",
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


def _report(case: QualityCase, **kwargs):
    return report_leakage_checks(
        recipe=case.recipe,
        construction=case.construction,
        curation=case.curation,
        split=case.split,
        **kwargs,
    )


def test_unbound_corpus_and_matching_hints_are_vacant(tmp_path: Path) -> None:
    case = _finished(
        tmp_path,
        (
            ("a.txt", "Alpha exact kept text for source one."),
            ("b.txt", "Beta completely different omega text."),
        ),
    )
    report = _report(case)
    require_quality_report_not_enforcing(report)
    assert report.enforcing is False
    names = {item.name for item in report.facts}
    assert set(LEAKAGE_FACT_NAMES) <= names
    assert _fact(report, "leakage-cross-partition-exact-target-count").integer_value == 0
    assert _fact(report, "leakage-imported-partition-mismatch-count").integer_value == 0
    assert _json(report, "leakage-imported-partition-mismatches") == []
    assert _json(report, "leakage-reference-corpus-digest") == UNBOUND_REFERENCE_CORPUS
    assert _fact(report, "leakage-reference-corpus-hit-count").integer_value == 0
    assert _json(report, "leakage-reference-corpus-hits") == []
    assert {item.name for item in report.policy_decisions} >= {
        "leakage-record-only",
        "near-duplicate-disabled",
    }


def test_imported_hint_mismatch_and_bound_corpus_hits(tmp_path: Path) -> None:
    case = _finished(
        tmp_path,
        (
            ("a.txt", "Alpha exact kept text for source one."),
            ("b.txt", "Beta completely different omega text."),
        ),
    )
    assignment = case.split.assignments[0]
    opposite: str = "evaluation" if assignment.partition == "train" else "train"
    target = next(
        field.value
        for record in case.construction.records
        if record.record_id == assignment.record_id
        for field in record.fields
        if field.name == "text"
    )
    corpus = bound_reference_corpus((sha256_digest(target),))
    report = _report(
        case,
        imported_partition_hints={assignment.record_id: opposite},
        reference_corpus=corpus,
    )
    assert _fact(report, "leakage-imported-partition-mismatch-count").integer_value == 1
    mismatches = _json(report, "leakage-imported-partition-mismatches")
    assert mismatches == [
        {
            "assigned": assignment.partition,
            "hinted": opposite,
            "record-id": assignment.record_id,
        }
    ]
    assert _json(report, "leakage-reference-corpus-digest") == corpus.corpus_digest
    assert _fact(report, "leakage-reference-corpus-hit-count").integer_value == 1
    assert _json(report, "leakage-reference-corpus-hits") == [assignment.record_id]
