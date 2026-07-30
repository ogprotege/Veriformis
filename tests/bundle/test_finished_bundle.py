import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

import veriformis.bundle.verifier as verifier_module
import veriformis.bundle.finished as finished_module
from veriformis.chunkers.strategies import chunk_paragraph
from veriformis.bundle.finished import (
    BundleAttestation,
    BundleFile,
    BundlePublicationReceipt,
    BundleVerificationError,
    EVALUATION_PATH,
    FinishedBundleError,
    FinishedBundleManifest,
    PROVENANCE_PATH,
    TRAIN_PATH,
    VALIDATION_PATH,
    build_finished_bundle,
    write_finished_bundle,
)
from veriformis.bundle.verifier import verify_finished_bundle
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
    ProductRow,
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
    V1_ARTIFACT_ROLES,
    dataset_validation_report_from_json_bytes,
    dataset_validation_report_json_bytes,
    validate_finished_dataset,
)
from veriformis.errors import (
    BundleVerificationError as TypedBundleVerificationError,
    WorkspaceRevisionConflict,
)
from veriformis.identity import (
    canonical_digest,
    derive_artifact_id,
    derive_id,
    lossless_json_bytes,
    sha256_digest,
)
from veriformis.ir import Document, Paragraph, Text, attach_canonical_provenance
from veriformis.ir.serde import document_to_dict
from veriformis.sources import register_source

ROWS_PATH = TRAIN_PATH
LINEAGE_PATH = PROVENANCE_PATH


def _record(text: str = "alpha") -> bytes:
    return (
        lossless_json_bytes(
            {
                "messages": (
                    {"content": "Continue the source faithfully.", "role": "user"},
                    {"content": text, "role": "assistant"},
                )
            }
        )
        + b"\n"
    )


def _lineage() -> bytes:
    return (
        lossless_json_bytes(
            {"record_index": 0, "source_evidence_id": derive_id("evidence", {"i": 0})}
        )
        + b"\n"
    )


def _compiled_payloads(
    text: str | tuple[str, ...] = "alpha",
    *,
    objective_kind: str = "full_text",
    row_schema: str = "text",
) -> tuple[dict[str, bytes], dict[str, int]]:
    texts = (text,) if isinstance(text, str) else text
    config_digest = canonical_digest({"fixture": "finished-bundle-v1"})
    sources = []
    chunks = []
    artifacts = []
    for index, value in enumerate(texts):
        logical_path = f"bundle-fixture-{index}.txt"
        document = Document(children=[Paragraph(children=[Text(value)])])
        stream = attach_canonical_provenance(document)
        source = register_source(
            logical_path,
            "fixture",
            stream,
            logical_path=logical_path,
            raw_bytes=stream.encode("utf-8"),
        )
        document.source_id = source.id
        sources.append(source)
        chunks.extend(
            chunk_paragraph(
                document.children,
                max_size=1_000,
                source=source,
                transformed=set(),
                block_derivations={},
                region_id="body",
            )
        )
        document_json = lossless_json_bytes(document_to_dict(document))
        artifacts.append(
            IRArtifactInput.create(
                source_id=source.id,
                artifact_id=derive_artifact_id(
                    kind="cleaned-document-ir",
                    content_sha256=sha256_digest(document_json),
                    source_ids=(source.id,),
                    producer_id="veriformis.test.finished-bundle",
                    producer_version="1",
                    config_digest=config_digest,
                ),
                artifact_kind="cleaned-document-ir",
                document_json=document_json,
                producer_id="veriformis.test.finished-bundle",
                producer_version="1",
                config_digest=config_digest,
            )
        )
    recipe = DatasetRecipe.create(
        objective=TrainingObjective.create(objective_kind),
        source_ids=tuple(source.id for source in sources),
        cleaning_config_digest=config_digest,
        segmentation=SegmentationPolicy(
            schema_version="veriformis.segmentation-policy/v1",
            strategy="paragraph",
            size=1_000,
            overlap=100,
        ),
        target_row_schema=row_schema,
    )
    inputs = ConstructionInputs.create(
        cleaning_config_digest=config_digest,
        sources=tuple(sources),
        chunks=tuple(chunks),
        ir_artifacts=tuple(artifacts),
    )
    construction = construct_dataset(recipe, inputs)
    plan = FinishedDatasetPlan.create(
        recipe_id=recipe.recipe_id,
        construction_result_id=construction.result_id,
        curation_policy=CurationPolicy.create(minimum_target_characters=1),
        split_policy=SplitPolicy.create(
            evaluation_ratio_ppm=500_000,
            evaluation_required=len(sources) > 1,
            seed="finished-bundle-test-v1",
        ),
        serialization_plan=SerializationPlan.create(row_schema=row_schema),
    )
    curation = curate_dataset(plan, recipe, inputs, construction)
    split = split_dataset(
        plan,
        construction,
        curation,
        {source.id: source.sha256 for source in sources},
    )
    output = serialize_dataset(plan, recipe, construction, curation, split)
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
    payloads = {
        TRAIN_PATH: output.train_jsonl,
        EVALUATION_PATH: output.evaluation_jsonl,
        PROVENANCE_PATH: output.provenance_jsonl,
        VALIDATION_PATH: dataset_validation_report_json_bytes(report),
    }
    counts = {
        TRAIN_PATH: output.row_set.train_row_count,
        EVALUATION_PATH: output.row_set.evaluation_row_count,
        PROVENANCE_PATH: output.row_set.total_row_count,
    }
    return payloads, counts


