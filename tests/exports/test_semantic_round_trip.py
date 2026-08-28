"""Phase 5.5 consolidated semantic import-round-trip fixtures."""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from veriformis.contracts import V1_ROW_SCHEMA_KINDS
from veriformis.datasets import (
    ProductRow,
    RowProvenance,
    RowSet,
    row_provenance_from_json_bytes,
)
from veriformis.errors import ExportContractError, ExportVerificationError
from veriformis.exports import (
    EXPORT_SURFACE_REQUEST_SCHEMA,
    ExportExecuteRequest,
    ExportService,
)
from veriformis.exports import canonical_json as json_module
from veriformis.exports import constrained_csv as csv_module
from veriformis.exports import service as service_module
from veriformis.exports import split_jsonl as split_module
from veriformis.exports.canonical_json import (
    CANONICAL_JSON_DATASET_PATH,
    CANONICAL_JSON_PROVENANCE_PATH,
    CanonicalJsonDataset,
    CanonicalJsonProvenance,
)
from veriformis.exports.constrained_csv import (
    CONSTRAINED_CSV_DATA_CARD_PATH,
    ConstrainedCsvDataCard,
    ConstrainedCsvPartition,
)
from veriformis.exports.split_jsonl import (
    SPLIT_JSONL_DATA_CARD_PATH,
    SplitJsonlDataCard,
    SplitJsonlOptions,
)
from veriformis.identity import derive_id, lossless_json_bytes, sha256_digest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ROUND_TRIP_FIXTURE = (
    REPOSITORY_ROOT
    / "tests"
    / "regressions"
    / "fixtures"
    / "phase5"
    / "generic-export-semantic-round-trip.json"
)
ROUND_TRIP_FIXTURE_SHA256 = (
    "ec22a171ee96b7a99a1d1c6e1c2a6db082d93603dd8c90e59684382c020fa371"
)
ROW_SCHEMAS = (
    "instruction_output",
    "messages",
    "prompt_completion",
    "text",
)
CONTAINERS = ("constrained-csv", "json", "split-jsonl-directory")
SUCCESSFUL_PAIRS = (
    ("constrained-csv", "instruction_output"),
    ("constrained-csv", "prompt_completion"),
    ("constrained-csv", "text"),
    ("json", "instruction_output"),
    ("json", "messages"),
    ("json", "prompt_completion"),
    ("json", "text"),
    ("split-jsonl-directory", "instruction_output"),
    ("split-jsonl-directory", "messages"),
    ("split-jsonl-directory", "prompt_completion"),
    ("split-jsonl-directory", "text"),
)


@dataclass(frozen=True, slots=True)
class _ReloadedRows:
    row_schema: str
    train_payloads: tuple[dict[str, Any], ...]
    evaluation_payloads: tuple[dict[str, Any], ...]
    provenance: tuple[RowProvenance, ...]
    row_set: RowSet


def _strict_fixture_object(data: bytes) -> dict[str, Any]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate fixture key {key!r}")
            result[key] = value
        return result

    value = json.loads(data.decode("utf-8"), object_pairs_hook=unique_object)
    if type(value) is not dict:
        raise ValueError("semantic round-trip fixture must be one object")
    return value


@pytest.fixture(scope="module")
def round_trip_fixture() -> dict[str, Any]:
    data = ROUND_TRIP_FIXTURE.read_bytes()
    assert sha256_digest(data) == ROUND_TRIP_FIXTURE_SHA256
    fixture = _strict_fixture_object(data)
    assert set(fixture) == {
        "compatible_row_schemas",
        "fixture_version",
        "partitions",
        "schema_version",
        "source_fixture",
        "source_manifest_sha256",
    }
    assert fixture["fixture_version"] == 1
    assert fixture["schema_version"] == (
        "veriformis.phase5-generic-export-semantic-round-trip/v1"
    )
    assert set(fixture["partitions"]) == set(ROW_SCHEMAS)
    for row_schema in ROW_SCHEMAS:
        partitions = fixture["partitions"][row_schema]
        assert set(partitions) == {"evaluation", "train"}
        assert len(partitions["train"]) == 1
        assert len(partitions["evaluation"]) == 2
    return fixture


