"""Optional policy detectors as findings, not certification.

Item 13.7 scans included field values with named, versioned regular
expressions. Hits are facts. They do not certify privacy, safety, or
license status and do not block seal.
"""

from __future__ import annotations

import re

from veriformis.construction import ConstructionResult, DatasetRecipe, DatasetRecord
from veriformis.datasets.models import CurationResult
from veriformis.datasets.splitting import SplitResult
from veriformis.errors import QualityReportError
from veriformis.identity import lossless_json_bytes
from veriformis.quality.distributions import included_dataset_records
from veriformis.quality.report import (
    QualityFact,
    QualityPolicyDecision,
    QualityReport,
    assemble_quality_report,
)
from veriformis.quality.tokenizer import report_tokenizer_simulations


DETECTOR_SET_ID = "veriformis.policy-detectors/v1"
DETECTOR_FACT_NAMES: tuple[str, ...] = (
    "detector-hits",
    "detector-license-hit-count",
    "detector-pii-hit-count",
    "detector-secret-hit-count",
    "detector-set-id",
    "detector-unsafe-hit-count",
)

_DETECTORS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("pii", "pii-email", re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)),
    ("secret", "secret-aws-access-key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("secret", "secret-pem-private-key", re.compile(r"BEGIN [A-Z ]*PRIVATE KEY")),
    ("unsafe", "unsafe-script-tag", re.compile(r"<script[\s>]", re.I)),
    ("license", "license-gpl-3", re.compile(r"\bGPL-3\.0\b")),
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


def _scan(records: tuple[DatasetRecord, ...]) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for record in records:
        blob = "\n".join(field.value for field in record.fields)
        for family, pattern_id, pattern in _DETECTORS:
            if pattern.search(blob) is None:
                continue
            hits.append(
                {
                    "family": family,
                    "pattern-id": pattern_id,
                    "record-id": record.record_id,
                }
            )
    hits.sort(key=lambda item: (item["record-id"], item["pattern-id"]))
    return hits


def report_policy_detectors(
    *,
    recipe: DatasetRecipe,
    construction: ConstructionResult,
    curation: CurationResult,
    split: SplitResult,
) -> QualityReport:
    """Add optional detector findings to the tokenizer quality report."""
    included = included_dataset_records(
        recipe=recipe,
        construction=construction,
        curation=curation,
        split=split,
    )
    hits = _scan(included)

    def _records(family: str) -> int:
        return len({item["record-id"] for item in hits if item["family"] == family})

    extra = (
        _text_fact("detector-hits", hits),
        _count_fact("detector-license-hit-count", _records("license")),
        _count_fact("detector-pii-hit-count", _records("pii")),
        _count_fact("detector-secret-hit-count", _records("secret")),
        _text_fact("detector-set-id", DETECTOR_SET_ID),
        _count_fact("detector-unsafe-hit-count", _records("unsafe")),
    )
    if tuple(item.name for item in extra) != DETECTOR_FACT_NAMES:
        raise QualityReportError("detector facts must match the v1 name set")
    base = report_tokenizer_simulations(
        recipe=recipe,
        construction=construction,
        curation=curation,
        split=split,
    )
    facts = tuple(sorted((*base.facts, *extra), key=lambda item: item.name))
    policy = tuple(
        sorted(
            (
                *base.policy_decisions,
                QualityPolicyDecision(
                    action="record-only",
                    name="detector-findings-not-certification",
                    threshold_id=None,
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
