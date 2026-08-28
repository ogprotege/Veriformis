"""Phase 17.3 keyed leakage grouping. Default SFT split stays unchanged."""

from __future__ import annotations

import pytest
from veriformis.chunkers.strategies import chunk_paragraph
from veriformis.construction import (
    ConstructionInputs,
    ConstructionPass,
    DatasetRecipe,
    SegmentationPolicy,
    TrainingObjective,
    construct_dataset,
)
from veriformis.datasets import (
    CoverageLedger,
    CoverageLedgerEntry,
    CurationDecision,
    CurationPolicy,
    CurationResult,
    FinishedDatasetPlan,
    SerializationPlan,
    SplitPolicy,
    V1_SPLIT_ALGORITHM,
    split_dataset,
)
from veriformis.datasets.splitting import (
    SplitPolicy as SplitPolicyModel,
    assign_leakage_partitions,
    build_leakage_groups,
)
from veriformis.errors import SplitError
from veriformis.families import (
    EXTRA_GROUPING_KEYS,
    LEAKAGE_GROUPING_KEYS,
    keyed_leakage_groups,
    keyed_split_assignments,
)
from veriformis.identity import canonical_digest
from veriformis.ir import Document, Paragraph, Text, attach_canonical_provenance
from veriformis.sources import register_source
from veriformis.taxonomy import (
    IMPLEMENTED_TRAINING_FAMILIES,
    PLANNED_TRAINING_FAMILIES,
)


def _policy() -> SplitPolicy:
    return SplitPolicy.create(
        evaluation_ratio_ppm=500_000,
        evaluation_required=True,
        seed="split-seed",
    )


def _source_bundle(tmp_path, *, logical_path: str, text: str):
    document = Document(children=[Paragraph(children=[Text(text)])])
    stream = attach_canonical_provenance(document)
    source = register_source(
        tmp_path / logical_path,
        "fixture",
        stream,
        logical_path=logical_path,
        raw_bytes=stream.encode("utf-8"),
    )
    document.source_id = source.id
    chunks = chunk_paragraph(
        document.children,
        max_size=1_000,
        source=source,
        transformed=set(),
        block_derivations={},
        region_id="body",
    )
    return source, tuple(chunks)


def _recipe(sources) -> DatasetRecipe:
    return DatasetRecipe.create(
        objective=TrainingObjective.create("full_text"),
        source_ids=tuple(source.id for source in sources),
        cleaning_config_digest=canonical_digest({"cleaning": "fixture-v1"}),
        segmentation=SegmentationPolicy(
            schema_version="veriformis.segmentation-policy/v1",
            strategy="paragraph",
            size=1_000,
            overlap=100,
        ),
        passes=(ConstructionPass.create(sequence=1, objective_kind="full_text"),),
        target_row_schema="text",
    )


