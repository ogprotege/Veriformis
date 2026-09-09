"""Direct validation invariants independent of stage replay implementations."""

from __future__ import annotations

from collections import Counter

from veriformis.datasets.curation import OBJECTIVE_FIELD_ROLES, exact_record_fingerprint
from veriformis.datasets.serialization import ProductRow
from veriformis.errors import VeriformisError


def record_lifecycle(construction) -> bool:
    candidates = {item.candidate_id: item for item in construction.candidates}
    decisions = {item.candidate_id: item for item in construction.decisions}
    accepted = {key for key, item in decisions.items() if item.status == "accepted"}
    return (
        set(candidates) == set(decisions)
        and len(decisions) == len(construction.decisions)
        and accepted == {item.candidate_id for item in construction.records}
        and len(accepted) == len(construction.records)
        and all(
            item.decision_id == decisions[item.candidate_id].decision_id
            and item.fields == candidates[item.candidate_id].fields
            for item in construction.records
        )
    )


def curation_checks(plan, recipe, construction, curation) -> dict[str, bool]:
    records = {item.record_id: item for item in construction.records}
    included = [records[key] for key in curation.included_record_ids if key in records]
    fingerprints = [exact_record_fingerprint(item) for item in included]
    targets = OBJECTIVE_FIELD_ROLES[recipe.objective.kind][1]
    counts = Counter(item.source_ids[0] for item in included)
    cap = plan.curation_policy.maximum_records_per_primary_source
    return {
        "curation": (
            set(curation.input_record_ids) == set(records)
            and {item.record_id for item in curation.decisions} == set(records)
            and len(curation.decisions) == len(records)
            and set(curation.included_record_ids) <= set(records)
        ),
        "deduplication": len(fingerprints) == len(set(fingerprints)),
        "quality": all(
            sum(len(field.value) for field in item.fields if field.name in targets)
            >= plan.curation_policy.minimum_target_characters for item in included
        ),
        "balance": (
            plan.curation_policy.balance_mode != "primary_source_cap"
            or (cap is not None and all(count <= cap for count in counts.values()))
        ),
    }


def leakage_check(split) -> bool:
    groups = {item.group_id: item for item in split.groups}
    parts = {"train": set(), "evaluation": set()}
    tokens = {"train": set(), "evaluation": set()}
    for item in split.assignments:
        if item.group_id not in groups or item.partition not in parts:
            return False
        group = groups[item.group_id]
        if item.record_id not in group.record_ids:
            return False
        parts[item.partition].add(group.group_id)
        tokens[item.partition].update(("source", value) for value in group.source_ids)
        tokens[item.partition].update(("raw", value) for value in group.raw_sha256_values)
        tokens[item.partition].update(("exact", value) for value in group.exact_record_fingerprints)
    return not (parts["train"] & parts["evaluation"] or tokens["train"] & tokens["evaluation"])


def row_checks(plan, recipe, construction, curation, split, row_set) -> dict[str, bool]:
    records = {item.record_id: item for item in construction.records}
    rows = (*row_set.train_rows, *row_set.evaluation_rows)
    assignments = {item.record_id: item.partition for item in split.assignments}
    row_ids = [item.record_id for item in rows]
    binding = len(set(row_ids)) == len(rows) and set(row_ids) == set(curation.included_record_ids)
    binding = binding and all(
        assignments.get(row.record_id) == partition
        for partition, members in (("train", row_set.train_rows), ("evaluation", row_set.evaluation_rows))
        for row in members
    )
    objective = all(
        item.objective_id == recipe.objective.objective_id for item in construction.records
    ) and all(item.objective_id == recipe.objective.objective_id for item in row_set.provenance)
    schema = row_set.row_schema == recipe.target_row_schema == plan.serialization_plan.row_schema
    try:
        schema = schema and all(
            ProductRow.model_validate_json(item.model_dump_json()) == item for item in rows
        )
    except (ValueError, VeriformisError):
        schema = False
    target_names = OBJECTIVE_FIELD_ROLES[recipe.objective.kind][1]
    context_names = OBJECTIVE_FIELD_ROLES[recipe.objective.kind][0]
    masking = True
    nonempty = True
    for row in rows:
        if row.record_id not in records:
            masking = False
            continue
        fields = {field.name: field.value for field in records[row.record_id].fields}
        if len(target_names) != 1 or len(context_names) != 1:
            masking = False
            continue
        target, context = fields[target_names[0]], fields[context_names[0]]
        payload = row.payload
        if row.row_schema == "text":
            expected = {"text": target}
        elif row.row_schema == "prompt_completion":
            expected = {"prompt": context, "completion": target}
        elif row.row_schema == "instruction_output":
            expected = {"instruction": plan.serialization_plan.instruction_text, "input": context, "output": target}
        elif row.row_schema == "messages":
            expected = {"messages": [{"role": "user", "content": context}, {"role": "assistant", "content": target}]}
        else:
            # Advanced-family document construction remains unadmitted.
            masking = False
            continue
        masking = masking and payload == expected
        nonempty = nonempty and isinstance(target, str) and bool(target)
    return {"row-binding": binding, "objective": objective, "schema": schema,
            "masking": masking, "aptus-row-shape": nonempty and schema}
