"""Phase 5.1 contract tests for the generic split-JSONL container."""

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
    ExportExecuteRequestV2,
    ExportService,
    ExportVerifyRequestV2,
    export_request_from_json_bytes,
)
from veriformis.exports import split_jsonl as split_module
from veriformis.exports.split_jsonl import (
    SPLIT_JSONL_CONTAINER_ID,
    SPLIT_JSONL_CONTAINER_VERSION,
    SPLIT_JSONL_DATA_CARD_PATH,
    SPLIT_JSONL_OPTIONS_SCHEMA,
    SPLIT_JSONL_PROVENANCE_PATH,
    SPLIT_JSONL_README_PATH,
    SplitJsonlDataCard,
    SplitJsonlOptions,
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
ROW_SCHEMAS = (
    "instruction_output",
    "label-classification",
    "messages",
    "preference-pair",
    "prompt_completion",
    "stepwise-trace",
    "text",
    "tool-call-conversation",
)
SFT_ROW_SCHEMAS = ("instruction_output", "messages", "prompt_completion", "text")
CUSTOM_EXPORT_GOLDEN = {
    "README.md": (
        "18391ab32d59181e4993f22b6c2b8e468fe5ca5caab66cd65656ac1b32d7ba9e",
        1052,
    ),
    "data/learn.jsonl": (
        "013e9debe42abf29be9b94c29b971af43a4b87b37e4563c020e7f59cbce4f417",
        101,
    ),
    "data/score.jsonl": (
        "20bff1129969a89d648d169ccfb7930c17401b6cc7355fe890cc9882ae3e7f37",
        245,
    ),
    "export-receipt.json": (
        "08cb5b2067c2821eccd710c56e501d320bb29e0bc616169d6f3304f2fd3ce1d0",
        10420,
    ),
    "metadata/dataset-card.json": (
        "f36605eae6d3059c30ec6ab915aa14b9fb0fc8b080c26950ef75b13ab2c705d2",
        770,
    ),
    "metadata/row-provenance.jsonl": (
        "5ed55e59a6fd12e12549bd1b3a97c34bd5dc5195d427a2abc4f4be95f16924ea",
        11465,
    ),
}


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
        "consumer_id": None,
        "consumer_profile_version": None,
        "source_trust_policy": "require_external_digest",
        "expected_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "overwrite_policy": "refuse",
    }


def _dry_v1(bundle: Path) -> ExportDryRunRequest:
    return ExportDryRunRequest(
        operation="dry_run",
        **_selection(bundle, schema_version=EXPORT_SURFACE_REQUEST_SCHEMA),
    )


def _dry_v2(
    bundle: Path,
    options: dict[str, str | bool | int | None],
) -> ExportDryRunRequestV2:
    return ExportDryRunRequestV2(
        operation="dry_run",
        container_options=options,
        **_selection(bundle, schema_version=EXPORT_SURFACE_REQUEST_SCHEMA_V2),
    )


def _execute_v2(
    bundle: Path,
    destination: Path,
    plan_id: str,
    options: dict[str, str | bool | int | None],
) -> ExportExecuteRequestV2:
    return ExportExecuteRequestV2(
        operation="execute",
        destination_root=str(destination),
        expected_export_plan_id=plan_id,
        container_options=options,
        **_selection(bundle, schema_version=EXPORT_SURFACE_REQUEST_SCHEMA_V2),
    )


def _verify_v2(
    bundle: Path,
    destination: Path,
    plan_id: str,
    options: dict[str, str | bool | int | None],
) -> ExportVerifyRequestV2:
    return ExportVerifyRequestV2(
        operation="verify",
        destination_root=str(destination),
        expected_export_plan_id=plan_id,
        container_options=options,
        **_selection(bundle, schema_version=EXPORT_SURFACE_REQUEST_SCHEMA_V2),
    )


