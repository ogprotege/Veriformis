from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import pytest

from veriformis.chunkers.base import Chunk
from veriformis.chunkers.strategies import chunk_paragraph
from veriformis.construction import (
    ConstructionInputs,
    DatasetRecipe,
    IRArtifactInput,
    SegmentationPolicy,
    TrainingObjective,
    construct_dataset,
)
from veriformis.contracts import V1_FINISHED_DATASET_GATES
from veriformis.datasets import (
    CurationPolicy,
    FinishedDatasetPlan,
    SerializationPlan,
    SplitPolicy,
    curate_dataset,
    serialize_dataset,
    split_dataset,
)
from veriformis.datasets.validation import (
    DatasetGateResult,
    DatasetSnapshot,
    DatasetValidationReport,
    SnapshotArtifactBinding,
    SnapshotFileBinding,
    SnapshotValidatorBinding,
    create_dataset_snapshot,
    dataset_snapshot_from_json_bytes,
    dataset_snapshot_json_bytes,
    dataset_validation_report_from_json_bytes,
    dataset_validation_report_json_bytes,
    validate_dataset_snapshot,
    validate_finished_dataset,
)
from veriformis.errors import DatasetValidationError, DuplicateIdentityError
from veriformis.identity import (
    canonical_digest,
    derive_artifact_id,
    lossless_json_bytes,
    sha256_digest,
)
from veriformis.ir import Document, Paragraph, Text, attach_canonical_provenance
from veriformis.ir.serde import document_to_dict
from veriformis.sources import SourceRef, register_source


@dataclass(frozen=True)
class _SourceBundle:
    source: SourceRef
    chunks: tuple[Chunk, ...]
    artifact: IRArtifactInput


def _source_bundle(tmp_path: Path, *, logical_path: str, text: str) -> _SourceBundle:
    document = Document(children=[Paragraph(children=[Text(text)])])
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
    config_digest = canonical_digest({"fixture": logical_path})
    artifact = IRArtifactInput.create(
        source_id=source.id,
        artifact_id=derive_artifact_id(
            kind="cleaned-document-ir",
            content_sha256=sha256_digest(document_json),
            source_ids=(source.id,),
            producer_id="veriformis.test.validation",
            producer_version="1",
            config_digest=config_digest,
        ),
        artifact_kind="cleaned-document-ir",
        document_json=document_json,
        producer_id="veriformis.test.validation",
        producer_version="1",
        config_digest=config_digest,
    )
    return _SourceBundle(source, tuple(chunks), artifact)


def _finished_case(tmp_path: Path):
    bundles = (
        _source_bundle(
            tmp_path,
            logical_path="validation-alpha.txt",
            text="Alpha exact source text.",
        ),
        _source_bundle(
            tmp_path,
            logical_path="validation-beta.txt",
            text="Beta exact source text.",
        ),
    )
    objective = TrainingObjective.create("full_text")
    recipe = DatasetRecipe.create(
        objective=objective,
        source_ids=tuple(bundle.source.id for bundle in bundles),
        cleaning_config_digest=canonical_digest({"cleaning": "validation-v1"}),
        segmentation=SegmentationPolicy(
            schema_version="veriformis.segmentation-policy/v1",
            strategy="paragraph",
            size=1_000,
            overlap=100,
        ),
        target_row_schema="text",
    )
    inputs = ConstructionInputs.create(
        cleaning_config_digest=recipe.cleaning_config_digest,
        sources=tuple(bundle.source for bundle in bundles),
        chunks=tuple(chunk for bundle in bundles for chunk in bundle.chunks),
        ir_artifacts=tuple(bundle.artifact for bundle in bundles),
    )
    construction = construct_dataset(recipe, inputs)
    plan = FinishedDatasetPlan.create(
        recipe_id=recipe.recipe_id,
        construction_result_id=construction.result_id,
        curation_policy=CurationPolicy.create(minimum_target_characters=1),
        split_policy=SplitPolicy.create(
            evaluation_ratio_ppm=500_000,
            evaluation_required=True,
            seed="validation-test-v1",
        ),
        serialization_plan=SerializationPlan.create(row_schema="text"),
    )
    curation = curate_dataset(plan, recipe, inputs, construction)
    split = split_dataset(
        plan,
        construction,
        curation,
        {bundle.source.id: bundle.source.sha256 for bundle in bundles},
    )
    output = serialize_dataset(plan, recipe, construction, curation, split)
    return (
        plan,
        recipe,
        inputs,
        construction,
        curation,
        split,
        output,
    )


