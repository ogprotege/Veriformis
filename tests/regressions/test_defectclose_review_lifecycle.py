"""Reviewed construction results must replay through every finished stage.

The workspace construct commit gate replays a persisted construction result
with the review evidence carried on the result's own decisions.  The
service-side loader must reconstruct exactly the same replay inputs, or a
gate-certified reviewed workspace is misreported as tamper ("construction
result does not match exact replay") by curate, split, format, validate,
and seal.
"""

from __future__ import annotations

from pathlib import Path

from veriformis.construction import (
    ConstructionInputs,
    ReviewEvidence,
    construct_dataset,
    construction_result_from_json_bytes,
    construction_result_to_dict,
    dataset_recipe_from_json_bytes,
)
from veriformis.identity import lossless_json_bytes
from veriformis.pipeline import PipelineService
from veriformis.pipeline.service import _load_construction_inputs
from veriformis.workspace import Workspace


def _write_corpus(tmp_path: Path) -> tuple[list[Path], Path]:
    root = tmp_path / "raw"
    root.mkdir()
    alpha = root / "alpha.txt"
    alpha.write_text(
        "Alpha reviewed paragraph one.\n\nAlpha reviewed paragraph two.\n",
        encoding="utf-8",
    )
    beta = root / "beta.txt"
    beta.write_text("Beta reviewed paragraph.\n", encoding="utf-8")
    return [alpha, beta], root


def _prepare_constructed_workspace(
    tmp_path: Path,
    *,
    require_review: bool,
) -> tuple[PipelineService, Path]:
    sources, root = _write_corpus(tmp_path)
    service = PipelineService()
    workspace = tmp_path / "workspace"
    service.parse(sources, workspace, source_root=root)
    service.clean(workspace)
    service.chunk(workspace)
    service.construct(
        workspace,
        objective="full_text",
        require_review=require_review,
    )
    return service, workspace


def _output_bytes(store: Workspace, stage: str, key: str) -> bytes:
    revision = store.head()
    artifact_id = revision.stages[stage].outputs[key]
    return store.read_artifact(artifact_id, revision=revision)


def _commit_reviewed_result(workspace_path: Path) -> None:
    """Review every pending candidate and commit through the construct gate."""
    store = Workspace.open(workspace_path)
    head = store.head()
    recipe = dataset_recipe_from_json_bytes(
        _output_bytes(store, "construct", "recipe")
    )
    pending = construction_result_from_json_bytes(
        _output_bytes(store, "construct", "result")
    )
    assert pending.candidates
    assert all(
        decision.status == "pending_review" for decision in pending.decisions
    )
    assert not pending.records

    base_inputs = _load_construction_inputs(store, head, recipe.source_ids)
    reviews = tuple(
        ReviewEvidence.create(
            candidate_id=candidate.candidate_id,
            reviewer_id="local-reviewer-1",
            verdict="accepted",
            rationale="source and field evidence verified",
        )
        for candidate in pending.candidates
    )
    reviewed_inputs = ConstructionInputs.create(
        cleaning_config_digest=base_inputs.cleaning_config_digest,
        sources=base_inputs.sources,
        chunks=base_inputs.chunks,
        transforms=base_inputs.transforms,
        ir_artifacts=base_inputs.ir_artifacts,
        reviews=reviews,
    )
    reviewed = construct_dataset(recipe, reviewed_inputs)
    assert all(decision.status == "accepted" for decision in reviewed.decisions)
    assert all(decision.review is not None for decision in reviewed.decisions)
    assert len(reviewed.records) == len(pending.candidates)

    config = dict(head.stages["construct"].config)
    with store.begin(
        "construct",
        expected_revision_id=head.revision_id,
    ) as transaction:
        recipe_artifact = transaction.put_artifact(
            _output_bytes(store, "construct", "recipe"),
            kind="dataset-recipe",
            media_type="application/json",
            source_ids=recipe.source_ids,
            producer_id="veriformis.construction.recipe",
            producer_version="1",
            config=config,
        )
        result_artifact = transaction.put_artifact(
            lossless_json_bytes(construction_result_to_dict(reviewed)),
            kind="construction-result",
            media_type="application/json",
            source_ids=recipe.source_ids,
            producer_id="veriformis.construction.result",
            producer_version="1",
            config=config,
        )
        # The commit gate's semantic replay must accept the reviewed result.
        transaction.commit(
            outputs={"recipe": recipe_artifact, "result": result_artifact},
            config=config,
        )


def test_reviewed_result_flows_through_finished_dataset_stages(tmp_path):
    service, workspace = _prepare_constructed_workspace(
        tmp_path,
        require_review=True,
    )
    _commit_reviewed_result(workspace)

    # Before the fix every downstream stage misreported the gate-certified
    # reviewed result as "construction result does not match exact replay".
    curated = service.curate(workspace, evaluation_required=False)
    assert curated.included_count > 0
    assert not curated.coverage_blockers

    split = service.split(workspace)
    assert split.train_record_count + split.evaluation_record_count > 0

    formatted = service.format(workspace)
    assert formatted.row_schema == "text"
    assert formatted.train_row_count + formatted.evaluation_row_count > 0

    validated = service.validate(workspace)
    assert validated.exit_status == 0
    assert validated.report is not None
    assert validated.report.status == "passed"

    bundle = tmp_path / "bundle"
    sealed = service.seal(workspace, bundle)
    assert sealed.publication is not None
    verified = service.verify(
        bundle,
        manifest_sha256=sealed.publication.manifest_sha256,
    )
    assert verified.verification is not None
    assert verified.verification.trust_grade == "external_digest"

    persisted = construction_result_from_json_bytes(
        _output_bytes(Workspace.open(workspace), "construct", "result")
    )
    assert all(decision.review is not None for decision in persisted.decisions)


def test_unreviewed_pipeline_replays_with_empty_review_evidence(tmp_path):
    service, workspace = _prepare_constructed_workspace(
        tmp_path,
        require_review=False,
    )
    persisted = construction_result_from_json_bytes(
        _output_bytes(Workspace.open(workspace), "construct", "result")
    )
    assert all(decision.review is None for decision in persisted.decisions)
    assert persisted.records

    curated = service.curate(workspace, evaluation_required=False)
    assert curated.included_count > 0
    service.split(workspace)
    formatted = service.format(workspace)
    assert formatted.row_schema == "text"
