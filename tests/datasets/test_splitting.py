from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from veriformis.chunkers.strategies import chunk_paragraph
from veriformis.construction import (
    CandidateRecord,
    ConstructionInputs,
    ConstructionPass,
    ConstructionResult,
    DatasetRecipe,
    DatasetRecord,
    PromotionDecision,
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
    curate_dataset,
)
from veriformis.datasets.splitting import (
    V1_PARTITIONS,
    LeakageGroup,
    RecordAssignment,
    SplitPolicy,
    SplitResult,
    leakage_group_from_json_bytes,
    leakage_group_to_dict,
    record_assignment_from_json_bytes,
    record_assignment_to_dict,
    split_dataset,
    split_policy_from_dict,
    split_policy_from_json_bytes,
    split_policy_to_dict,
    split_result_from_dict,
    split_result_from_json_bytes,
    split_result_to_dict,
    validate_split_result,
)
from veriformis.errors import DuplicateIdentityError, SplitError
from veriformis.identity import (
    canonical_digest,
    lossless_json_bytes,
    sha256_digest,
)
from veriformis.ir import Document, Paragraph, Text, attach_canonical_provenance
from veriformis.sources import register_source


def source_bundle(tmp_path, *, logical_path: str, blocks, max_size: int = 1_000):
    document = Document(children=list(blocks))
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
        max_size=max_size,
        source=source,
        transformed=set(),
        block_derivations={},
        region_id="body",
    )
    return SimpleNamespace(source=source, chunks=tuple(chunks))


def recipe_for(sources, objective_kind: str):
    objective = TrainingObjective.create(objective_kind)
    construction_pass = ConstructionPass.create(
        sequence=1,
        objective_kind=objective_kind,
    )
    return DatasetRecipe.create(
        objective=objective,
        source_ids=tuple(source.id for source in sources),
        cleaning_config_digest=canonical_digest({"cleaning": "fixture-v1"}),
        segmentation=SegmentationPolicy(
            schema_version="veriformis.segmentation-policy/v1",
            strategy="paragraph",
            size=1_000,
            overlap=100,
        ),
        passes=(construction_pass,),
        target_row_schema=(
            "text" if objective_kind == "full_text" else "prompt_completion"
        ),
    )


def inputs_for(bundles):
    return ConstructionInputs.create(
        cleaning_config_digest=canonical_digest({"cleaning": "fixture-v1"}),
        sources=tuple(bundle.source for bundle in bundles),
        chunks=tuple(chunk for bundle in bundles for chunk in bundle.chunks),
    )


def _case(
    tmp_path,
    texts: tuple[str, ...],
    *,
    split_policy: SplitPolicy | None = None,
):
    bundles = tuple(
        source_bundle(
            tmp_path,
            logical_path=f"source-{index}.txt",
            blocks=[Paragraph(children=[Text(text)])],
        )
        for index, text in enumerate(texts)
    )
    recipe = recipe_for(
        tuple(bundle.source for bundle in bundles),
        "full_text",
    )
    inputs = inputs_for(bundles)
    construction = construct_dataset(recipe, inputs)
    curation_policy = CurationPolicy.create(minimum_target_characters=0)
    selected_split_policy = split_policy or _policy()
    plan = FinishedDatasetPlan.create(
        recipe_id=recipe.recipe_id,
        construction_result_id=construction.result_id,
        curation_policy=curation_policy,
        split_policy=selected_split_policy,
        serialization_plan=SerializationPlan.create(row_schema="text"),
    )
    curation = curate_dataset(
        plan,
        recipe,
        inputs,
        construction,
    )
    raw_digests = {bundle.source.id: bundle.source.sha256 for bundle in bundles}
    return bundles, recipe, construction, curation, raw_digests, plan


