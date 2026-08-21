"""Defect-closure regressions for the datasets cluster.

Covers three verified defects:

1. Deeply nested JSON payloads must fail closed with typed errors instead of
   escaping as ``RecursionError`` from dataset loaders, the snapshot
   validator, and the independent bundle verifier.
2. ``_DisjointSet.find`` must survive adversarially chained multi-source
   leakage groups without blowing the interpreter recursion limit, while
   producing exactly the same groups as before.
3. The documented ``primary-source-cap`` balance mode must be reachable from
   the ``PipelineService.curate`` surface and persist the exact
   ``primary_source_cap`` schema literal.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from veriformis.bundle.finished import (
    EVALUATION_PATH,
    PROVENANCE_PATH,
    TRAIN_PATH,
    VALIDATION_PATH,
    write_finished_bundle,
)
from veriformis.bundle.verifier import verify_finished_bundle
from veriformis.chunkers.base import Chunk
from veriformis.chunkers.strategies import chunk_paragraph
from veriformis.construction import (
    ConstructionInputs,
    DatasetRecipe,
    IRArtifactInput,
    SegmentationPolicy,
    TrainingObjective,
    construct_dataset,
)
from veriformis.construction.models import DatasetRecord, RecordField
from veriformis.datasets import (
    CurationPolicy,
    FinishedDatasetPlan,
    SerializationPlan,
    SplitPolicy,
    curate_dataset,
    curation_result_from_json_bytes,
    finished_dataset_plan_from_json_bytes,
    serialize_dataset,
    split_dataset,
    split_result_from_json_bytes,
)
from veriformis.datasets.splitting import _build_leakage_groups
from veriformis.datasets.validation import (
    create_dataset_snapshot,
    dataset_validation_report_json_bytes,
    validate_dataset_snapshot,
    validate_finished_dataset,
)
from veriformis.errors import (
    BundleVerificationError,
    CurationError,
    SplitError,
)
from veriformis.identity import (
    canonical_digest,
    derive_artifact_id,
    lossless_json_bytes,
    sha256_digest,
)
from veriformis.ir import Document, Paragraph, Text, attach_canonical_provenance
from veriformis.ir.serde import document_to_dict
from veriformis.pipeline import PipelineService
from veriformis.sources import SourceRef, register_source
from veriformis.workspace import Workspace


def _deep_json_bytes(depth: int = 50_000) -> bytes:
    """One JSON object nested far beyond any sane interpreter stack."""
    return b'{"a":' * depth + b"null" + b"}" * depth


# ---------------------------------------------------------------------------
# Shared finished-dataset fixture (mirrors tests/datasets/test_validation.py)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _SourceBundle:
    source: SourceRef
    chunks: tuple[Chunk, ...]
    artifact: IRArtifactInput


def _source_bundle(tmp_path: Path, *, logical_path: str, text: str) -> _SourceBundle:
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
    document_json = lossless_json_bytes(document_to_dict(document))
    config_digest = canonical_digest({"fixture": logical_path})
    artifact = IRArtifactInput.create(
        source_id=source.id,
        artifact_id=derive_artifact_id(
            kind="cleaned-document-ir",
            content_sha256=sha256_digest(document_json),
            source_ids=(source.id,),
            producer_id="veriformis.test.defectclose",
            producer_version="1",
            config_digest=config_digest,
        ),
        artifact_kind="cleaned-document-ir",
        document_json=document_json,
        producer_id="veriformis.test.defectclose",
        producer_version="1",
        config_digest=config_digest,
    )
    return _SourceBundle(source, tuple(chunks), artifact)


def _finished_case(tmp_path: Path, *, text_repeat: int = 1):
    bundles = (
        _source_bundle(
            tmp_path,
            logical_path="defectclose-alpha.txt",
            text="Alpha exact source text. " * text_repeat,
        ),
        _source_bundle(
            tmp_path,
            logical_path="defectclose-beta.txt",
            text="Beta exact source text. " * text_repeat,
        ),
    )
    objective = TrainingObjective.create("full_text")
    recipe = DatasetRecipe.create(
        objective=objective,
        source_ids=tuple(bundle.source.id for bundle in bundles),
        cleaning_config_digest=canonical_digest({"cleaning": "defectclose-v1"}),
        segmentation=SegmentationPolicy(
            schema_version="veriformis.segmentation-policy/v1",
            strategy="paragraph",
            size=1_000,
            overlap=100,
        ),
        target_row_schema="text",
    )
    inputs = ConstructionInputs.create(
        cleaning_config_digest=recipe.cleaning_config_digest,
        sources=tuple(bundle.source for bundle in bundles),
        chunks=tuple(chunk for bundle in bundles for chunk in bundle.chunks),
        ir_artifacts=tuple(bundle.artifact for bundle in bundles),
    )
    construction = construct_dataset(recipe, inputs)
    plan = FinishedDatasetPlan.create(
        recipe_id=recipe.recipe_id,
        construction_result_id=construction.result_id,
        curation_policy=CurationPolicy.create(minimum_target_characters=1),
        split_policy=SplitPolicy.create(
            evaluation_ratio_ppm=500_000,
            evaluation_required=True,
            seed="defectclose-test-v1",
        ),
        serialization_plan=SerializationPlan.create(row_schema="text"),
    )
    curation = curate_dataset(plan, recipe, inputs, construction)
    split = split_dataset(
        plan,
        construction,
        curation,
        {bundle.source.id: bundle.source.sha256 for bundle in bundles},
    )
    output = serialize_dataset(plan, recipe, construction, curation, split)
    return plan, recipe, inputs, construction, curation, split, output


# ---------------------------------------------------------------------------
# Defect 1: RecursionError containment
# ---------------------------------------------------------------------------


def test_deep_nested_json_bytes_fail_typed_in_dataset_loaders() -> None:
    """Dataset loaders must raise their typed error, never RecursionError."""
    data = _deep_json_bytes()
    with pytest.raises(CurationError, match="nesting"):
        curation_result_from_json_bytes(data)
    with pytest.raises(SplitError, match="nesting"):
        split_result_from_json_bytes(data)


def test_deep_nested_critical_input_still_produces_failed_report(
    tmp_path: Path,
) -> None:
    """The validator must persist a failed report, not crash the process."""
    plan, recipe, inputs, construction, curation, split, output = _finished_case(
        tmp_path
    )
    snapshot = create_dataset_snapshot(
        plan,
        recipe,
        construction,
        curation,
        split,
        output.row_set,
        train_jsonl=output.train_jsonl,
        evaluation_jsonl=output.evaluation_jsonl,
        provenance_jsonl=output.provenance_jsonl,
    )

    report = validate_dataset_snapshot(
        snapshot,
        plan=plan,
        recipe=recipe,
        construction_inputs=inputs,
        construction_result=construction,
        curation_result=_deep_json_bytes(),
        split_result=split,
        row_set=output.row_set,
        train_jsonl=output.train_jsonl,
        evaluation_jsonl=output.evaluation_jsonl,
        provenance_jsonl=output.provenance_jsonl,
    )

    gates = {item.gate_id: item for item in report.gate_results}
    assert report.status == "failed"
    assert gates["construction-replay"].status == "passed"
    assert gates["curation"].status == "failed"
    assert gates["curation"].finding_codes == ("critical-input-load-failed",)
    assert gates["deduplication"].status == "blocked"
    assert gates["split"].status == "blocked"
    assert gates["snapshot"].status == "failed"


def test_deep_nested_construction_input_still_produces_failed_report(
    tmp_path: Path,
) -> None:
    """A deep-nested first-stage artifact blocks dependents with a report."""
    plan, recipe, inputs, construction, curation, split, output = _finished_case(
        tmp_path
    )
    snapshot = create_dataset_snapshot(
        plan,
        recipe,
        construction,
        curation,
        split,
        output.row_set,
        train_jsonl=output.train_jsonl,
        evaluation_jsonl=output.evaluation_jsonl,
        provenance_jsonl=output.provenance_jsonl,
    )

    report = validate_dataset_snapshot(
        snapshot,
        plan=plan,
        recipe=recipe,
        construction_inputs=inputs,
        construction_result=_deep_json_bytes(),
        curation_result=curation,
        split_result=split,
        row_set=output.row_set,
        train_jsonl=output.train_jsonl,
        evaluation_jsonl=output.evaluation_jsonl,
        provenance_jsonl=output.provenance_jsonl,
    )

    gates = {item.gate_id: item for item in report.gate_results}
    assert report.status == "failed"
    assert gates["construction-replay"].status == "failed"
    assert gates["construction-replay"].finding_codes == (
        "critical-input-load-failed",
    )
    assert gates["curation"].status == "blocked"


def test_hostile_bundle_with_deep_nested_record_fails_typed(tmp_path: Path) -> None:
    """A tampered deep-nested data line must raise BundleVerificationError.

    The tamper preserves the declared byte size so the verifier reaches the
    per-record JSON parse instead of the earlier size check.
    """
    plan, recipe, inputs, construction, curation, split, output = _finished_case(
        tmp_path,
        text_repeat=16_000,
    )
    report = validate_finished_dataset(
        plan,
        recipe,
        inputs,
        construction,
        curation,
        split,
        output.row_set,
        train_jsonl=output.train_jsonl,
        evaluation_jsonl=output.evaluation_jsonl,
        provenance_jsonl=output.provenance_jsonl,
    )
    assert report.status == "passed"
    payloads = {
        TRAIN_PATH: output.train_jsonl,
        EVALUATION_PATH: output.evaluation_jsonl,
        PROVENANCE_PATH: output.provenance_jsonl,
        VALIDATION_PATH: dataset_validation_report_json_bytes(report),
    }
    roles = {
        TRAIN_PATH: "training-partition",
        EVALUATION_PATH: "evaluation-partition",
        PROVENANCE_PATH: "row-provenance",
        VALIDATION_PATH: "dataset-validation-report",
    }
    media_types = {
        TRAIN_PATH: "application/jsonl",
        EVALUATION_PATH: "application/jsonl",
        PROVENANCE_PATH: "application/jsonl",
        VALIDATION_PATH: "application/json",
    }
    counts = {
        TRAIN_PATH: output.row_set.train_row_count,
        EVALUATION_PATH: output.row_set.evaluation_row_count,
        PROVENANCE_PATH: output.row_set.total_row_count,
    }
    target = tmp_path / "hostile.vfbundle"
    write_finished_bundle(
        target,
        payloads,
        roles=roles,
        media_types=media_types,
        record_counts=counts,
        dataset_snapshot_id=report.snapshot_id,
        validation_report_id=report.report_id,
    )
    assert verify_finished_bundle(target).bundle_id

    deep = _deep_json_bytes()
    padding = len(output.train_jsonl) - len(deep) - 1
    assert padding >= 0, "fixture train partition must exceed the hostile record"
    (target / TRAIN_PATH).write_bytes(deep + b" " * padding + b"\n")

    with pytest.raises(BundleVerificationError):
        verify_finished_bundle(target)


# ---------------------------------------------------------------------------
# Defect 2: iterative disjoint-set find
# ---------------------------------------------------------------------------


def _chained_corpus(chain_length: int):
    """Adversarially chained corpus whose union path grows with chain_length.

    Mirrors the verified reproduction: singletons S_0..S_K on unique sources,
    bridges B_1..B_K that repeatedly demote the deep root, and a final record
    that touches the deep end of the parent chain.  Records are built with
    ``model_construct`` purely to pin the sorted order; ``_build_leakage_groups``
    never validates identities itself.
    """

    def rec_id(index: int) -> str:
        return "rec-v1-" + f"{index:08x}" + "0" * 56

    def src_id(index: int) -> str:
        return "src-v1-" + f"{index:08x}" + "0" * 56

    def digest(index: int) -> str:
        return f"{index:08x}" + "a" * 56

    def make_record(index: int, sources: tuple[str, ...]) -> DatasetRecord:
        field = RecordField.model_construct(
            name="text",
            value=f"unique-value-{index}",
            evidence=None,
        )
        return DatasetRecord.model_construct(
            record_id=rec_id(index),
            objective_id="obj-v1-" + "0" * 64,
            source_ids=tuple(sorted(sources)),
            fields=(field,),
        )

    records: list[DatasetRecord] = []
    raw_digests: dict[str, str] = {}
    source_bases: dict[str, tuple[str, ...]] = {}
    for index in range(chain_length + 1):
        record = make_record(index, (src_id(index),))
        records.append(record)
        raw_digests[src_id(index)] = digest(index)
        source_bases[record.record_id] = record.source_ids
    for offset in range(1, chain_length + 1):
        record = make_record(
            chain_length + offset,
            (src_id(chain_length + 1 - offset), src_id(chain_length - offset)),
        )
        records.append(record)
        source_bases[record.record_id] = record.source_ids
    final = make_record(2 * chain_length + 1, (src_id(chain_length),))
    records.append(final)
    source_bases[final.record_id] = final.source_ids
    return tuple(records), raw_digests, source_bases


def _group_facts(groups) -> tuple[tuple[tuple[str, ...], tuple[str, ...]], ...]:
    return tuple((group.record_ids, group.source_ids) for group in groups)


def test_chained_leakage_groups_survive_recursion_limit_with_same_semantics() -> None:
    """K=1500 chains complete without RecursionError, matching a small control."""
    control_records, control_digests, control_bases = _chained_corpus(6)
    control_groups = _build_leakage_groups(
        control_records,
        control_digests,
        control_bases,
    )
    assert len(control_groups) == 1
    assert control_groups[0].record_ids == tuple(
        sorted(record.record_id for record in control_records)
    )
    assert control_groups[0].source_ids == tuple(sorted(control_digests))
    # Determinism: an identical corpus yields byte-identical groups.
    assert _group_facts(control_groups) == _group_facts(
        _build_leakage_groups(control_records, control_digests, control_bases)
    )

    records, raw_digests, source_bases = _chained_corpus(1500)
    groups = _build_leakage_groups(records, raw_digests, source_bases)
    assert len(groups) == 1
    assert groups[0].record_ids == tuple(
        sorted(record.record_id for record in records)
    )
    assert groups[0].source_ids == tuple(sorted(raw_digests))
    assert len(groups[0].exact_record_fingerprints) == len(records)


# ---------------------------------------------------------------------------
# Defect 3: primary-source-cap reachable from the service surface
# ---------------------------------------------------------------------------


def _constructed_workspace(tmp_path: Path) -> Path:
    alpha = tmp_path / "cap-alpha.txt"
    alpha.write_text("Alpha paragraph one.\n\nAlpha paragraph two.", encoding="utf-8")
    beta = tmp_path / "cap-beta.txt"
    beta.write_text("Beta paragraph one.\n\nBeta paragraph two.", encoding="utf-8")
    workspace = tmp_path / "workspace"
    service = PipelineService()
    service.parse([alpha, beta], workspace, source_root=tmp_path)
    service.clean(workspace)
    service.chunk(workspace)
    service.construct(workspace, objective="full_text")
    return workspace


def test_primary_source_cap_balance_mode_is_reachable_from_the_service(
    tmp_path: Path,
) -> None:
    """The documented surface spelling curates and persists the schema literal."""
    workspace = _constructed_workspace(tmp_path)
    service = PipelineService()

    outcome = service.curate(
        workspace,
        balance_mode="primary-source-cap",
        maximum_records_per_primary_source=10,
        evaluation_required=False,
    )
    assert outcome.plan_id

    store = Workspace.open(workspace)
    revision = store.head()
    plan_bytes = store.read_artifact(
        revision.stages["curate"].outputs["plan"],
        revision=revision,
    )
    plan = finished_dataset_plan_from_json_bytes(plan_bytes)
    assert plan.plan_id == outcome.plan_id
    assert plan.curation_policy.balance_mode == "primary_source_cap"
    assert plan.curation_policy.maximum_records_per_primary_source == 10


def test_persisted_balance_literal_is_rejected_at_the_service_surface(
    tmp_path: Path,
) -> None:
    """Only the documented hyphenated spelling is a valid surface value."""
    workspace = _constructed_workspace(tmp_path)
    service = PipelineService()

    with pytest.raises(ValueError, match="primary-source-cap"):
        service.curate(
            workspace,
            balance_mode="primary_source_cap",
            maximum_records_per_primary_source=10,
            evaluation_required=False,
        )
