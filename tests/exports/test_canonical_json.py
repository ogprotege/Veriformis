"""Phase 5.2 contract tests for the generic canonical-JSON container."""

from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from veriformis.datasets import (
    ProductRow,
    RowSet,
    row_provenance_from_json_bytes,
)
from veriformis.errors import ExportContractError, ExportVerificationError
from veriformis.exports import (
    EXPORT_SURFACE_REQUEST_SCHEMA,
    EXPORT_SURFACE_REQUEST_SCHEMA_V2,
    ExportDryRunRequest,
    ExportDryRunRequestV2,
    ExportExecuteRequest,
    ExportService,
    ExportVerifyRequest,
)
from veriformis.exports import canonical_json as json_module
from veriformis.exports.canonical_json import (
    CANONICAL_JSON_CONTAINER_ID,
    CANONICAL_JSON_CONTAINER_VERSION,
    CANONICAL_JSON_DATASET_PATH,
    CANONICAL_JSON_PROVENANCE_PATH,
    CANONICAL_JSON_README_PATH,
    CanonicalJsonDataset,
    CanonicalJsonProvenance,
)
from veriformis.identity import derive_id, lossless_json_bytes, sha256_digest


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "regressions"
    / "fixtures"
    / "phase3"
    / "pre-taxonomy-full-text.vfbundle.json"
)
EXPECTED_MANIFEST_SHA256 = (
    "2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733"
)
ROW_SCHEMAS = ("instruction_output", "messages", "prompt_completion", "text")
DISCOVERY_ROW_SCHEMAS = (
    "instruction_output",
    "label-classification",
    "messages",
    "preference-pair",
    "prompt_completion",
    "text",
    "tool-call-conversation",
)


