"""Phase 13.4 near-duplicates: named clusters, no silent deletes."""

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
    DISTRIBUTION_FACT_NAMES,
    NEAR_DUPLICATE_ALGORITHM_ID,
    NEAR_DUPLICATE_FACT_NAMES,
    report_near_duplicates,
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
        producer_id="veriformis.test.quality-near-duplicates",
        producer_version="1",
        config_digest=artifact_config_digest,
    )
    artifact = IRArtifactInput.create(
        source_id=source.id,
        artifact_id=artifact_id,
        artifact_kind="cleaned-document-ir",
        document_json=document_json,
        producer_id="veriformis.test.quality-near-duplicates",
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
    construction = construct_dataset(
        recipe,
        ConstructionInputs.create(
            cleaning_config_digest=canonical_digest({"cleaning": "fixture-v1"}),
            sources=tuple(bundle.source for bundle in bundles),
            chunks=tuple(chunk for bundle in bundles for chunk in bundle.chunks),
            transforms=(),
            ir_artifacts=tuple(bundle.artifact for bundle in bundles),
        ),
    )
    inputs = ConstructionInputs.create(
        cleaning_config_digest=canonical_digest({"cleaning": "fixture-v1"}),
        sources=tuple(bundle.source for bundle in bundles),
        chunks=tuple(chunk for bundle in bundles for chunk in bundle.chunks),
        transforms=(),
        ir_artifacts=tuple(bundle.artifact for bundle in bundles),
    )
    finished_plan = FinishedDatasetPlan.create(
        recipe_id=recipe.recipe_id,
        construction_result_id=construction.result_id,
        curation_policy=CurationPolicy.create(minimum_target_characters=1),
        split_policy=SplitPolicy.create(
            evaluation_ratio_ppm=500_000,
            evaluation_required=True,
            seed="quality-near-duplicates-v1",
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
    return report_near_duplicates(
        recipe=case.recipe,
        construction=case.construction,
        curation=case.curation,
        split=case.split,
    )


def test_similar_targets_form_an_inspectable_cluster(tmp_path: Path) -> None:
    case = _finished(
        tmp_path,
        (
            (
                "near-a.txt",
                "The quick brown fox jumps over the lazy dog.",
            ),
            (
                "near-b.txt",
                "The quick brown fox jumps over the lazy dog!",
            ),
            (
                "other.txt",
                "Omega zeta unrelated material for the third source.",
            ),
        ),
    )
    first = _report(case)
    second = _report(case)
    assert first == second
    assert first.enforcing is False
    require_quality_report_not_enforcing(first)
    assert tuple(sorted(case.curation.included_record_ids)) == tuple(
        sorted(record.record_id for record in case.construction.records)
    )
    assert len(case.curation.included_record_ids) == 3
    assert _fact(first, "included-record-count").integer_value == 3
    names = tuple(item.name for item in first.facts)
    assert names == tuple(sorted(DISTRIBUTION_FACT_NAMES + NEAR_DUPLICATE_FACT_NAMES))
    assert _json(first, "near-duplicate-algorithm") == NEAR_DUPLICATE_ALGORITHM_ID
    assert "semantic" not in NEAR_DUPLICATE_ALGORITHM_ID
    assert _fact(first, "near-duplicate-cluster-count").integer_value == 1
    assert _fact(first, "near-duplicate-member-count").integer_value == 2
    assert _fact(first, "near-duplicate-shingle-size").integer_value == 5
    assert _fact(first, "near-duplicate-cluster-threshold-ppm").integer_value == 800000
    clusters = _json(first, "near-duplicate-clusters")
    assert len(clusters) == 1
    assert len(clusters[0]["record-ids"]) == 2
    ppm = clusters[0]["pair-similarities-ppm"][0][2]
    assert type(ppm) is int
    assert ppm >= 800000
    preview = _json(first, "near-duplicate-threshold-preview")
    assert preview["800000"]["cluster-count"] == 1
    assert preview["990000"]["cluster-count"] == 0
    policy = first.policy_decisions
    assert len(policy) == 1
    assert policy[0].action == "record-only"
    assert policy[0].name == "near-duplicate-disabled"
    assert policy[0].threshold_id is None
    assert first.recommendations == ()
    assert first.plan_id == case.curation.plan_id
    assert CurationPolicy.create(minimum_target_characters=1).near_duplicate_policy == (
        "disabled"
    )


def test_casefold_and_whitespace_normalize_cluster(tmp_path: Path) -> None:
    case = _finished(
        tmp_path,
        (
            ("cafe-a.txt", "Café au lait for the first source."),
            ("cafe-b.txt", "CAFÉ  au   lait for the first source."),
            ("other.txt", "Omega zeta unrelated material for the third source."),
        ),
    )
    report = _report(case)
    assert _fact(report, "included-record-count").integer_value == 3
    assert _fact(report, "near-duplicate-cluster-count").integer_value == 1
    assert _fact(report, "near-duplicate-member-count").integer_value == 2
    ppm = _json(report, "near-duplicate-clusters")[0]["pair-similarities-ppm"][0][2]
    assert type(ppm) is int
    assert ppm == 1_000_000


def test_distinct_targets_do_not_cluster(tmp_path: Path) -> None:
    case = _finished(
        tmp_path,
        (
            ("a.txt", "Alpha exact kept text for source one."),
            ("b.txt", "Beta completely different omega text."),
            ("c.txt", "Gamma zeta unrelated material here."),
        ),
    )
    report = _report(case)
    assert _fact(report, "included-record-count").integer_value == 3
    assert _fact(report, "near-duplicate-cluster-count").integer_value == 0
    assert _json(report, "near-duplicate-clusters") == []
    assert _json(report, "near-duplicate-threshold-preview")["500000"][
        "cluster-count"
    ] == 0
