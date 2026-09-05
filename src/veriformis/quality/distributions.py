"""Plan-bound dataset distributions as quality facts.

Item 13.3 fills the quality report with observed counts and histograms.
Facts stay separate from policy and recommendations. The report does not
enforce heuristics and does not block seal.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from veriformis.construction import ConstructionResult, DatasetRecipe
from veriformis.datasets.models import CurationResult
from veriformis.datasets.splitting import SplitResult
from veriformis.errors import QualityReportError
from veriformis.identity import lossless_json_bytes
from veriformis.quality.preview import (
    QualityPreviewBinding,
    bind_document_quality_preview,
    context_and_target_names,
)
from veriformis.quality.report import QualityFact, QualityReport, assemble_quality_report


LANGUAGE_UNQUALIFIED = "evidence-unqualified"

DISTRIBUTION_FACT_NAMES: tuple[str, ...] = (
    "context-length-distribution",
    "coverage-blocker-count",
    "coverage-distribution",
    "distinct-objective-count",
    "distinct-source-count",
    "evaluation-record-count",
    "excluded-record-count",
    "exclusion-distribution",
    "included-record-count",
    "label-distribution",
    "language-distribution",
    "language-evidence-qualified-count",
    "language-evidence-unqualified-count",
    "objective-distribution",
    "quarantined-record-count",
    "role-distribution",
    "row-schema-distribution",
    "source-distribution",
    "split-distribution",
    "target-length-distribution",
    "train-record-count",
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


def _tally(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return {key: counts[key] for key in sorted(counts)}


def _length_histogram(lengths: Sequence[int]) -> list[list[int]]:
    counts: dict[int, int] = {}
    for length in lengths:
        counts[length] = counts.get(length, 0) + 1
    return [[length, counts[length]] for length in sorted(counts)]


def report_distributions_from_binding(binding: QualityPreviewBinding) -> QualityReport:
    """Build distribution facts from a private preview binding."""
    included = binding.included
    context_names, target_names = context_and_target_names(binding)
    included_count = len(included)
    excluded_count = sum(decision.status == "excluded" for decision in binding.decisions)
    quarantined_count = sum(
        decision.status == "quarantined" for decision in binding.decisions
    )
    source_ids = tuple(
        source_id for record in included for source_id in record.source_ids
    )
    objective_ids = tuple(record.objective_id for record in included)
    field_names = tuple(field.name for record in included for field in record.fields)
    target_lengths = tuple(
        sum(len(value) for value in record.require_values(target_names))
        for record in included
    )
    context_lengths = tuple(
        sum(len(value) for value in record.require_values(context_names))
        for record in included
    )
    language_values: list[str] = []
    qualified = 0
    unqualified = 0
    for record in included:
        tokens = [
            field.language_token
            for field in record.fields
            if field.language_token is not None
        ]
        if tokens:
            qualified += len(tokens)
            language_values.extend(tokens)
        else:
            unqualified += 1
            language_values.append(LANGUAGE_UNQUALIFIED)
    role_values: tuple[str, ...]
    if binding.row_schema == "messages" and included_count:
        role_values = ("assistant",) * included_count + ("user",) * included_count
    else:
        role_values = ()
    row_schema_values = (binding.row_schema,) * included_count
    exclusion_values = tuple(
        decision.reason_codes[0]
        for decision in binding.decisions
        if decision.status != "included"
    )
    coverage_payload = {
        entry.source_id: {
            "blocker-codes": list(entry.blocker_codes),
            "candidate-count": entry.candidate_count,
            "excluded-count": entry.excluded_count,
            "included-count": entry.included_count,
            "primary-included-count": entry.primary_included_count,
            "quarantined-count": entry.quarantined_count,
            "record-count": entry.record_count,
        }
        for entry in binding.coverage_ledger.entries
    }
    blocker_count = sum(
        len(entry.blocker_codes) for entry in binding.coverage_ledger.entries
    )
    facts = (
        _text_fact("context-length-distribution", _length_histogram(context_lengths)),
        _count_fact("coverage-blocker-count", blocker_count),
        _text_fact("coverage-distribution", coverage_payload),
        _count_fact("distinct-objective-count", len(set(objective_ids))),
        _count_fact("distinct-source-count", len(set(source_ids))),
        _count_fact(
            "evaluation-record-count", binding.realized_evaluation_record_count
        ),
        _count_fact("excluded-record-count", excluded_count),
        _text_fact("exclusion-distribution", _tally(exclusion_values)),
        _count_fact("included-record-count", included_count),
        _text_fact("label-distribution", _tally(field_names)),
        _text_fact("language-distribution", _tally(language_values)),
        _count_fact("language-evidence-qualified-count", qualified),
        _count_fact("language-evidence-unqualified-count", unqualified),
        _text_fact("objective-distribution", _tally(objective_ids)),
        _count_fact("quarantined-record-count", quarantined_count),
        _text_fact("role-distribution", _tally(role_values)),
        _text_fact("row-schema-distribution", _tally(row_schema_values)),
        _text_fact("source-distribution", _tally(source_ids)),
        _text_fact(
            "split-distribution",
            {
                "evaluation": binding.realized_evaluation_record_count,
                "train": binding.realized_train_record_count,
            },
        ),
        _text_fact("target-length-distribution", _length_histogram(target_lengths)),
        _count_fact("train-record-count", binding.realized_train_record_count),
    )
    names = tuple(item.name for item in facts)
    if names != DISTRIBUTION_FACT_NAMES:
        raise QualityReportError("distribution facts must match the v1 name set")
    return assemble_quality_report(plan_id=binding.plan_id, facts=facts)


def report_dataset_distributions(
    *,
    recipe: DatasetRecipe,
    construction: ConstructionResult,
    curation: CurationResult,
    split: SplitResult,
) -> QualityReport:
    """Build a non-enforcing report of plan-bound dataset distributions."""
    return report_distributions_from_binding(
        bind_document_quality_preview(
            recipe=recipe,
            construction=construction,
            curation=curation,
            split=split,
        )
    )