def _materialize_source_bundle(root: Path, fixture: Mapping[str, Any]) -> Path:
    source_path = REPOSITORY_ROOT.joinpath(*fixture["source_fixture"].split("/"))
    source = _strict_fixture_object(source_path.read_bytes())
    bundle = root / "source.vfbundle"
    for relative_path, encoded in sorted(source["files_base64"].items()):
        data = base64.b64decode(encoded, validate=True)
        assert sha256_digest(data) == source["file_sha256"][relative_path]
        target = bundle.joinpath(*relative_path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return bundle


@pytest.fixture(scope="module")
def verified_source(
    tmp_path_factory: pytest.TempPathFactory,
    round_trip_fixture: dict[str, Any],
) -> tuple[Path, RowSet]:
    root = tmp_path_factory.mktemp("phase5-semantic-round-trip")
    bundle = _materialize_source_bundle(root, round_trip_fixture)
    expected_digest = round_trip_fixture["source_manifest_sha256"]
    source = ExportService().verified_source(
        bundle,
        expected_manifest_sha256=expected_digest,
    )
    return bundle, source.row_set


def _row_set_for_schema(
    source: RowSet,
    fixture: Mapping[str, Any],
    row_schema: str,
) -> RowSet:
    payload_partitions = fixture["partitions"][row_schema]
    train_payloads = tuple(payload_partitions["train"])
    evaluation_payloads = tuple(payload_partitions["evaluation"])
    assert len(train_payloads) == source.train_row_count
    assert len(evaluation_payloads) == source.evaluation_row_count

    source_rows = (*source.train_rows, *source.evaluation_rows)
    payloads = (*train_payloads, *evaluation_payloads)
    converted = tuple(
        ProductRow.create(
            record_id=row.record_id,
            row_schema=row_schema,  # type: ignore[arg-type]
            payload=payload,
        )
        for row, payload in zip(source_rows, payloads, strict=True)
    )
    converted_by_record = {row.record_id: row for row in converted}
    provenance: list[RowProvenance] = []
    for item in source.provenance:
        row = converted_by_record[item.record_id]
        body = item.model_dump(mode="json", exclude={"provenance_id"})
        body.update(row_id=row.row_id, payload_sha256=row.payload_sha256)
        provenance.append(
            row_provenance_from_json_bytes(
                lossless_json_bytes({"provenance_id": derive_id("prv", body), **body})
            )
        )
    return RowSet.create(
        plan_id=source.plan_id,
        serialization_plan_id=source.serialization_plan_id,
        recipe_id=source.recipe_id,
        construction_result_id=source.construction_result_id,
        curation_result_id=source.curation_result_id,
        split_result_id=source.split_result_id,
        row_schema=row_schema,  # type: ignore[arg-type]
        train_rows=converted[: source.train_row_count],
        evaluation_rows=converted[source.train_row_count :],
        provenance=provenance,
    )


def _rendered_files(
    container_id: str,
    row_set: RowSet,
) -> tuple[tuple[str, bytes], ...]:
    if container_id == "split-jsonl-directory":
        return split_module._rendered_files(row_set, SplitJsonlOptions())
    if container_id == "json":
        return json_module._rendered_files(row_set)
    if container_id == "constrained-csv":
        return csv_module._rendered_files(row_set)
    raise AssertionError(f"unmapped semantic fixture container {container_id!r}")


def _materialize_export(
    root: Path,
    files: Sequence[tuple[str, bytes]],
) -> None:
    assert not root.exists()
    for relative_path, data in files:
        target = root.joinpath(*relative_path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def _strict_json_object(data: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = _strict_fixture_object(data)
        canonical = lossless_json_bytes(value)
    except (RecursionError, TypeError, UnicodeError, ValueError) as exc:
        raise ExportVerificationError(f"invalid {label}: {exc}") from exc
    if canonical != data:
        raise ExportVerificationError(f"{label} bytes are not canonical")
    return value


def _strict_payload_jsonl(
    data: bytes,
    *,
    row_schema: str,
    label: str,
) -> tuple[dict[str, Any], ...]:
    if data == b"":
        return ()
    if data.startswith(b"\xef\xbb\xbf") or not data.endswith(b"\n"):
        raise ExportVerificationError(f"{label} is not canonical JSONL")
    lines = data.split(b"\n")
    if lines[-1] != b"" or any(not line for line in lines[:-1]):
        raise ExportVerificationError(f"{label} is not canonical JSONL")

    payloads: list[dict[str, Any]] = []
    for ordinal, line in enumerate(lines[:-1]):
        payload = _strict_json_object(line, label=f"{label} row {ordinal}")
        try:
            ProductRow.create(
                record_id=derive_id(
                    "rec",
                    {"label": label, "ordinal": ordinal},
                ),
                row_schema=row_schema,  # type: ignore[arg-type]
                payload=payload,
            )
        except (TypeError, UnicodeError, ValueError) as exc:
            raise ExportVerificationError(
                f"{label} row {ordinal} violates {row_schema!r}: {exc}"
            ) from exc
        payloads.append(payload)
    return tuple(payloads)


def _strict_provenance_jsonl(
    data: bytes,
    *,
    label: str,
) -> tuple[RowProvenance, ...]:
    if not data or not data.endswith(b"\n"):
        raise ExportVerificationError(f"{label} is not canonical JSONL")
    lines = data.split(b"\n")
    if lines[-1] != b"" or any(not line for line in lines[:-1]):
        raise ExportVerificationError(f"{label} is not canonical JSONL")
    rows: list[RowProvenance] = []
    for ordinal, line in enumerate(lines[:-1]):
        _strict_json_object(line, label=f"{label} row {ordinal}")
        try:
            rows.append(row_provenance_from_json_bytes(line))
        except (TypeError, UnicodeError, ValueError) as exc:
            raise ExportVerificationError(
                f"invalid {label} row {ordinal}: {exc}"
            ) from exc
    canonical = b"".join(
        lossless_json_bytes(item.model_dump(mode="json")) + b"\n" for item in rows
    )
    if canonical != data:
        raise ExportVerificationError(f"{label} bytes are not canonical")
    return tuple(rows)


def _rebuild_row_set(
    *,
    row_schema: str,
    train_payloads: tuple[dict[str, Any], ...],
    evaluation_payloads: tuple[dict[str, Any], ...],
    provenance: tuple[RowProvenance, ...],
    expected_row_set_id: str,
    expected_split_result_id: str,
    expected_objective_id: str,
) -> RowSet:
    try:
        if not provenance:
            raise ValueError("semantic reload requires aligned provenance")
        if {item.objective_id for item in provenance} != {expected_objective_id}:
            raise ValueError("semantic reload objective differs from its metadata")
        payloads = (*train_payloads, *evaluation_payloads)
        rows = tuple(
            ProductRow.create(
                record_id=item.record_id,
                row_schema=row_schema,  # type: ignore[arg-type]
                payload=payload,
            )
            for payload, item in zip(payloads, provenance, strict=True)
        )
        first = provenance[0]
        rebuilt = RowSet.create(
            plan_id=first.plan_id,
            serialization_plan_id=first.serialization_plan_id,
            recipe_id=first.recipe_id,
            construction_result_id=first.construction_result_id,
            curation_result_id=first.curation_result_id,
            split_result_id=expected_split_result_id,
            row_schema=row_schema,  # type: ignore[arg-type]
            train_rows=rows[: len(train_payloads)],
            evaluation_rows=rows[len(train_payloads) :],
            provenance=provenance,
        )
    except (RecursionError, TypeError, UnicodeError, ValueError) as exc:
        raise ExportVerificationError(
            f"semantic rows do not reconstruct one source row set: {exc}"
        ) from exc
    if rebuilt.row_set_id != expected_row_set_id:
        raise ExportVerificationError(
            "semantic reload row-set identity differs from its metadata"
        )
    return rebuilt


def _reload_split_jsonl(root: Path) -> _ReloadedRows:
    card = SplitJsonlDataCard.from_json_bytes(
        (root / SPLIT_JSONL_DATA_CARD_PATH).read_bytes()
    )
    if card.provenance_path is None:
        raise ExportVerificationError(
            "semantic round-trip fixture requires split JSONL provenance"
        )
    train = _strict_payload_jsonl(
        root.joinpath(*card.train_path.split("/")).read_bytes(),
        row_schema=card.row_schema,
        label="split JSONL train partition",
    )
    evaluation = _strict_payload_jsonl(
        root.joinpath(*card.evaluation_path.split("/")).read_bytes(),
        row_schema=card.row_schema,
        label="split JSONL evaluation partition",
    )
    provenance = _strict_provenance_jsonl(
        root.joinpath(*card.provenance_path.split("/")).read_bytes(),
        label="split JSONL provenance",
    )
    if (
        len(train) != card.train_row_count
        or len(evaluation) != card.evaluation_row_count
        or len(provenance) != card.provenance_row_count
    ):
        raise ExportVerificationError(
            "split JSONL semantic reload counts differ from its data card"
        )
    rebuilt = _rebuild_row_set(
        row_schema=card.row_schema,
        train_payloads=train,
        evaluation_payloads=evaluation,
        provenance=provenance,
        expected_row_set_id=card.row_set_id,
        expected_split_result_id=card.split_result_id,
        expected_objective_id=card.objective_id,
    )
    return _ReloadedRows(
        row_schema=card.row_schema,
        train_payloads=train,
        evaluation_payloads=evaluation,
        provenance=provenance,
        row_set=rebuilt,
    )


def _reload_canonical_json(root: Path) -> _ReloadedRows:
    dataset = CanonicalJsonDataset.from_json_bytes(
        (root / CANONICAL_JSON_DATASET_PATH).read_bytes()
    )
    provenance_document = CanonicalJsonProvenance.from_json_bytes(
        (root / CANONICAL_JSON_PROVENANCE_PATH).read_bytes()
    )
    dataset.validate_provenance(provenance_document)
    train = tuple(dataset.splits.train)
    evaluation = tuple(dataset.splits.evaluation)
    provenance = provenance_document.rows
    rebuilt = _rebuild_row_set(
        row_schema=dataset.row_schema,
        train_payloads=train,
        evaluation_payloads=evaluation,
        provenance=provenance,
        expected_row_set_id=dataset.row_set_id,
        expected_split_result_id=dataset.split_result_id,
        expected_objective_id=dataset.objective_id,
    )
    return _ReloadedRows(
        row_schema=dataset.row_schema,
        train_payloads=train,
        evaluation_payloads=evaluation,
        provenance=provenance,
        row_set=rebuilt,
    )


def _reload_constrained_csv(root: Path) -> _ReloadedRows:
    card = ConstrainedCsvDataCard.from_json_bytes(
        (root / CONSTRAINED_CSV_DATA_CARD_PATH).read_bytes()
    )
    train = ConstrainedCsvPartition.from_csv_bytes(
        root.joinpath(*card.train_path.split("/")).read_bytes(),
        row_schema=card.row_schema,
    )
    evaluation = ConstrainedCsvPartition.from_csv_bytes(
        root.joinpath(*card.evaluation_path.split("/")).read_bytes(),
        row_schema=card.row_schema,
    )
    provenance = _strict_provenance_jsonl(
        root.joinpath(*card.provenance_path.split("/")).read_bytes(),
        label="constrained CSV provenance",
    )
    rebuilt = card.validate_row_set(
        train=train,
        evaluation=evaluation,
        provenance=provenance,
    )
    return _ReloadedRows(
        row_schema=card.row_schema,
        train_payloads=train.payloads,
        evaluation_payloads=evaluation.payloads,
        provenance=provenance,
        row_set=rebuilt,
    )


def _reload_export(container_id: str, root: Path) -> _ReloadedRows:
    if container_id == "split-jsonl-directory":
        return _reload_split_jsonl(root)
    if container_id == "json":
        return _reload_canonical_json(root)
    if container_id == "constrained-csv":
        return _reload_constrained_csv(root)
    raise AssertionError(f"unmapped semantic fixture container {container_id!r}")


def test_fixture_closes_the_discovered_container_schema_matrix(
    round_trip_fixture: dict[str, Any],
) -> None:
    assert set(ROW_SCHEMAS) == set(V1_ROW_SCHEMA_KINDS)
    expected = {
        (container_id, 1, None, None): tuple(row_schemas)
        for container_id, row_schemas in round_trip_fixture[
            "compatible_row_schemas"
        ].items()
    }
    discovery = ExportService().discover_exports()
    observed = {
        profile.selector: profile.supported_row_schemas
        for profile in discovery.profiles
        if profile.consumer_profile is None and profile.selector[0] in CONTAINERS
    }
    assert len(observed) == len(expected)
    assert expected == observed
    assert {selector[0] for selector in expected} == set(CONTAINERS)
    observed_pairs = {
        (selector[0], row_schema)
        for selector, row_schemas in observed.items()
        for row_schema in row_schemas
    }
    assert set(SUCCESSFUL_PAIRS) <= observed_pairs
    all_pairs = {
        (container_id, row_schema)
        for container_id in CONTAINERS
        for row_schema in ROW_SCHEMAS
    }
    assert all_pairs - observed_pairs == {("constrained-csv", "messages")}
    assert ("constrained-csv", "label-classification") not in observed_pairs
    assert ("constrained-csv", "preference-pair") not in observed_pairs
    assert ("constrained-csv", "tool-call-conversation") not in observed_pairs
    assert ("constrained-csv", "stepwise-trace") not in observed_pairs


@pytest.mark.parametrize(("container_id", "row_schema"), SUCCESSFUL_PAIRS)
def test_every_compatible_container_schema_pair_round_trips_from_ordinary_files(
    tmp_path: Path,
    round_trip_fixture: dict[str, Any],
    verified_source: tuple[Path, RowSet],
    container_id: str,
    row_schema: str,
) -> None:
    _, source_row_set = verified_source
    expected = _row_set_for_schema(
        source_row_set,
        round_trip_fixture,
        row_schema,
    )
    destination = tmp_path / f"{container_id}-{row_schema}"
    _materialize_export(destination, _rendered_files(container_id, expected))

    reloaded = _reload_export(container_id, destination)

    assert reloaded.row_schema == row_schema
    assert reloaded.train_payloads == tuple(row.payload for row in expected.train_rows)
    assert reloaded.evaluation_payloads == tuple(
        row.payload for row in expected.evaluation_rows
    )
    assert reloaded.provenance == expected.provenance
    assert reloaded.row_set == expected
    assert reloaded.row_set.row_set_id == expected.row_set_id
    assert tuple(item.partition for item in reloaded.provenance) == (
        "train",
        "evaluation",
        "evaluation",
    )
    assert tuple(item.ordinal for item in reloaded.provenance) == (0, 0, 1)


def test_constrained_csv_messages_refusal_is_actionable_before_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    round_trip_fixture: dict[str, Any],
    verified_source: tuple[Path, RowSet],
) -> None:
    bundle, source_row_set = verified_source
    messages = _row_set_for_schema(
        source_row_set,
        round_trip_fixture,
        "messages",
    )
    destination = tmp_path / "must-not-be-created"
    service = ExportService()
    monkeypatch.setattr(service, "verified_source", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        service_module,
        "_source_plan_evidence",
        lambda _source: (
            None,
            messages,
            None,
            messages.provenance[0].objective_id,
            None,
        ),
    )
    request = ExportExecuteRequest(
        schema_version=EXPORT_SURFACE_REQUEST_SCHEMA,
        operation="execute",
        bundle=str(bundle),
        container_id="constrained-csv",
        container_version=1,
        consumer_id=None,
        consumer_profile_version=None,
        source_trust_policy="require_external_digest",
        expected_manifest_sha256=round_trip_fixture["source_manifest_sha256"],
        overwrite_policy="refuse",
        destination_root=str(destination),
        expected_export_plan_id=derive_id(
            "export-plan",
            {"unsupported": "messages"},
        ),
    )

    with pytest.raises(ExportContractError) as error:
        service.execute_export(request)

    message = str(error.value)
    assert "constrained-csv" in message
    assert "messages" in message
    assert "split-jsonl-directory v1" in message
    assert "json v1" in message
    assert not destination.exists()


def _tamper_train_semantics(container_id: str, root: Path) -> None:
    changed = "changed semantic payload"
    if container_id == "split-jsonl-directory":
        card = SplitJsonlDataCard.from_json_bytes(
            (root / SPLIT_JSONL_DATA_CARD_PATH).read_bytes()
        )
        root.joinpath(*card.train_path.split("/")).write_bytes(
            lossless_json_bytes({"text": changed}) + b"\n"
        )
        return
    if container_id == "json":
        path = root / CANONICAL_JSON_DATASET_PATH
        dataset = _strict_json_object(path.read_bytes(), label="canonical JSON")
        dataset["splits"]["train"][0]["text"] = changed
        path.write_bytes(lossless_json_bytes(dataset))
        return
    if container_id == "constrained-csv":
        card = ConstrainedCsvDataCard.from_json_bytes(
            (root / CONSTRAINED_CSV_DATA_CARD_PATH).read_bytes()
        )
        root.joinpath(*card.train_path.split("/")).write_bytes(
            csv_module._payloads_csv_bytes("text", ({"text": changed},))
        )
        return
    raise AssertionError(f"unmapped semantic fixture container {container_id!r}")


@pytest.mark.parametrize("container_id", CONTAINERS)
def test_semantic_tamper_with_canonical_bytes_fails_row_set_reconstruction(
    tmp_path: Path,
    round_trip_fixture: dict[str, Any],
    verified_source: tuple[Path, RowSet],
    container_id: str,
) -> None:
    _, source_row_set = verified_source
    expected = _row_set_for_schema(
        source_row_set,
        round_trip_fixture,
        "text",
    )
    destination = tmp_path / container_id
    _materialize_export(destination, _rendered_files(container_id, expected))
    _tamper_train_semantics(container_id, destination)

    with pytest.raises(ExportVerificationError):
        _reload_export(container_id, destination)
