"""Versioned quality report: facts, policy, and recommendations stay separate.

Item 13.2 records the schema. Item 13.3 fills plan-bound distribution facts.
Item 13.4 adds inspectable near-duplicate clusters. The report does not
enforce heuristics, does not delete rows, and does not block seal.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from veriformis.contracts import (
    QUALITY_REPORT_CONTRACT_ID,
    QUALITY_REPORT_CONTRACT_VERSION,
    QUALITY_REPORT_SCHEMA_ID,
)
from veriformis.errors import QualityReportError
from veriformis.identity import derive_id, validate_id


REPORT_LIMITATIONS: tuple[str, ...] = (
    "no-blocking",
    "facts-are-not-policy",
    "recommendations-are-not-facts",
    "no-privacy-certification",
    "no-copyright-certification",
    "no-safety-certification",
    "no-contamination-certification",
    "no-model-quality-claim",
)

_FACT_NAME = re.compile(r"^[a-z][a-z0-9-]*$")


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


def _tuple_str(value: Any) -> Any:
    return tuple(value) if isinstance(value, list) else value


class QualityFact(_StrictModel):
    bound_to: Literal["plan"]
    integer_value: int | None
    name: str
    text_value: str | None

    @model_validator(mode="after")
    def _closed(self) -> QualityFact:
        if _FACT_NAME.fullmatch(self.name) is None:
            raise QualityReportError("quality fact name is not a lowercase token")
        if "recommend" in self.name or "should" in self.name:
            raise QualityReportError("quality facts cannot encode a recommendation")
        if self.integer_value is None and self.text_value is None:
            raise QualityReportError("quality fact requires an integer or text value")
        if self.integer_value is not None and type(self.integer_value) is not int:
            raise QualityReportError("quality fact integer_value must be an int")
        return self


class QualityPolicyDecision(_StrictModel):
    action: Literal["record-only"]
    name: str
    threshold_id: str | None

    @model_validator(mode="after")
    def _closed(self) -> QualityPolicyDecision:
        if _FACT_NAME.fullmatch(self.name) is None:
            raise QualityReportError("quality policy name is not a lowercase token")
        if self.action != "record-only":
            raise QualityReportError("quality policy cannot enforce a gate in 13.2")
        return self


class QualityRecommendation(_StrictModel):
    code: str
    message: str
    related_fact_names: tuple[str, ...]

    @field_validator("related_fact_names", mode="before")
    @classmethod
    def _names(cls, value: Any) -> Any:
        return _tuple_str(value)

    @model_validator(mode="after")
    def _closed(self) -> QualityRecommendation:
        if _FACT_NAME.fullmatch(self.code) is None:
            raise QualityReportError("quality recommendation code is not a lowercase token")
        if not self.message.strip():
            raise QualityReportError("quality recommendation message is empty")
        names = tuple(sorted(set(self.related_fact_names)))
        if names != self.related_fact_names:
            raise QualityReportError(
                "quality recommendation related_fact_names must be sorted and unique"
            )
        return self


class QualityReport(_StrictModel):
    contract_id: str
    contract_version: int
    enforcing: Literal[False]
    facts: tuple[QualityFact, ...]
    limitations: tuple[str, ...]
    plan_id: str
    policy_decisions: tuple[QualityPolicyDecision, ...]
    recommendations: tuple[QualityRecommendation, ...]
    report_id: str
    schema_id: str

    @field_validator("facts", "policy_decisions", "recommendations", "limitations", mode="before")
    @classmethod
    def _tuples(cls, value: Any) -> Any:
        return _tuple_str(value)

    @model_validator(mode="after")
    def _closed(self) -> QualityReport:
        if self.contract_id != QUALITY_REPORT_CONTRACT_ID:
            raise QualityReportError("quality report contract_id is invalid")
        if self.contract_version != QUALITY_REPORT_CONTRACT_VERSION:
            raise QualityReportError("quality report contract_version is invalid")
        if self.schema_id != QUALITY_REPORT_SCHEMA_ID:
            raise QualityReportError("quality report schema_id is invalid")
        if self.enforcing:
            raise QualityReportError("quality report cannot enforce heuristics in 13.2")
        if self.limitations != REPORT_LIMITATIONS:
            raise QualityReportError("quality report limitations must match the v1 set")
        validate_id(self.plan_id, kind="fdp")
        validate_id(self.report_id, kind="qrp")
        fact_names = tuple(item.name for item in self.facts)
        if fact_names != tuple(sorted(set(fact_names))):
            raise QualityReportError("quality facts must be unique and sorted by name")
        policy_names = tuple(item.name for item in self.policy_decisions)
        if policy_names != tuple(sorted(set(policy_names))):
            raise QualityReportError("quality policy decisions must be unique and sorted")
        overlap = set(fact_names) & set(policy_names)
        if overlap:
            raise QualityReportError("quality facts and policy decisions share names")
        rec_codes = tuple(item.code for item in self.recommendations)
        if rec_codes != tuple(sorted(set(rec_codes))):
            raise QualityReportError("quality recommendations must be unique and sorted")
        known_facts = set(fact_names)
        for item in self.recommendations:
            missing = [name for name in item.related_fact_names if name not in known_facts]
            if missing:
                raise QualityReportError(
                    "quality recommendation names facts that are not in the report"
                )
        expected = derive_id(
            "qrp",
            self.model_dump(mode="json", exclude={"report_id"}),
        )
        if self.report_id != expected:
            raise QualityReportError("quality report identity mismatch")
        return self


def assemble_quality_report(
    *,
    plan_id: str,
    facts: tuple[QualityFact, ...] = (),
    policy_decisions: tuple[QualityPolicyDecision, ...] = (),
    recommendations: tuple[QualityRecommendation, ...] = (),
) -> QualityReport:
    """Bind a non-enforcing report. Callers must already sort unique names."""
    payload = {
        "contract_id": QUALITY_REPORT_CONTRACT_ID,
        "contract_version": QUALITY_REPORT_CONTRACT_VERSION,
        "enforcing": False,
        "facts": facts,
        "limitations": REPORT_LIMITATIONS,
        "plan_id": plan_id,
        "policy_decisions": policy_decisions,
        "recommendations": recommendations,
        "schema_id": QUALITY_REPORT_SCHEMA_ID,
    }
    return QualityReport(report_id=derive_id("qrp", payload), **payload)


def empty_quality_report(*, plan_id: str) -> QualityReport:
    """Bound empty report. Facts, policy, and recommendations stay vacant."""
    return assemble_quality_report(plan_id=plan_id)


def require_quality_report_not_enforcing(report: QualityReport) -> None:
    if report.enforcing:
        raise QualityReportError("quality report cannot enforce heuristics in 13.2")
