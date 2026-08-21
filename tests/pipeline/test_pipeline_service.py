"""Group 4 service surface and CLI-parity acceptance tests."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.construction import construction_result_from_json_bytes
from veriformis.datasets import (
    dataset_validation_report_from_json_bytes,
    split_result_from_json_bytes,
)
from veriformis.errors import ConstructionError
from veriformis.pipeline import PipelineService
from veriformis.workspace import Workspace

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "acceptance" / "v1"
runner = CliRunner()


def _raw_sources() -> list[Path]:
    """Golden multi-source corpus used by the M1.1 dual-objective gate."""
    return sorted(
        path
        for path in (FIXTURE_ROOT / "raw" / "corpus").rglob("*")
        if path.is_file()
    )


def _succeeded(result) -> None:
    assert result.exit_code == 0, result.output


def _artifact_bytes(workspace: Workspace, stage: str, key: str) -> bytes:
    revision = workspace.head()
    artifact_id = revision.stages[stage].outputs[key]
    return workspace.read_artifact(artifact_id, revision=revision)


def _stage_config(workspace: Workspace, stage: str) -> dict:
    return workspace.head().stages[stage].config


def _finish_via_service(
    service: PipelineService,
    workspace: Path,
    *,
    objective: str,
    bundle: Path,
    split_ratio_ppm: int = 500_000,
) -> dict[str, object]:
    if objective == "continuation":
        service.construct(
            workspace,
            objective=objective,
            split_ratio_ppm=split_ratio_ppm,
        )
    else:
        service.construct(workspace, objective=objective)
    service.curate(workspace, evaluation_required=False)
    service.split(workspace)
    service.format(workspace)
    validate = service.validate(workspace)
    assert validate.exit_status == 0
    assert validate.report is not None
    assert validate.report.status == "passed"
    seal = service.seal(workspace, bundle)
    assert seal.publication is not None
    verify = service.verify(
        bundle,
        manifest_sha256=seal.publication.manifest_sha256,
    )
    assert verify.verification is not None
    assert verify.verification.trust_grade == "external_digest"
    store = Workspace.open(workspace)
    return {
        "recipe": _artifact_bytes(store, "construct", "recipe"),
        "result": _artifact_bytes(store, "construct", "result"),
        "plan": _artifact_bytes(store, "curate", "plan"),
        "curation": _artifact_bytes(store, "curate", "result"),
        "split": _artifact_bytes(store, "split", "result"),
        "row_set": _artifact_bytes(store, "format", "row-set"),
        "train": _artifact_bytes(store, "format", "train"),
        "evaluation": _artifact_bytes(store, "format", "evaluation"),
        "provenance": _artifact_bytes(store, "format", "provenance"),
        "snapshot": _artifact_bytes(store, "validate", "snapshot"),
        "report": _artifact_bytes(store, "validate", "report"),
        "manifest": _artifact_bytes(store, "seal", "manifest"),
        "attestation": _artifact_bytes(store, "seal", "attestation"),
        "construct_config": _stage_config(store, "construct"),
        "curate_config": _stage_config(store, "curate"),
        "split_config": _stage_config(store, "split"),
        "format_config": _stage_config(store, "format"),
        "validate_config": _stage_config(store, "validate"),
        "seal_config": _stage_config(store, "seal"),
        "manifest_sha256": seal.publication.manifest_sha256,
        "bundle_id": seal.publication.bundle_id,
        "snapshot_id": validate.snapshot_id,
        "assignment_digest": split_result_from_json_bytes(
            _artifact_bytes(store, "split", "result")
        ).assignment_digest,
        "result_id": construction_result_from_json_bytes(
            _artifact_bytes(store, "construct", "result")
        ).result_id,
        "report_id": dataset_validation_report_from_json_bytes(
            _artifact_bytes(store, "validate", "report")
        ).report_id,
        "bundle_files": {
            path.relative_to(bundle).as_posix(): path.read_bytes()
            for path in sorted(bundle.rglob("*"))
            if path.is_file()
        },
    }


def _finish_via_cli(
    workspace: Path,
    *,
    objective: str,
    bundle: Path,
    split_ratio_ppm: int = 500_000,
) -> dict[str, object]:
    construct_cmd = ["construct", str(workspace), "--objective", objective]
    if objective == "continuation":
        construct_cmd.extend(["--split-ratio-ppm", str(split_ratio_ppm)])
    for command in (
        construct_cmd,
        ["curate", str(workspace), "--allow-empty-evaluation"],
        ["split", str(workspace)],
        ["format", str(workspace)],
        ["validate", str(workspace)],
        ["seal", str(workspace), "-o", str(bundle)],
    ):
        _succeeded(runner.invoke(app, command))
    store = Workspace.open(workspace)
    manifest_sha256 = None
    # Recover digest from seal stdout is fragile; recompute via verify path.
    from veriformis.bundle import verify_finished_bundle
    from veriformis.identity import sha256_digest

    manifest_bytes = (bundle / "manifest.json").read_bytes()
    manifest_sha256 = sha256_digest(manifest_bytes)
    verification = verify_finished_bundle(
        bundle,
        expected_manifest_sha256=manifest_sha256,
    )
    assert verification.trust_grade == "external_digest"
    return {
        "recipe": _artifact_bytes(store, "construct", "recipe"),
        "result": _artifact_bytes(store, "construct", "result"),
        "plan": _artifact_bytes(store, "curate", "plan"),
        "curation": _artifact_bytes(store, "curate", "result"),
        "split": _artifact_bytes(store, "split", "result"),
        "row_set": _artifact_bytes(store, "format", "row-set"),
        "train": _artifact_bytes(store, "format", "train"),
        "evaluation": _artifact_bytes(store, "format", "evaluation"),
        "provenance": _artifact_bytes(store, "format", "provenance"),
        "snapshot": _artifact_bytes(store, "validate", "snapshot"),
        "report": _artifact_bytes(store, "validate", "report"),
        "manifest": _artifact_bytes(store, "seal", "manifest"),
        "attestation": _artifact_bytes(store, "seal", "attestation"),
        "construct_config": _stage_config(store, "construct"),
        "curate_config": _stage_config(store, "curate"),
        "split_config": _stage_config(store, "split"),
        "format_config": _stage_config(store, "format"),
        "validate_config": _stage_config(store, "validate"),
        "seal_config": _stage_config(store, "seal"),
        "manifest_sha256": manifest_sha256,
        "bundle_id": verification.bundle_id,
        "snapshot_id": verification.dataset_snapshot_id,
        "assignment_digest": split_result_from_json_bytes(
            _artifact_bytes(store, "split", "result")
        ).assignment_digest,
        "result_id": construction_result_from_json_bytes(
            _artifact_bytes(store, "construct", "result")
        ).result_id,
        "report_id": dataset_validation_report_from_json_bytes(
            _artifact_bytes(store, "validate", "report")
        ).report_id,
        "bundle_files": {
            path.relative_to(bundle).as_posix(): path.read_bytes()
            for path in sorted(bundle.rglob("*"))
            if path.is_file()
        },
    }


def _prepare_shared_base(tmp_path: Path) -> Path:
    """Parse/clean/chunk once, then clone the workspace for independent finishes."""
    sources = _raw_sources()
    base = tmp_path / "base-workspace"
    service = PipelineService()
    service.parse(sources, base, source_root=FIXTURE_ROOT)
    service.clean(base)
    service.chunk(base)
    return base


def _clone_workspace(src: Path, dest: Path) -> Path:
    shutil.copytree(src, dest)
    return dest


def _assert_semantic_parity(left: dict[str, object], right: dict[str, object]) -> None:
    comparable_keys = (
        "recipe",
        "result",
        "plan",
        "curation",
        "split",
        "row_set",
        "train",
        "evaluation",
        "provenance",
        "snapshot",
        "report",
        "manifest",
        "attestation",
        "construct_config",
        "curate_config",
        "split_config",
        "format_config",
        "validate_config",
        "seal_config",
        "manifest_sha256",
        "bundle_id",
        "snapshot_id",
        "assignment_digest",
        "result_id",
        "report_id",
        "bundle_files",
    )
    for key in comparable_keys:
        assert left[key] == right[key], key


def test_pipeline_service_parse_clean_chunk_are_typed(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("one paragraph\n\ntwo paragraph", encoding="utf-8")
    workspace = tmp_path / "workspace"
    service = PipelineService()

    parsed = service.parse([source], workspace, source_root=tmp_path)
    assert parsed.source_count == 1
    assert parsed.revision_id is not None
    cleaned = service.clean(workspace)
    assert cleaned.document_count == 1
    chunked = service.chunk(workspace)
    assert chunked.chunk_count >= 1
    assert Workspace.open(workspace).head().committed_stage == "chunk"


def test_cli_and_service_dual_objective_m1_1_acceptance(tmp_path):
    """Same multi-source corpus, both objectives, API and CLI digests match."""
    base = _prepare_shared_base(tmp_path)
    service = PipelineService()
    objectives = (
        ("full_text", 500_000),
        ("continuation", 400_000),
    )
    for objective, split_ratio_ppm in objectives:
        api_ws = _clone_workspace(base, tmp_path / f"api-{objective}")
        cli_ws = _clone_workspace(base, tmp_path / f"cli-{objective}")
        api_bundle = tmp_path / f"api-{objective}.vfbundle"
        cli_bundle = tmp_path / f"cli-{objective}.vfbundle"

        api_facts = _finish_via_service(
            service,
            api_ws,
            objective=objective,
            bundle=api_bundle,
            split_ratio_ppm=split_ratio_ppm,
        )
        cli_facts = _finish_via_cli(
            cli_ws,
            objective=objective,
            bundle=cli_bundle,
            split_ratio_ppm=split_ratio_ppm,
        )
        _assert_semantic_parity(api_facts, cli_facts)

        # Evidence graph: every accepted record keeps field-level evidence.
        result = construction_result_from_json_bytes(api_facts["result"])  # type: ignore[arg-type]
        assert result.records
        for record in result.records:
            assert record.fields
            for field in record.fields:
                assert field.evidence is not None

        report = dataset_validation_report_from_json_bytes(api_facts["report"])  # type: ignore[arg-type]
        assert report.status == "passed"
        assert all(gate.status == "passed" for gate in report.gate_results)


def test_cli_adapter_does_not_own_stage_policy_for_construct(tmp_path):
    """Construct validation errors originate from the service, not Typer option code."""
    source = tmp_path / "source.txt"
    source.write_text("stable source text for construct refusal", encoding="utf-8")
    workspace = tmp_path / "workspace"
    service = PipelineService()
    service.parse([source], workspace, source_root=tmp_path)
    service.clean(workspace)
    service.chunk(workspace)

    with pytest.raises(ConstructionError, match="unknown objective 'summary'"):
        service.construct(workspace, objective="summary")

    result = runner.invoke(
        app,
        ["construct", str(workspace), "--objective", "summary"],
    )
    assert result.exit_code == 2
    assert "error[construction-invalid]" in result.output
    assert "unknown objective 'summary'" in result.output


def test_construct_rejects_invalid_taxonomy_before_opening_workspace(tmp_path):
    service = PipelineService()
    missing = tmp_path / "not-created"

    with pytest.raises(ConstructionError, match="aptus-handoff-v1"):
        service.construct(
            missing,
            objective="full_text",
            consumer_profile="aptus-handoff-v1",
        )
    with pytest.raises(ConstructionError, match="unknown semantic row ''"):
        service.construct(
            missing,
            objective="continuation",
            target_row_schema="",
        )

    assert not missing.exists()
