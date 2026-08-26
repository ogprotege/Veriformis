"""Previewable quality gates. Item 13.9 records thresholds and fixtures.

Gates are configurable, versioned, and previewable. They bind to the
finished-dataset plan identity. They do not change FinishedDatasetPlan or
the seventeen-gate validation snapshot. No heuristic is admitted to block
seal: labeled fixtures exist, and v1 still records findings only.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from veriformis.construction import ConstructionResult, DatasetRecipe
from veriformis.datasets.models import CurationResult
from veriformis.datasets.splitting import SplitResult
from veriformis.errors import QualityReportError
from veriformis.identity import lossless_json_bytes
from veriformis.quality.report import (
    QualityFact,
    QualityPolicyDecision,
    QualityReport,
    assemble_quality_report,
)
from veriformis.quality.split_findings import report_split_findings


QUALITY_GATE_POLICY_ID = "veriformis.quality-gate-policy/v1"
LABELED_FIXTURE_SET_ID = "veriformis.quality-labeled-fixtures/v1"

GATE_FACT_NAMES: tuple[str, ...] = (
    "quality-admitted-blocking-count",
    "quality-gate-plan-id",
    "quality-gate-policy-id",
    "quality-gate-preview",
    "quality-gate-would-block-count",
    "quality-labeled-fixture-count",
    "quality-labeled-fixture-set-id",
)


@dataclass(frozen=True)
class QualityGateSpec:
    gate_id: str
    fact_name: str
    threshold: int
    admitted_to_block: bool


@dataclass(frozen=True)
class LabeledFixture:
    fact_name: str
    fixture_id: str
    heuristic: str
    label: str


V1_QUALITY_GATES: tuple[QualityGateSpec, ...] = (
    QualityGateSpec("preview-detector-pii", "detector-pii-hit-count", 1, False),
    QualityGateSpec("preview-detector-secret", "detector-secret-hit-count", 1, False),
    QualityGateSpec(
        "preview-leakage-cross-partition",
        "leakage-cross-partition-exact-target-count",
        1,
        False,
    ),
    QualityGateSpec(
        "preview-near-duplicate-members",
        "near-duplicate-member-count",
        1,
        False,
    ),
    QualityGateSpec("preview-split-empty-target", "split-empty-target-count", 1, False),
    QualityGateSpec(
        "preview-split-malformed-role",
        "split-malformed-role-count",
        1,
        False,
    ),
)

LABELED_FIXTURES: tuple[LabeledFixture, ...] = (
    LabeledFixture(
        "detector-pii-hit-count",
        "detector-clean-negative",
        "detector-pii",
        "negative",
    ),
    LabeledFixture(
        "detector-pii-hit-count",
        "detector-pii-email-positive",
        "detector-pii",
        "positive",
    ),
    LabeledFixture(
        "leakage-cross-partition-exact-target-count",
        "leakage-distinct-negative",
        "leakage-cross-partition",
        "negative",
    ),
    LabeledFixture(
        "near-duplicate-member-count",
        "near-duplicate-punct-positive",
        "near-duplicate",
        "positive",
    ),
    LabeledFixture(
        "near-duplicate-member-count",
        "near-duplicate-unrelated-negative",
        "near-duplicate",
        "negative",
    ),
    LabeledFixture(
        "detector-secret-hit-count",
        "secret-aws-key-positive",
        "detector-secret",
        "positive",
    ),
    LabeledFixture(
        "split-empty-target-count",
        "split-empty-valid-negative",
        "split-empty-target",
        "negative",
    ),
    LabeledFixture(
        "split-malformed-role-count",
        "split-malformed-role-valid-negative",
        "split-malformed-role",
        "negative",
    ),
)


def _count_fact(name: str, value: int) -> QualityFact:
    return QualityFact(
        bound_to="plan",
        integer_value=value,
        name=name,
        text_value=None,
    )


def _text_fact(name: str, value: object) -> QualityFact:
    return QualityFact(
        bound_to="plan",
        integer_value=None,
        name=name,
        text_value=lossless_json_bytes(value).decode("utf-8"),
    )


def _require_gate_specs(gates: Sequence[QualityGateSpec]) -> tuple[QualityGateSpec, ...]:
    specs = tuple(gates)
    seen: set[str] = set()
    for spec in specs:
        if spec.admitted_to_block:
            raise QualityReportError(
                "heuristic cannot block seal without labeled-fixture admission"
            )
        if type(spec.threshold) is not int or spec.threshold < 1:
            raise QualityReportError("quality gate threshold must be a positive integer")
        if spec.gate_id in seen:
            raise QualityReportError("quality gate ids must be unique")
        seen.add(spec.gate_id)
    return tuple(sorted(specs, key=lambda item: item.gate_id))


def preview_quality_gates(
    *,
    recipe: DatasetRecipe,
    construction: ConstructionResult,
    curation: CurationResult,
    split: SplitResult,
    gates: Sequence[QualityGateSpec] | None = None,
) -> QualityReport:
    """Preview named thresholds against the composed quality report."""
    specs = _require_gate_specs(V1_QUALITY_GATES if gates is None else gates)
    base = report_split_findings(
        recipe=recipe,
        construction=construction,
        curation=curation,
        split=split,
    )
    facts_by_name = {item.name: item for item in base.facts}
    rows: list[dict[str, object]] = []
    would_block = 0
    for spec in specs:
        fact = facts_by_name.get(spec.fact_name)
        if fact is None or fact.integer_value is None:
            raise QualityReportError(
                f"quality gate {spec.gate_id} requires integer fact {spec.fact_name}"
            )
        blocked = fact.integer_value >= spec.threshold
        if blocked:
            would_block += 1
        rows.append(
            {
                "admitted-to-block": False,
                "fact": spec.fact_name,
                "gate-id": spec.gate_id,
                "observed": fact.integer_value,
                "threshold": spec.threshold,
                "would-block": blocked,
            }
        )
    extra = (
        _count_fact("quality-admitted-blocking-count", 0),
        _text_fact("quality-gate-plan-id", base.plan_id),
        _text_fact("quality-gate-policy-id", QUALITY_GATE_POLICY_ID),
        _text_fact("quality-gate-preview", rows),
        _count_fact("quality-gate-would-block-count", would_block),
        _count_fact("quality-labeled-fixture-count", len(LABELED_FIXTURES)),
        _text_fact("quality-labeled-fixture-set-id", LABELED_FIXTURE_SET_ID),
    )
    if tuple(item.name for item in extra) != GATE_FACT_NAMES:
        raise QualityReportError("quality-gate facts must match the v1 name set")
    facts = tuple(sorted((*base.facts, *extra), key=lambda item: item.name))
    policy = tuple(
        sorted(
            (
                *base.policy_decisions,
                QualityPolicyDecision(
                    action="record-only",
                    name="quality-gates-preview-only",
                    threshold_id=QUALITY_GATE_POLICY_ID,
                ),
                QualityPolicyDecision(
                    action="record-only",
                    name="quality-no-heuristic-admitted-to-block",
                    threshold_id=LABELED_FIXTURE_SET_ID,
                ),
            ),
            key=lambda item: item.name,
        )
    )
    return assemble_quality_report(
        plan_id=base.plan_id,
        facts=facts,
        policy_decisions=policy,
        recommendations=base.recommendations,
    )
