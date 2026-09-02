"""Phase 13.2 quality report: facts, policy, and recommendations stay separate."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from veriformis.cli import app
from veriformis.contracts import QUALITY_REPORT_SCHEMA_ID
from veriformis.errors import QualityReportError
from veriformis.identity import derive_id
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.quality import (
    QualityFact,
    QualityReport,
    empty_quality_report,
    require_quality_report_not_enforcing,
)


def _plan_id() -> str:
    return derive_id("fdp", {"phase13": "quality-report"})


def test_empty_report_is_bound_and_not_enforcing() -> None:
    plan_id = _plan_id()
    first = empty_quality_report(plan_id=plan_id)
    second = empty_quality_report(plan_id=plan_id)
    assert first == second
    assert first.enforcing is False
    assert first.facts == ()
    assert first.policy_decisions == ()
    assert first.recommendations == ()
    assert first.schema_id == QUALITY_REPORT_SCHEMA_ID
    assert first.plan_id == plan_id
    require_quality_report_not_enforcing(first)


def test_fact_cannot_encode_a_recommendation() -> None:
    with pytest.raises(QualityReportError, match="cannot encode a recommendation"):
        QualityFact(
            bound_to="plan",
            integer_value=1,
            name="recommend-drop",
            text_value=None,
        )


def test_facts_and_policy_cannot_share_a_name() -> None:
    plan_id = _plan_id()
    empty = empty_quality_report(plan_id=plan_id)
    payload = empty.model_dump(mode="json", exclude={"report_id"})
    payload["facts"] = [
        {
            "bound_to": "plan",
            "integer_value": 3,
            "name": "included-rows",
            "text_value": None,
        }
    ]
    payload["policy_decisions"] = [
        {
            "action": "record-only",
            "name": "included-rows",
            "threshold_id": None,
        }
    ]
    with pytest.raises(QualityReportError, match="share names"):
        QualityReport(report_id=derive_id("qrp", payload), **payload)


def test_recommendation_cannot_name_a_missing_fact() -> None:
    plan_id = _plan_id()
    empty = empty_quality_report(plan_id=plan_id)
    payload = empty.model_dump(mode="json", exclude={"report_id"})
    payload["recommendations"] = [
        {
            "code": "review-imbalance",
            "message": "Train and evaluation counts differ.",
            "related_fact_names": ["included-rows"],
        }
    ]
    with pytest.raises(QualityReportError, match="facts that are not in the report"):
        QualityReport(report_id=derive_id("qrp", payload), **payload)


def test_enforcing_literal_rejects_true() -> None:
    plan_id = _plan_id()
    empty = empty_quality_report(plan_id=plan_id)
    payload = empty.model_dump(mode="json")
    payload["enforcing"] = True
    with pytest.raises(ValidationError):
        QualityReport.model_validate(payload)


def test_cli_and_service_have_preview_quality_report_without_mcp() -> None:
    names = {command.name for command in app.registered_commands}
    assert "quality-report" in names
    assert hasattr(PipelineService(), "quality_report")
    tools = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert "quality_report" not in tools
    assert "quality-report" not in tools