def test_exact_validation_replays_every_stage_and_all_seventeen_gates(
    tmp_path: Path,
) -> None:
    plan, recipe, inputs, construction, curation, split, output = _finished_case(
        tmp_path
    )

    report = validate_finished_dataset(
        plan,
        recipe,
        inputs,
        construction,
        curation,
        split,
        output.row_set,
        train_jsonl=output.train_jsonl,
        evaluation_jsonl=output.evaluation_jsonl,
        provenance_jsonl=output.provenance_jsonl,
    )

    assert report.status == "passed"
    assert tuple(item.gate_id for item in report.gate_results) == (
        V1_FINISHED_DATASET_GATES
    )
    assert all(item.status == "passed" for item in report.gate_results)
    assert report.snapshot_id == report.snapshot.snapshot_id
    assert report.snapshot.source_ids == recipe.source_ids
    assert tuple(item.role for item in report.snapshot.artifact_bindings) == (
        "plan",
        "recipe",
        "construction-result",
        "curation-result",
        "split-result",
        "row-set",
    )
    assert tuple(item.path for item in report.snapshot.file_bindings) == (
        "data/train.jsonl",
        "data/evaluation.jsonl",
        "metadata/row-provenance.jsonl",
    )

    report_bytes = dataset_validation_report_json_bytes(report)
    assert dataset_validation_report_from_json_bytes(report_bytes) == report
    snapshot_bytes = dataset_snapshot_json_bytes(report.snapshot)
    assert dataset_snapshot_from_json_bytes(snapshot_bytes) == report.snapshot
    assert report_bytes == dataset_validation_report_json_bytes(
        validate_finished_dataset(
            plan,
            recipe,
            inputs,
            construction,
            curation,
            split,
            output.row_set,
            train_jsonl=output.train_jsonl,
            evaluation_jsonl=output.evaluation_jsonl,
            provenance_jsonl=output.provenance_jsonl,
        )
    )


def test_exact_byte_tamper_fails_encoding_and_snapshot_without_hiding_gates(
    tmp_path: Path,
) -> None:
    plan, recipe, inputs, construction, curation, split, output = _finished_case(
        tmp_path
    )
    snapshot = create_dataset_snapshot(
        plan,
        recipe,
        construction,
        curation,
        split,
        output.row_set,
        train_jsonl=output.train_jsonl,
        evaluation_jsonl=output.evaluation_jsonl,
        provenance_jsonl=output.provenance_jsonl,
    )

    report = validate_dataset_snapshot(
        snapshot,
        plan=plan,
        recipe=recipe,
        construction_inputs=inputs,
        construction_result=construction,
        curation_result=curation,
        split_result=split,
        row_set=output.row_set,
        train_jsonl=output.train_jsonl + b" ",
        evaluation_jsonl=output.evaluation_jsonl,
        provenance_jsonl=output.provenance_jsonl,
    )

    gates = {item.gate_id: item for item in report.gate_results}
    assert report.status == "failed"
    assert len(report.gate_results) == 17
    assert gates["encoding"].status == "failed"
    assert gates["encoding"].finding_codes == ("emitted-bytes-mismatch",)
    assert gates["snapshot"].status == "failed"
    assert "snapshot-file-digest-mismatch" in gates["snapshot"].finding_codes
    assert gates["objective"].status == "passed"


