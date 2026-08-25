"""Phase 10.2: candidate admission pins stay non-executable."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.contracts import (
    CANDIDATE_PROFILE_ADMISSION_SCHEMA_ID,
    PROFILE_ADMISSION_CONTRACT_ID,
    PROFILE_ADMISSION_CONTRACT_VERSION,
)
from veriformis.errors import ExportContractError
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.profiles import (
    CANDIDATE_ADMISSION_DATA_NAME,
    CandidateProfileAdmission,
    CandidateProfileAdmissionCatalog,
    candidate_profile_admission_catalog,
    candidate_profile_admission_catalog_json,
    discover_candidate_profile_admissions,
    discover_profile_admissions,
)
from veriformis.taxonomy import CANDIDATE_CONSUMER_PROFILES

DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "veriformis"
    / "profiles"
    / CANDIDATE_ADMISSION_DATA_NAME
)
ROOT = Path(__file__).resolve().parents[2]
RUNNER = CliRunner()
SERVICE = PipelineService()


def test_candidate_admission_contract_constants_are_exact() -> None:
    assert CANDIDATE_ADMISSION_DATA_NAME == "candidate-admission-v1.json"
    assert (
        CANDIDATE_PROFILE_ADMISSION_SCHEMA_ID
        == "veriformis.candidate-profile-admission-discovery/v1"
    )
    assert PROFILE_ADMISSION_CONTRACT_ID == "veriformis.consumer-profile-admission"
    assert PROFILE_ADMISSION_CONTRACT_VERSION == 1


def test_packaged_candidate_catalog_is_canonical_and_shared() -> None:
    stored = DATA_PATH.read_text(encoding="utf-8")
    payload = json.loads(stored)
    canonical = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    assert stored == canonical
    assert payload["schema_id"] == CANDIDATE_PROFILE_ADMISSION_SCHEMA_ID
    assert payload["contract_id"] == PROFILE_ADMISSION_CONTRACT_ID
    expected = candidate_profile_admission_catalog_json()
    python = json.dumps(
        discover_candidate_profile_admissions(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    cli = RUNNER.invoke(app, ["candidate-profile-admissions"])
    assert cli.exit_code == 0, cli.output
    tools = {
        tool.name: tool.fn
        for tool in create_mcp_server(SERVICE)._tool_manager.list_tools()
    }
    mcp = tools["candidate_profile_admissions"]()
    assert python + "\n" == expected
    assert cli.output == expected
    assert mcp == expected
    assert SERVICE.discover_candidate_profile_admissions() == json.loads(expected)
    first = SERVICE.discover_candidate_profile_admissions()
    second = SERVICE.discover_candidate_profile_admissions()
    assert first == second and first is not second


def test_candidate_catalog_closes_over_unsloth_skip() -> None:
    catalog = candidate_profile_admission_catalog()
    assert isinstance(catalog, CandidateProfileAdmissionCatalog)
    assert tuple(record.profile_id for record in catalog.records) == ("unsloth",)
    assert CANDIDATE_CONSUMER_PROFILES == ("unsloth",)
    unsloth = catalog.records[0]
    assert unsloth.state == "experimental" and unsloth.emit_eligible is False
    assert unsloth.later_item == "none"
    assert unsloth.package == "unsloth"
    assert unsloth.machine_checkable_contract is False
    assert "skipped Unsloth" in unsloth.admission_verdict
    assert all(record.round_trip is False for record in catalog.records)


def test_implemented_profile_admissions_include_phase_10_emits() -> None:
    implemented = discover_profile_admissions()
    assert [record["profile_id"] for record in implemented["records"]] == [
        "trl",
        "mlx-lm",
        "axolotl",
        "llama-factory",
        "aptus",
    ]
    assert all(record["state"] == "implemented" for record in implemented["records"])


def test_candidate_models_refuse_executable_claims_and_unknown_ids() -> None:
    payload = candidate_profile_admission_catalog().model_dump(mode="json")
    first = dict(payload["records"][0])
    first["profile_id"] = "trl"
    with pytest.raises(ExportContractError, match="not a Phase 10 pin"):
        CandidateProfileAdmission.model_validate(first)
    first = dict(payload["records"][0])
    first["emit_eligible"] = True
    with pytest.raises(ExportContractError, match="emit_eligible"):
        CandidateProfileAdmission.model_validate(first)
    first = dict(payload["records"][0])
    first["round_trip"] = True
    with pytest.raises(ExportContractError, match="round-trip"):
        CandidateProfileAdmission.model_validate(first)
    first = dict(payload["records"][0])
    first["unexpected"] = True
    with pytest.raises(Exception):
        CandidateProfileAdmission.model_validate(first)


def test_importing_candidate_admission_does_not_import_trainer_libraries() -> None:
    assert "axolotl" not in sys.modules
    assert "llamafactory" not in sys.modules
    assert "unsloth" not in sys.modules
    assert "torch" not in sys.modules
    discover_candidate_profile_admissions()
    assert "axolotl" not in sys.modules
    assert "llamafactory" not in sys.modules
    assert "unsloth" not in sys.modules
    assert "torch" not in sys.modules


def test_phase_10_extras_remain_empty() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "axolotl = []" in text
    assert "ocr = []" in text
    assert "llama-factory = []" in text
    assert "unsloth = []" in text
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert 'name = "axolotl"\n' not in lock
    assert 'name = "unsloth"\n' not in lock
    assert 'name = "llamafactory"\n' not in lock
    assert 'name = "torch"\n' not in lock
