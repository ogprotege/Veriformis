"""Pure deterministic curation over replay-validated construction records."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING, Literal

from veriformis.construction import (
    ConstructionInputs,
    ConstructionResult,
    DatasetRecipe,
    DatasetRecord,
    validate_construction_result,
)
from veriformis.identity import canonical_digest

from .models import (
    CoverageLedger,
    CoverageLedgerEntry,
    CurationDecision,
    CurationError,
    CurationReasonCode,
    CurationResult,
    CurationStatus,
    QualityFinding,
)

if TYPE_CHECKING:
    from .plan import FinishedDatasetPlan


ObjectiveKind = Literal[
    "full_text",
    "continuation",
    "section_reconstruction",
    "before_after_transformation",
    "structured_field",
    "explicit_label",
    "preference_pair",
    "tool_call",
    "stepwise",
]

OBJECTIVE_FIELD_ROLES: Mapping[
    str,
    tuple[tuple[str, ...], tuple[str, ...]],
] = MappingProxyType(
    {
        # A full-text objective has no separate prompt. Using the exact text as
        # both context and target prevents unrelated documents from forming one
        # false empty-context conflict class.
        "full_text": (("text",), ("text",)),
        "continuation": (("prompt",), ("completion",)),
        "section_reconstruction": (("heading",), ("section",)),
        "before_after_transformation": (("before",), ("after",)),
        "structured_field": (("input",), ("fields",)),
        "explicit_label": (("context",), ("label",)),
        "preference_pair": (("prompt",), ("chosen",)),
        "tool_call": (("conversation_id",), ("turns",)),
        "stepwise": (("prompt",), ("steps",)),
    }
)


def exact_record_fingerprint(record: DatasetRecord) -> str:
    """Digest only objective identity plus ordered exact field names/values."""
    return canonical_digest(
        {
            "schema_version": "veriformis.exact-record-fingerprint/v1",
            "objective_id": record.objective_id,
            "fields": tuple(
                {"name": field.name, "value": field.value} for field in record.fields
            ),
        }
    )


def curate_dataset(
    plan: FinishedDatasetPlan,
    recipe: DatasetRecipe,
    inputs: ConstructionInputs,
    construction_result: ConstructionResult,
) -> CurationResult:
    """Replay construction, then apply the exact v1 curation order.

    The order is minimum-target filtering, conflicting-target quarantine,
    exact deduplication, optional primary-source cap, then coverage closure.
    """
    from .plan import finished_dataset_plan_from_dict

    checked_result = validate_construction_result(
        recipe,
        inputs,
        construction_result,
    )
    try:
        checked_plan = finished_dataset_plan_from_dict(plan.model_dump(mode="json"))
    except (AttributeError, TypeError, UnicodeError, ValueError) as exc:
        raise CurationError(f"invalid finished dataset plan: {exc}") from exc
    if checked_plan.recipe_id != recipe.recipe_id:
        raise CurationError("finished dataset plan names another recipe")
    if checked_plan.construction_result_id != checked_result.result_id:
        raise CurationError("finished dataset plan names another construction result")
    if checked_plan.serialization_plan.row_schema != recipe.target_row_schema:
        raise CurationError(
            "finished dataset plan row schema differs from its construction recipe"
        )

    records = tuple(sorted(checked_result.records, key=lambda item: item.record_id))
    objective_kind = recipe.objective.kind
    context_names, target_names = OBJECTIVE_FIELD_ROLES[objective_kind]
    outcomes: dict[
        str,
        tuple[CurationStatus, CurationReasonCode, QualityFinding | None],
    ] = {}
    remaining: dict[str, DatasetRecord] = {}

    # 1. Invalid short targets cannot poison an otherwise valid conflict class.
    for record in records:
        target_count = sum(
            len(value) for _, value in _selected_fields(record, target_names)
        )
        minimum = checked_plan.curation_policy.minimum_target_characters
        if target_count < minimum:
            finding = QualityFinding.create(
                record_id=record.record_id,
                code="target-too-short",
                observed_count=target_count,
                required_count=minimum,
            )
            outcomes[record.record_id] = (
                "excluded",
                "target-too-short",
                finding,
            )
        else:
            remaining[record.record_id] = record

    # 2. The same objective-specific context within one exact source scope,
    # paired with distinct targets, is a deterministic conflict. Source scope
    # prevents common prompts in unrelated documents from poisoning each other.
    conflict_groups: dict[
        tuple[str, tuple[str, ...], tuple[tuple[str, str], ...]],
        list[DatasetRecord],
    ] = {}
    for record in remaining.values():
        key = (
            record.objective_id,
            record.source_ids,
            _selected_fields(record, context_names),
        )
        conflict_groups.setdefault(key, []).append(record)
    conflicted: set[str] = set()
    for group in conflict_groups.values():
        target_variants = {_selected_fields(record, target_names) for record in group}
        if len(target_variants) < 2:
            continue
        ordered_group = tuple(sorted(group, key=lambda item: item.record_id))
        for record in ordered_group:
            related = tuple(
                item.record_id
                for item in ordered_group
                if item.record_id != record.record_id
            )
            finding = QualityFinding.create(
                record_id=record.record_id,
                code="conflicting-target",
                related_record_ids=related,
                observed_count=len(target_variants),
            )
            outcomes[record.record_id] = (
                "quarantined",
                "conflicting-target",
                finding,
            )
            conflicted.add(record.record_id)
    for record_id in conflicted:
        del remaining[record_id]

    # 3. Exact duplicates use only objective ID plus ordered exact field values.
    duplicate_groups: dict[str, list[DatasetRecord]] = {}
    for record in remaining.values():
        duplicate_groups.setdefault(exact_record_fingerprint(record), []).append(record)
    duplicates: set[str] = set()
    for group in duplicate_groups.values():
        if len(group) < 2:
            continue
        ordered_group = tuple(sorted(group, key=lambda item: item.record_id))
        representative = ordered_group[0]
        for record in ordered_group[1:]:
            finding = QualityFinding.create(
                record_id=record.record_id,
                code="exact-duplicate",
                related_record_ids=(representative.record_id,),
            )
            outcomes[record.record_id] = (
                "excluded",
                "exact-duplicate",
                finding,
            )
            duplicates.add(record.record_id)
    for record_id in duplicates:
        del remaining[record_id]

    # 4. The primary source of a multi-source record is its canonical first ID.
    policy = checked_plan.curation_policy
    if policy.balance_mode == "primary_source_cap":
        cap = policy.maximum_records_per_primary_source
        assert cap is not None
        source_counts: dict[str, int] = {}
        capped: set[str] = set()
        for record in sorted(remaining.values(), key=lambda item: item.record_id):
            primary_source_id = record.source_ids[0]
            ordinal = source_counts.get(primary_source_id, 0) + 1
            source_counts[primary_source_id] = ordinal
            if ordinal <= cap:
                continue
            finding = QualityFinding.create(
                record_id=record.record_id,
                code="primary-source-cap",
                observed_count=ordinal,
                required_count=cap,
            )
            outcomes[record.record_id] = (
                "excluded",
                "primary-source-cap",
                finding,
            )
            capped.add(record.record_id)
        for record_id in capped:
            del remaining[record_id]

    for record in remaining.values():
        outcomes[record.record_id] = ("included", "quality-passed", None)

    findings = tuple(
        sorted(
            (finding for _, _, finding in outcomes.values() if finding is not None),
            key=lambda item: item.finding_id,
        )
    )
    decisions = tuple(
        CurationDecision.create(
            record_id=record.record_id,
            status=outcomes[record.record_id][0],
            reason_code=outcomes[record.record_id][1],
            finding_ids=(
                (outcomes[record.record_id][2].finding_id,)
                if outcomes[record.record_id][2] is not None
                else ()
            ),
        )
        for record in records
    )
    coverage = _build_coverage_ledger(
        recipe,
        checked_result,
        decisions,
    )
    included_record_ids = tuple(
        decision.record_id for decision in decisions if decision.status == "included"
    )
    return CurationResult.create(
        plan_id=checked_plan.plan_id,
        recipe_id=recipe.recipe_id,
        construction_result_id=checked_result.result_id,
        policy_id=policy.policy_id,
        input_record_ids=tuple(record.record_id for record in records),
        decisions=decisions,
        findings=findings,
        included_record_ids=included_record_ids,
        coverage_ledger=coverage,
    )


def _selected_fields(
    record: DatasetRecord,
    names: tuple[str, ...],
) -> tuple[tuple[str, str], ...]:
    fields = {field.name: field.value for field in record.fields}
    try:
        return tuple((name, fields[name]) for name in names)
    except KeyError as exc:  # Construction replay should make this unreachable.
        raise CurationError(
            f"record fields do not implement objective role {exc.args[0]!r}"
        ) from exc


def _build_coverage_ledger(
    recipe: DatasetRecipe,
    result: ConstructionResult,
    decisions: tuple[CurationDecision, ...],
) -> CoverageLedger:
    decisions_by_record = {decision.record_id: decision for decision in decisions}
    entries: list[CoverageLedgerEntry] = []
    for source_id in recipe.source_ids:
        candidates = tuple(
            candidate
            for candidate in result.candidates
            if source_id in candidate.source_ids
        )
        records = tuple(
            record for record in result.records if source_id in record.source_ids
        )
        counts = {"included": 0, "excluded": 0, "quarantined": 0}
        primary_included_count = 0
        for record in records:
            decision = decisions_by_record[record.record_id]
            counts[decision.status] += 1
            if decision.status == "included" and record.source_ids[0] == source_id:
                primary_included_count += 1
        entries.append(
            CoverageLedgerEntry.create(
                source_id=source_id,
                candidate_count=len(candidates),
                record_count=len(records),
                included_count=counts["included"],
                excluded_count=counts["excluded"],
                quarantined_count=counts["quarantined"],
                primary_included_count=primary_included_count,
            )
        )
    return CoverageLedger.create(
        selected_source_ids=recipe.source_ids,
        entries=tuple(entries),
    )


__all__ = [
    "OBJECTIVE_FIELD_ROLES",
    "curate_dataset",
    "exact_record_fingerprint",
]
