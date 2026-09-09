"""Post-20 defect D-05: ``handoff-verify`` proves, it does not trust.

``consume_aptus_handoff`` checked the row schema against the descriptor's own
``backend_capabilities`` and never recomputed the masking expectation or the
plan, recipe, objective, and source identities against the sealed provenance.
A hand-built descriptor for a ``text`` bundle that declared permissive
capabilities was accepted. The consumer now recomputes every claim from the
taxonomy pin and the sealed bytes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.handoff import (
    build_aptus_handoff,
    consume_aptus_handoff,
    handoff_path_for_bundle,
    write_aptus_handoff,
)
from veriformis.handoff.aptus_v1 import (
    _APTUS_CONSUMER_PROFILE,
    _DEFAULT_ACCEPTED_SCHEMAS,
    _DEFAULT_REJECTED_SCHEMAS,
    _masking_expectation,
)
from veriformis.identity import derive_id
from veriformis.pipeline import PipelineService
from veriformis.taxonomy import PROFILE_FORBIDDEN_ROW_SCHEMAS

runner = CliRunner()


def _seal(tmp_path: Path, objective: str) -> tuple[Path, str]:
    source = tmp_path / "source.txt"
    source.write_text(
        "Prompt-bearing first paragraph with enough grounded text.\n\n"
        "Second paragraph continues the supervised construction material.",
        encoding="utf-8",
    )
    workspace = tmp_path / "workspace"
    bundle = tmp_path / "out.vfbundle"
    service = PipelineService()
    service.parse([source], workspace, source_root=tmp_path)
    service.clean(workspace)
    service.chunk(workspace)
    if objective == "continuation":
        service.construct(workspace, objective=objective, split_ratio_ppm=400_000)
    else:
        service.construct(workspace, objective=objective)
    service.curate(workspace, evaluation_required=False)
    service.split(workspace)
    service.format(workspace)
    assert service.validate(workspace).exit_status == 0
    sealed = service.seal(workspace, bundle)
    assert sealed.publication is not None
    return bundle, sealed.publication.manifest_sha256


def _reissue(body: dict[str, Any]) -> dict[str, Any]:
    """Return a self-consistent descriptor: normalized nested blocks, fresh id."""
    from veriformis.handoff.aptus_v1 import (
        BackendCapabilities,
        FileBinding,
        MaskingExpectation,
        PartitionBinding,
    )

    body = {key: value for key, value in body.items() if key != "handoff_id"}
    for name, model in (
        ("train", PartitionBinding),
        ("evaluation", PartitionBinding),
        ("provenance", FileBinding),
        ("validation", FileBinding),
        ("masking", MaskingExpectation),
        ("backend_capabilities", BackendCapabilities),
    ):
        body[name] = model.model_validate(body[name]).model_dump(mode="json")
    body["source_ids"] = list(body["source_ids"])
    return {"handoff_id": derive_id("ahd", body), **body}


def _text_descriptor(bundle: Path, manifest_sha: str) -> dict[str, Any]:
    """Hand-build the descriptor build_aptus_handoff refuses to emit for text rows."""
    from veriformis.bundle import verify_finished_bundle
    from veriformis.handoff.aptus_v1 import _load_jsonl_objects, portable_assignment_digest
    from veriformis.identity import sha256_digest

    verification = verify_finished_bundle(bundle, expected_manifest_sha256=manifest_sha)
    train = (bundle / "data" / "train.jsonl").read_bytes()
    evaluation = (bundle / "data" / "evaluation.jsonl").read_bytes()
    provenance = (bundle / "metadata" / "row-provenance.jsonl").read_bytes()
    validation = (bundle / "validation.json").read_bytes()
    provenance_rows = _load_jsonl_objects(provenance)
    first = provenance_rows[0]
    body = {
        "schema_version": "veriformis.aptus-handoff/v1",
        "bundle_id": verification.bundle_id,
        "manifest_sha256": manifest_sha,
        "content_root_sha256": verification.content_root_sha256,
        "dataset_snapshot_id": verification.dataset_snapshot_id,
        "validation_report_id": verification.validation_report_id,
        "plan_id": first["plan_id"],
        "recipe_id": first["recipe_id"],
        "construction_result_id": first["construction_result_id"],
        "split_result_id": first["split_result_id"],
        "objective_id": first["objective_id"],
        "row_schema": "text",
        "assignment_digest": portable_assignment_digest(provenance_rows),
        "source_ids": sorted({s for row in provenance_rows for s in row["source_ids"]}),
        "train": {
            "path": "data/train.jsonl",
            "role": "training-partition",
            "sha256": sha256_digest(train),
            "record_count": len(_load_jsonl_objects(train)),
            "byte_size": len(train),
        },
        "evaluation": {
            "path": "data/evaluation.jsonl",
            "role": "evaluation-partition",
            "sha256": sha256_digest(evaluation),
            "record_count": len(_load_jsonl_objects(evaluation)),
            "byte_size": len(evaluation),
        },
        "provenance": {
            "path": "metadata/row-provenance.jsonl",
            "role": "row-provenance",
            "media_type": "application/jsonl",
            "sha256": sha256_digest(provenance),
            "byte_size": len(provenance),
        },
        "validation": {
            "path": "validation.json",
            "role": "dataset-validation-report",
            "media_type": "application/json",
            "sha256": sha256_digest(validation),
            "byte_size": len(validation),
        },
        "masking": _masking_expectation("text").model_dump(mode="json"),
        "backend_capabilities": {
            # The forgery: the descriptor claims Aptus accepts text rows.
            "accepts_row_schemas": ["text", *_DEFAULT_ACCEPTED_SCHEMAS],
            "rejects_row_schemas": [],
        },
        "required_verification_grade": "external_digest",
    }
    return _reissue(body)


def test_pin_matches_taxonomy() -> None:
    assert tuple(_DEFAULT_REJECTED_SCHEMAS) == tuple(
        PROFILE_FORBIDDEN_ROW_SCHEMAS[_APTUS_CONSUMER_PROFILE]
    )
    assert "text" in _DEFAULT_REJECTED_SCHEMAS


def test_forged_permissive_capabilities_do_not_admit_a_text_bundle(tmp_path: Path) -> None:
    bundle, manifest_sha = _seal(tmp_path, "full_text")
    descriptor = _text_descriptor(bundle, manifest_sha)

    report = consume_aptus_handoff(descriptor, bundle=bundle)

    assert report.status == "rejected"
    assert "profile-forbids-row-schema:text" in report.findings
    assert "backend-capabilities-differ-from-profile-pin" in report.findings
    # The bundle itself is sound; only the claim is refused.
    assert report.verified_grade == "external_digest"


def test_forged_masking_block_is_rejected(tmp_path: Path) -> None:
    bundle, manifest_sha = _seal(tmp_path, "continuation")
    handoff = build_aptus_handoff(bundle, expected_manifest_sha256=manifest_sha)
    body = handoff.model_dump(mode="json")
    body["masking"] = {
        "row_schema": "prompt_completion",
        "supervised_boundary": "full-sequence",
        "notes": "Everything is supervised.",
    }

    report = consume_aptus_handoff(_reissue(body), bundle=bundle)

    assert report.status == "rejected"
    assert "masking-expectation-mismatch" in report.findings


def test_forged_provenance_identities_are_rejected(tmp_path: Path) -> None:
    bundle, manifest_sha = _seal(tmp_path, "continuation")
    handoff = build_aptus_handoff(bundle, expected_manifest_sha256=manifest_sha)
    body = handoff.model_dump(mode="json")
    body["plan_id"] = "fdp-v1-" + "0" * 64
    body["objective_id"] = body["recipe_id"]  # well-formed id, wrong identity
    body["source_ids"] = []

    report = consume_aptus_handoff(_reissue(body), bundle=bundle)

    assert report.status == "rejected"
    assert "provenance-binding-mismatch:plan_id" in report.findings
    assert "provenance-binding-mismatch:objective_id" in report.findings
    assert "source-ids-mismatch" in report.findings


def test_genuine_descriptor_still_accepts(tmp_path: Path) -> None:
    bundle, manifest_sha = _seal(tmp_path, "continuation")
    handoff = build_aptus_handoff(bundle, expected_manifest_sha256=manifest_sha)
    report = consume_aptus_handoff(handoff, bundle=bundle)
    assert report.status == "accepted", report.findings
    assert report.findings == ()


def test_cli_handoff_verify_rejects_the_forged_text_descriptor(tmp_path: Path) -> None:
    bundle, manifest_sha = _seal(tmp_path, "full_text")
    descriptor = _text_descriptor(bundle, manifest_sha)
    path = handoff_path_for_bundle(bundle)
    path.write_text(json.dumps(descriptor, indent=2, sort_keys=True), encoding="utf-8")

    result = runner.invoke(app, ["handoff-verify", str(path), "--bundle", str(bundle)])

    assert result.exit_code == 1, result.output
    assert "profile-forbids-row-schema:text" in result.output


def test_written_genuine_descriptor_round_trips_through_the_cli(tmp_path: Path) -> None:
    bundle, manifest_sha = _seal(tmp_path, "continuation")
    handoff = build_aptus_handoff(bundle, expected_manifest_sha256=manifest_sha)
    path = write_aptus_handoff(handoff, handoff_path_for_bundle(bundle))
    result = runner.invoke(app, ["handoff-verify", str(path), "--bundle", str(bundle)])
    assert result.exit_code == 0, result.output