def _passing_validation_report(
    *,
    train: bytes,
    evaluation: bytes,
    provenance: bytes,
    counts: dict[str, int],
) -> DatasetValidationReport:
    identity_by_role = {
        "plan": derive_id("fdp", {"fixture": "plan"}),
        "recipe": derive_id("rcp", {"fixture": "recipe"}),
        "construction-result": derive_id("run", {"fixture": "construction"}),
        "curation-result": derive_id("cur", {"fixture": "curation"}),
        "split-result": derive_id("spt", {"fixture": "split"}),
        "row-set": derive_id("rws", {"fixture": "rows"}),
    }
    body = {
        "schema_version": "veriformis.dataset-snapshot/v1",
        "plan_id": identity_by_role["plan"],
        "recipe_id": identity_by_role["recipe"],
        "construction_result_id": identity_by_role["construction-result"],
        "curation_result_id": identity_by_role["curation-result"],
        "split_result_id": identity_by_role["split-result"],
        "row_set_id": identity_by_role["row-set"],
        "source_ids": (derive_id("src", {"fixture": "source"}),),
        "artifact_bindings": tuple(
            SnapshotArtifactBinding.create(
                role=role,
                artifact_id=identity_by_role[role],
                artifact_bytes=lossless_json_bytes({"fixture": role}),
            )
            for role in V1_ARTIFACT_ROLES
        ),
        "file_bindings": (
            SnapshotFileBinding.create(
                role="training-partition",
                file_bytes=train,
                record_count=counts[TRAIN_PATH],
            ),
            SnapshotFileBinding.create(
                role="evaluation-partition",
                file_bytes=evaluation,
                record_count=counts[EVALUATION_PATH],
            ),
            SnapshotFileBinding.create(
                role="row-provenance",
                file_bytes=provenance,
                record_count=counts[PROVENANCE_PATH],
            ),
        ),
        "validator_bindings": tuple(
            SnapshotValidatorBinding(
                schema_version="veriformis.snapshot-validator-binding/v1",
                gate_id=gate_id,
                validator_version="1",
            )
            for gate_id in V1_FINISHED_DATASET_GATES
        ),
    }
    snapshot = DatasetSnapshot(snapshot_id=derive_id("dss", body), **body)
    return DatasetValidationReport.create(
        snapshot=snapshot,
        gate_results=tuple(
            DatasetGateResult.create(
                snapshot_id=snapshot.snapshot_id,
                gate_id=gate_id,
                status="passed",
            )
            for gate_id in V1_FINISHED_DATASET_GATES
        ),
    )


def _bundle_arguments(
    *,
    files: dict[str, bytes] | None = None,
    record_counts: dict[str, int] | None = None,
    compiled_text: str | tuple[str, ...] = "alpha",
    objective_kind: str = "full_text",
    row_schema: str = "text",
) -> dict:
    if files is None:
        payloads, compiled_counts = _compiled_payloads(
            compiled_text,
            objective_kind=objective_kind,
            row_schema=row_schema,
        )
        counts = compiled_counts if record_counts is None else record_counts
        report = dataset_validation_report_from_json_bytes(payloads[VALIDATION_PATH])
    else:
        counts = (
            {TRAIN_PATH: 1, EVALUATION_PATH: 0, PROVENANCE_PATH: 1}
            if record_counts is None
            else record_counts
        )
        payloads = files
        report = None
        if {
            TRAIN_PATH,
            EVALUATION_PATH,
            PROVENANCE_PATH,
        }.issubset(payloads):
            report = _passing_validation_report(
                train=payloads[TRAIN_PATH],
                evaluation=payloads[EVALUATION_PATH],
                provenance=payloads[PROVENANCE_PATH],
                counts=counts,
            )
            payloads = {
                **payloads,
                VALIDATION_PATH: dataset_validation_report_json_bytes(report),
            }
    roles_by_path = {
        TRAIN_PATH: "training-partition",
        EVALUATION_PATH: "evaluation-partition",
        PROVENANCE_PATH: "row-provenance",
        VALIDATION_PATH: "dataset-validation-report",
    }
    media_by_path = {
        TRAIN_PATH: "application/jsonl",
        EVALUATION_PATH: "application/jsonl",
        PROVENANCE_PATH: "application/jsonl",
        VALIDATION_PATH: "application/json",
    }
    snapshot_id = (
        report.snapshot_id
        if report is not None
        else derive_id("dss", {"fixture": "unreachable-invalid-profile"})
    )
    report_id = (
        report.report_id
        if report is not None
        else derive_id("dvr", {"fixture": "unreachable-invalid-profile"})
    )
    return {
        "files": payloads,
        "roles": {path: roles_by_path.get(path, "invalid") for path in payloads},
        "media_types": {
            path: media_by_path.get(path, "application/octet-stream")
            for path in payloads
        },
        "record_counts": counts,
        "dataset_snapshot_id": snapshot_id,
        "validation_report_id": report_id,
    }


def _rebind_validation_report_to_current_files(arguments: dict) -> None:
    original_report = dataset_validation_report_from_json_bytes(
        arguments["files"][VALIDATION_PATH]
    )
    original_snapshot = original_report.snapshot
    snapshot_body = {
        **original_snapshot.model_dump(mode="python", exclude={"snapshot_id"}),
        "file_bindings": (
            SnapshotFileBinding.create(
                role="training-partition",
                file_bytes=arguments["files"][TRAIN_PATH],
                record_count=arguments["record_counts"][TRAIN_PATH],
            ),
            SnapshotFileBinding.create(
                role="evaluation-partition",
                file_bytes=arguments["files"][EVALUATION_PATH],
                record_count=arguments["record_counts"][EVALUATION_PATH],
            ),
            SnapshotFileBinding.create(
                role="row-provenance",
                file_bytes=arguments["files"][PROVENANCE_PATH],
                record_count=arguments["record_counts"][PROVENANCE_PATH],
            ),
        ),
    }
    changed_snapshot = DatasetSnapshot(
        snapshot_id=derive_id("dss", snapshot_body),
        **snapshot_body,
    )
    changed_report = DatasetValidationReport.create(
        snapshot=changed_snapshot,
        gate_results=tuple(
            DatasetGateResult.create(
                snapshot_id=changed_snapshot.snapshot_id,
                gate_id=gate_id,
                status="passed",
            )
            for gate_id in V1_FINISHED_DATASET_GATES
        ),
    )
    arguments["files"][VALIDATION_PATH] = dataset_validation_report_json_bytes(
        changed_report
    )
    arguments["dataset_snapshot_id"] = changed_report.snapshot_id
    arguments["validation_report_id"] = changed_report.report_id