def _case(tmp_path, texts: tuple[str, ...]):
    bundles = tuple(
        _source_bundle(
            tmp_path,
            logical_path=f"source-{index}.txt",
            text=text,
        )
        for index, text in enumerate(texts)
    )
    sources = tuple(source for source, _chunks in bundles)
    recipe = _recipe(sources)
    inputs = ConstructionInputs.create(
        cleaning_config_digest=recipe.cleaning_config_digest,
        sources=sources,
        chunks=tuple(chunk for _source, chunks in bundles for chunk in chunks),
    )
    construction = construct_dataset(recipe, inputs)
    policy = CurationPolicy.create(minimum_target_characters=0)
    plan = FinishedDatasetPlan.create(
        recipe_id=recipe.recipe_id,
        construction_result_id=construction.result_id,
        curation_policy=policy,
        split_policy=_policy(),
        serialization_plan=SerializationPlan.create(row_schema="text"),
    )
    ordered_records = tuple(
        sorted(construction.records, key=lambda item: item.record_id)
    )
    selected_source_ids = tuple(sorted(source.id for source, _chunks in bundles))
    decisions = tuple(
        CurationDecision.create(
            record_id=record.record_id,
            status="included",
            reason_code="quality-passed",
        )
        for record in ordered_records
    )
    entries = tuple(
        CoverageLedgerEntry.create(
            source_id=source_id,
            candidate_count=sum(
                source_id in candidate.source_ids
                for candidate in construction.candidates
            ),
            record_count=sum(
                source_id in record.source_ids for record in construction.records
            ),
            included_count=sum(
                source_id in record.source_ids for record in construction.records
            ),
            excluded_count=0,
            quarantined_count=0,
            primary_included_count=sum(
                record.source_ids[0] == source_id for record in construction.records
            ),
        )
        for source_id in selected_source_ids
    )
    curation = CurationResult.create(
        plan_id=plan.plan_id,
        recipe_id=construction.recipe_id,
        construction_result_id=construction.result_id,
        policy_id=policy.policy_id,
        input_record_ids=tuple(record.record_id for record in ordered_records),
        decisions=decisions,
        findings=(),
        included_record_ids=tuple(record.record_id for record in ordered_records),
        coverage_ledger=CoverageLedger.create(
            selected_source_ids=selected_source_ids,
            entries=entries,
        ),
    )
    raw_digests = {source.id: source.sha256 for source, _chunks in bundles}
    return construction, curation, raw_digests, plan


def _included(construction, curation):
    by_id = {record.record_id: record for record in construction.records}
    records = tuple(by_id[record_id] for record_id in curation.included_record_ids)
    source_bases = {record.record_id: record.source_ids for record in records}
    return records, source_bases


def test_grouping_key_vocabulary_is_closed() -> None:
    assert LEAKAGE_GROUPING_KEYS == (
        "source",
        "shared-prompt",
        "conversation",
        "annotator",
        "entity",
    )
    assert EXTRA_GROUPING_KEYS == (
        "shared-prompt",
        "conversation",
        "annotator",
        "entity",
    )
    assert V1_SPLIT_ALGORITHM == "transitive-leakage-prefix-v1"
    assert set(SplitPolicyModel.model_fields) == {
        "schema_version",
        "policy_id",
        "algorithm",
        "evaluation_ratio_ppm",
        "evaluation_required",
        "seed",
    }


def test_source_only_keyed_groups_match_default_sft_groups(tmp_path) -> None:
    construction, curation, raw_digests, plan = _case(
        tmp_path,
        ("alpha unique text", "beta unique text", "gamma unique text"),
    )
    records, source_bases = _included(construction, curation)
    default = split_dataset(plan, construction, curation, raw_digests)
    keyed = keyed_leakage_groups(
        records,
        raw_digests,
        source_bases,
        grouping_keys=("source",),
        values_by_record={record.record_id: {} for record in records},
    )
    built = build_leakage_groups(records, raw_digests, source_bases)
    assert keyed == default.groups == built
    assert default.policy_id == plan.split_policy.policy_id
    assert plan.split_policy.algorithm == V1_SPLIT_ALGORITHM


def test_shared_prompt_cannot_straddle_partitions(tmp_path) -> None:
    construction, curation, raw_digests, plan = _case(
        tmp_path,
        ("first independent source", "second independent source", "third independent"),
    )
    records, source_bases = _included(construction, curation)
    default = split_dataset(plan, construction, curation, raw_digests)
    assert len(default.groups) == 3
    first, second, third = records
    values = {
        first.record_id: {"shared-prompt": "same-item"},
        second.record_id: {"shared-prompt": "same-item"},
        third.record_id: {"shared-prompt": "other-item"},
    }
    groups, assignments, _requested = keyed_split_assignments(
        plan.split_policy,
        records,
        raw_digests,
        source_bases,
        curation.included_record_ids,
        grouping_keys=("shared-prompt", "source"),
        values_by_record=values,
    )
    assert len(groups) == 2
    partition = {item.record_id: item.partition for item in assignments}
    assert partition[first.record_id] == partition[second.record_id]
    default_partition = {
        item.record_id: item.partition for item in default.assignments
    }
    assert default_partition.keys() == partition.keys()


