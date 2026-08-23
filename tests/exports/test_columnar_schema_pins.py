"""Phase 9.2: packaged Arrow and Hugging Face feature schema pins."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.contracts import (
    COLUMNAR_SCHEMA_CONTRACT_ID,
    COLUMNAR_SCHEMA_CONTRACT_VERSION,
    COLUMNAR_SCHEMA_SCHEMA_ID,
    V1_ROW_SCHEMA_KINDS,
)
from veriformis.exports.columnar_schemas import (
    COLUMNAR_SCHEMA_DATA_NAME,
    MESSAGE_ROLES,
    MESSAGE_STRUCT_FIELDS,
    PAYLOAD_FIELDS,
    ColumnarSchemaCatalog,
    columnar_schema_catalog,
    columnar_schema_catalog_json,
    discover_columnar_schemas,
)
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.taxonomy import (
    PLANNED_PHYSICAL_CONTAINERS,
    UNEXECUTABLE_PHYSICAL_CONTAINER_ITEMS,
)

DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "veriformis"
    / "exports"
    / COLUMNAR_SCHEMA_DATA_NAME
)
ROOT = Path(__file__).resolve().parents[2]
RUNNER = CliRunner()
SERVICE = PipelineService()


def test_columnar_schema_contract_constants_are_exact() -> None:
    assert COLUMNAR_SCHEMA_CONTRACT_ID == "veriformis.columnar-schema-pin"
    assert COLUMNAR_SCHEMA_CONTRACT_VERSION == 1
    assert COLUMNAR_SCHEMA_SCHEMA_ID == "veriformis.columnar-schema-discovery/v1"
    assert COLUMNAR_SCHEMA_DATA_NAME == "columnar_schemas-v1.json"


def test_packaged_catalog_is_canonical_and_shared() -> None:
    stored = DATA_PATH.read_text(encoding="utf-8")
    payload = json.loads(stored)
    canonical = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    assert stored == canonical
    assert payload["schema_id"] == COLUMNAR_SCHEMA_SCHEMA_ID
    assert payload["contract_id"] == COLUMNAR_SCHEMA_CONTRACT_ID
    assert payload["contract_version"] == COLUMNAR_SCHEMA_CONTRACT_VERSION
    expected = columnar_schema_catalog_json()
    python = json.dumps(
        discover_columnar_schemas(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    cli = RUNNER.invoke(app, ["columnar-schemas"])
    assert cli.exit_code == 0, cli.output
    tools = {
        tool.name: tool.fn
        for tool in create_mcp_server(SERVICE)._tool_manager.list_tools()
    }
    mcp = tools["columnar_schemas"]()
    assert python + "\n" == expected
    assert cli.output == expected
    assert mcp == expected
    assert SERVICE.discover_columnar_schemas() == json.loads(expected)
    first = SERVICE.discover_columnar_schemas()
    second = SERVICE.discover_columnar_schemas()
    assert first == second and first is not second


def test_catalog_closes_over_every_row_schema_and_planned_container() -> None:
    catalog = columnar_schema_catalog()
    assert isinstance(catalog, ColumnarSchemaCatalog)
    assert catalog.state == "planned"
    assert catalog.round_trip is False
    assert catalog.extra == "columnar"
    assert catalog.null_policy == "unrepresentable"
    assert tuple(item.source_row_schema for item in catalog.row_schemas) == tuple(
        sorted(V1_ROW_SCHEMA_KINDS)
    )
    assert tuple(item.package for item in catalog.packages) == ("datasets", "pyarrow")
    assert tuple(item.container_id for item in catalog.planned_containers) == tuple(
        sorted(PLANNED_PHYSICAL_CONTAINERS)
    )
    for pin in catalog.planned_containers:
        assert pin.executable_item == UNEXECUTABLE_PHYSICAL_CONTAINER_ITEMS[pin.container_id]
    by_schema = {item.source_row_schema: item for item in catalog.row_schemas}
    for schema, columns in PAYLOAD_FIELDS.items():
        assert tuple(field.name for field in by_schema[schema].fields) == columns
        for field in by_schema[schema].fields:
            assert field.nullable is False


def test_package_pins_match_reviewed_docs_and_stay_out_of_the_lock() -> None:
    by_package = {item.package: item for item in columnar_schema_catalog().packages}
    datasets = by_package["datasets"]
    assert datasets.version_range == ">=3.0.0,<6.0.0"
    assert datasets.license == "Apache-2.0"
    assert datasets.primary_docs_url == (
        "https://huggingface.co/docs/datasets/en/about_dataset_features"
    )
    assert datasets.docs_reviewed_on == "2026-08-23"
    assert datasets.role == "hugging-face-dataset"
    pyarrow = by_package["pyarrow"]
    assert pyarrow.version_range == ">=19.0.0,<26.0.0"
    assert pyarrow.license == "Apache-2.0"
    assert pyarrow.primary_docs_url == (
        "https://arrow.apache.org/docs/python/api/datatypes.html"
    )
    assert pyarrow.docs_reviewed_on == "2026-08-23"
    assert pyarrow.role == "parquet-and-arrow-ipc"
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert 'name = "pyarrow"\n' not in lock
    assert 'name = "datasets"\n' not in lock
    toml = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "columnar = []" in toml


def test_messages_pin_is_nested_role_then_content() -> None:
    pin = next(
        item
        for item in columnar_schema_catalog().row_schemas
        if item.source_row_schema == "messages"
    )
    assert pin.message_roles == MESSAGE_ROLES
    assert pin.message_turn_count == 2
    messages = pin.fields[0]
    assert messages.arrow_type.kind == "list"
    assert messages.arrow_type.item_nullable is False
    assert messages.arrow_type.item is not None
    assert messages.arrow_type.item.kind == "struct"
    assert messages.arrow_type.item.fields is not None
    nested = tuple(field.name for field in messages.arrow_type.item.fields)
    assert nested == MESSAGE_STRUCT_FIELDS
    for field in messages.arrow_type.item.fields:
        assert field.nullable is False
        assert field.arrow_type.kind == "utf8"
    assert messages.hf_feature.kind == "list"
    assert messages.hf_feature.item is not None
    assert messages.hf_feature.item.kind == "struct"


def test_catalog_refuses_round_trip_claims_and_unknown_fields() -> None:
    payload = json.loads(columnar_schema_catalog_json())
    payload["round_trip"] = True
    with pytest.raises(Exception):
        ColumnarSchemaCatalog.model_validate(payload)
    payload = json.loads(columnar_schema_catalog_json())
    payload["state"] = "implemented"
    with pytest.raises(Exception):
        ColumnarSchemaCatalog.model_validate(payload)
    payload = json.loads(columnar_schema_catalog_json())
    payload["unexpected"] = True
    with pytest.raises(Exception):
        ColumnarSchemaCatalog.model_validate(payload)
    payload = json.loads(columnar_schema_catalog_json())
    first = dict(payload["row_schemas"][0])
    first["fields"] = list(first["fields"])
    first["fields"][0] = dict(first["fields"][0])
    first["fields"][0]["nullable"] = True
    payload["row_schemas"] = [first, *payload["row_schemas"][1:]]
    with pytest.raises(Exception, match="nullable"):
        ColumnarSchemaCatalog.model_validate(payload)


def test_importing_schema_pins_does_not_import_columnar_libraries() -> None:
    assert "pyarrow" not in sys.modules
    assert "datasets" not in sys.modules
    assert "pandas" not in sys.modules
    discover_columnar_schemas()
    assert "pyarrow" not in sys.modules
    assert "datasets" not in sys.modules
    assert "pandas" not in sys.modules