def _replace_validation_snapshot(arguments: dict, snapshot_body: dict) -> None:
    changed_snapshot = DatasetSnapshot(
        snapshot_id=derive_id("dss", snapshot_body),
        **snapshot_body,
    )
    changed_report = DatasetValidationReport.create(
        snapshot=changed_snapshot,
        gate_results=tuple(
            DatasetGateResult.create(
                snapshot_id=changed_snapshot.snapshot_id,
                gate_id=gate_id,
                status="passed",
            )
            for gate_id in V1_FINISHED_DATASET_GATES
        ),
    )
    arguments["files"][VALIDATION_PATH] = dataset_validation_report_json_bytes(
        changed_report
    )
    arguments["dataset_snapshot_id"] = changed_report.snapshot_id
    arguments["validation_report_id"] = changed_report.report_id


def _provenance_records(arguments: dict) -> list[dict]:
    return [
        json.loads(line)
        for line in arguments["files"][PROVENANCE_PATH].decode("utf-8").splitlines()
    ]


def _replace_provenance_records(arguments: dict, records: list[dict]) -> None:
    arguments["files"][PROVENANCE_PATH] = b"".join(
        lossless_json_bytes(record) + b"\n" for record in records
    )
    _rebind_validation_report_to_current_files(arguments)


def _refresh_provenance_id(record: dict) -> None:
    record["provenance_id"] = derive_id(
        "prv",
        {key: value for key, value in record.items() if key != "provenance_id"},
    )


def _write_valid(tmp_path: Path, name: str = "finished.vfbundle"):
    target = tmp_path / name
    result = write_finished_bundle(target, **_bundle_arguments())
    return target, result


def test_finished_bundle_is_deterministic_closed_and_externally_verifiable(tmp_path):
    target, written = _write_valid(tmp_path)
    manifest_bytes = (target / "manifest.json").read_bytes()
    manifest = FinishedBundleManifest.from_json_bytes(manifest_bytes)
    attestation = BundleAttestation.from_json_bytes(
        (target / "attestation.json").read_bytes()
    )

    assert isinstance(written, BundlePublicationReceipt)
    assert written.trust_grade == "self_consistent"
    assert written.bundle_id == manifest.bundle_id
    assert attestation.manifest_sha256 == sha256_digest(manifest_bytes)
    assert attestation.content_root_sha256 == manifest.content_root_sha256
    assert "manifest_sha256" not in type(manifest).model_fields
    assert {
        str(path.relative_to(target)) for path in target.rglob("*") if path.is_file()
    } == {
        "manifest.json",
        "attestation.json",
        TRAIN_PATH,
        EVALUATION_PATH,
        PROVENANCE_PATH,
        VALIDATION_PATH,
    }
    assert written.manifest_bytes == manifest_bytes
    assert written.attestation_bytes == (target / "attestation.json").read_bytes()
    assert written.manifest_sha256 == sha256_digest(manifest_bytes)

    self_consistent = verify_finished_bundle(target)
    externally_anchored = verify_finished_bundle(
        target,
        expected_manifest_sha256=sha256_digest(manifest_bytes),
    )
    assert self_consistent.trust_grade == "self_consistent"
    assert externally_anchored.trust_grade == "external_digest"
    assert self_consistent.verification_id != externally_anchored.verification_id


def test_finished_bundle_verifies_in_a_fresh_process(tmp_path):
    target, written = _write_valid(tmp_path)
    script = """
from pathlib import Path
import sys

from veriformis.bundle import verify_finished_bundle

result = verify_finished_bundle(
    Path(sys.argv[1]),
    expected_manifest_sha256=sys.argv[2],
)
print(result.trust_grade)
print(result.manifest_sha256)
"""

    completed = subprocess.run(
        [sys.executable, "-c", script, str(target), written.manifest_sha256],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        "external_digest",
        written.manifest_sha256,
    ]


def test_finished_models_are_frozen_strict_and_exact_field(tmp_path):
    target, _ = _write_valid(tmp_path)
    manifest = FinishedBundleManifest.from_json_bytes(
        (target / "manifest.json").read_bytes()
    )
    file_payload = manifest.files[0].model_dump(mode="json")

    with pytest.raises(ValidationError, match="extra"):
        BundleFile.model_validate({**file_payload, "extra": "not allowed"})
    with pytest.raises(ValidationError):
        BundleFile.model_validate({**file_payload, "record_count": 1.0})
    with pytest.raises(ValidationError, match="frozen"):
        manifest.bundle_id = derive_id("bundle", {"forged": True})


def test_public_bundle_verifier_uses_canonical_typed_error():
    assert BundleVerificationError is TypedBundleVerificationError
    assert BundleVerificationError("invalid").code == "bundle-invalid"


def test_finished_bundle_refuses_empty_dataset_before_creating_target(tmp_path):
    target = tmp_path / "empty.vfbundle"
    arguments = _bundle_arguments()
    arguments["files"][TRAIN_PATH] = b""
    arguments["files"][EVALUATION_PATH] = b""
    arguments["files"][PROVENANCE_PATH] = b""
    arguments["record_counts"] = {
        TRAIN_PATH: 0,
        EVALUATION_PATH: 0,
        PROVENANCE_PATH: 0,
    }

    with pytest.raises(
        FinishedBundleError, match="training partition cannot be empty"
    ) as caught:
        write_finished_bundle(target, **arguments)

    assert caught.value.code == "seal-invalid"
    assert not target.exists()


def test_payload_mutation_is_rejected(tmp_path):
    target, _ = _write_valid(tmp_path)
    (target / ROWS_PATH).write_bytes(_record("omega"))

    with pytest.raises(BundleVerificationError, match="(?:size|digest) mismatch"):
        verify_finished_bundle(target)


def test_validation_report_must_be_passing_and_bind_exact_payloads(tmp_path):
    arguments = _bundle_arguments()
    passing = dataset_validation_report_from_json_bytes(
        arguments["files"][VALIDATION_PATH]
    )
    failed_results = list(passing.gate_results)
    failed_results[0] = DatasetGateResult.create(
        snapshot_id=passing.snapshot_id,
        gate_id=failed_results[0].gate_id,
        status="failed",
        finding_codes=("injected-failure",),
    )
    failed = DatasetValidationReport.create(
        snapshot=passing.snapshot,
        gate_results=failed_results,
    )
    arguments["files"][VALIDATION_PATH] = dataset_validation_report_json_bytes(failed)
    arguments["validation_report_id"] = failed.report_id

    target = tmp_path / "failed-validation.vfbundle"
    with pytest.raises(FinishedBundleError, match="passing validation report"):
        write_finished_bundle(target, **arguments)
    assert not target.exists()

    mismatched = _bundle_arguments()
    mismatched["files"][TRAIN_PATH] = _record("changed-after-validation")
    with pytest.raises(FinishedBundleError, match="snapshot binding differs"):
        write_finished_bundle(
            tmp_path / "mismatched-validation.vfbundle",
            **mismatched,
        )


