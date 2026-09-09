"""Phase 5.5 consolidated semantic import-round-trip fixtures."""

from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from veriformis.contracts import V1_ROW_SCHEMA_KINDS
from veriformis.datasets import (
    RowSet,
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
)
from veriformis.exports.constrained_csv import (
    CONSTRAINED_CSV_DATA_CARD_PATH,
    ConstrainedCsvDataCard,
)
from veriformis.exports.split_jsonl import (
    SPLIT_JSONL_DATA_CARD_PATH,
    SplitJsonlDataCard,
    SplitJsonlOptions,
)
from veriformis.identity import derive_id, lossless_json_bytes, sha256_digest

from support.export_round_trip import (
    REPOSITORY_ROOT,
    ROUND_TRIP_FIXTURE,
    ROUND_TRIP_FIXTURE_SHA256,
    SUCCESSFUL_PAIRS,
    _reload_export,
    _row_set_for_schema,
    _strict_fixture_object,
    _strict_json_object,
)

pytestmark = pytest.mark.matrix


ROW_SCHEMAS = (
    "instruction_output",
    "messages",
    "prompt_completion",
    "text",
)
CONTAINERS = ("constrained-csv", "json", "split-jsonl-directory")


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