def _options(
    *,
    train: str = "train",
    evaluation: str = "evaluation",
    provenance: bool = True,
) -> dict[str, str | bool | int | None]:
    return SplitJsonlOptions(
        train_partition_name=train,
        evaluation_partition_name=evaluation,
        include_provenance=provenance,
    ).model_dump(mode="json")


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _jsonl_objects(data: bytes) -> tuple[dict[str, Any], ...]:
    """Independent strict reload used by the round-trip assertions."""
    if not data:
        return ()
    assert not data.startswith(b"\xef\xbb\xbf")
    assert data.endswith(b"\n")
    lines = data.splitlines(keepends=True)
    assert lines and all(line.endswith(b"\n") and line != b"\n" for line in lines)
    objects: list[dict[str, Any]] = []
    for line in lines:
        value = json.loads(line[:-1].decode("utf-8"))
        assert isinstance(value, dict)
        assert lossless_json_bytes(value) + b"\n" == line
        objects.append(value)
    return tuple(objects)


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


def _assert_full_round_trip(row_set: RowSet, files: dict[str, bytes]) -> None:
    card = SplitJsonlDataCard.from_json_bytes(files[SPLIT_JSONL_DATA_CARD_PATH])
    train_payloads = _jsonl_objects(files[card.train_path])
    evaluation_payloads = _jsonl_objects(files[card.evaluation_path])
    assert train_payloads == tuple(row.payload for row in row_set.train_rows)
    assert evaluation_payloads == tuple(row.payload for row in row_set.evaluation_rows)
    assert card.provenance_path == SPLIT_JSONL_PROVENANCE_PATH
    assert card.provenance_row_count == row_set.total_row_count

    provenance = tuple(
        row_provenance_from_json_bytes(line[:-1])
        for line in files[SPLIT_JSONL_PROVENANCE_PATH].splitlines(keepends=True)
    )
    payloads = (*train_payloads, *evaluation_payloads)
    rows = tuple(
        ProductRow.create(
            record_id=item.record_id,
            row_schema=row_set.row_schema,
            payload=payload,
        )
        for item, payload in zip(provenance, payloads, strict=True)
    )
    rebuilt = RowSet.create(
        plan_id=row_set.plan_id,
        serialization_plan_id=row_set.serialization_plan_id,
        recipe_id=row_set.recipe_id,
        construction_result_id=row_set.construction_result_id,
        curation_result_id=row_set.curation_result_id,
        split_result_id=row_set.split_result_id,
        row_schema=row_set.row_schema,
        train_rows=rows[: row_set.train_row_count],
        evaluation_rows=rows[row_set.train_row_count :],
        provenance=provenance,
    )
    assert rebuilt == row_set
    assert rebuilt.row_set_id == card.row_set_id


