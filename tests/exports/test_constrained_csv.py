"""Phase 5.3 contract tests for the generic constrained-CSV container."""

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
    ExportContainerProfile,
    ExportExecuteRequest,
    ExportExecuteRequestV2,
    ExportService,
    ExportProfileDescriptor,
    ExportVerifyRequest,
    ExportVerifyRequestV2,
)
from veriformis.exports import constrained_csv as csv_module
from veriformis.exports.constrained_csv import (
    CONSTRAINED_CSV_CONTAINER_ID,
    CONSTRAINED_CSV_CONTAINER_VERSION,
    CONSTRAINED_CSV_DATA_CARD_PATH,
    CONSTRAINED_CSV_DATA_CARD_SCHEMA,
    CONSTRAINED_CSV_DIALECT_SCHEMA,
    CONSTRAINED_CSV_EVALUATION_PATH,
    CONSTRAINED_CSV_PROVENANCE_PATH,
    CONSTRAINED_CSV_README_PATH,
    CONSTRAINED_CSV_TRAIN_PATH,
    ConstrainedCsvDataCard,
    ConstrainedCsvPartition,
)
from veriformis.exports.models import EXPORT_RECEIPT_PATH
from veriformis.exports import service as service_module
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
ROW_SCHEMAS = ("instruction_output", "prompt_completion", "text")


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
        "container_id": CONSTRAINED_CSV_CONTAINER_ID,
        "container_version": CONSTRAINED_CSV_CONTAINER_VERSION,
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
    exact = (
        f'{value}, "quoted"\t leading and trailing \x00'
        " CR=\r LF=\n CRLF=\r\n formula==1+1 "
        "composed=\u00e9 decomposed=e\u0301 nonbmp=\U0001f600"
    )
    if row_schema == "text":
        return {"text": exact}
    if row_schema == "prompt_completion":
        return {"prompt": f"context:{exact}", "completion": f"target:{exact}"}
    if row_schema == "instruction_output":
        return {
            "instruction": f"instruction:{exact}",
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


def _load_rendered_row_set(
    row_set: RowSet,
    files: dict[str, bytes],
) -> RowSet:
    card = ConstrainedCsvDataCard.from_json_bytes(
        files[CONSTRAINED_CSV_DATA_CARD_PATH]
    )
    train = ConstrainedCsvPartition.from_csv_bytes(
        files[CONSTRAINED_CSV_TRAIN_PATH],
        row_schema=row_set.row_schema,
    )
    evaluation = ConstrainedCsvPartition.from_csv_bytes(
        files[CONSTRAINED_CSV_EVALUATION_PATH],
        row_schema=row_set.row_schema,
    )
    provenance = csv_module._provenance_from_jsonl_bytes(
        files[CONSTRAINED_CSV_PROVENANCE_PATH]
    )
    return card.validate_row_set(
        train=train,
        evaluation=evaluation,
        provenance=provenance,
    )


def test_constrained_csv_discovery_and_fixed_plan(tmp_path: Path) -> None:
    bundle = _materialize_bundle(tmp_path)
    service = ExportService()
    profiles = {
        profile.selector: profile for profile in service.discover_exports().profiles
    }
    selector = (CONSTRAINED_CSV_CONTAINER_ID, 1, None, None)

    assert selector in profiles
    assert profiles[selector].supported_row_schemas == ROW_SCHEMAS
    assert profiles[selector].consumer_profile is None
    assert (
        profiles[selector].container_profile.determinism_claim
        == "portable_exact_bytes"
    )
    assert profiles[selector].dependencies[0].dependency_name == (
        "veriformis-constrained-csv-renderer"
    )

    first = service.dry_run_export(_dry(bundle))
    second = service.dry_run_export(_dry(bundle))
    assert first == second
    plans = {item.path: item for item in first.file_plans}
    assert set(plans) == {
        CONSTRAINED_CSV_README_PATH,
        CONSTRAINED_CSV_TRAIN_PATH,
        CONSTRAINED_CSV_EVALUATION_PATH,
        CONSTRAINED_CSV_DATA_CARD_PATH,
        CONSTRAINED_CSV_PROVENANCE_PATH,
    }
    assert plans[CONSTRAINED_CSV_TRAIN_PATH].membership_scope == "train"
    assert plans[CONSTRAINED_CSV_TRAIN_PATH].record_count == 1
    assert plans[CONSTRAINED_CSV_EVALUATION_PATH].membership_scope == "evaluation"
    assert plans[CONSTRAINED_CSV_EVALUATION_PATH].record_count == 2
    assert plans[CONSTRAINED_CSV_PROVENANCE_PATH].membership_scope == "none"
    assert plans[CONSTRAINED_CSV_PROVENANCE_PATH].record_count == 3
    assert plans[CONSTRAINED_CSV_TRAIN_PATH].media_type == "text/csv"


@pytest.mark.parametrize("row_schema", ROW_SCHEMAS)
def test_every_admitted_schema_round_trips_exact_rows_partitions_and_provenance(
    tmp_path: Path,
    row_schema: str,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    row_set = _row_set_for_schema(_source_row_set(bundle), row_schema)

    first = dict(csv_module._rendered_files(row_set))
    second = dict(csv_module._rendered_files(row_set))
    assert first == second
    assert _load_rendered_row_set(row_set, first) == row_set

    train = ConstrainedCsvPartition.from_csv_bytes(
        first[CONSTRAINED_CSV_TRAIN_PATH],
        row_schema=row_schema,
    )
    evaluation = ConstrainedCsvPartition.from_csv_bytes(
        first[CONSTRAINED_CSV_EVALUATION_PATH],
        row_schema=row_schema,
    )
    assert train.payloads == tuple(row.payload for row in row_set.train_rows)
    assert evaluation.payloads == tuple(
        row.payload for row in row_set.evaluation_rows
    )
    assert first[CONSTRAINED_CSV_README_PATH].endswith(b"\n")
    assert b"portable" not in first[CONSTRAINED_CSV_README_PATH]
    assert b"split-jsonl-directory" in first[CONSTRAINED_CSV_README_PATH]
    assert b"does not select a training objective" in first[
        CONSTRAINED_CSV_README_PATH
    ]

    plans = {
        item.path: item
        for item in csv_module._file_plans(
            csv_module.CONSTRAINED_CSV_DESCRIPTOR,
            row_set,
        )
    }
    assert set(plans) == set(first)
    assert all(
        plans[path].expected_sha256 == sha256_digest(data)
        and plans[path].expected_byte_size == len(data)
        for path, data in first.items()
    )


def test_csv_golden_bytes_freeze_quote_all_unicode_and_embedded_controls() -> None:
    payload = {
        "prompt": ' leading,"quote"\t\x00\r\n\u00e9e\u0301\U0001f600 ',
        "completion": "=1+1\\Nnull",
    }
    data = csv_module._payloads_csv_bytes("prompt_completion", (payload,))

    assert data == (
        '"prompt","completion"\n'
        '" leading,""quote""\t\x00\r\n\u00e9e\u0301\U0001f600 ","=1+1\\Nnull"\n'
    ).encode("utf-8")
    loaded = ConstrainedCsvPartition.from_csv_bytes(
        data,
        row_schema="prompt_completion",
    )
    assert loaded.payloads == (payload,)


@pytest.mark.parametrize(
    ("row_schema", "expected_header"),
    [
        ("instruction_output", b'"instruction","input","output"\n'),
        ("prompt_completion", b'"prompt","completion"\n'),
        ("text", b'"text"\n'),
    ],
)
def test_every_admitted_schema_has_an_independent_literal_header_golden(
    row_schema: str,
    expected_header: bytes,
) -> None:
    assert csv_module._payloads_csv_bytes(row_schema, ()) == expected_header


def test_strict_loader_has_no_small_global_csv_field_limit() -> None:
    value = "x" * 200_000
    data = csv_module._payloads_csv_bytes("text", ({"text": value},))

    loaded = ConstrainedCsvPartition.from_csv_bytes(data, row_schema="text")

    assert loaded.payloads == ({"text": value},)


@pytest.mark.parametrize(
    "changed",
    [
        b"\xef\xbb\xbf\"text\"\n\"value\"\n",
        b'"text"\n"\xff"\n',
        b'text\n"value"\n',
        b'"text"\nvalue\n',
        b'"text"\r\n"value"\r\n',
        b'"text"\n"value"',
        b'"prompt"\n"value"\n',
        b'"text","text"\n"value","value"\n',
        b'"text"\n"value","extra"\n',
        b'"text"\n\n"value"\n',
        b'"text"\n""\n',
        b'"text";\n"value";\n',
        b"'text'\n'value'\n",
    ],
)
def test_partition_loader_rejects_noncanonical_or_schema_invalid_csv(
    changed: bytes,
) -> None:
    with pytest.raises(ExportVerificationError):
        ConstrainedCsvPartition.from_csv_bytes(changed, row_schema="text")


@pytest.mark.parametrize("value", ["null", "NULL", "None", r"\N", "=1+1"])
def test_null_and_formula_looking_literals_remain_exact_strings(value: str) -> None:
    data = csv_module._payloads_csv_bytes("text", ({"text": value},))

    loaded = ConstrainedCsvPartition.from_csv_bytes(data, row_schema="text")

    assert loaded.payloads == ({"text": value},)


@pytest.mark.parametrize("value", [None, 1, False, ["nested"], {"nested": True}])
def test_codec_refuses_null_and_non_string_values(value: object) -> None:
    with pytest.raises(ValueError, match="unrepresentable"):
        csv_module._payloads_csv_bytes("text", ({"text": value},))


def test_empty_evaluation_is_canonical_header_only_csv(tmp_path: Path) -> None:
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

    files = dict(csv_module._rendered_files(row_set))
    evaluation = ConstrainedCsvPartition.from_csv_bytes(
        files[CONSTRAINED_CSV_EVALUATION_PATH],
        row_schema="text",
    )
    card = ConstrainedCsvDataCard.from_json_bytes(
        files[CONSTRAINED_CSV_DATA_CARD_PATH]
    )

    assert files[CONSTRAINED_CSV_EVALUATION_PATH] == b'"text"\n'
    assert evaluation.payloads == ()
    assert card.evaluation_row_count == 0
    assert _load_rendered_row_set(row_set, files) == row_set


def test_data_card_is_strict_canonical_and_has_the_exact_frozen_fields(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    data = dict(csv_module._rendered_files(_source_row_set(bundle)))[
        CONSTRAINED_CSV_DATA_CARD_PATH
    ]
    card = ConstrainedCsvDataCard.from_json_bytes(data)

    assert set(ConstrainedCsvDataCard.model_fields) == {
        "schema_version",
        "container_id",
        "container_version",
        "dialect",
        "encoding",
        "byte_order_mark",
        "delimiter",
        "quote_character",
        "quoting",
        "doublequote",
        "record_terminator",
        "null_encoding",
        "empty_string_encoding",
        "row_schema",
        "columns",
        "objective_id",
        "loss_policy",
        "row_set_id",
        "split_result_id",
        "train_path",
        "train_row_count",
        "evaluation_path",
        "evaluation_row_count",
        "provenance_path",
        "provenance_row_count",
        "provenance_alignment",
        "receipt_path",
        "consumer_profile",
        "trainer_compatibility_claimed",
    }
    assert card.schema_version == CONSTRAINED_CSV_DATA_CARD_SCHEMA
    assert card.dialect == CONSTRAINED_CSV_DIALECT_SCHEMA
    assert card.encoding == "utf-8"
    assert card.byte_order_mark is False
    assert card.delimiter == ","
    assert card.quote_character == '"'
    assert card.quoting == "all"
    assert card.doublequote is True
    assert card.record_terminator == "lf"
    assert card.null_encoding is None
    assert card.empty_string_encoding == "quoted-empty-field"
    assert card.canonical_bytes() == data
    assert not data.endswith(b"\n")

    for key, changed in (
        ("dialect", "excel"),
        ("columns", ["wrong"]),
        ("train_row_count", 99),
        ("provenance_alignment", "evaluation_then_train"),
        ("consumer_profile", "trainer"),
        ("trainer_compatibility_claimed", True),
    ):
        mutated = card.model_dump(mode="json")
        mutated[key] = changed
        with pytest.raises(ExportVerificationError):
            ConstrainedCsvDataCard.from_json_bytes(lossless_json_bytes(mutated))


@pytest.mark.parametrize("mutation", ["payload", "provenance", "row-set"])
def test_cross_file_validation_rejects_semantic_or_identity_drift(
    tmp_path: Path,
    mutation: str,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    row_set = _source_row_set(bundle)
    files = dict(csv_module._rendered_files(row_set))
    card_data = ConstrainedCsvDataCard.from_json_bytes(
        files[CONSTRAINED_CSV_DATA_CARD_PATH]
    ).model_dump(mode="json")
    train_data = files[CONSTRAINED_CSV_TRAIN_PATH]
    provenance = list(
        csv_module._provenance_from_jsonl_bytes(
            files[CONSTRAINED_CSV_PROVENANCE_PATH]
        )
    )

    if mutation == "payload":
        train_data = csv_module._payloads_csv_bytes(
            "text",
            ({"text": row_set.train_rows[0].payload["text"] + " changed"},),
        )
    elif mutation == "provenance":
        provenance[1], provenance[2] = provenance[2], provenance[1]
    else:
        assert mutation == "row-set"
        card_data["row_set_id"] = derive_id("rws", {"changed": True})

    card = ConstrainedCsvDataCard.from_json_bytes(lossless_json_bytes(card_data))
    train = ConstrainedCsvPartition.from_csv_bytes(train_data, row_schema="text")
    evaluation = ConstrainedCsvPartition.from_csv_bytes(
        files[CONSTRAINED_CSV_EVALUATION_PATH],
        row_schema="text",
    )
    with pytest.raises(ExportVerificationError):
        card.validate_row_set(
            train=train,
            evaluation=evaluation,
            provenance=provenance,
        )


@pytest.mark.parametrize(
    "changed",
    [
        b"",
        b"{}",
        b"{}\n\n",
        b"{}\r\n",
    ],
)
def test_provenance_loader_rejects_noncanonical_jsonl(changed: bytes) -> None:
    with pytest.raises(ExportVerificationError):
        csv_module._provenance_from_jsonl_bytes(changed)


def test_messages_fail_before_destination_access_with_actionable_alternatives(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    messages = _row_set_for_schema(_source_row_set(bundle), "messages")
    destination = tmp_path / "must-not-be-read-or-created"
    service = ExportService()
    monkeypatch.setattr(service, "verified_source", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        service_module,
        "_source_plan_evidence",
        lambda _source: (None, messages, None, messages.provenance[0].objective_id, None),
    )
    plan_id = derive_id("export-plan", {"unsupported": "messages"})
    requests = (
        _dry(bundle),
        _execute(bundle, destination, plan_id),
        _verify(bundle, destination, plan_id),
    )

    for request in requests:
        operation = request.operation
        call = {
            "dry_run": service.dry_run_export,
            "execute": service.execute_export,
            "verify": service.verify_export,
        }[operation]
        with pytest.raises(ExportContractError) as error:
            call(request)  # type: ignore[arg-type]
        message = str(error.value)
        assert "constrained-csv" in message
        assert "messages" in message
        assert "split-jsonl-directory v1" in message
        assert "json v1" in message
        assert not destination.exists()


def test_future_constrained_csv_selector_gets_generic_schema_guidance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    messages = _row_set_for_schema(_source_row_set(bundle), "messages")
    current = csv_module.CONSTRAINED_CSV_IMPLEMENTATION
    future_descriptor = ExportProfileDescriptor(
        container_profile=ExportContainerProfile.create(
            container_id=CONSTRAINED_CSV_CONTAINER_ID,
            container_version=2,
            determinism_claim="portable_exact_bytes",
        ),
        consumer_profile=None,
        dependencies=current.descriptor.dependencies,
        supported_row_schemas=current.descriptor.supported_row_schemas,
    )
    service = ExportService(
        _implementations=(
            service_module._ExportImplementation(
                descriptor=future_descriptor,
                file_planner=current.file_planner,
                renderer=current.renderer,
                semantic_replayer=None,
            ),
        )
    )
    monkeypatch.setattr(service, "verified_source", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        service_module,
        "_source_plan_evidence",
        lambda _source: (None, messages, None, messages.provenance[0].objective_id, None),
    )
    selected = _selection(bundle, schema_version=EXPORT_SURFACE_REQUEST_SCHEMA)
    selected["container_version"] = 2

    with pytest.raises(ExportContractError) as error:
        service.dry_run_export(ExportDryRunRequest(operation="dry_run", **selected))

    message = str(error.value)
    assert "constrained-csv" in message
    assert "v2" in message
    assert "choose a discovered profile" in message
    assert "split-jsonl-directory" not in message
    assert "json v1" not in message


def test_constrained_csv_refuses_container_options_before_source_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = tmp_path / "must-not-be-opened.vfbundle"
    destination = tmp_path / "must-not-be-opened-or-created"
    plan_id = derive_id("export-plan", {"configured": "refused"})
    selected = _selection(bundle, schema_version=EXPORT_SURFACE_REQUEST_SCHEMA_V2)
    requests = (
        ExportDryRunRequestV2(
            operation="dry_run",
            container_options={},
            **selected,
        ),
        ExportExecuteRequestV2(
            operation="execute",
            container_options={},
            destination_root=str(destination),
            expected_export_plan_id=plan_id,
            **selected,
        ),
        ExportVerifyRequestV2(
            operation="verify",
            container_options={},
            destination_root=str(destination),
            expected_export_plan_id=plan_id,
            **selected,
        ),
    )
    service = ExportService()
    source_opened = False

    def fail_if_opened(*_args: object, **_kwargs: object) -> None:
        nonlocal source_opened
        source_opened = True
        raise AssertionError("container options must fail before source access")

    monkeypatch.setattr(service, "verified_source", fail_if_opened)
    for request in requests:
        call = {
            "dry_run": service.dry_run_export,
            "execute": service.execute_export,
            "verify": service.verify_export,
        }[request.operation]
        with pytest.raises(
            ExportContractError,
            match="does not accept container_options",
        ):
            call(request)  # type: ignore[arg-type]
    assert source_opened is False
    assert not destination.exists()


def test_constrained_csv_publishes_verifies_and_detects_every_file_tamper(
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
        CONSTRAINED_CSV_README_PATH,
        CONSTRAINED_CSV_TRAIN_PATH,
        CONSTRAINED_CSV_EVALUATION_PATH,
        CONSTRAINED_CSV_DATA_CARD_PATH,
        CONSTRAINED_CSV_PROVENANCE_PATH,
        EXPORT_RECEIPT_PATH,
    }
    assert _load_rendered_row_set(_source_row_set(bundle), tree) == _source_row_set(
        bundle
    )

    for index, relative_path in enumerate(sorted(tree)):
        changed = tmp_path / f"tampered-{index}"
        shutil.copytree(destination, changed)
        target = changed.joinpath(*relative_path.split("/"))
        target.write_bytes(target.read_bytes() + b"\n")
        with pytest.raises(ExportVerificationError):
            service.verify_export(_verify(bundle, changed, plan.export_plan_id))


@pytest.mark.parametrize("mutation", ["missing", "unexpected"])
def test_constrained_csv_verification_rejects_closed_tree_mutations(
    tmp_path: Path,
    mutation: str,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service = ExportService()
    plan = service.dry_run_export(_dry(bundle))
    destination = tmp_path / "published"
    service.execute_export(_execute(bundle, destination, plan.export_plan_id))

    if mutation == "missing":
        (destination / CONSTRAINED_CSV_README_PATH).unlink()
    else:
        (destination / "unexpected.csv").write_bytes(b'"extra"\n')

    with pytest.raises(ExportVerificationError):
        service.verify_export(_verify(bundle, destination, plan.export_plan_id))