def _materialize_bundle(root: Path) -> Path:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bundle = root / "source.vfbundle"
    for relative_path, encoded in sorted(fixture["files_base64"].items()):
        data = base64.b64decode(encoded, validate=True)
        assert sha256_digest(data) == fixture["file_sha256"][relative_path]
        target = bundle.joinpath(*relative_path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return bundle


def _selection(bundle: Path, *, schema_version: str) -> dict[str, object]:
    return {
        "schema_version": schema_version,
        "bundle": str(bundle),
        "container_id": CANONICAL_JSON_CONTAINER_ID,
        "container_version": CANONICAL_JSON_CONTAINER_VERSION,
        "consumer_id": None,
        "consumer_profile_version": None,
        "source_trust_policy": "require_external_digest",
        "expected_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "overwrite_policy": "refuse",
    }


def _dry(bundle: Path) -> ExportDryRunRequest:
    return ExportDryRunRequest(
        operation="dry_run",
        **_selection(bundle, schema_version=EXPORT_SURFACE_REQUEST_SCHEMA),
    )


def _execute(
    bundle: Path,
    destination: Path,
    plan_id: str,
) -> ExportExecuteRequest:
    return ExportExecuteRequest(
        operation="execute",
        destination_root=str(destination),
        expected_export_plan_id=plan_id,
        **_selection(bundle, schema_version=EXPORT_SURFACE_REQUEST_SCHEMA),
    )


def _verify(
    bundle: Path,
    destination: Path,
    plan_id: str,
) -> ExportVerifyRequest:
    return ExportVerifyRequest(
        operation="verify",
        destination_root=str(destination),
        expected_export_plan_id=plan_id,
        **_selection(bundle, schema_version=EXPORT_SURFACE_REQUEST_SCHEMA),
    )


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _payload(row_schema: str, value: str) -> dict[str, Any]:
    exact = f'{value}\n"quoted" \\ composed=\u00e9 decomposed=e\u0301 \U0001f600'
    if row_schema == "text":
        return {"text": exact}
    if row_schema == "prompt_completion":
        return {"prompt": f"context:{exact}", "completion": f"target:{exact}"}
    if row_schema == "instruction_output":
        return {
            "instruction": "Preserve the exact value.",
            "input": f"context:{exact}",
            "output": f"target:{exact}",
        }
    assert row_schema == "messages"
    return {
        "messages": [
            {"role": "user", "content": f"context:{exact}"},
            {"role": "assistant", "content": f"target:{exact}"},
        ]
    }


def _row_set_for_schema(source: RowSet, row_schema: str) -> RowSet:
    source_rows = (*source.train_rows, *source.evaluation_rows)
    converted = tuple(
        ProductRow.create(
            record_id=row.record_id,
            row_schema=row_schema,  # type: ignore[arg-type]
            payload=_payload(row_schema, str(index)),
        )
        for index, row in enumerate(source_rows)
    )
    converted_by_record = {row.record_id: row for row in converted}
    provenance = []
    for item in source.provenance:
        row = converted_by_record[item.record_id]
        body = item.model_dump(mode="json", exclude={"provenance_id"})
        body.update(row_id=row.row_id, payload_sha256=row.payload_sha256)
        provenance.append(
            row_provenance_from_json_bytes(
                lossless_json_bytes({"provenance_id": derive_id("prv", body), **body})
            )
        )
    train_count = source.train_row_count
    return RowSet.create(
        plan_id=source.plan_id,
        serialization_plan_id=source.serialization_plan_id,
        recipe_id=source.recipe_id,
        construction_result_id=source.construction_result_id,
        curation_result_id=source.curation_result_id,
        split_result_id=source.split_result_id,
        row_schema=row_schema,  # type: ignore[arg-type]
        train_rows=converted[:train_count],
        evaluation_rows=converted[train_count:],
        provenance=provenance,
    )


def _source_row_set(bundle: Path) -> RowSet:
    return ExportService().verified_source(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    ).row_set


def test_canonical_json_discovery_and_fixed_plan(tmp_path: Path) -> None:
    bundle = _materialize_bundle(tmp_path)
    service = ExportService()
    profiles = {
        profile.selector: profile for profile in service.discover_exports().profiles
    }
    selector = (CANONICAL_JSON_CONTAINER_ID, 1, None, None)

    assert selector in profiles
    assert profiles[selector].supported_row_schemas == DISCOVERY_ROW_SCHEMAS
    assert (
        profiles[selector].container_profile.determinism_claim
        == "portable_exact_bytes"
    )

    first = service.dry_run_export(_dry(bundle))
    second = service.dry_run_export(_dry(bundle))
    assert first == second
    assert first.consumer_profile is None
    assert first.loss_policy == "full-sequence"
    plans = {item.path: item for item in first.file_plans}
    assert set(plans) == {
        CANONICAL_JSON_README_PATH,
        CANONICAL_JSON_DATASET_PATH,
        CANONICAL_JSON_PROVENANCE_PATH,
    }
    assert plans[CANONICAL_JSON_DATASET_PATH].membership_scope == "all"
    assert plans[CANONICAL_JSON_DATASET_PATH].record_count == 3
    assert plans[CANONICAL_JSON_PROVENANCE_PATH].membership_scope == "none"
    assert plans[CANONICAL_JSON_PROVENANCE_PATH].record_count == 3
    assert plans[CANONICAL_JSON_README_PATH].membership_scope == "none"
    assert plans[CANONICAL_JSON_README_PATH].record_count is None


@pytest.mark.parametrize("row_schema", ROW_SCHEMAS)
def test_every_current_schema_round_trips_exact_rows_partitions_and_provenance(
    tmp_path: Path,
    row_schema: str,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    row_set = _row_set_for_schema(_source_row_set(bundle), row_schema)

    first = dict(json_module._rendered_files(row_set))
    second = dict(json_module._rendered_files(row_set))
    assert first == second
    dataset = CanonicalJsonDataset.from_json_bytes(
        first[CANONICAL_JSON_DATASET_PATH]
    )
    provenance = CanonicalJsonProvenance.from_json_bytes(
        first[CANONICAL_JSON_PROVENANCE_PATH]
    )
    dataset.validate_provenance(provenance)

    assert dataset.row_schema == row_schema
    assert dataset.partition_order == ("train", "evaluation")
    assert dataset.consumer_profile is None
    assert dataset.trainer_compatibility_claimed is False
    assert dataset.splits.train == tuple(row.payload for row in row_set.train_rows)
    assert dataset.splits.evaluation == tuple(
        row.payload for row in row_set.evaluation_rows
    )
    assert provenance.rows == row_set.provenance
    assert first[CANONICAL_JSON_DATASET_PATH].endswith(b"}")
    assert not first[CANONICAL_JSON_DATASET_PATH].endswith(b"\n")
    assert first[CANONICAL_JSON_README_PATH].endswith(b"\n")
    assert b"trainer-neutral" in first[CANONICAL_JSON_README_PATH]
    assert b"does not select a training objective" in first[
        CANONICAL_JSON_README_PATH
    ]

    payloads = (*dataset.splits.train, *dataset.splits.evaluation)
    rows = tuple(
        ProductRow.create(
            record_id=item.record_id,
            row_schema=row_schema,  # type: ignore[arg-type]
            payload=payload,
        )
        for payload, item in zip(payloads, provenance.rows, strict=True)
    )
    rebuilt = RowSet.create(
        plan_id=row_set.plan_id,
        serialization_plan_id=row_set.serialization_plan_id,
        recipe_id=row_set.recipe_id,
        construction_result_id=row_set.construction_result_id,
        curation_result_id=row_set.curation_result_id,
        split_result_id=row_set.split_result_id,
        row_schema=row_schema,  # type: ignore[arg-type]
        train_rows=rows[: dataset.train_row_count],
        evaluation_rows=rows[dataset.train_row_count :],
        provenance=provenance.rows,
    )
    assert rebuilt == row_set

    plans = {
        item.path: item
        for item in json_module._file_plans(
            json_module.CANONICAL_JSON_DESCRIPTOR,
            row_set,
        )
    }
    assert set(plans) == set(first)
    assert all(
        plans[path].expected_sha256 == sha256_digest(data)
        and plans[path].expected_byte_size == len(data)
        for path, data in first.items()
    )


def test_empty_evaluation_remains_an_explicit_empty_array(tmp_path: Path) -> None:
    bundle = _materialize_bundle(tmp_path)
    source = _source_row_set(bundle)
    row_set = RowSet.create(
        plan_id=source.plan_id,
        serialization_plan_id=source.serialization_plan_id,
        recipe_id=source.recipe_id,
        construction_result_id=source.construction_result_id,
        curation_result_id=source.curation_result_id,
        split_result_id=source.split_result_id,
        row_schema=source.row_schema,
        train_rows=source.train_rows,
        evaluation_rows=(),
        provenance=source.provenance[: source.train_row_count],
    )

    files = dict(json_module._rendered_files(row_set))
    dataset = CanonicalJsonDataset.from_json_bytes(
        files[CANONICAL_JSON_DATASET_PATH]
    )
    provenance = CanonicalJsonProvenance.from_json_bytes(
        files[CANONICAL_JSON_PROVENANCE_PATH]
    )
    dataset.validate_provenance(provenance)
    assert dataset.splits.evaluation == ()
    assert dataset.evaluation_row_count == 0
    assert provenance.evaluation_row_count == 0


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-field",
        "unknown-field",
        "nested-unknown-field",
        "wrong-loss-policy",
        "wrong-train-count",
        "reversed-partitions",
        "row-metadata",
        "wrong-row-shape",
        "consumer-profile",
        "trainer-claim",
    ],
)
def test_dataset_contract_rejects_shape_and_metadata_mutations(
    tmp_path: Path,
    mutation: str,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    files = dict(json_module._rendered_files(_source_row_set(bundle)))
    original = CanonicalJsonDataset.from_json_bytes(
        files[CANONICAL_JSON_DATASET_PATH]
    ).model_dump(mode="json")

    if mutation == "missing-field":
        original.pop("split_result_id")
    elif mutation == "unknown-field":
        original["unexpected"] = True
    elif mutation == "nested-unknown-field":
        original["splits"]["unexpected"] = []
    elif mutation == "wrong-loss-policy":
        original["loss_policy"] = "completion-only"
    elif mutation == "wrong-train-count":
        original["train_row_count"] = 2
    elif mutation == "reversed-partitions":
        original["partition_order"] = ["evaluation", "train"]
    elif mutation == "row-metadata":
        original["splits"]["train"][0]["row_id"] = derive_id("row", {})
    elif mutation == "wrong-row-shape":
        original["splits"]["train"][0] = {"prompt": "not text"}
    elif mutation == "consumer-profile":
        original["consumer_profile"] = "trainer"
    else:
        assert mutation == "trainer-claim"
        original["trainer_compatibility_claimed"] = True

    with pytest.raises(ExportVerificationError):
        CanonicalJsonDataset.from_json_bytes(lossless_json_bytes(original))


@pytest.mark.parametrize("mutation", ["newline", "duplicate-key", "float"])
def test_dataset_loader_rejects_noncanonical_or_ambiguous_json(
    tmp_path: Path,
    mutation: str,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    data = dict(json_module._rendered_files(_source_row_set(bundle)))[
        CANONICAL_JSON_DATASET_PATH
    ]
    if mutation == "newline":
        changed = data + b"\n"
    elif mutation == "duplicate-key":
        changed = data.replace(
            b'"container_id":"json"',
            b'"container_id":"json","container_id":"json"',
            1,
        )
    else:
        assert mutation == "float"
        changed = data.replace(b'"train_row_count":1', b'"train_row_count":1.0', 1)
    with pytest.raises(ExportVerificationError):
        CanonicalJsonDataset.from_json_bytes(changed)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-field",
        "unknown-field",
        "wrong-count",
        "wrong-objective",
        "reordered",
        "duplicate-row",
    ],
)
def test_provenance_contract_rejects_incomplete_or_misaligned_rows(
    tmp_path: Path,
    mutation: str,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    original = CanonicalJsonProvenance.from_json_bytes(
        dict(json_module._rendered_files(_source_row_set(bundle)))[
            CANONICAL_JSON_PROVENANCE_PATH
        ]
    ).model_dump(mode="json")

    if mutation == "missing-field":
        original.pop("row_set_id")
    elif mutation == "unknown-field":
        original["unexpected"] = True
    elif mutation == "wrong-count":
        original["evaluation_row_count"] = 1
    elif mutation == "wrong-objective":
        original["objective_id"] = derive_id("obj", {"changed": True})
    elif mutation == "reordered":
        original["rows"][1], original["rows"][2] = (
            original["rows"][2],
            original["rows"][1],
        )
    else:
        assert mutation == "duplicate-row"
        original["rows"][2] = original["rows"][1]

    with pytest.raises(ExportVerificationError):
        CanonicalJsonProvenance.from_json_bytes(lossless_json_bytes(original))


@pytest.mark.parametrize("mutation", ["row-set", "payload", "row-schema"])
def test_cross_file_binding_rejects_valid_documents_that_disagree(
    tmp_path: Path,
    mutation: str,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    files = dict(json_module._rendered_files(_source_row_set(bundle)))
    dataset_data = CanonicalJsonDataset.from_json_bytes(
        files[CANONICAL_JSON_DATASET_PATH]
    ).model_dump(mode="json")
    provenance_data = CanonicalJsonProvenance.from_json_bytes(
        files[CANONICAL_JSON_PROVENANCE_PATH]
    ).model_dump(mode="json")

    if mutation == "row-set":
        dataset_data["row_set_id"] = derive_id("rws", {"changed": True})
    elif mutation == "payload":
        dataset_data["splits"]["train"][0]["text"] += " changed"
    else:
        assert mutation == "row-schema"
        provenance_data["row_schema"] = "prompt_completion"

    dataset = CanonicalJsonDataset.from_json_bytes(lossless_json_bytes(dataset_data))
    provenance = CanonicalJsonProvenance.from_json_bytes(
        lossless_json_bytes(provenance_data)
    )
    with pytest.raises(ExportVerificationError):
        dataset.validate_provenance(provenance)


def test_cross_file_binding_reconstructs_and_closes_the_source_row_set(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    files = dict(json_module._rendered_files(_source_row_set(bundle)))
    dataset = CanonicalJsonDataset.from_json_bytes(
        files[CANONICAL_JSON_DATASET_PATH]
    )
    provenance_data = CanonicalJsonProvenance.from_json_bytes(
        files[CANONICAL_JSON_PROVENANCE_PATH]
    ).model_dump(mode="json")
    first = provenance_data["rows"][0]
    first["plan_id"] = derive_id("fdp", {"changed": True})
    first["provenance_id"] = derive_id(
        "prv",
        {key: value for key, value in first.items() if key != "provenance_id"},
    )
    provenance = CanonicalJsonProvenance.from_json_bytes(
        lossless_json_bytes(provenance_data)
    )

    with pytest.raises(ExportVerificationError, match="source row set"):
        dataset.validate_provenance(provenance)


def test_canonical_json_publishes_verifies_and_detects_every_file_tamper(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service = ExportService()
    plan = service.dry_run_export(_dry(bundle))
    destination = tmp_path / "published"

    publication = service.execute_export(
        _execute(bundle, destination, plan.export_plan_id)
    )
    verified = service.verify_export(_verify(bundle, destination, plan.export_plan_id))
    assert (
        publication.verification.export_verification_id
        == verified.verification.export_verification_id
    )
    tree = _tree_bytes(destination)
    assert set(tree) == {
        CANONICAL_JSON_README_PATH,
        CANONICAL_JSON_DATASET_PATH,
        CANONICAL_JSON_PROVENANCE_PATH,
        "export-receipt.json",
    }
    dataset = CanonicalJsonDataset.from_json_bytes(
        tree[CANONICAL_JSON_DATASET_PATH]
    )
    provenance = CanonicalJsonProvenance.from_json_bytes(
        tree[CANONICAL_JSON_PROVENANCE_PATH]
    )
    dataset.validate_provenance(provenance)

    for index, relative_path in enumerate(sorted(tree)):
        changed = tmp_path / f"tampered-{index}"
        shutil.copytree(destination, changed)
        target = changed.joinpath(*relative_path.split("/"))
        target.write_bytes(target.read_bytes() + b"\n")
        with pytest.raises(ExportVerificationError):
            service.verify_export(_verify(bundle, changed, plan.export_plan_id))


@pytest.mark.parametrize("mutation", ["missing", "unexpected"])
def test_canonical_json_verification_rejects_closed_tree_mutations(
    tmp_path: Path,
    mutation: str,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service = ExportService()
    plan = service.dry_run_export(_dry(bundle))
    destination = tmp_path / "published"
    service.execute_export(_execute(bundle, destination, plan.export_plan_id))

    if mutation == "missing":
        (destination / CANONICAL_JSON_README_PATH).unlink()
    else:
        (destination / "unexpected.json").write_bytes(b"{}")

    with pytest.raises(ExportVerificationError):
        service.verify_export(_verify(bundle, destination, plan.export_plan_id))


def test_canonical_json_refuses_container_options_before_source_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = tmp_path / "must-not-be-opened.vfbundle"
    request = ExportDryRunRequestV2(
        operation="dry_run",
        container_options={},
        **_selection(bundle, schema_version=EXPORT_SURFACE_REQUEST_SCHEMA_V2),
    )
    service = ExportService()
    source_opened = False

    def fail_if_opened(*_args: object, **_kwargs: object) -> None:
        nonlocal source_opened
        source_opened = True
        raise AssertionError("container options must fail before source access")

    monkeypatch.setattr(service, "verified_source", fail_if_opened)
    with pytest.raises(ExportContractError, match="does not accept container_options"):
        service.dry_run_export(request)
    assert source_opened is False