def test_verifier_rejects_semantically_misaligned_row_provenance(tmp_path):
    arguments = _bundle_arguments()
    original_report = dataset_validation_report_from_json_bytes(
        arguments["files"][VALIDATION_PATH]
    )
    raw_provenance = json.loads(arguments["files"][PROVENANCE_PATH].decode("utf-8"))
    raw_provenance["ordinal"] = 1
    raw_provenance["provenance_id"] = derive_id(
        "prv",
        {key: value for key, value in raw_provenance.items() if key != "provenance_id"},
    )
    changed_provenance = lossless_json_bytes(raw_provenance) + b"\n"
    original_snapshot = original_report.snapshot
    snapshot_body = {
        **original_snapshot.model_dump(mode="python", exclude={"snapshot_id"}),
        "file_bindings": (
            SnapshotFileBinding.create(
                role="training-partition",
                file_bytes=arguments["files"][TRAIN_PATH],
                record_count=1,
            ),
            SnapshotFileBinding.create(
                role="evaluation-partition",
                file_bytes=arguments["files"][EVALUATION_PATH],
                record_count=0,
            ),
            SnapshotFileBinding.create(
                role="row-provenance",
                file_bytes=changed_provenance,
                record_count=1,
            ),
        ),
    }
    changed_snapshot = DatasetSnapshot(
        snapshot_id=derive_id("dss", snapshot_body),
        **snapshot_body,
    )
    changed_report = DatasetValidationReport.create(
        snapshot=changed_snapshot,
        gate_results=tuple(
            DatasetGateResult.create(
                snapshot_id=changed_snapshot.snapshot_id,
                gate_id=gate_id,
                status="passed",
            )
            for gate_id in V1_FINISHED_DATASET_GATES
        ),
    )
    arguments["files"][PROVENANCE_PATH] = changed_provenance
    arguments["files"][VALIDATION_PATH] = dataset_validation_report_json_bytes(
        changed_report
    )
    arguments["dataset_snapshot_id"] = changed_report.snapshot_id
    arguments["validation_report_id"] = changed_report.report_id
    target = tmp_path / "misaligned-provenance.vfbundle"

    with pytest.raises(FinishedBundleError, match="not aligned"):
        write_finished_bundle(target, **arguments)

    assert not target.exists()


def test_verifier_rejects_field_evidence_outside_provenance_sources(tmp_path):
    arguments = _bundle_arguments(compiled_text=("alpha", "omega"))
    original_report = dataset_validation_report_from_json_bytes(
        arguments["files"][VALIDATION_PATH]
    )
    provenance_records = [
        json.loads(line)
        for line in arguments["files"][PROVENANCE_PATH].decode("utf-8").splitlines()
    ]
    evidence = provenance_records[0]["record_fields"][0]["evidence"]
    evidence_source_id = (
        evidence["evidence"]["source_id"]
        if evidence["kind"] == "source_text"
        else evidence["source_id"]
    )
    other_source_id = provenance_records[1]["source_ids"][0]
    assert evidence_source_id != other_source_id
    provenance_records[0]["source_ids"] = [other_source_id]
    provenance_records[0]["provenance_id"] = derive_id(
        "prv",
        {
            key: value
            for key, value in provenance_records[0].items()
            if key != "provenance_id"
        },
    )
    changed_provenance = b"".join(
        lossless_json_bytes(record) + b"\n" for record in provenance_records
    )
    original_snapshot = original_report.snapshot
    snapshot_body = {
        **original_snapshot.model_dump(mode="python", exclude={"snapshot_id"}),
        "file_bindings": (
            SnapshotFileBinding.create(
                role="training-partition",
                file_bytes=arguments["files"][TRAIN_PATH],
                record_count=arguments["record_counts"][TRAIN_PATH],
            ),
            SnapshotFileBinding.create(
                role="evaluation-partition",
                file_bytes=arguments["files"][EVALUATION_PATH],
                record_count=arguments["record_counts"][EVALUATION_PATH],
            ),
            SnapshotFileBinding.create(
                role="row-provenance",
                file_bytes=changed_provenance,
                record_count=arguments["record_counts"][PROVENANCE_PATH],
            ),
        ),
    }
    changed_snapshot = DatasetSnapshot(
        snapshot_id=derive_id("dss", snapshot_body),
        **snapshot_body,
    )
    changed_report = DatasetValidationReport.create(
        snapshot=changed_snapshot,
        gate_results=tuple(
            DatasetGateResult.create(
                snapshot_id=changed_snapshot.snapshot_id,
                gate_id=gate_id,
                status="passed",
            )
            for gate_id in V1_FINISHED_DATASET_GATES
        ),
    )
    arguments["files"][PROVENANCE_PATH] = changed_provenance
    arguments["files"][VALIDATION_PATH] = dataset_validation_report_json_bytes(
        changed_report
    )
    arguments["dataset_snapshot_id"] = changed_report.snapshot_id
    arguments["validation_report_id"] = changed_report.report_id
    target = tmp_path / "cross-source-evidence.vfbundle"

    with pytest.raises(
        FinishedBundleError, match="field evidence names another source"
    ):
        write_finished_bundle(target, **arguments)

    assert not target.exists()


def test_verifier_rejects_one_leakage_group_in_multiple_partitions(tmp_path):
    arguments = _bundle_arguments(compiled_text=("alpha", "omega"))
    provenance_records = _provenance_records(arguments)
    train_record = next(
        record for record in provenance_records if record["partition"] == "train"
    )
    evaluation_record = next(
        record for record in provenance_records if record["partition"] == "evaluation"
    )
    evaluation_record["leakage_group_id"] = train_record["leakage_group_id"]
    _refresh_provenance_id(evaluation_record)
    _replace_provenance_records(arguments, provenance_records)
    target = tmp_path / "cross-partition-group.vfbundle"

    with pytest.raises(FinishedBundleError, match="group appears in multiple"):
        write_finished_bundle(target, **arguments)

    assert not target.exists()


