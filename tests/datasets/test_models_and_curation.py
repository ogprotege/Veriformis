from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from veriformis.chunkers.strategies import chunk_paragraph
from veriformis.construction import (
    ConstructionPass,
    ConstructionError,
    ConstructionInputs,
    DatasetRecipe,
    SegmentationPolicy,
    TrainingObjective,
    construct_dataset,
)
from veriformis.contracts import FINISHED_DATASET_SCHEMA_IDS
from veriformis.datasets import (
    V1_COVERAGE_BLOCKER_CODES,
    V1_CURATION_REASON_CODES,
    V1_QUALITY_FINDING_CODES,
    CoverageLedger,
    CoverageLedgerEntry,
    CurationDecision,
    CurationError,
    CurationPolicy,
    CurationResult,
    FinishedDatasetPlan,
    QualityFinding,
    SerializationPlan,
    SplitPolicy,
    curate_dataset,
    curation_policy_from_dict,
    curation_policy_from_json_bytes,
    curation_policy_to_dict,
    curation_result_from_dict,
    curation_result_from_json_bytes,
    curation_result_to_dict,
    exact_record_fingerprint,
    finished_dataset_plan_from_json_bytes,
    finished_dataset_plan_to_dict,
)
from veriformis.datasets.curation import _build_coverage_ledger
from veriformis.errors import DuplicateIdentityError
from veriformis.identity import canonical_digest, derive_id, lossless_json_bytes
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


