"""Plan-bound dataset distributions as quality facts.

Item 13.3 fills the quality report with observed counts and histograms.
Facts stay separate from policy and recommendations. The report does not
enforce heuristics and does not block seal.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from veriformis.construction import (
    ConstructionResult,
    DatasetRecipe,
    DatasetRecord,
    IRFieldEvidence,
    RecordField,
)
from veriformis.datasets.curation import OBJECTIVE_FIELD_ROLES
from veriformis.datasets.models import CurationResult
from veriformis.datasets.splitting import SplitResult
from veriformis.errors import QualityReportError
from veriformis.identity import lossless_json_bytes
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


def _field_values(record: DatasetRecord, names: tuple[str, ...]) -> tuple[str, ...]:
    by_name = {field.name: field.value for field in record.fields}
    missing = [name for name in names if name not in by_name]
    if missing:
        raise QualityReportError(
            f"included record {record.record_id} is missing objective field {missing[0]!r}"
        )
    return tuple(by_name[name] for name in names)


def _language_token(field: RecordField) -> str | None:
    if field.name == "language":
        return field.value
    evidence = field.evidence
    if not isinstance(evidence, IRFieldEvidence):
        return None
    tokens = [part for part in evidence.json_pointer.split("/") if part]
    if tokens and tokens[-1] == "language":
        return field.value
    return None


def _require_bound_inputs(
    *,
    recipe: DatasetRecipe,
    construction: ConstructionResult,
    curation: CurationResult,
    split: SplitResult,
) -> None:
    if recipe.recipe_id != construction.recipe_id:
        raise QualityReportError("distribution recipe does not match construction")
    if recipe.recipe_id != curation.recipe_id:
        raise QualityReportError("distribution recipe does not match curation")
    if construction.result_id != curation.construction_result_id:
        raise QualityReportError("distribution construction does not match curation")
    if construction.result_id != split.construction_result_id:
        raise QualityReportError("distribution construction does not match split")
    if curation.result_id != split.curation_result_id:
        raise QualityReportError("distribution curation does not match split")
    if curation.plan_id != split.plan_id:
        raise QualityReportError("distribution plan identities do not match")
    if tuple(sorted(curation.included_record_ids)) != split.input_record_ids:
        raise QualityReportError("split input does not match included records")


def included_dataset_records(
    *,
    recipe: DatasetRecipe,
    construction: ConstructionResult,
    curation: CurationResult,
    split: SplitResult,
) -> tuple[DatasetRecord, ...]:
    _require_bound_inputs(
        recipe=recipe,
        construction=construction,
        curation=curation,
        split=split,
    )
    records_by_id: Mapping[str, DatasetRecord] = {
        record.record_id: record for record in construction.records
    }
    missing = [
        record_id
        for record_id in curation.included_record_ids
        if record_id not in records_by_id
    ]
    if missing:
        raise QualityReportError("included record is missing from construction")
    return tuple(
        records_by_id[record_id] for record_id in curation.included_record_ids
    )


def report_dataset_distributions(
    *,
    recipe: DatasetRecipe,
    construction: ConstructionResult,
    curation: CurationResult,
    split: SplitResult,
) -> QualityReport:
    """Build a non-enforcing report of plan-bound dataset distributions."""
    included = included_dataset_records(
        recipe=recipe,
        construction=construction,
        curation=curation,
        split=split,
    )
    context_names, target_names = OBJECTIVE_FIELD_ROLES[recipe.objective.kind]
    included_count = len(included)
    excluded_count = sum(
        decision.status == "excluded" for decision in curation.decisions
    )
    quarantined_count = sum(
        decision.status == "quarantined" for decision in curation.decisions
    )
    source_ids = tuple(
        source_id for record in included for source_id in record.source_ids
    )
    objective_ids = tuple(record.objective_id for record in included)
    field_names = tuple(field.name for record in included for field in record.fields)
    target_lengths = tuple(
        sum(len(value) for value in _field_values(record, target_names))
        for record in included
    )
    context_lengths = tuple(
        sum(len(value) for value in _field_values(record, context_names))
        for record in included
    )
    language_values: list[str] = []
    qualified = 0
    unqualified = 0
    for record in included:
        tokens = []
        for field in record.fields:
            token = _language_token(field)
            if token is not None:
                tokens.append(token)
        if tokens:
            qualified += len(tokens)
            language_values.extend(tokens)
        else:
            unqualified += 1
            language_values.append(LANGUAGE_UNQUALIFIED)
    role_values: tuple[str, ...]
    if recipe.target_row_schema == "messages" and included_count:
        role_values = ("assistant",) * included_count + ("user",) * included_count
    else:
        role_values = ()
    row_schema_values = (recipe.target_row_schema,) * included_count
    exclusion_values = tuple(
        decision.reason_codes[0]
        for decision in curation.decisions
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
        for entry in curation.coverage_ledger.entries
    }
    blocker_count = sum(
        len(entry.blocker_codes) for entry in curation.coverage_ledger.entries
    )
    facts = (
        _text_fact("context-length-distribution", _length_histogram(context_lengths)),
        _count_fact("coverage-blocker-count", blocker_count),
        _text_fact("coverage-distribution", coverage_payload),
        _count_fact("distinct-objective-count", len(set(objective_ids))),
        _count_fact("distinct-source-count", len(set(source_ids))),
        _count_fact("evaluation-record-count", split.realized_evaluation_record_count),
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
                "evaluation": split.realized_evaluation_record_count,
                "train": split.realized_train_record_count,
            },
        ),
        _text_fact("target-length-distribution", _length_histogram(target_lengths)),
        _count_fact("train-record-count", split.realized_train_record_count),
    )
    names = tuple(item.name for item in facts)
    if names != DISTRIBUTION_FACT_NAMES:
        raise QualityReportError("distribution facts must match the v1 name set")
    return assemble_quality_report(plan_id=curation.plan_id, facts=facts)