def _construction_with_added_source(
    construction: ConstructionResult,
    *,
    record_id: str,
    added_source_ids: tuple[str, ...],
) -> ConstructionResult:
    target = next(
        record for record in construction.records if record.record_id == record_id
    )
    candidates = []
    decisions = []
    records = []
    original_decisions = {
        decision.candidate_id: decision for decision in construction.decisions
    }
    original_records = {record.candidate_id: record for record in construction.records}
    for candidate in construction.candidates:
        if candidate.candidate_id != target.candidate_id:
            candidates.append(candidate)
            decisions.append(original_decisions[candidate.candidate_id])
            records.append(original_records[candidate.candidate_id])
            continue
        replacement = CandidateRecord.create(
            ordinal=candidate.ordinal,
            recipe_id=candidate.recipe_id,
            objective_id=candidate.objective_id,
            pass_id=candidate.pass_id,
            source_ids=(*candidate.source_ids, *added_source_ids),
            chunk_ids=candidate.chunk_ids,
            transform_ids=candidate.transform_ids,
            fields=candidate.fields,
        )
        decision = PromotionDecision.create(
            candidate_id=replacement.candidate_id,
            status="accepted",
            reason_codes=("construction-integrity-v1",),
        )
        candidates.append(replacement)
        decisions.append(decision)
        records.append(DatasetRecord.promote(replacement, decision))
    return ConstructionResult.create(
        recipe_id=construction.recipe_id,
        input_digest=construction.input_digest,
        executed_pass_ids=construction.executed_pass_ids,
        candidates=tuple(candidates),
        decisions=tuple(decisions),
        records=tuple(records),
        diagnostics=construction.diagnostics,
    )


def _include_all(
    construction: ConstructionResult,
    selected_source_ids: tuple[str, ...],
    *,
    split_policy: SplitPolicy | None = None,
) -> tuple[FinishedDatasetPlan, CurationResult]:
    policy = CurationPolicy.create(minimum_target_characters=0)
    plan = FinishedDatasetPlan.create(
        recipe_id=construction.recipe_id,
        construction_result_id=construction.result_id,
        curation_policy=policy,
        split_policy=split_policy or _policy(),
        serialization_plan=SerializationPlan.create(row_schema="text"),
    )
    ordered_records = tuple(
        sorted(construction.records, key=lambda item: item.record_id)
    )
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
    ledger = CoverageLedger.create(
        selected_source_ids=selected_source_ids,
        entries=entries,
    )
    record_ids = tuple(record.record_id for record in ordered_records)
    curation = CurationResult.create(
        plan_id=plan.plan_id,
        recipe_id=construction.recipe_id,
        construction_result_id=construction.result_id,
        policy_id=policy.policy_id,
        input_record_ids=record_ids,
        decisions=decisions,
        findings=(),
        included_record_ids=record_ids,
        coverage_ledger=ledger,
    )
    return plan, curation


def _policy(
    *,
    ratio: int = 500_000,
    required: bool = True,
    seed: str = "split-seed",
) -> SplitPolicy:
    return SplitPolicy.create(
        evaluation_ratio_ppm=ratio,
        evaluation_required=required,
        seed=seed,
    )


def _rebind_split_policy(
    construction: ConstructionResult,
    curation: CurationResult,
    split_policy: SplitPolicy,
) -> tuple[FinishedDatasetPlan, CurationResult]:
    curation_policy = CurationPolicy.create(minimum_target_characters=0)
    assert curation.policy_id == curation_policy.policy_id
    plan = FinishedDatasetPlan.create(
        recipe_id=construction.recipe_id,
        construction_result_id=construction.result_id,
        curation_policy=curation_policy,
        split_policy=split_policy,
        serialization_plan=SerializationPlan.create(row_schema="text"),
    )
    rebound = CurationResult.create(
        plan_id=plan.plan_id,
        recipe_id=curation.recipe_id,
        construction_result_id=curation.construction_result_id,
        policy_id=curation.policy_id,
        input_record_ids=curation.input_record_ids,
        decisions=curation.decisions,
        findings=curation.findings,
        included_record_ids=curation.included_record_ids,
        coverage_ledger=curation.coverage_ledger,
    )
    return plan, rebound


