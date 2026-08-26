"""Phase 13.1 isolation: quality intelligence is not yet a report or gate."""

from __future__ import annotations

from veriformis.cli import app
from veriformis.contracts import (
    FINISHED_DATASET_SCHEMA_IDS,
    V1_FINISHED_DATASET_GATES,
    V1_QUALITY_FINDING_CODES,
)
from veriformis.datasets.models import CurationPolicy
from veriformis.goals.preflight import _limitations
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService


def test_seventeen_finished_dataset_gates_are_unchanged() -> None:
    assert V1_FINISHED_DATASET_GATES == (
        "construction-replay",
        "record-lifecycle",
        "curation",
        "deduplication",
        "quality",
        "balance",
        "coverage",
        "split",
        "leakage",
        "row-binding",
        "objective",
        "schema",
        "encoding",
        "masking",
        "partition-nonempty",
        "aptus-row-shape",
        "snapshot",
    )
    assert len(V1_FINISHED_DATASET_GATES) == 17


def test_quality_finding_codes_remain_the_four_curation_codes() -> None:
    assert V1_QUALITY_FINDING_CODES == (
        "conflicting-target",
        "exact-duplicate",
        "primary-source-cap",
        "target-too-short",
    )


def test_near_duplicate_policy_stays_disabled() -> None:
    policy = CurationPolicy.create(minimum_target_characters=1)
    assert policy.near_duplicate_policy == "disabled"


def test_preflight_still_names_no_quality_intelligence() -> None:
    codes = {item.code for item in _limitations()}
    assert "no-quality-intelligence" in codes


def test_no_quality_report_schema() -> None:
    assert all("quality-report" not in schema for schema in FINISHED_DATASET_SCHEMA_IDS)


def test_cli_has_no_quality_report_command() -> None:
    names = {command.name for command in app.registered_commands}
    assert "quality-report" not in names
    assert "quality" not in names


def test_mcp_has_no_quality_report_tool() -> None:
    tools = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert "quality_report" not in tools
    assert "quality-report" not in tools


def test_pipeline_service_has_no_quality_report() -> None:
    service = PipelineService()
    assert not hasattr(service, "quality_report")
    assert not hasattr(service, "quality_preview")