def test_verifier_rejects_one_source_in_multiple_partitions(tmp_path):
    arguments = _bundle_arguments(compiled_text=("alpha", "omega"))
    provenance_records = _provenance_records(arguments)
    train_record = next(
        record for record in provenance_records if record["partition"] == "train"
    )
    evaluation_record = next(
        record for record in provenance_records if record["partition"] == "evaluation"
    )
    evaluation_record["source_ids"] = sorted(
        {*evaluation_record["source_ids"], *train_record["source_ids"]}
    )
    _refresh_provenance_id(evaluation_record)
    _replace_provenance_records(arguments, provenance_records)
    target = tmp_path / "cross-partition-source.vfbundle"

    with pytest.raises(FinishedBundleError, match="source appears in multiple"):
        write_finished_bundle(target, **arguments)

    assert not target.exists()


def test_verifier_requires_rows_to_cover_snapshot_source_scope(tmp_path):
    arguments = _bundle_arguments(compiled_text=("alpha", "omega"))
    original_report = dataset_validation_report_from_json_bytes(
        arguments["files"][VALIDATION_PATH]
    )
    original_snapshot = original_report.snapshot
    unused_source_id = derive_id("src", {"fixture": "unused-snapshot-source"})
    snapshot_body = {
        **original_snapshot.model_dump(mode="python", exclude={"snapshot_id"}),
        "source_ids": tuple(sorted((*original_snapshot.source_ids, unused_source_id))),
    }
    changed_snapshot = DatasetSnapshot(
        snapshot_id=derive_id("dss", snapshot_body),
        **snapshot_body,
    )
    changed_report = DatasetValidationReport.create(
        snapshot=changed_snapshot,
        gate_results=tuple(
            DatasetGateResult.create(
                snapshot_id=changed_snapshot.snapshot_id,
                gate_id=gate_id,
                status="passed",
            )
            for gate_id in V1_FINISHED_DATASET_GATES
        ),
    )
    arguments["files"][VALIDATION_PATH] = dataset_validation_report_json_bytes(
        changed_report
    )
    arguments["dataset_snapshot_id"] = changed_report.snapshot_id
    arguments["validation_report_id"] = changed_report.report_id
    target = tmp_path / "unused-snapshot-source.vfbundle"

    with pytest.raises(FinishedBundleError, match="exact snapshot source scope"):
        write_finished_bundle(target, **arguments)

    assert not target.exists()


def test_verifier_rejects_duplicate_exact_record_fingerprints(tmp_path):
    arguments = _bundle_arguments(compiled_text=("alpha", "beta", "gamma"))
    provenance_records = _provenance_records(arguments)
    partition_records = {
        partition: [
            record for record in provenance_records if record["partition"] == partition
        ]
        for partition in ("train", "evaluation")
    }
    partition, records = next(
        (partition, records)
        for partition, records in partition_records.items()
        if len(records) >= 2
    )
    original, duplicate = records[:2]
    duplicate["record_fields"] = original["record_fields"]
    duplicate["source_ids"] = sorted(
        {*duplicate["source_ids"], *original["source_ids"]}
    )
    duplicate["field_values_sha256"] = canonical_digest(
        {
            "schema_version": "veriformis.row-field-values/v1",
            "fields": tuple(
                {"name": field["name"], "value": field["value"]}
                for field in duplicate["record_fields"]
            ),
        }
    )
    duplicate["field_evidence_sha256"] = canonical_digest(
        {
            "schema_version": "veriformis.row-field-evidence/v1",
            "fields": tuple(
                {"name": field["name"], "evidence": field["evidence"]}
                for field in duplicate["record_fields"]
            ),
        }
    )
    payload_path = TRAIN_PATH if partition == "train" else EVALUATION_PATH
    payloads = [
        json.loads(line)
        for line in arguments["files"][payload_path].decode("utf-8").splitlines()
    ]
    duplicate_payload = {"text": duplicate["record_fields"][0]["value"]}
    payloads[duplicate["ordinal"]] = duplicate_payload
    arguments["files"][payload_path] = b"".join(
        lossless_json_bytes(payload) + b"\n" for payload in payloads
    )
    duplicate_row = ProductRow.create(
        record_id=duplicate["record_id"],
        row_schema="text",
        payload=duplicate_payload,
    )
    duplicate["row_id"] = duplicate_row.row_id
    duplicate["payload_sha256"] = duplicate_row.payload_sha256
    _refresh_provenance_id(duplicate)
    _replace_provenance_records(arguments, provenance_records)
    target = tmp_path / "duplicate-fingerprint.vfbundle"

    with pytest.raises(FinishedBundleError, match="exact duplicate record"):
        write_finished_bundle(target, **arguments)

    assert not target.exists()


def test_verifier_requires_shared_sources_to_share_one_leakage_group(tmp_path):
    arguments = _bundle_arguments(compiled_text=("alpha", "beta", "gamma"))
    provenance_records = _provenance_records(arguments)
    partition_records = {
        partition: [
            record for record in provenance_records if record["partition"] == partition
        ]
        for partition in ("train", "evaluation")
    }
    _, records = next(
        (partition, records)
        for partition, records in partition_records.items()
        if len(records) >= 2
    )
    first, second = records[:2]
    assert first["leakage_group_id"] != second["leakage_group_id"]
    second["source_ids"] = sorted({*second["source_ids"], *first["source_ids"]})
    _refresh_provenance_id(second)
    _replace_provenance_records(arguments, provenance_records)
    target = tmp_path / "shared-source-distinct-groups.vfbundle"

    with pytest.raises(FinishedBundleError, match="source appears in multiple leakage"):
        write_finished_bundle(target, **arguments)

    assert not target.exists()