def test_strict_models_and_exact_canonical_serde(tmp_path):
    _, _, construction, curation, raw_digests, plan = _case(
        tmp_path,
        ("alpha", "beta"),
    )
    policy = plan.split_policy
    result = split_dataset(plan, construction, curation, raw_digests)

    assert set(SplitPolicy.model_fields) == {
        "schema_version",
        "policy_id",
        "algorithm",
        "evaluation_ratio_ppm",
        "evaluation_required",
        "seed",
    }
    assert set(LeakageGroup.model_fields) == {
        "schema_version",
        "group_id",
        "record_ids",
        "source_ids",
        "raw_sha256_values",
        "exact_record_fingerprints",
    }
    assert set(RecordAssignment.model_fields) == {
        "schema_version",
        "assignment_id",
        "policy_id",
        "record_id",
        "group_id",
        "partition",
    }
    assert set(SplitResult.model_fields) == {
        "schema_version",
        "result_id",
        "policy_id",
        "plan_id",
        "construction_result_id",
        "curation_result_id",
        "input_record_ids",
        "groups",
        "assignments",
        "requested_evaluation_record_count",
        "realized_train_record_count",
        "realized_evaluation_record_count",
        "assignment_digest",
    }
    assert SplitError.code == "split-invalid"
    assert V1_PARTITIONS == ("train", "evaluation")
    assert result.plan_id == curation.plan_id

    with pytest.raises(DuplicateIdentityError, match="duplicate identities"):
        LeakageGroup.create(
            record_ids=(result.input_record_ids[0], result.input_record_ids[0]),
            source_ids=result.groups[0].source_ids,
            raw_sha256_values=result.groups[0].raw_sha256_values,
            exact_record_fingerprints=(result.groups[0].exact_record_fingerprints),
        )

    with pytest.raises(ValidationError, match="frozen"):
        policy.seed = "changed"
    with pytest.raises(ValidationError):
        SplitPolicy.create(
            evaluation_ratio_ppm=0.5,
            evaluation_required=True,
            seed="no-floats",
        )

    round_trips = (
        (
            policy,
            split_policy_to_dict,
            split_policy_from_json_bytes,
        ),
        (
            result.groups[0],
            leakage_group_to_dict,
            leakage_group_from_json_bytes,
        ),
        (
            result.assignments[0],
            record_assignment_to_dict,
            record_assignment_from_json_bytes,
        ),
        (
            result,
            split_result_to_dict,
            split_result_from_json_bytes,
        ),
    )
    for value, to_dict, from_bytes in round_trips:
        payload = to_dict(value)
        exact_bytes = lossless_json_bytes(payload)
        assert from_bytes(exact_bytes) == value
        with pytest.raises(SplitError, match="canonical"):
            from_bytes(exact_bytes + b"\n")

    altered = split_policy_to_dict(policy)
    altered["unexpected"] = True
    with pytest.raises(SplitError, match=r"extra=\['unexpected'\]"):
        split_policy_from_dict(altered)


def test_multi_source_record_bridges_transitive_source_components(tmp_path):
    bundle_a = source_bundle(
        tmp_path,
        logical_path="a.txt",
        blocks=[Paragraph(children=[Text("a-one")])],
    )
    bundle_b = source_bundle(
        tmp_path,
        logical_path="b.txt",
        blocks=[Paragraph(children=[Text("b-one")])],
    )
    bundle_c = source_bundle(
        tmp_path,
        logical_path="c.txt",
        blocks=[Paragraph(children=[Text("c-one")])],
    )
    bundle_d = source_bundle(
        tmp_path,
        logical_path="d.txt",
        blocks=[Paragraph(children=[Text("bridge")])],
    )
    bundles = (bundle_a, bundle_b, bundle_c, bundle_d)
    recipe = recipe_for(tuple(bundle.source for bundle in bundles), "full_text")
    construction = construct_dataset(recipe, inputs_for(bundles))
    record_d = next(
        record
        for record in construction.records
        if bundle_d.source.id in record.source_ids
    )
    construction = _construction_with_added_source(
        construction,
        record_id=record_d.record_id,
        added_source_ids=(bundle_a.source.id, bundle_b.source.id),
    )
    plan, curation = _include_all(construction, recipe.source_ids)
    raw_digests = {bundle.source.id: bundle.source.sha256 for bundle in bundles}

    result = split_dataset(plan, construction, curation, raw_digests)
    bridge_group = next(
        group for group in result.groups if bundle_a.source.id in group.source_ids
    )
    assert set(bridge_group.source_ids) == {
        bundle_a.source.id,
        bundle_b.source.id,
        bundle_d.source.id,
    }
    assert len(bridge_group.record_ids) == 3
    assert len(result.groups) == 2
    partitions = {
        assignment.partition
        for assignment in result.assignments
        if assignment.group_id == bridge_group.group_id
    }
    assert len(partitions) == 1