def test_annotators_on_the_same_item_stay_together(tmp_path) -> None:
    construction, curation, raw_digests, plan = _case(
        tmp_path,
        ("item a annotator one", "item a annotator two", "unrelated item"),
    )
    records, source_bases = _included(construction, curation)
    first, second, third = records
    values = {
        first.record_id: {"annotator": "alice", "entity": "item-a"},
        second.record_id: {"annotator": "bob", "entity": "item-a"},
        third.record_id: {"annotator": "carol", "entity": "item-b"},
    }
    groups, assignments, _requested = keyed_split_assignments(
        plan.split_policy,
        records,
        raw_digests,
        source_bases,
        curation.included_record_ids,
        grouping_keys=("annotator", "entity", "source"),
        values_by_record=values,
    )
    assert any(
        {first.record_id, second.record_id}.issubset(set(group.record_ids))
        for group in groups
    )
    assert all(third.record_id not in group.record_ids or len(group.record_ids) == 1 for group in groups)
    partition = {item.record_id: item.partition for item in assignments}
    assert partition[first.record_id] == partition[second.record_id]


def test_missing_grouping_value_fails_closed(tmp_path) -> None:
    construction, curation, raw_digests, _plan = _case(
        tmp_path,
        ("alpha unique text", "beta unique text"),
    )
    records, source_bases = _included(construction, curation)
    values = {
        records[0].record_id: {"annotator": "alice"},
        records[1].record_id: {"annotator": ""},
    }
    with pytest.raises(SplitError, match="missing or empty"):
        keyed_leakage_groups(
            records,
            raw_digests,
            source_bases,
            grouping_keys=("annotator", "source"),
            values_by_record=values,
        )


def test_unknown_grouping_key_fails_closed(tmp_path) -> None:
    construction, curation, raw_digests, _plan = _case(
        tmp_path,
        ("alpha unique text", "beta unique text"),
    )
    records, source_bases = _included(construction, curation)
    with pytest.raises(SplitError, match="unknown leakage grouping key: 'topic'"):
        keyed_leakage_groups(
            records,
            raw_digests,
            source_bases,
            grouping_keys=("source", "topic"),
            values_by_record={record.record_id: {} for record in records},
        )


def test_grouping_does_not_guess_values_from_record_fields(tmp_path) -> None:
    construction, curation, raw_digests, _plan = _case(
        tmp_path,
        ("shared wording in the source", "shared wording in the source"),
    )
    records, source_bases = _included(construction, curation)
    with pytest.raises(SplitError, match="exactly the selected extra keys"):
        keyed_leakage_groups(
            records,
            raw_digests,
            source_bases,
            grouping_keys=("shared-prompt", "source"),
            values_by_record={record.record_id: {} for record in records},
        )


def test_default_sft_assignment_digest_is_unchanged(tmp_path) -> None:
    construction, curation, raw_digests, plan = _case(
        tmp_path,
        ("alpha unique text", "beta unique text", "gamma unique text"),
    )
    first = split_dataset(plan, construction, curation, raw_digests)
    second = split_dataset(plan, construction, curation, raw_digests)
    assert first.assignment_digest == second.assignment_digest
    records, source_bases = _included(construction, curation)
    assignments, requested = assign_leakage_partitions(
        plan.split_policy,
        first.groups,
        curation.included_record_ids,
    )
    assert assignments == first.assignments
    assert requested == first.requested_evaluation_record_count
    assert {record.record_id for record in records} == set(curation.included_record_ids)
    assert source_bases


def test_keyed_grouping_does_not_admit_other_families() -> None:
    assert IMPLEMENTED_TRAINING_FAMILIES == (
        "source-grounded-language-modeling",
        "source-grounded-supervised-fine-tuning",
        "explicit-label-classification",
        "preference-and-ranking",
    )
    assert "preference-and-ranking" not in PLANNED_TRAINING_FAMILIES
    assert "explicit-label-classification" not in PLANNED_TRAINING_FAMILIES