def test_verifier_rejects_source_scoped_conflicting_targets(tmp_path):
    arguments = _bundle_arguments(
        compiled_text=("abcdefgh", "ijklmnop", "qrstuvwx"),
        objective_kind="continuation",
        row_schema="prompt_completion",
    )
    provenance_records = _provenance_records(arguments)
    partition_records = {
        partition: [
            record for record in provenance_records if record["partition"] == partition
        ]
        for partition in ("train", "evaluation")
    }
    partition, records = next(
        (partition, records)
        for partition, records in partition_records.items()
        if len(records) >= 2
    )
    first, conflicting = records[:2]
    shared_sources = sorted({*first["source_ids"], *conflicting["source_ids"]})
    first["source_ids"] = shared_sources
    conflicting["source_ids"] = shared_sources
    conflicting["leakage_group_id"] = first["leakage_group_id"]
    first_prompt = next(
        field for field in first["record_fields"] if field["name"] == "prompt"
    )
    conflicting_fields = {
        field["name"]: field for field in conflicting["record_fields"]
    }
    conflicting_fields["prompt"] = first_prompt
    conflicting["record_fields"] = [
        conflicting_fields["prompt"],
        conflicting_fields["completion"],
    ]
    assert conflicting_fields["completion"]["value"] != next(
        field["value"]
        for field in first["record_fields"]
        if field["name"] == "completion"
    )
    conflicting["field_values_sha256"] = canonical_digest(
        {
            "schema_version": "veriformis.row-field-values/v1",
            "fields": tuple(
                {"name": field["name"], "value": field["value"]}
                for field in conflicting["record_fields"]
            ),
        }
    )
    conflicting["field_evidence_sha256"] = canonical_digest(
        {
            "schema_version": "veriformis.row-field-evidence/v1",
            "fields": tuple(
                {"name": field["name"], "evidence": field["evidence"]}
                for field in conflicting["record_fields"]
            ),
        }
    )
    payload_path = TRAIN_PATH if partition == "train" else EVALUATION_PATH
    payloads = [
        json.loads(line)
        for line in arguments["files"][payload_path].decode("utf-8").splitlines()
    ]
    conflicting_payload = {
        "prompt": conflicting_fields["prompt"]["value"],
        "completion": conflicting_fields["completion"]["value"],
    }
    payloads[conflicting["ordinal"]] = conflicting_payload
    arguments["files"][payload_path] = b"".join(
        lossless_json_bytes(payload) + b"\n" for payload in payloads
    )
    conflicting_row = ProductRow.create(
        record_id=conflicting["record_id"],
        row_schema="prompt_completion",
        payload=conflicting_payload,
    )
    conflicting["row_id"] = conflicting_row.row_id
    conflicting["payload_sha256"] = conflicting_row.payload_sha256
    _refresh_provenance_id(first)
    _refresh_provenance_id(conflicting)
    _replace_provenance_records(arguments, provenance_records)
    target = tmp_path / "conflicting-targets.vfbundle"

    with pytest.raises(FinishedBundleError, match="conflicting target class"):
        write_finished_bundle(target, **arguments)

    assert not target.exists()


def test_verifier_reconstructs_included_curation_decision_identity(tmp_path):
    arguments = _bundle_arguments()
    provenance_records = _provenance_records(arguments)
    provenance_records[0]["curation_decision_id"] = derive_id(
        "cud",
        {"fixture": "forged-included-decision"},
    )
    _refresh_provenance_id(provenance_records[0])
    _replace_provenance_records(arguments, provenance_records)
    target = tmp_path / "forged-curation-decision.vfbundle"

    with pytest.raises(FinishedBundleError, match="included curation decision"):
        write_finished_bundle(target, **arguments)

    assert not target.exists()


def test_verifier_reconstructs_snapshot_row_set_identity(tmp_path):
    arguments = _bundle_arguments()
    report = dataset_validation_report_from_json_bytes(
        arguments["files"][VALIDATION_PATH]
    )
    original_snapshot = report.snapshot
    forged_row_set_id = derive_id("rws", {"fixture": "forged-row-set"})
    artifact_bindings = tuple(
        SnapshotArtifactBinding(
            **{
                **binding.model_dump(mode="python"),
                "artifact_id": forged_row_set_id,
            }
        )
        if binding.role == "row-set"
        else binding
        for binding in original_snapshot.artifact_bindings
    )
    snapshot_body = {
        **original_snapshot.model_dump(mode="python", exclude={"snapshot_id"}),
        "row_set_id": forged_row_set_id,
        "artifact_bindings": artifact_bindings,
    }
    _replace_validation_snapshot(arguments, snapshot_body)
    target = tmp_path / "forged-row-set-id.vfbundle"

    with pytest.raises(FinishedBundleError, match="row-set identity differs"):
        write_finished_bundle(target, **arguments)

    assert not target.exists()


def test_verifier_reconstructs_snapshot_row_set_artifact_bytes(tmp_path):
    arguments = _bundle_arguments()
    report = dataset_validation_report_from_json_bytes(
        arguments["files"][VALIDATION_PATH]
    )
    original_snapshot = report.snapshot
    artifact_bindings = tuple(
        SnapshotArtifactBinding(
            **{
                **binding.model_dump(mode="python"),
                "sha256": sha256_digest(b"forged-row-set-artifact"),
                "byte_size": binding.byte_size + 1,
            }
        )
        if binding.role == "row-set"
        else binding
        for binding in original_snapshot.artifact_bindings
    )
    snapshot_body = {
        **original_snapshot.model_dump(mode="python", exclude={"snapshot_id"}),
        "artifact_bindings": artifact_bindings,
    }
    _replace_validation_snapshot(arguments, snapshot_body)
    target = tmp_path / "forged-row-set-bytes.vfbundle"

    with pytest.raises(FinishedBundleError, match="row-set bytes differ"):
        write_finished_bundle(target, **arguments)

    assert not target.exists()


def test_another_valid_bundle_only_earns_self_consistency(tmp_path):
    original, _ = _write_valid(tmp_path, "original.vfbundle")
    original_manifest_bytes = (original / "manifest.json").read_bytes()
    original_manifest_sha256 = sha256_digest(original_manifest_bytes)
    changed_arguments = _bundle_arguments(compiled_text="omega")
    changed = tmp_path / "changed.vfbundle"
    write_finished_bundle(changed, **changed_arguments)

    assert verify_finished_bundle(changed).trust_grade == "self_consistent"
    with pytest.raises(BundleVerificationError, match="external digest"):
        verify_finished_bundle(
            changed,
            expected_manifest_sha256=original_manifest_sha256,
        )