def test_unreadable_critical_input_reports_failure_and_blocked_dependents(
    tmp_path: Path,
) -> None:
    plan, recipe, inputs, construction, curation, split, output = _finished_case(
        tmp_path
    )
    snapshot = create_dataset_snapshot(
        plan,
        recipe,
        construction,
        curation,
        split,
        output.row_set,
        train_jsonl=output.train_jsonl,
        evaluation_jsonl=output.evaluation_jsonl,
        provenance_jsonl=output.provenance_jsonl,
    )

    report = validate_dataset_snapshot(
        snapshot,
        plan=plan,
        recipe=recipe,
        construction_inputs=inputs,
        construction_result=construction,
        curation_result=b"not-json",
        split_result=split,
        row_set=output.row_set,
        train_jsonl=output.train_jsonl,
        evaluation_jsonl=output.evaluation_jsonl,
        provenance_jsonl=output.provenance_jsonl,
    )

    gates = {item.gate_id: item for item in report.gate_results}
    assert report.status == "failed"
    assert gates["construction-replay"].status == "passed"
    assert gates["record-lifecycle"].status == "passed"
    assert gates["curation"].status == "failed"
    assert gates["deduplication"].status == "blocked"
    assert gates["split"].status == "blocked"
    assert gates["snapshot"].status == "failed"
    assert tuple(item.gate_id for item in report.gate_results) == (
        V1_FINISHED_DATASET_GATES
    )


def test_strict_loaders_reject_unknown_duplicate_noncanonical_and_identity_tamper(
    tmp_path: Path,
) -> None:
    plan, recipe, inputs, construction, curation, split, output = _finished_case(
        tmp_path
    )
    report = validate_finished_dataset(
        plan,
        recipe,
        inputs,
        construction,
        curation,
        split,
        output.row_set,
        train_jsonl=output.train_jsonl,
        evaluation_jsonl=output.evaluation_jsonl,
        provenance_jsonl=output.provenance_jsonl,
    )
    canonical = dataset_validation_report_json_bytes(report)

    with pytest.raises(DatasetValidationError, match="not canonical"):
        dataset_validation_report_from_json_bytes(canonical + b"\n")

    value = report.model_dump(mode="json")
    value["extra"] = True
    with pytest.raises(DatasetValidationError, match="extra"):
        dataset_validation_report_from_json_bytes(lossless_json_bytes(value))

    value = report.model_dump(mode="json")
    value["status"] = "failed"
    with pytest.raises(DatasetValidationError, match="status contradicts"):
        dataset_validation_report_from_json_bytes(lossless_json_bytes(value))

    duplicate = canonical.replace(
        b'{"gate_results":',
        b'{"gate_results":[],"gate_results":',
        1,
    )
    with pytest.raises(DuplicateIdentityError, match="duplicate key"):
        dataset_validation_report_from_json_bytes(duplicate)


def test_exact_model_fields_and_failed_report_invariants_are_closed(
    tmp_path: Path,
) -> None:
    assert set(SnapshotArtifactBinding.model_fields) == {
        "schema_version",
        "role",
        "artifact_id",
        "artifact_schema_version",
        "sha256",
        "byte_size",
    }
    assert set(SnapshotFileBinding.model_fields) == {
        "schema_version",
        "path",
        "role",
        "media_type",
        "sha256",
        "byte_size",
        "record_count",
    }
    assert set(SnapshotValidatorBinding.model_fields) == {
        "schema_version",
        "gate_id",
        "validator_version",
    }
    assert set(DatasetSnapshot.model_fields) == {
        "schema_version",
        "snapshot_id",
        "plan_id",
        "recipe_id",
        "construction_result_id",
        "curation_result_id",
        "split_result_id",
        "row_set_id",
        "source_ids",
        "artifact_bindings",
        "file_bindings",
        "validator_bindings",
    }
    assert set(DatasetGateResult.model_fields) == {
        "schema_version",
        "gate_result_id",
        "snapshot_id",
        "gate_id",
        "validator_version",
        "status",
        "finding_codes",
    }
    assert set(DatasetValidationReport.model_fields) == {
        "schema_version",
        "report_id",
        "snapshot_id",
        "snapshot",
        "status",
        "gate_results",
    }

    plan, recipe, inputs, construction, curation, split, output = _finished_case(
        tmp_path
    )
    report = validate_finished_dataset(
        plan,
        recipe,
        inputs,
        construction,
        curation,
        split,
        output.row_set,
        train_jsonl=output.train_jsonl,
        evaluation_jsonl=output.evaluation_jsonl,
        provenance_jsonl=output.provenance_jsonl,
    )
    bad = deepcopy(report.model_dump(mode="json"))
    bad["gate_results"][0]["status"] = "failed"
    bad["gate_results"][0]["finding_codes"] = ["forced-failure"]
    with pytest.raises(DatasetValidationError):
        dataset_validation_report_from_json_bytes(lossless_json_bytes(bad))
