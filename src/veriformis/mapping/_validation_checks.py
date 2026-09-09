"""Independent imported dataset assertions against captured source bytes."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from veriformis.datasets.serialization import ProductRow
from veriformis.errors import DatasetValidationError
from veriformis.identity import derive_source_id, lossless_json_bytes, sha256_digest
from veriformis.mapping.capture import capture_row_source
from veriformis.mapping.detect import confirm_mapping_plan
from veriformis.mapping.execute import execute_mapping
from veriformis.mapping.result import MappingRecipe, MappingResult


def replay_captured_mapping(mapping_plan, recipe, mapping_result, raw_sources):
    if set(raw_sources) != set(recipe.source_ids):
        raise DatasetValidationError("mapping replay requires the exact captured source set")
    captures = {}
    digests = {}
    for source_id, (logical_path, raw) in sorted(raw_sources.items()):
        digest = sha256_digest(raw)
        if derive_source_id(logical_path, digest) != source_id:
            raise DatasetValidationError("mapping replay source identity differs from captured bytes")
        captures[source_id] = capture_row_source(Path(logical_path), logical_path=logical_path, raw_bytes=raw)
        digests[source_id] = digest
    confirm_mapping_plan(mapping_plan, tuple(
        (raw_sources[key][0], digests[key]) for key in sorted(raw_sources)
    ))
    rebuilt_recipe = MappingRecipe.create(plan=mapping_plan, source_ids=tuple(sorted(raw_sources)))
    records = tuple(record for source_id, capture in captures.items() for record in execute_mapping(
        mapping_plan, capture, source_id=source_id, recipe=rebuilt_recipe,
    ))
    rebuilt_result = MappingResult.create(
        plan=mapping_plan, recipe=rebuilt_recipe, records=records,
        row_source_ids=tuple(capture.row_source.row_source_id for capture in captures.values()),
    )
    return recipe == rebuilt_recipe and mapping_result == rebuilt_result, digests


def direct_import_checks(plan, recipe, mapping_result, curation, split, row_set, snapshot, files):
    from veriformis.mapping.finish import exact_imported_fingerprint

    records = {record.record_id: record for record in mapping_result.records}
    included = [records[key] for key in curation.included_record_ids if key in records]
    counts = Counter(record.source_id for record in included)
    fingerprints = [exact_imported_fingerprint(record) for record in included]
    assignments = {item.record_id: item for item in split.assignments}
    group_parts = {}
    fingerprint_parts = {"train": set(), "evaluation": set()}
    leakage = True
    for group in split.groups:
        parts = {assignments[key].partition for key in group.record_ids if key in assignments}
        leakage = leakage and len(parts) == 1 and all(key in assignments for key in group.record_ids)
        group_parts[group.group_id] = parts
    for item in split.assignments:
        if item.record_id not in records:
            leakage = False
        else:
            fingerprint_parts[item.partition].add(exact_imported_fingerprint(records[item.record_id]))
        leakage = leakage and group_parts.get(item.group_id) == {item.partition}
    leakage = leakage and not (fingerprint_parts["train"] & fingerprint_parts["evaluation"])
    rows = (*row_set.train_rows, *row_set.evaluation_rows)
    payloads = {}
    lengths = []
    for record in included:
        values = {field.name: field.value for field in record.fields}
        for key in ("messages", "turns", "steps"):
            if key in values:
                values[key] = json.loads(values[key])
        payloads[record.record_id] = values
        if "messages" in values:
            target = values["messages"][-1]["content"]
        elif "turns" in values:
            target = values["turns"][-1]["content"]
        elif "steps" in values:
            target = values["steps"][-1]
        else:
            target = next(values[key] for key in ("text", "completion", "output", "label", "chosen") if key in values)
        lengths.append(len(target))
    cap = plan.curation_policy.maximum_records_per_primary_source
    quality = all(length >= plan.curation_policy.minimum_target_characters for length in lengths)
    quality = quality and (plan.curation_policy.balance_mode != "primary_source_cap" or (
        cap is not None and all(count <= cap for count in counts.values())
    ))
    expected_files = (
        b"".join(lossless_json_bytes(row.payload) + b"\n" for row in row_set.train_rows),
        b"".join(lossless_json_bytes(row.payload) + b"\n" for row in row_set.evaluation_rows),
        b"".join(lossless_json_bytes(item.model_dump(mode="json")) + b"\n" for item in row_set.provenance),
    )
    return {
        "record-lifecycle": all(
            record.recipe_id == recipe.recipe_id and record.mapping_plan_id == recipe.mapping_plan_id
            and record.source_id in recipe.source_ids and record.objective_id == recipe.objective_id
            for record in records.values()
        ),
        "curation": (
            set(curation.input_record_ids) == set(records)
            and {item.record_id for item in curation.decisions} == set(records)
            and len(curation.decisions) == len(records)
            and set(curation.included_record_ids) <= set(records)
        ),
        "deduplication": len(fingerprints) == len(set(fingerprints)),
        "quality": quality,
        "coverage": (
            {item.source_id for item in curation.coverage_ledger.entries} == set(recipe.source_ids)
            and all(not item.blocker_codes and item.included_count == counts[item.source_id]
                    for item in curation.coverage_ledger.entries)
        ),
        "split": (
            len(assignments) == len(split.assignments)
            and set(assignments) == set(curation.included_record_ids)
            and split.realized_train_record_count == sum(item.partition == "train" for item in split.assignments)
            and split.realized_evaluation_record_count == sum(item.partition == "evaluation" for item in split.assignments)
        ),
        "leakage": leakage,
        "row-binding": (
            len(rows) == len(included) and {row.record_id for row in rows} == set(payloads)
            and all(row.payload == payloads.get(row.record_id) and assignments[row.record_id].partition == partition
                    for partition, members in (("train", row_set.train_rows), ("evaluation", row_set.evaluation_rows))
                    for row in members)
        ),
        "schema": row_set.row_schema == recipe.row_schema == plan.serialization_plan.row_schema
                  and all(ProductRow.model_validate_json(row.model_dump_json()) == row for row in rows),
        "encoding": files == expected_files,
        "partition-nonempty": bool(row_set.train_rows) and (bool(row_set.evaluation_rows) or not plan.split_policy.evaluation_required),
        "snapshot": all(binding.sha256 == sha256_digest(raw) and binding.byte_size == len(raw)
                        for binding, raw in zip(snapshot.file_bindings, files, strict=True)),
    }