def test_undeclared_file_is_rejected(tmp_path):
    target, _ = _write_valid(tmp_path)
    (target / "undeclared.txt").write_bytes(b"not declared")

    with pytest.raises(BundleVerificationError, match="file set is not closed"):
        verify_finished_bundle(target)


def test_missing_declared_file_is_rejected(tmp_path):
    target, _ = _write_valid(tmp_path)
    (target / ROWS_PATH).unlink()

    with pytest.raises(BundleVerificationError, match="file set is not closed"):
        verify_finished_bundle(target)


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../outside.jsonl",
        "/absolute.jsonl",
        "dir\\rows.jsonl",
        "./rows.jsonl",
        "dir//rows.jsonl",
        "C:/rows.jsonl",
        "rows/\x00bad.jsonl",
        "rows/con.jsonl",
    ],
)
def test_manifest_payload_paths_cannot_escape_or_alias_bundle(tmp_path, unsafe_path):
    target, _ = _write_valid(tmp_path)
    manifest = json.loads((target / "manifest.json").read_bytes())
    manifest["files"][0]["path"] = unsafe_path
    (target / "manifest.json").write_bytes(lossless_json_bytes(manifest))

    with pytest.raises(BundleVerificationError, match="path"):
        verify_finished_bundle(target)


@pytest.mark.parametrize(
    "path",
    [
        "rows/other.jsonl",
        "Manifest.json/data.jsonl",
        "rows/cafe\u0301.jsonl",
    ],
)
def test_minimal_profile_rejects_every_other_payload_mapping(path):
    arguments = _bundle_arguments(files={path: _record()})

    with pytest.raises(FinishedBundleError, match="minimal-v1"):
        build_finished_bundle(**arguments)


def test_actual_case_alias_is_rejected(tmp_path):
    target, _ = _write_valid(tmp_path)
    alias = target / "Ｄata"
    alias.mkdir()
    (alias / "train.jsonl").write_bytes(_record())

    with pytest.raises(BundleVerificationError, match="collide by case or Unicode"):
        verify_finished_bundle(target)


def test_symlink_is_rejected_even_when_it_has_declared_bytes(tmp_path):
    target, _ = _write_valid(tmp_path)
    payload = target / ROWS_PATH
    outside = tmp_path / "outside.jsonl"
    outside.write_bytes(payload.read_bytes())
    payload.unlink()
    payload.symlink_to(outside)

    with pytest.raises(BundleVerificationError, match="symlink"):
        verify_finished_bundle(target)


def test_hard_link_is_rejected_even_when_bytes_match(tmp_path):
    target, _ = _write_valid(tmp_path)
    outside = tmp_path / "outside-hard-link.jsonl"
    os.link(target / ROWS_PATH, outside)

    with pytest.raises(BundleVerificationError, match="hard-linked"):
        verify_finished_bundle(target)


def test_payload_replacement_after_hash_is_detected(tmp_path, monkeypatch):
    target, _ = _write_valid(tmp_path)
    original_verify = verifier_module._verify_payload

    def verify_then_replace(root_descriptor, file, *, expected_facts):
        original_verify(
            root_descriptor,
            file,
            expected_facts=expected_facts,
        )
        if file.path == TRAIN_PATH:
            (target / TRAIN_PATH).write_bytes(_record("omega"))

    monkeypatch.setattr(verifier_module, "_verify_payload", verify_then_replace)

    with pytest.raises(BundleVerificationError, match="changed"):
        verify_finished_bundle(target)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFOs are POSIX-only")
def test_special_file_is_rejected(tmp_path):
    target, _ = _write_valid(tmp_path)
    os.mkfifo(target / "unexpected.pipe")

    with pytest.raises(BundleVerificationError, match="special file"):
        verify_finished_bundle(target)


def test_unexpected_directory_is_rejected(tmp_path):
    target, _ = _write_valid(tmp_path)
    (target / "empty-extra-directory").mkdir()

    with pytest.raises(BundleVerificationError, match="directory set is not closed"):
        verify_finished_bundle(target)


def test_existing_target_is_never_overwritten(tmp_path):
    target = tmp_path / "existing.vfbundle"
    target.mkdir()
    sentinel = target / "sentinel"
    sentinel.write_bytes(b"preserve me")

    with pytest.raises(FinishedBundleError, match="already exists") as caught:
        write_finished_bundle(target, **_bundle_arguments())

    assert caught.value.code == "seal-invalid"
    assert sentinel.read_bytes() == b"preserve me"
    assert sorted(path.name for path in target.iterdir()) == ["sentinel"]


def test_repeated_seals_have_identical_semantic_bytes(tmp_path):
    first, first_result = _write_valid(tmp_path, "first.vfbundle")
    second, second_result = _write_valid(tmp_path, "second.vfbundle")

    first_files = {
        str(path.relative_to(first)): path.read_bytes()
        for path in first.rglob("*")
        if path.is_file()
    }
    second_files = {
        str(path.relative_to(second)): path.read_bytes()
        for path in second.rglob("*")
        if path.is_file()
    }
    assert first_files == second_files
    assert first_result.manifest == second_result.manifest
    assert first_result.attestation == second_result.attestation
    assert first_result.verification == second_result.verification
    assert first_result.manifest_bytes == second_result.manifest_bytes
    assert first_result.attestation_bytes == second_result.attestation_bytes


def test_interruption_before_rename_leaves_no_target_or_staging_tree(tmp_path):
    target = tmp_path / "interrupted.vfbundle"

    def fail(point: str) -> None:
        if point == "before-rename":
            raise RuntimeError("injected interruption")

    with pytest.raises(RuntimeError, match="injected interruption"):
        write_finished_bundle(
            target,
            **_bundle_arguments(),
            failure_injector=fail,
        )

    assert not target.exists()
    assert not list(tmp_path.glob(".interrupted.vfbundle.tmp-*"))


def test_replaced_staging_path_is_never_deleted_or_published(tmp_path):
    target = tmp_path / "swapped.vfbundle"
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "sentinel").write_bytes(b"must survive")
    replacement: list[Path] = []

    def swap(point: str) -> None:
        if point != "before-rename":
            return
        staged = next(tmp_path.glob(".swapped.vfbundle.tmp-*"))
        staged.rename(tmp_path / "verified-stage-backup")
        victim.rename(staged)
        replacement.append(staged)

    with pytest.warns(RuntimeWarning, match="refused to clean"):
        with pytest.raises(FinishedBundleError, match="changed identity"):
            write_finished_bundle(
                target,
                **_bundle_arguments(),
                failure_injector=swap,
            )

    assert not target.exists()
    assert (replacement[0] / "sentinel").read_bytes() == b"must survive"
    assert (tmp_path / "verified-stage-backup").is_dir()