def test_split_jsonl_discovery_and_v1_v2_defaults_are_compatible(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service = ExportService()
    profiles = service.discover_exports().profiles

    profile = next(
        item
        for item in profiles
        if item.selector
        == (SPLIT_JSONL_CONTAINER_ID, SPLIT_JSONL_CONTAINER_VERSION, None, None)
    )
    assert profile.supported_row_schemas == ROW_SCHEMAS
    assert profile.container_profile.determinism_claim == "portable_exact_bytes"

    v1 = service.dry_run_export(_dry_v1(bundle))
    explicit_v2 = service.dry_run_export(_dry_v2(bundle, _options()))
    assert v1 == explicit_v2
    assert v1.consumer_profile is None
    assert v1.loss_policy == "full-sequence"

    paths = {item.path: item for item in v1.file_plans}
    assert set(paths) == {
        SPLIT_JSONL_README_PATH,
        "data/evaluation.jsonl",
        "data/train.jsonl",
        SPLIT_JSONL_DATA_CARD_PATH,
        SPLIT_JSONL_PROVENANCE_PATH,
    }
    assert paths["data/train.jsonl"].membership_scope == "train"
    assert paths["data/evaluation.jsonl"].membership_scope == "evaluation"
    assert all(
        item.membership_scope == "none"
        for path, item in paths.items()
        if path not in {"data/train.jsonl", "data/evaluation.jsonl"}
    )


def test_v2_requests_are_canonical_and_operation_specific(tmp_path: Path) -> None:
    bundle = _materialize_bundle(tmp_path)
    request = _dry_v2(bundle, _options(train="learn", evaluation="score"))

    assert (
        export_request_from_json_bytes(
            request.canonical_bytes(), expected_operation="dry_run"
        )
        == request
    )
    with pytest.raises(ExportContractError, match="operation must be 'execute'"):
        export_request_from_json_bytes(
            request.canonical_bytes(), expected_operation="execute"
        )
    with pytest.raises(ExportContractError):
        export_request_from_json_bytes(
            request.canonical_bytes() + b"\n", expected_operation="dry_run"
        )


@pytest.mark.parametrize(
    "options",
    [
        {},
        {"schema_version": "veriformis.split-jsonl-options/v2"},
        {"schema_version": SPLIT_JSONL_OPTIONS_SCHEMA, "unexpected": "value"},
        {"schema_version": SPLIT_JSONL_OPTIONS_SCHEMA, "train_partition_name": "Train"},
        {
            "schema_version": SPLIT_JSONL_OPTIONS_SCHEMA,
            "train_partition_name": "../train",
        },
        {"schema_version": SPLIT_JSONL_OPTIONS_SCHEMA, "train_partition_name": "con"},
        {
            "schema_version": SPLIT_JSONL_OPTIONS_SCHEMA,
            "train_partition_name": "same",
            "evaluation_partition_name": "same",
            "include_provenance": False,
        },
        {
            "schema_version": SPLIT_JSONL_OPTIONS_SCHEMA,
            "train_partition_name": "a" * 65,
            "evaluation_partition_name": "evaluation",
            "include_provenance": False,
        },
        {
            "schema_version": SPLIT_JSONL_OPTIONS_SCHEMA,
            "train_partition_name": "train",
            "evaluation_partition_name": "evaluation",
            "include_provenance": 1,
        },
    ],
)
def test_invalid_options_fail_before_source_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    options: dict[str, str | bool | int | None],
) -> None:
    bundle = tmp_path / "must-not-be-opened.vfbundle"
    service = ExportService()
    source_opened = False

    def fail_if_opened(*_args: object, **_kwargs: object) -> None:
        nonlocal source_opened
        source_opened = True
        raise AssertionError("invalid options must fail before source access")

    monkeypatch.setattr(service, "verified_source", fail_if_opened)
    with pytest.raises(ExportContractError):
        service.dry_run_export(_dry_v2(bundle, options))
    assert source_opened is False


@pytest.mark.parametrize(
    ("name", "valid"),
    [
        ("a", True),
        ("0", True),
        ("a" * 64, True),
        ("train_01-safe", True),
        ("", False),
        ("a" * 65, False),
        ("Train", False),
        ("train.jsonl", False),
        ("train/name", False),
        ("train\\name", False),
        ("train\x00name", False),
        ("tr\u00e1in", False),
        ("e\u0301", False),
        ("\uff0f", False),
        ("nul", False),
        ("lpt1", False),
    ],
)
def test_partition_name_safety_property(name: str, valid: bool) -> None:
    if not valid:
        with pytest.raises(ValueError):
            SplitJsonlOptions(train_partition_name=name)
        return
    options = SplitJsonlOptions(train_partition_name=name)
    assert options.train_path == f"data/{name}.jsonl"
    assert options.train_path != options.evaluation_path


