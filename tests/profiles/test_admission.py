"""Phase 8.2: planned TRL and MLX-LM admission pins. No emission."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.contracts import (
    PROFILE_ADMISSION_CONTRACT_ID,
    PROFILE_ADMISSION_CONTRACT_VERSION,
    PROFILE_ADMISSION_SCHEMA_ID,
    V1_ROW_SCHEMA_KINDS,
)
from veriformis.errors import ExportContractError
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.profiles import (
    ADMISSION_DATA_NAME,
    ProfileAdmission,
    ProfileAdmissionCatalog,
    discover_profile_admissions,
    profile_admission_catalog,
    profile_admission_catalog_json,
)
from veriformis.taxonomy import PLANNED_CONSUMER_PROFILE_ITEMS, PLANNED_CONSUMER_PROFILES

DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "veriformis"
    / "profiles"
    / ADMISSION_DATA_NAME
)
ROOT = Path(__file__).resolve().parents[2]
RUNNER = CliRunner()
SERVICE = PipelineService()
TRL_REFUSED = (
    "preference",
    "prompt-only",
    "stepwise-supervision",
    "tools",
    "unpaired-preference",
    "vision",
)


def test_admission_contract_constants_are_exact() -> None:
    assert PROFILE_ADMISSION_CONTRACT_ID == "veriformis.consumer-profile-admission"
    assert PROFILE_ADMISSION_CONTRACT_VERSION == 1
    assert PROFILE_ADMISSION_SCHEMA_ID == "veriformis.profile-admission-discovery/v1"
    assert ADMISSION_DATA_NAME == "admission-v1.json"


def test_packaged_admission_catalog_is_canonical_and_shared() -> None:
    stored = DATA_PATH.read_text(encoding="utf-8")
    payload = json.loads(stored)
    canonical = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    assert stored == canonical
    assert payload["schema_id"] == PROFILE_ADMISSION_SCHEMA_ID
    assert payload["contract_id"] == PROFILE_ADMISSION_CONTRACT_ID
    assert payload["contract_version"] == PROFILE_ADMISSION_CONTRACT_VERSION
    expected = profile_admission_catalog_json()
    python = json.dumps(
        discover_profile_admissions(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    cli = RUNNER.invoke(app, ["profile-admissions"])
    assert cli.exit_code == 0, cli.output
    tools = {
        tool.name: tool.fn
        for tool in create_mcp_server(SERVICE)._tool_manager.list_tools()
    }
    mcp = tools["profile_admissions"]()
    assert python + "\n" == expected
    assert cli.output == expected
    assert mcp == expected
    assert SERVICE.discover_profile_admissions() == json.loads(expected)
    first = SERVICE.discover_profile_admissions()
    second = SERVICE.discover_profile_admissions()
    assert first == second and first is not second


def test_catalog_closes_over_planned_profiles_only() -> None:
    catalog = profile_admission_catalog()
    assert isinstance(catalog, ProfileAdmissionCatalog)
    assert tuple(record.profile_id for record in catalog.records) == PLANNED_CONSUMER_PROFILES
    assert PLANNED_CONSUMER_PROFILES == ("trl", "mlx-lm")
    for record in catalog.records:
        assert record.state == "planned"
        assert record.round_trip is False
        assert record.extra == record.profile_id
        assert record.executable_item == PLANNED_CONSUMER_PROFILE_ITEMS[record.profile_id]
        assert record.admitted_row_schemas == tuple(sorted(V1_ROW_SCHEMA_KINDS))
        assert record.refused_dataset_types == TRL_REFUSED
        assert record.docs_reviewed_on == "2026-08-23"
        assert tuple(sorted(record.partition_mapping)) == ("evaluation", "train")


def test_trl_and_mlx_lm_pins_match_official_docs() -> None:
    by_id = {record.profile_id: record for record in profile_admission_catalog().records}
    trl = by_id["trl"]
    assert trl.package == "trl"
    assert trl.license == "Apache-2.0"
    assert trl.version_range == ">=0.15.0,<1.0.0"
    assert trl.primary_docs_url == "https://huggingface.co/docs/trl/main/en/dataset_formats"
    assert trl.executable_item == "8.3"
    assert [item.mapping_kind for item in trl.row_mappings] == [
        "assemble-prompt",
        "identity",
        "identity",
        "identity",
    ]
    mlx = by_id["mlx-lm"]
    assert mlx.package == "mlx-lm"
    assert mlx.license == "MIT"
    assert mlx.version_range == ">=0.22.0,<1.0.0"
    assert mlx.primary_docs_url == (
        "https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md"
    )
    assert mlx.executable_item == "8.4"
    assert mlx.partition_mapping["train"] == "train.jsonl (required)"
    assert "valid.jsonl" in mlx.partition_mapping["evaluation"]
    assert "test.jsonl" in mlx.workflow
    assert "not mapped from Veriformis evaluation" in mlx.workflow


def test_admission_models_refuse_unknown_profiles_and_round_trip_claims() -> None:
    payload = profile_admission_catalog().model_dump(mode="json")
    first = dict(payload["records"][0])
    first["profile_id"] = "axolotl"
    with pytest.raises(ExportContractError, match="not a planned consumer"):
        ProfileAdmission.model_validate(first)
    first = dict(payload["records"][0])
    first["round_trip"] = True
    with pytest.raises(ExportContractError, match="do not claim round-trip"):
        ProfileAdmission.model_validate(first)
    first = dict(payload["records"][0])
    first["unexpected"] = True
    with pytest.raises(Exception):
        ProfileAdmission.model_validate(first)


def test_importing_admission_does_not_import_trainer_libraries() -> None:
    assert "trl" not in sys.modules
    assert "mlx_lm" not in sys.modules
    assert "torch" not in sys.modules
    assert "mlx" not in sys.modules
    discover_profile_admissions()
    assert "trl" not in sys.modules
    assert "mlx_lm" not in sys.modules
    assert "torch" not in sys.modules
    assert "mlx" not in sys.modules
