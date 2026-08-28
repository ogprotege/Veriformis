"""Split-comparability, imbalance, rare-shape, role, and empty-field facts.

Item 13.8 records findings over included records and split assignments.
v1 construction forbids empty fields. Message roles exist only after
row lowering, so `split-malformed-role-count` stays reserved-zero on
these inputs. The report does not block seal.
"""

from __future__ import annotations

from collections import Counter

from veriformis.construction import ConstructionResult, DatasetRecipe, DatasetRecord
from veriformis.datasets.curation import OBJECTIVE_FIELD_ROLES
from veriformis.datasets.models import CurationResult
from veriformis.datasets.splitting import SplitResult
from veriformis.errors import QualityReportError
from veriformis.identity import lossless_json_bytes
from veriformis.quality.detectors import report_policy_detectors
from veriformis.quality.distributions import included_dataset_records
from veriformis.quality.family_hooks import report_family_hooks
from veriformis.quality.report import (
    QualityFact,
    QualityPolicyDecision,
    QualityReport,
    assemble_quality_report,
)


SPLIT_FINDING_FACT_NAMES: tuple[str, ...] = (
    "split-empty-context-count",
    "split-empty-target-count",
    "split-imbalance-ppm",
    "split-malformed-role-count",
    "split-rare-shape-count",
    "split-rare-shapes",
    "split-source-comparability",
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


def _field_map(record: DatasetRecord) -> dict[str, str]:
    return {field.name: field.value for field in record.fields}


def report_split_findings(
    *,
    recipe: DatasetRecipe,
    construction: ConstructionResult,
    curation: CurationResult,
    split: SplitResult,
) -> QualityReport:
    """Add split-comparability findings to the detector quality report."""
    included = included_dataset_records(
        recipe=recipe,
        construction=construction,
        curation=curation,
        split=split,
    )
    records = {record.record_id: record for record in included}
    context_names, target_names = OBJECTIVE_FIELD_ROLES[recipe.objective.kind]
    empty_target = 0
    empty_context = 0
    malformed_role = 0
    shapes: list[str] = []
    train_sources: Counter[str] = Counter()
    eval_sources: Counter[str] = Counter()
    for assignment in split.assignments:
        record = records[assignment.record_id]
        fields = _field_map(record)
        if any(not fields.get(name) for name in target_names):
            empty_target += 1
        if any(not fields.get(name) for name in context_names):
            empty_context += 1
        shape = ",".join(field.name for field in record.fields)
        shapes.append(shape)
        if assignment.partition == "train":
            bucket = train_sources
        elif assignment.partition == "evaluation":
            bucket = eval_sources
        else:
            raise QualityReportError("split assignment is not a v1 partition")
        for source_id in record.source_ids:
            bucket[source_id] += 1
    shape_counts = Counter(shapes)
    rare = sorted(shape for shape, count in shape_counts.items() if count == 1)
    total = split.realized_train_record_count + split.realized_evaluation_record_count
    if total == 0:
        imbalance = 0
    else:
        delta = abs(
            split.realized_train_record_count - split.realized_evaluation_record_count
        )
        imbalance = (delta * 1_000_000) // total
    comparability = {
        source_id: {
            "evaluation": eval_sources.get(source_id, 0),
            "train": train_sources.get(source_id, 0),
        }
        for source_id in sorted(set(train_sources) | set(eval_sources))
    }
    extra = (
        _count_fact("split-empty-context-count", empty_context),
        _count_fact("split-empty-target-count", empty_target),
        _count_fact("split-imbalance-ppm", imbalance),
        _count_fact("split-malformed-role-count", malformed_role),
        _count_fact("split-rare-shape-count", len(rare)),
        _text_fact("split-rare-shapes", rare),
        _text_fact("split-source-comparability", comparability),
    )
    if tuple(item.name for item in extra) != SPLIT_FINDING_FACT_NAMES:
        raise QualityReportError("split-finding facts must match the v1 name set")
    base = report_policy_detectors(
        recipe=recipe,
        construction=construction,
        curation=curation,
        split=split,
    )
    family = report_family_hooks(
        recipe=recipe,
        construction=construction,
        curation=curation,
        split=split,
    )
    facts = tuple(sorted((*base.facts, *extra, *family), key=lambda item: item.name))
    policy = tuple(
        sorted(
            (
                *base.policy_decisions,
                QualityPolicyDecision(
                    action="record-only",
                    name="split-findings-record-only",
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