@pytest.mark.parametrize("row_schema", SFT_ROW_SCHEMAS)
@pytest.mark.parametrize("include_provenance", [False, True])
def test_every_current_row_schema_preserves_exact_rows_and_partitions(
    tmp_path: Path,
    row_schema: str,
    include_provenance: bool,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    source = (
        ExportService()
        .verified_source(bundle, expected_manifest_sha256=EXPECTED_MANIFEST_SHA256)
        .row_set
    )
    row_set = _row_set_for_schema(source, row_schema)
    options = SplitJsonlOptions(
        train_partition_name="learn",
        evaluation_partition_name="score",
        include_provenance=include_provenance,
    )

    first = dict(split_module._rendered_files(row_set, options))
    second = dict(split_module._rendered_files(row_set, options))
    assert first == second
    assert _jsonl_objects(first[options.train_path]) == tuple(
        row.payload for row in row_set.train_rows
    )
    assert _jsonl_objects(first[options.evaluation_path]) == tuple(
        row.payload for row in row_set.evaluation_rows
    )
    card = SplitJsonlDataCard.from_json_bytes(first[SPLIT_JSONL_DATA_CARD_PATH])
    assert card.row_schema == row_schema
    assert card.train_row_count == row_set.train_row_count
    assert card.evaluation_row_count == row_set.evaluation_row_count
    assert first[SPLIT_JSONL_README_PATH].endswith(b"\n")
    assert b"trainer-neutral" in first[SPLIT_JSONL_README_PATH]
    assert b"does not select a training objective" in first[SPLIT_JSONL_README_PATH]

    plans = {
        item.path: item
        for item in split_module._file_plans(
            split_module.SPLIT_JSONL_DESCRIPTOR, row_set, options
        )
    }
    assert set(plans) == set(first)
    assert all(
        plans[path].expected_sha256 == sha256_digest(data)
        and plans[path].expected_byte_size == len(data)
        for path, data in first.items()
    )
    if include_provenance:
        assert plans[SPLIT_JSONL_PROVENANCE_PATH].membership_scope == "none"
        assert (
            plans[SPLIT_JSONL_PROVENANCE_PATH].record_count == row_set.total_row_count
        )
        _assert_full_round_trip(row_set, first)
    else:
        assert SPLIT_JSONL_PROVENANCE_PATH not in first
        assert card.provenance_path is None
        assert card.provenance_row_count is None


def test_empty_evaluation_partition_is_emitted_as_an_empty_jsonl_file(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    source = (
        ExportService()
        .verified_source(bundle, expected_manifest_sha256=EXPECTED_MANIFEST_SHA256)
        .row_set
    )
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
    options = SplitJsonlOptions()

    files = dict(split_module._rendered_files(row_set, options))
    plans = {
        item.path: item
        for item in split_module._file_plans(
            split_module.SPLIT_JSONL_DESCRIPTOR, row_set, options
        )
    }
    card = SplitJsonlDataCard.from_json_bytes(files[SPLIT_JSONL_DATA_CARD_PATH])

    assert files[options.evaluation_path] == b""
    assert plans[options.evaluation_path].record_count == 0
    assert plans[options.evaluation_path].expected_sha256 == sha256_digest(b"")
    assert card.evaluation_row_count == 0


def test_custom_provenance_export_publishes_verifies_and_detects_every_tamper(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service = ExportService()
    options = _options(train="learn", evaluation="score", provenance=True)
    plan = service.dry_run_export(_dry_v2(bundle, options))
    destination = tmp_path / "published"

    publication = service.execute_export(
        _execute_v2(bundle, destination, plan.export_plan_id, options)
    )
    assert publication.verification.export_plan_id == plan.export_plan_id
    verified = service.verify_export(
        _verify_v2(bundle, destination, plan.export_plan_id, options)
    )
    assert (
        verified.verification.export_verification_id
        == publication.verification.export_verification_id
    )

    tree = _tree_bytes(destination)
    assert set(tree) == {
        SPLIT_JSONL_README_PATH,
        "data/learn.jsonl",
        "data/score.jsonl",
        SPLIT_JSONL_DATA_CARD_PATH,
        SPLIT_JSONL_PROVENANCE_PATH,
        "export-receipt.json",
    }
    assert {
        path: (sha256_digest(data), len(data)) for path, data in tree.items()
    } == CUSTOM_EXPORT_GOLDEN
    assert tree["data/learn.jsonl"] == (bundle / "data/train.jsonl").read_bytes()
    assert tree["data/score.jsonl"] == (bundle / "data/evaluation.jsonl").read_bytes()
    assert (
        tree[SPLIT_JSONL_PROVENANCE_PATH]
        == (bundle / SPLIT_JSONL_PROVENANCE_PATH).read_bytes()
    )

    for index, relative_path in enumerate(sorted(tree)):
        changed = tmp_path / f"tampered-{index}"
        shutil.copytree(destination, changed)
        target = changed.joinpath(*relative_path.split("/"))
        target.write_bytes(target.read_bytes() + b"\n")
        with pytest.raises(ExportVerificationError):
            service.verify_export(
                _verify_v2(bundle, changed, plan.export_plan_id, options)
            )


def test_changed_execute_or_verify_options_cannot_replay_confirmed_plan(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service = ExportService()
    confirmed = _options(train="learn", evaluation="score", provenance=True)
    changed = _options(train="train", evaluation="evaluation", provenance=False)
    plan = service.dry_run_export(_dry_v2(bundle, confirmed))

    with pytest.raises(ExportVerificationError, match="operator-confirmed dry run"):
        service.execute_export(
            _execute_v2(
                bundle, tmp_path / "must-not-exist", plan.export_plan_id, changed
            )
        )
    assert not (tmp_path / "must-not-exist").exists()

    with pytest.raises(ExportVerificationError, match="operator-confirmed dry run"):
        service.verify_export(
            _verify_v2(
                bundle, tmp_path / "also-must-not-exist", plan.export_plan_id, changed
            )
        )
    assert not (tmp_path / "also-must-not-exist").exists()


@pytest.mark.parametrize("mutation", ["missing", "unexpected"])
def test_split_jsonl_verification_rejects_closed_tree_mutations(
    tmp_path: Path,
    mutation: str,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service = ExportService()
    options = _options()
    plan = service.dry_run_export(_dry_v2(bundle, options))
    destination = tmp_path / "published"
    service.execute_export(
        _execute_v2(bundle, destination, plan.export_plan_id, options)
    )

    if mutation == "missing":
        (destination / SPLIT_JSONL_README_PATH).unlink()
    else:
        (destination / "unexpected.json").write_bytes(b"{}")

    with pytest.raises(ExportVerificationError):
        service.verify_export(
            _verify_v2(bundle, destination, plan.export_plan_id, options)
        )


def test_service_refuses_wrong_operation_and_request_subclasses(tmp_path: Path) -> None:
    bundle = _materialize_bundle(tmp_path)
    service = ExportService()
    options = _options()
    plan = service.dry_run_export(_dry_v2(bundle, options))
    execute = _execute_v2(
        bundle, tmp_path / "destination", plan.export_plan_id, options
    )

    with pytest.raises(ExportContractError):
        service.dry_run_export(execute)  # type: ignore[arg-type]

    class DerivedDryRunRequest(ExportDryRunRequestV2):
        pass

    derived = DerivedDryRunRequest.model_validate(
        _dry_v2(bundle, options).model_dump(mode="json")
    )
    with pytest.raises(ExportContractError):
        service.dry_run_export(derived)


def test_data_card_contract_is_strict_frozen_and_canonical(tmp_path: Path) -> None:
    bundle = _materialize_bundle(tmp_path)
    source = (
        ExportService()
        .verified_source(bundle, expected_manifest_sha256=EXPECTED_MANIFEST_SHA256)
        .row_set
    )
    files = dict(
        split_module._rendered_files(
            source,
            SplitJsonlOptions(include_provenance=True),
        )
    )
    data = files[SPLIT_JSONL_DATA_CARD_PATH]
    card = SplitJsonlDataCard.from_json_bytes(data)

    assert set(SplitJsonlDataCard.model_fields) == {
        "schema_version",
        "container_id",
        "container_version",
        "row_schema",
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
    assert card.canonical_bytes() == data
    with pytest.raises(ExportVerificationError):
        SplitJsonlDataCard.from_json_bytes(data + b"\n")
    changed = card.model_dump(mode="json")
    changed["unexpected"] = True
    with pytest.raises(ExportVerificationError):
        SplitJsonlDataCard.from_json_bytes(lossless_json_bytes(changed))
    with pytest.raises(Exception):
        card.train_path = "data/changed.jsonl"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("train_path", "data/nested/train.jsonl"),
        ("evaluation_path", "data/Evaluation.jsonl"),
        ("loss_policy", "completion-only"),
    ],
)
def test_data_card_rejects_noncanonical_layout_bindings(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    source = (
        ExportService()
        .verified_source(bundle, expected_manifest_sha256=EXPECTED_MANIFEST_SHA256)
        .row_set
    )
    files = dict(
        split_module._rendered_files(
            source,
            SplitJsonlOptions(include_provenance=True),
        )
    )
    card = SplitJsonlDataCard.from_json_bytes(files[SPLIT_JSONL_DATA_CARD_PATH])
    changed = card.model_dump(mode="json")
    changed[field] = value

    with pytest.raises(ExportVerificationError):
        SplitJsonlDataCard.from_json_bytes(lossless_json_bytes(changed))