def test_equal_raw_digests_join_otherwise_distinct_sources(tmp_path):
    bundles, _, construction, curation, raw_digests, plan = _case(
        tmp_path,
        ("first", "second", "third"),
    )
    first_id, second_id = bundles[0].source.id, bundles[1].source.id
    raw_digests[second_id] = raw_digests[first_id]

    result = split_dataset(plan, construction, curation, raw_digests)
    joined = next(group for group in result.groups if first_id in group.source_ids)
    assert set(joined.source_ids) == {first_id, second_id}
    assert len(joined.record_ids) == 2
    assert len(result.groups) == 2


def test_exact_record_fingerprint_families_join_distinct_sources(tmp_path):
    bundles, recipe, construction, _, _, _ = _case(
        tmp_path,
        ("same exact record", "same exact record", "independent"),
    )
    plan, curation = _include_all(construction, recipe.source_ids)
    raw_digests = {
        bundle.source.id: sha256_digest(f"distinct-raw-{index}")
        for index, bundle in enumerate(bundles)
    }

    result = split_dataset(plan, construction, curation, raw_digests)
    duplicate_sources = {bundles[0].source.id, bundles[1].source.id}
    joined = next(
        group for group in result.groups if bundles[0].source.id in group.source_ids
    )
    assert set(joined.source_ids) == duplicate_sources
    assert len(joined.exact_record_fingerprints) == 1
    assert len(joined.record_ids) == 2
    assert len(result.groups) == 2


def test_seeded_prefix_is_repeatable_and_tie_uses_smaller_prefix(tmp_path):
    bundles, _, construction, curation, raw_digests, _ = _case(
        tmp_path,
        ("one", "two", "three", "four"),
    )
    raw_digests[bundles[1].source.id] = raw_digests[bundles[0].source.id]

    tied_result = None
    tied_plan = None
    tied_curation = None
    tied_policy = None
    for index in range(100):
        policy = _policy(seed=f"tie-seed-{index}")
        plan, rebound = _rebind_split_policy(construction, curation, policy)
        result = split_dataset(plan, construction, rebound, raw_digests)
        if result.realized_evaluation_record_count == 1:
            tied_policy = policy
            tied_plan = plan
            tied_curation = rebound
            tied_result = result
            break
    assert tied_policy is not None
    assert tied_plan is not None
    assert tied_curation is not None
    assert tied_result is not None
    assert tied_result.requested_evaluation_record_count == 2
    assert tied_result.realized_evaluation_record_count == 1
    assert tied_result.realized_train_record_count == 3
    assert (
        split_dataset(tied_plan, construction, tied_curation, raw_digests)
        == tied_result
    )
    assert (
        validate_split_result(
            tied_plan,
            construction,
            tied_curation,
            raw_digests,
            tied_result,
        )
        == tied_result
    )


def test_required_evaluation_fails_closed_and_optional_one_group_stays_train(
    tmp_path,
):
    _, _, construction, curation, raw_digests, required_plan = _case(
        tmp_path,
        ("only record",),
    )
    with pytest.raises(SplitError, match="fewer than two leakage groups") as caught:
        split_dataset(required_plan, construction, curation, raw_digests)
    assert caught.value.code == "split-invalid"

    optional_plan, optional_curation = _rebind_split_policy(
        construction,
        curation,
        _policy(required=False),
    )
    result = split_dataset(
        optional_plan,
        construction,
        optional_curation,
        raw_digests,
    )
    assert result.requested_evaluation_record_count == 0
    assert result.realized_evaluation_record_count == 0
    assert result.realized_train_record_count == 1
    assert {assignment.partition for assignment in result.assignments} == {"train"}


def test_only_included_records_are_assigned_once(tmp_path):
    bundles, _, construction, curation, raw_digests, plan = _case(
        tmp_path,
        ("duplicate", "duplicate", "independent"),
    )
    result = split_dataset(plan, construction, curation, raw_digests)
    excluded_ids = {
        decision.record_id
        for decision in curation.decisions
        if decision.status != "included"
    }
    assigned_ids = tuple(assignment.record_id for assignment in result.assignments)

    assert assigned_ids == curation.included_record_ids
    assert not excluded_ids.intersection(assigned_ids)
    assert len(assigned_ids) == len(set(assigned_ids))
    assert sorted(
        record_id for group in result.groups for record_id in group.record_ids
    ) == list(curation.included_record_ids)
    representative_id = next(
        decision.record_id
        for decision in curation.decisions
        if decision.status == "included"
        and any(
            finding.related_record_ids == (decision.record_id,)
            for finding in curation.findings
            if finding.code == "exact-duplicate"
        )
    )
    representative_group = next(
        group for group in result.groups if representative_id in group.record_ids
    )
    assert {
        bundles[0].source.id,
        bundles[1].source.id,
    }.issubset(representative_group.source_ids)


