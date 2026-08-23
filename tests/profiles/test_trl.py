"""Phase 8.3: emit TRL SFT files without importing TRL."""

from __future__ import annotations

import base64
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

from veriformis.datasets import ProductRow, RowSet, row_provenance_from_json_bytes
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
from veriformis.exports.split_jsonl import (
    SPLIT_JSONL_CONTAINER_ID,
    SPLIT_JSONL_CONTAINER_VERSION,
)
from veriformis.identity import derive_id, lossless_json_bytes, sha256_digest
from veriformis.taxonomy import loss_policy_for_row
from veriformis.profiles.trl import (
    TRL_CONSUMER_ID,
    TRL_DATA_CARD_PATH,
    TRL_EVALUATION_PATH,
    TRL_PROFILE_METADATA_PATH,
    TRL_PROFILE_VERSION,
    TRL_PROVENANCE_PATH,
    TRL_README_PATH,
    TRL_TRAIN_PATH,
    TrlDataCard,
    TrlProfileMetadata,
    map_trl_payload,
)
from veriformis.profiles import trl as trl_module

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
SELECTOR = (
    SPLIT_JSONL_CONTAINER_ID,
    SPLIT_JSONL_CONTAINER_VERSION,
    TRL_CONSUMER_ID,
    TRL_PROFILE_VERSION,
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
        "container_id": SPLIT_JSONL_CONTAINER_ID,
        "container_version": SPLIT_JSONL_CONTAINER_VERSION,
        "consumer_id": TRL_CONSUMER_ID,
        "consumer_profile_version": TRL_PROFILE_VERSION,
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
    bundle: Path, destination: Path, plan_id: str
) -> ExportExecuteRequest:
    return ExportExecuteRequest(
        operation="execute",
        destination_root=str(destination),
        expected_export_plan_id=plan_id,
        **_selection(bundle, schema_version=EXPORT_SURFACE_REQUEST_SCHEMA),
    )


def _verify(bundle: Path, destination: Path, plan_id: str) -> ExportVerifyRequest:
    return ExportVerifyRequest(
        operation="verify",
        destination_root=str(destination),
        expected_export_plan_id=plan_id,
        **_selection(bundle, schema_version=EXPORT_SURFACE_REQUEST_SCHEMA),
    )


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


def test_trl_is_discoverable_beside_generic_split_jsonl() -> None:
    profiles = {
        profile.selector: profile
        for profile in ExportService().discover_exports().profiles
    }
    assert SELECTOR in profiles
    assert (
        SPLIT_JSONL_CONTAINER_ID,
        SPLIT_JSONL_CONTAINER_VERSION,
        None,
        None,
    ) in profiles
    trl = profiles[SELECTOR]
    assert trl.consumer_profile is not None
    assert trl.consumer_profile.consumer_id == TRL_CONSUMER_ID
    assert trl.supported_row_schemas == ROW_SCHEMAS
    assert trl.container_profile.determinism_claim == "portable_exact_bytes"


def test_map_trl_payload_assembles_instruction_output_and_keeps_identity() -> None:
    assembled = map_trl_payload(
        "instruction_output",
        {"instruction": "Task", "input": "Context", "output": "Answer"},
    )
    assert assembled == {"completion": "Answer", "prompt": "Task\nContext"}
    text = map_trl_payload("text", {"text": "café"})
    assert text == {"text": "café"}


def test_trl_render_maps_every_schema_without_changing_counts(tmp_path: Path) -> None:
    bundle = _materialize_bundle(tmp_path)
    source = _source_row_set(bundle)
    for row_schema in ROW_SCHEMAS:
        row_set = _row_set_for_schema(source, row_schema)
        files = dict(trl_module._rendered_files(row_set))
        train = [
            json.loads(line)
            for line in files[TRL_TRAIN_PATH].decode("utf-8").splitlines()
        ]
        evaluation = [
            json.loads(line)
            for line in files[TRL_EVALUATION_PATH].decode("utf-8").splitlines()
            if line
        ]
        assert len(train) == row_set.train_row_count
        assert len(evaluation) == row_set.evaluation_row_count
        expected_train = [
            map_trl_payload(row_schema, row.payload) for row in row_set.train_rows
        ]
        assert train == expected_train
        if row_schema == "instruction_output":
            assert all("instruction" not in row for row in train)
            assert all("\n" in row["prompt"] for row in train)
        card = TrlDataCard.from_json_bytes(files[TRL_DATA_CARD_PATH])
        meta = TrlProfileMetadata.from_json_bytes(files[TRL_PROFILE_METADATA_PATH])
        assert card.loss_policy == loss_policy_for_row(row_schema)
        assert card.trainer_compatibility_claimed is False
        assert meta.round_trip is False
        assert meta.taxonomy_state == "planned"
        assert files[TRL_README_PATH].endswith(b"\n")
        assert b"does not claim that TRL has loaded" in files[TRL_README_PATH]


def test_trl_publishes_and_verifies_the_text_fixture(tmp_path: Path) -> None:
    bundle = _materialize_bundle(tmp_path)
    service = ExportService()
    plan = service.dry_run_export(_dry(bundle))
    assert plan.consumer_profile is not None
    assert plan.consumer_profile.consumer_id == TRL_CONSUMER_ID
    assert plan.loss_policy == "full-sequence"
    destination = tmp_path / "published"
    publication = service.execute_export(
        _execute(bundle, destination, plan.export_plan_id)
    )
    verified = service.verify_export(_verify(bundle, destination, plan.export_plan_id))
    assert (
        publication.verification.export_verification_id
        == verified.verification.export_verification_id
    )
    tree = {
        path.relative_to(destination).as_posix(): path.read_bytes()
        for path in sorted(destination.rglob("*"))
        if path.is_file()
    }
    assert set(tree) == {
        TRL_README_PATH,
        TRL_TRAIN_PATH,
        TRL_EVALUATION_PATH,
        TRL_DATA_CARD_PATH,
        TRL_PROFILE_METADATA_PATH,
        TRL_PROVENANCE_PATH,
        "export-receipt.json",
    }
    train = [
        json.loads(line) for line in tree[TRL_TRAIN_PATH].decode("utf-8").splitlines()
    ]
    assert train and all(set(row) == {"text"} for row in train)

    changed = tmp_path / "tampered"
    shutil.copytree(destination, changed)
    (changed / TRL_TRAIN_PATH).write_bytes(
        (changed / TRL_TRAIN_PATH).read_bytes() + b"\n"
    )
    with pytest.raises(ExportVerificationError):
        service.verify_export(_verify(bundle, changed, plan.export_plan_id))


def test_trl_refuses_container_options_before_source_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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


def test_trl_emission_does_not_import_trainer_libraries() -> None:
    assert "trl" not in sys.modules
    assert "torch" not in sys.modules
    map_trl_payload("text", {"text": "ok"})
    assert "trl" not in sys.modules
    assert "torch" not in sys.modules