def test_cleanup_never_recursively_deletes_a_postcheck_replacement(
    tmp_path, monkeypatch
):
    target = tmp_path / "cleanup-race.vfbundle"
    victim = tmp_path / "cleanup-victim"
    victim.mkdir()
    (victim / "sentinel").write_bytes(b"must survive")
    backup = tmp_path / "cleanup-verified-stage-backup"
    original_check = finished_module._path_matches_directory_descriptor
    matching_checks = 0

    def check_then_swap(path: Path, descriptor: int) -> bool:
        nonlocal matching_checks
        matches = original_check(path, descriptor)
        if matches and path.name.startswith(".cleanup-race.vfbundle.tmp-"):
            matching_checks += 1
            if matching_checks == 4:
                path.rename(backup)
                victim.rename(path)
        return matches

    def interrupt(point: str) -> None:
        if point == "before-rename":
            raise RuntimeError("injected interruption")

    monkeypatch.setattr(
        finished_module,
        "_path_matches_directory_descriptor",
        check_then_swap,
    )
    with pytest.warns(RuntimeWarning, match="refused to remove"):
        with pytest.raises(RuntimeError, match="injected interruption"):
            write_finished_bundle(
                target,
                **_bundle_arguments(),
                failure_injector=interrupt,
            )

    replacement = next(tmp_path.glob(".cleanup-race.vfbundle.tmp-*"))
    assert not target.exists()
    assert (replacement / "sentinel").read_bytes() == b"must survive"
    assert backup.is_dir()


def test_pre_publish_guard_runs_after_verification_and_aborts_safely(tmp_path):
    target = tmp_path / "guarded.vfbundle"
    calls = 0

    def guard() -> None:
        nonlocal calls
        calls += 1
        raise WorkspaceRevisionConflict("expected-revision", "changed-revision")

    with pytest.raises(WorkspaceRevisionConflict):
        write_finished_bundle(
            target,
            **_bundle_arguments(),
            pre_publish_guard=guard,
        )

    assert calls == 1
    assert not target.exists()
    assert not list(tmp_path.glob(".guarded.vfbundle.tmp-*"))


def test_parent_fsync_failure_returns_visible_publication_receipt(
    tmp_path, monkeypatch
):
    target = tmp_path / "durability-warning.vfbundle"

    def fail_parent_sync(path: Path) -> None:
        raise OSError(f"cannot sync {path}")

    monkeypatch.setattr(finished_module, "_fsync_directory", fail_parent_sync)
    with pytest.warns(RuntimeWarning, match="could not be synced"):
        receipt = write_finished_bundle(target, **_bundle_arguments())

    assert target.is_dir()
    assert receipt.bundle_path == target
    assert receipt.durability_warning is not None
    assert "could not be synced" in receipt.durability_warning


@pytest.mark.parametrize(
    "payload,error",
    [
        (b'{"text": "alpha"}\n', "not canonical"),
        (b'{"text":"alpha"}', "every record with LF"),
        (b'{"text":"alpha","text":"alpha"}\n', "duplicate key"),
        (b'{"score":1.5}\n', "floating-point"),
        (b'{"score":NaN}\n', "non-finite"),
        (b'["not-an-object"]\n', "root must be an object"),
    ],
)
def test_noncanonical_jsonl_never_reaches_target(tmp_path, payload, error):
    target = tmp_path / "invalid-jsonl.vfbundle"
    arguments = _bundle_arguments(
        files={
            TRAIN_PATH: payload,
            EVALUATION_PATH: b"",
            PROVENANCE_PATH: _lineage(),
        }
    )

    with pytest.raises(FinishedBundleError, match=error):
        write_finished_bundle(target, **arguments)

    assert not target.exists()


def test_wrong_record_count_never_reaches_target(tmp_path):
    target = tmp_path / "wrong-count.vfbundle"
    arguments = _bundle_arguments(
        record_counts={TRAIN_PATH: 2, EVALUATION_PATH: 0, PROVENANCE_PATH: 2}
    )

    with pytest.raises(FinishedBundleError, match="record count mismatch"):
        write_finished_bundle(target, **arguments)

    assert not target.exists()


def test_duplicate_or_noncanonical_manifest_json_is_rejected(tmp_path):
    target, _ = _write_valid(tmp_path)
    canonical = (target / "manifest.json").read_bytes()
    bundle_id = FinishedBundleManifest.from_json_bytes(canonical).bundle_id
    duplicate = canonical.replace(
        b'"bundle_id":',
        b'"bundle_id":"' + bundle_id.encode("ascii") + b'","bundle_id":',
        1,
    )
    (target / "manifest.json").write_bytes(duplicate)

    with pytest.raises(BundleVerificationError, match="duplicate key"):
        verify_finished_bundle(target)

    payload = json.loads(canonical)
    (target / "manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with pytest.raises(BundleVerificationError, match="not canonical"):
        verify_finished_bundle(target)


def test_manifest_identity_mismatch_is_rejected(tmp_path):
    target, _ = _write_valid(tmp_path)
    manifest = json.loads((target / "manifest.json").read_bytes())
    manifest["bundle_id"] = derive_id("bundle", {"forged": True})
    (target / "manifest.json").write_bytes(lossless_json_bytes(manifest))

    with pytest.raises(BundleVerificationError, match="identity mismatch"):
        verify_finished_bundle(target)


def test_minimal_payload_roles_and_dataset_record_count_are_bound(tmp_path):
    target, result = _write_valid(tmp_path)

    assert result.payload_file_count == 4
    assert result.declared_record_count == 1
    manifest = FinishedBundleManifest.from_json_bytes(
        (target / "manifest.json").read_bytes()
    )
    assert tuple(file.path for file in manifest.files) == (
        EVALUATION_PATH,
        TRAIN_PATH,
        PROVENANCE_PATH,
        VALIDATION_PATH,
    )
