"""Row-mapping contracts: exact fields, identity replay, closed refusals."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.contracts import (
    MAPPING_CONTRACT_ID,
    MAPPING_CONTRACT_VERSION,
    MAPPING_DISCOVERY_SCHEMA_ID,
)
from veriformis.errors import MappingError, RowSourceError
from veriformis.identity import derive_id, sha256_digest
from veriformis.mapping import (
    FieldMapping,
    ImportedField,
    ImportedRecord,
    MappedValueEvidence,
    MappingPlan,
    RowSource,
    mapping_contract_discovery,
    mapping_contract_discovery_json,
)
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService

DATA_PATH = (
    Path(__file__).parents[2] / "src" / "veriformis" / "mapping" / "contracts-v1.json"
)
RUNNER = CliRunner()
SERVICE = PipelineService()
CONFIRM = sha256_digest("phase7-02-confirmation")


def _text_plan() -> MappingPlan:
    return MappingPlan.create(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        container_kind="jsonl",
        confirmation_digest=CONFIRM,
        field_mappings=[
            FieldMapping.create(source_path="text", target_key="text"),
        ],
    )


def test_contract_discovery_is_canonical_and_shared() -> None:
    stored = DATA_PATH.read_text(encoding="utf-8")
    payload = json.loads(stored)
    canonical = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    assert stored == canonical
    assert payload["schema_id"] == MAPPING_DISCOVERY_SCHEMA_ID
    assert payload["contract_id"] == MAPPING_CONTRACT_ID
    assert payload["contract_version"] == MAPPING_CONTRACT_VERSION
    expected = mapping_contract_discovery_json().rstrip("\n")
    python = json.dumps(
        mapping_contract_discovery(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    cli = RUNNER.invoke(app, ["mapping-contracts"])
    assert cli.exit_code == 0, cli.output
    tools = {
        tool.name: tool.fn
        for tool in create_mcp_server(SERVICE)._tool_manager.list_tools()
    }
    mcp = tools["mapping_contracts"]()
    assert python == expected
    assert cli.output.strip() == expected
    assert mcp.strip() == expected
    assert SERVICE.discover_mapping_contracts() == json.loads(expected)


def test_row_source_and_mapping_plan_round_trip() -> None:
    source = RowSource.create(
        logical_path="rows.jsonl",
        sha256=sha256_digest('{"text":"café"}\n'),
        size=16,
        record_count=1,
        container_kind="jsonl",
    )
    plan = _text_plan()
    reloaded = MappingPlan.model_validate(plan.model_dump(mode="json"))
    assert reloaded.mapping_plan_id == plan.mapping_plan_id
    assert source.container_kind == "jsonl"
    evidence = MappedValueEvidence.create(
        source_id=derive_id("src", {"logical_path": "rows.jsonl"}),
        row_index=1,
        field_path="text",
        original_value_sha256=sha256_digest("café"),
        mapping_rule_id=plan.field_mappings[0].mapping_rule_id,
        output_sha256=sha256_digest("café"),
    )
    record = ImportedRecord.create(
        source_id=evidence.source_id,
        row_index=1,
        mapping_plan_id=plan.mapping_plan_id,
        goal_id="learn-the-text",
        recipe_id=derive_id("rcp", {"recipe": "imported"}),
        objective_id=derive_id("obj", {"kind": "full_text"}),
        fields=[ImportedField(name="text", value="café", evidence=evidence)],
    )
    assert ImportedRecord.model_validate(record.model_dump(mode="json")) == record


def test_unknown_and_missing_fields_fail_closed() -> None:
    plan = _text_plan()
    payload = plan.model_dump(mode="json")
    with pytest.raises(MappingError, match="extra"):
        MappingPlan.model_validate({**payload, "unexpected": True})
    payload.pop("goal_id")
    with pytest.raises(MappingError, match="missing"):
        MappingPlan.model_validate(payload)


def test_identity_mismatch_fails_closed() -> None:
    plan = _text_plan()
    payload = plan.model_dump(mode="json")
    payload["mapping_plan_id"] = derive_id("mpl", {"tampered": True})
    with pytest.raises(MappingError, match="identity mismatch"):
        MappingPlan.model_validate(payload)


@pytest.mark.parametrize("container", ["json", "csv", "parquet", "arrow"])
def test_json_csv_parquet_and_arrow_containers_are_admitted(container: str) -> None:
    plan = MappingPlan.create(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        container_kind=container,
        confirmation_digest=CONFIRM,
        field_mappings=[
            FieldMapping.create(source_path="text", target_key="text"),
        ],
    )
    assert plan.container_kind == container


def test_csv_messages_plan_is_refused() -> None:
    with pytest.raises(MappingError, match="split-jsonl-directory or json"):
        MappingPlan.create(
            goal_id="continue-a-passage",
            representation_id="conversation",
            row_schema="messages",
            container_kind="csv",
            confirmation_digest=CONFIRM,
            field_mappings=[
                FieldMapping.create(source_path="messages", target_key="messages"),
            ],
        )


def test_row_source_rejects_empty_and_identity_drift() -> None:
    with pytest.raises(RowSourceError):
        RowSource.create(
            logical_path="rows.jsonl",
            sha256=sha256_digest(b"{}"),
            size=2,
            record_count=0,
            container_kind="jsonl",
        )
    source = RowSource.create(
        logical_path="rows.jsonl",
        sha256=sha256_digest(b"{}"),
        size=2,
        record_count=1,
        container_kind="jsonl",
    )
    payload = source.model_dump(mode="json")
    payload["row_source_id"] = derive_id("rws", {"tampered": True})
    with pytest.raises(RowSourceError, match="identity mismatch"):
        RowSource.model_validate(payload)