def test_malformed_or_tampered_inputs_and_results_fail_closed(tmp_path):
    _, _, construction, curation, raw_digests, plan = _case(
        tmp_path,
        ("alpha", "beta", "gamma"),
    )
    policy = plan.split_policy
    result = split_dataset(plan, construction, curation, raw_digests)

    tampered_nested_assignment = result.assignments[0].model_copy(
        update={
            "partition": (
                "train"
                if result.assignments[0].partition == "evaluation"
                else "evaluation"
            )
        }
    )
    with pytest.raises(ValidationError, match="identity mismatch"):
        SplitResult.create(
            policy_id=result.policy_id,
            plan_id=result.plan_id,
            construction_result_id=result.construction_result_id,
            curation_result_id=result.curation_result_id,
            input_record_ids=result.input_record_ids,
            groups=result.groups,
            assignments=(tampered_nested_assignment, *result.assignments[1:]),
            requested_evaluation_record_count=(
                result.requested_evaluation_record_count
            ),
        )

    tampered_policy = policy.model_copy(update={"seed": "altered"})
    tampered_plan = plan.model_copy(update={"split_policy": tampered_policy})
    with pytest.raises(SplitError, match="identity mismatch"):
        split_dataset(
            tampered_plan,
            construction,
            curation,
            raw_digests,
        )

    missing_digest = dict(raw_digests)
    missing_digest.pop(next(iter(missing_digest)))
    with pytest.raises(SplitError, match="exactly cover"):
        split_dataset(plan, construction, curation, missing_digest)

    tampered_curation = curation.model_copy(
        update={"construction_result_id": construction.recipe_id}
    )
    with pytest.raises(SplitError, match="curation result"):
        split_dataset(
            plan,
            construction,
            tampered_curation,
            raw_digests,
        )

    payload = split_result_to_dict(result)
    payload["assignments"][0]["partition"] = (
        "train"
        if payload["assignments"][0]["partition"] == "evaluation"
        else "evaluation"
    )
    with pytest.raises(SplitError, match="identity mismatch"):
        split_result_from_dict(payload)

    valid_payload = split_result_to_dict(result)
    valid_payload["groups"][0]["record_ids"].append(
        valid_payload["groups"][-1]["record_ids"][0]
    )
    with pytest.raises(SplitError):
        split_result_from_dict(valid_payload)

    altered_result = result.model_copy(
        update={
            "requested_evaluation_record_count": (
                result.requested_evaluation_record_count + 1
            )
        }
    )
    with pytest.raises(SplitError, match="identity mismatch"):
        validate_split_result(
            plan,
            construction,
            curation,
            raw_digests,
            altered_result,
        )

    noncanonical = deepcopy(split_result_to_dict(result))
    noncanonical["input_record_ids"].reverse()
    with pytest.raises(SplitError, match="canonical order"):
        split_result_from_dict(noncanonical)


def test_integer_ratio_rounding_is_clamped_without_empty_partitions(tmp_path):
    _, _, construction, curation, raw_digests, _ = _case(
        tmp_path,
        ("one", "two", "three"),
    )
    low_plan, low_curation = _rebind_split_policy(
        construction,
        curation,
        _policy(ratio=1, seed="low"),
    )
    high_plan, high_curation = _rebind_split_policy(
        construction,
        curation,
        _policy(ratio=999_999, seed="high"),
    )
    low = split_dataset(
        low_plan,
        construction,
        low_curation,
        raw_digests,
    )
    high = split_dataset(
        high_plan,
        construction,
        high_curation,
        raw_digests,
    )
    assert low.requested_evaluation_record_count == 1
    assert high.requested_evaluation_record_count == 2
    assert low.realized_evaluation_record_count >= 1
    assert low.realized_train_record_count >= 1
    assert high.realized_evaluation_record_count >= 1
    assert high.realized_train_record_count >= 1

    with pytest.raises(ValidationError, match="1..999999"):
        _policy(ratio=0)
    with pytest.raises(ValidationError, match="1..999999"):
        _policy(ratio=1_000_000)