def recipe_for(
    sources,
    objective_kind: str,
    *,
    parameters: dict | None = None,
    size: int = 1_000,
):
    objective = TrainingObjective.create(objective_kind)
    construction_pass = ConstructionPass.create(
        sequence=1,
        objective_kind=objective_kind,
        parameters=parameters,
    )
    return DatasetRecipe.create(
        objective=objective,
        source_ids=tuple(source.id for source in sources),
        cleaning_config_digest=canonical_digest({"cleaning": "fixture-v1"}),
        segmentation=SegmentationPolicy(
            schema_version="veriformis.segmentation-policy/v1",
            strategy="paragraph",
            size=size,
            overlap=min(100, size - 1),
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


def finished_plan_for(recipe, construction, curation_policy):
    return FinishedDatasetPlan.create(
        recipe_id=recipe.recipe_id,
        construction_result_id=construction.result_id,
        curation_policy=curation_policy,
        split_policy=SplitPolicy.create(
            evaluation_ratio_ppm=500_000,
            evaluation_required=False,
            seed="curation-test-v1",
        ),
        serialization_plan=SerializationPlan.create(
            row_schema=recipe.target_row_schema,
        ),
    )


def _case(
    tmp_path,
    texts: tuple[str, ...],
    *,
    objective_kind: str = "full_text",
    parameters: dict | None = None,
    minimum_target_characters: int = 0,
    balance_mode: str = "none",
    maximum_records_per_primary_source: int | None = None,
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
        objective_kind,
        parameters=parameters,
    )
    inputs = inputs_for(bundles)
    construction = construct_dataset(recipe, inputs)
    policy = CurationPolicy.create(
        minimum_target_characters=minimum_target_characters,
        balance_mode=balance_mode,
        maximum_records_per_primary_source=(maximum_records_per_primary_source),
    )
    plan = finished_plan_for(recipe, construction, policy)
    curated = curate_dataset(plan, recipe, inputs, construction)
    return bundles, recipe, inputs, construction, policy, plan, curated


def test_strict_models_have_exact_fields_and_frozen_values(tmp_path):
    _, _, _, _, policy, plan, curated = _case(tmp_path, ("source text",))

    assert set(CurationPolicy.model_fields) == {
        "schema_version",
        "policy_id",
        "minimum_target_characters",
        "exact_duplicate_policy",
        "conflict_policy",
        "near_duplicate_policy",
        "balance_mode",
        "maximum_records_per_primary_source",
    }
    assert set(FinishedDatasetPlan.model_fields) == {
        "schema_version",
        "plan_id",
        "recipe_id",
        "construction_result_id",
        "curation_policy",
        "split_policy",
        "serialization_plan",
        "required_validation_gates",
        "required_partitions",
        "bundle_retention_profile",
    }
    assert set(QualityFinding.model_fields) == {
        "schema_version",
        "finding_id",
        "record_id",
        "code",
        "related_record_ids",
        "observed_count",
        "required_count",
    }
    assert set(CurationDecision.model_fields) == {
        "schema_version",
        "decision_id",
        "record_id",
        "status",
        "reason_codes",
        "finding_ids",
    }
    assert set(CoverageLedgerEntry.model_fields) == {
        "schema_version",
        "entry_id",
        "source_id",
        "candidate_count",
        "record_count",
        "included_count",
        "excluded_count",
        "quarantined_count",
        "primary_included_count",
        "blocker_codes",
    }
    assert set(CoverageLedger.model_fields) == {
        "schema_version",
        "ledger_id",
        "selected_source_ids",
        "entries",
    }
    assert set(CurationResult.model_fields) == {
        "schema_version",
        "result_id",
        "plan_id",
        "recipe_id",
        "construction_result_id",
        "policy_id",
        "input_record_ids",
        "decisions",
        "findings",
        "included_record_ids",
        "coverage_ledger",
    }

    with pytest.raises(ValidationError, match="frozen"):
        policy.minimum_target_characters = 4

    value = curation_policy_to_dict(policy)
    value["unexpected"] = True
    with pytest.raises(CurationError, match=r"extra=\['unexpected'\]"):
        curation_policy_from_dict(value)

    assert plan.plan_id.startswith("fdp-v1-")
    assert curated.result_id.startswith("cur-v1-")


def test_registry_and_error_codes_are_stable():
    assert "veriformis.exact-record-fingerprint/v1" in FINISHED_DATASET_SCHEMA_IDS
    assert V1_QUALITY_FINDING_CODES == (
        "conflicting-target",
        "exact-duplicate",
        "primary-source-cap",
        "target-too-short",
    )
    assert V1_CURATION_REASON_CODES == (
        "conflicting-target",
        "exact-duplicate",
        "primary-source-cap",
        "quality-passed",
        "target-too-short",
    )
    assert V1_COVERAGE_BLOCKER_CODES == (
        "no-constructed-candidates",
        "no-dataset-records",
        "no-included-contribution",
    )
    assert CurationError.code == "curation-invalid"
    assert DuplicateIdentityError.code == "duplicate-identity"


def test_positive_curation_binds_every_record_and_source(tmp_path):
    bundles, recipe, _, construction, policy, plan, curated = _case(
        tmp_path,
        ("alpha", "beta"),
        minimum_target_characters=1,
    )

    assert curated.plan_id == plan.plan_id
    assert curated.recipe_id == recipe.recipe_id
    assert curated.construction_result_id == construction.result_id
    assert curated.policy_id == policy.policy_id
    assert curated.input_record_ids == tuple(
        sorted(record.record_id for record in construction.records)
    )
    assert len(curated.decisions) == len(construction.records) == 2
    assert {decision.status for decision in curated.decisions} == {"included"}
    assert curated.included_record_ids == curated.input_record_ids
    assert not curated.findings
    assert curated.coverage_ledger.selected_source_ids == recipe.source_ids
    assert {
        entry.source_id: (
            entry.candidate_count,
            entry.record_count,
            entry.included_count,
            entry.blocker_codes,
        )
        for entry in curated.coverage_ledger.entries
    } == {bundle.source.id: (1, 1, 1, ()) for bundle in bundles}


def test_curation_refuses_a_plan_whose_row_schema_differs_from_recipe(tmp_path):
    _, recipe, inputs, construction, policy, _, _ = _case(
        tmp_path,
        ("exact full text",),
    )
    mismatched = FinishedDatasetPlan.create(
        recipe_id=recipe.recipe_id,
        construction_result_id=construction.result_id,
        curation_policy=policy,
        split_policy=SplitPolicy.create(
            evaluation_ratio_ppm=500_000,
            evaluation_required=False,
            seed="curation-test-v1",
        ),
        serialization_plan=SerializationPlan.create(row_schema="messages"),
    )

    with pytest.raises(CurationError, match="row schema differs"):
        curate_dataset(mismatched, recipe, inputs, construction)


def test_exact_duplicates_keep_lexicographically_smallest_record_id(tmp_path):
    _, _, _, construction, _, _, curated = _case(
        tmp_path,
        ("same exact text", "same exact text"),
    )
    record_ids = tuple(sorted(record.record_id for record in construction.records))

    assert (
        len({exact_record_fingerprint(record) for record in construction.records}) == 1
    )
    assert curated.included_record_ids == (record_ids[0],)
    decisions = {decision.record_id: decision for decision in curated.decisions}
    assert decisions[record_ids[0]].status == "included"
    assert decisions[record_ids[1]].status == "excluded"
    assert decisions[record_ids[1]].reason_codes == ("exact-duplicate",)
    finding = next(
        finding for finding in curated.findings if finding.record_id == record_ids[1]
    )
    assert finding.related_record_ids == (record_ids[0],)


def test_same_context_text_in_unrelated_sources_does_not_create_a_conflict(tmp_path):
    _, _, _, construction, _, _, curated = _case(
        tmp_path,
        ("contextA", "contextB"),
        objective_kind="continuation",
        minimum_target_characters=1,
    )
    assert [record.fields[0].value for record in construction.records] == [
        "cont",
        "cont",
    ]
    assert {record.fields[1].value for record in construction.records} == {
        "extA",
        "extB",
    }

    assert curated.included_record_ids == tuple(
        sorted(record.record_id for record in construction.records)
    )
    assert {decision.status for decision in curated.decisions} == {"included"}
    assert not curated.findings


def test_distinct_targets_quarantine_one_source_context_class(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="conflicts.txt",
        blocks=[
            Paragraph(children=[Text("contextA")]),
            Paragraph(children=[Text("contextB")]),
        ],
        max_size=8,
    )
    recipe = recipe_for((bundle.source,), "continuation", size=8)
    inputs = inputs_for((bundle,))
    construction = construct_dataset(recipe, inputs)
    policy = CurationPolicy.create(minimum_target_characters=1)
    plan = finished_plan_for(recipe, construction, policy)

    curated = curate_dataset(plan, recipe, inputs, construction)

    assert [record.fields[0].value for record in construction.records] == [
        "cont",
        "cont",
    ]
    assert {record.fields[1].value for record in construction.records} == {
        "extA",
        "extB",
    }
    assert not curated.included_record_ids
    assert {decision.status for decision in curated.decisions} == {"quarantined"}
    assert {decision.reason_codes for decision in curated.decisions} == {
        ("conflicting-target",)
    }
    assert len(curated.findings) == 2
    assert {finding.observed_count for finding in curated.findings} == {2}


def test_minimum_target_filter_runs_before_conflict_detection(tmp_path):
    _, _, _, construction, _, _, curated = _case(
        tmp_path,
        ("P1", "P22"),
        objective_kind="continuation",
        parameters={"split_ratio_ppm": 100_000},
        minimum_target_characters=2,
    )
    targets = {
        record.record_id: record.fields[1].value for record in construction.records
    }
    assert set(targets.values()) == {"1", "22"}
    decisions = {decision.record_id: decision for decision in curated.decisions}
    short_id = next(record_id for record_id, target in targets.items() if target == "1")
    long_id = next(record_id for record_id, target in targets.items() if target == "22")

    assert decisions[short_id].status == "excluded"
    assert decisions[short_id].reason_codes == ("target-too-short",)
    assert decisions[long_id].status == "included"
    assert not any(
        decision.reason_codes == ("conflicting-target",)
        for decision in curated.decisions
    )


def test_balance_policy_is_explicit_and_primary_source_cap_is_deterministic(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="many.txt",
        blocks=[
            Paragraph(children=[Text("first distinct record")]),
            Paragraph(children=[Text("second distinct record")]),
            Paragraph(children=[Text("third distinct record")]),
        ],
        max_size=22,
    )
    recipe = recipe_for((bundle.source,), "full_text", size=22)
    inputs = inputs_for((bundle,))
    construction = construct_dataset(recipe, inputs)
    policy = CurationPolicy.create(
        minimum_target_characters=0,
        balance_mode="primary_source_cap",
        maximum_records_per_primary_source=1,
    )
    plan = finished_plan_for(recipe, construction, policy)
    curated = curate_dataset(plan, recipe, inputs, construction)
    ordered_ids = tuple(sorted(record.record_id for record in construction.records))

    assert curated.included_record_ids == (ordered_ids[0],)
    assert (
        sum(
            decision.reason_codes == ("primary-source-cap",)
            for decision in curated.decisions
        )
        == 2
    )
    assert curated.coverage_ledger.entries[0].primary_included_count == 1

    with pytest.raises(ValueError, match="null source cap"):
        CurationPolicy.create(
            minimum_target_characters=0,
            balance_mode="none",
            maximum_records_per_primary_source=1,
        )
    with pytest.raises(ValueError, match="positive integer source cap"):
        CurationPolicy.create(
            minimum_target_characters=0,
            balance_mode="primary_source_cap",
        )


def test_selected_source_coverage_records_explicit_zero_stage_blockers(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="too-short.txt",
        blocks=[Paragraph(children=[Text("x")])],
    )
    recipe = recipe_for((bundle.source,), "continuation")
    inputs = inputs_for((bundle,))
    construction = construct_dataset(recipe, inputs)
    assert not construction.candidates
    assert not construction.records
    policy = CurationPolicy.create(minimum_target_characters=1)
    plan = finished_plan_for(recipe, construction, policy)

    curated = curate_dataset(plan, recipe, inputs, construction)

    assert not curated.decisions
    entry = curated.coverage_ledger.entries[0]
    assert (
        entry.candidate_count,
        entry.record_count,
        entry.included_count,
    ) == (0, 0, 0)
    assert entry.blocker_codes == V1_COVERAGE_BLOCKER_CODES


def test_multi_source_coverage_credits_every_bound_source():
    source_a = derive_id("src", {"source": "a"})
    source_b = derive_id("src", {"source": "b"})
    record_id = derive_id("rec", {"record": "shared"})
    decision = CurationDecision.create(
        record_id=record_id,
        status="included",
        reason_code="quality-passed",
    )
    recipe = SimpleNamespace(source_ids=tuple(sorted((source_a, source_b))))
    shared = SimpleNamespace(
        record_id=record_id,
        source_ids=recipe.source_ids,
    )
    result = SimpleNamespace(candidates=(shared,), records=(shared,))

    ledger = _build_coverage_ledger(recipe, result, (decision,))

    assert [entry.included_count for entry in ledger.entries] == [1, 1]
    assert sum(entry.primary_included_count for entry in ledger.entries) == 1
    assert all(not entry.blocker_codes for entry in ledger.entries)


def test_curation_is_independent_of_declared_input_order(tmp_path):
    bundles, recipe, forward, construction, policy, plan, first = _case(
        tmp_path,
        ("alpha", "beta", "gamma"),
    )
    reverse = ConstructionInputs.create(
        cleaning_config_digest=forward.cleaning_config_digest,
        sources=tuple(reversed(forward.sources)),
        chunks=tuple(reversed(forward.chunks)),
        transforms=tuple(reversed(forward.transforms)),
        ir_artifacts=tuple(reversed(forward.ir_artifacts)),
        reviews=tuple(reversed(forward.reviews)),
    )
    replayed = construct_dataset(recipe, reverse)
    assert replayed == construction

    second = curate_dataset(plan, recipe, reverse, replayed)

    assert second == first
    assert tuple(bundle.source.id for bundle in bundles) != tuple(
        source.id for source in reverse.sources
    )
    assert second.policy_id == policy.policy_id


def test_construction_and_plan_tamper_fail_before_curation(tmp_path):
    _, recipe, inputs, construction, _, plan, _ = _case(
        tmp_path,
        ("unaltered",),
    )
    unsafe_result = construction.model_copy(update={"input_digest": "0" * 64})
    with pytest.raises(ConstructionError):
        curate_dataset(plan, recipe, inputs, unsafe_result)

    unsafe_plan = plan.model_copy(
        update={"construction_result_id": derive_id("run", {"other": True})}
    )
    with pytest.raises(CurationError, match="identity mismatch"):
        curate_dataset(unsafe_plan, recipe, inputs, construction)


def test_unicode_is_exact_for_dedup_conflict_and_identity(tmp_path):
    composed = "P\N{LATIN SMALL LETTER E WITH ACUTE}"
    decomposed = "Pe\N{COMBINING ACUTE ACCENT}"
    _, _, _, construction, _, _, curated = _case(
        tmp_path,
        (composed, decomposed),
        objective_kind="continuation",
        parameters={"split_ratio_ppm": 100_000},
        minimum_target_characters=1,
    )
    targets = {record.fields[1].value for record in construction.records}

    assert targets == {
        "\N{LATIN SMALL LETTER E WITH ACUTE}",
        "e\N{COMBINING ACUTE ACCENT}",
    }
    assert (
        len({exact_record_fingerprint(record) for record in construction.records}) == 2
    )
    assert {decision.status for decision in curated.decisions} == {"included"}


def test_canonical_lossless_json_round_trips_and_rejects_malformed_bytes(tmp_path):
    _, _, _, _, policy, plan, curated = _case(
        tmp_path,
        ("Caf\N{LATIN SMALL LETTER E}\N{COMBINING ACUTE ACCENT} \N{BOOKS}",),
    )
    policy_bytes = lossless_json_bytes(curation_policy_to_dict(policy))
    plan_bytes = lossless_json_bytes(finished_dataset_plan_to_dict(plan))
    result_bytes = lossless_json_bytes(curation_result_to_dict(curated))

    assert curation_policy_from_json_bytes(policy_bytes) == policy
    assert finished_dataset_plan_from_json_bytes(plan_bytes) == plan
    assert curation_result_from_json_bytes(result_bytes) == curated
    assert lossless_json_bytes(curation_result_to_dict(curated)) == result_bytes

    with pytest.raises(CurationError, match="not canonical"):
        curation_result_from_json_bytes(result_bytes + b"\n")
    with pytest.raises(CurationError, match="floating-point"):
        value = curation_policy_to_dict(policy)
        value["minimum_target_characters"] = 1.5
        curation_policy_from_json_bytes(lossless_json_bytes(value))
    with pytest.raises(DuplicateIdentityError, match="duplicate key"):
        duplicate = policy_bytes.replace(
            b"{",
            b'{"balance_mode":"none",',
            1,
        )
        curation_policy_from_json_bytes(duplicate)


def test_result_loader_rejects_semantic_and_identity_tamper(tmp_path):
    _, _, _, _, _, _, curated = _case(tmp_path, ("source",))
    value = curation_result_to_dict(curated)
    value["decisions"][0]["status"] = "excluded"

    with pytest.raises(CurationError):
        curation_result_from_dict(value)

    value = deepcopy(curation_result_to_dict(curated))
    value["input_record_ids"].append(value["input_record_ids"][0])
    value["result_id"] = derive_id(
        "cur",
        {key: item for key, item in value.items() if key != "result_id"},
    )
    with pytest.raises(DuplicateIdentityError):
        curation_result_from_dict(value)


def test_nested_unchecked_model_copies_are_revalidated(tmp_path):
    _, _, _, _, policy, plan, curated = _case(tmp_path, ("source",))
    unsafe_policy = policy.model_copy(update={"policy_id": derive_id("cpl", {})})
    with pytest.raises(ValidationError, match="curation policy identity mismatch"):
        FinishedDatasetPlan.create(
            recipe_id=plan.recipe_id,
            construction_result_id=plan.construction_result_id,
            curation_policy=unsafe_policy,
            split_policy=plan.split_policy,
            serialization_plan=plan.serialization_plan,
        )

    decision = curated.decisions[0]
    unsafe_decision = decision.model_copy(update={"status": "excluded"})
    with pytest.raises(ValidationError, match="excluded decision"):
        CurationResult.create(
            plan_id=curated.plan_id,
            recipe_id=curated.recipe_id,
            construction_result_id=curated.construction_result_id,
            policy_id=curated.policy_id,
            input_record_ids=curated.input_record_ids,
            decisions=(unsafe_decision,),
            findings=curated.findings,
            included_record_ids=curated.included_record_ids,
            coverage_ledger=curated.coverage_ledger,
        )
