"""Post-20 defect D-06: the dataset-row seal shares the document seal's recovery.

``_seal_imported`` had no partial-publication contract: a bundle that became
visible while the workspace receipt failed to commit surfaced as a plain error
with no receipt facts, and an already-published identical destination was not
adopted. Both seal paths now run through one publish-or-recover helper.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis import workspace as workspace_module
from veriformis.cli import app
from veriformis.identity import sha256_digest
from veriformis.mapping import FieldMapping, MappingPlan, mapping_confirmation_digest
from veriformis.pipeline import PipelineService
from veriformis.pipeline.service import SealPartialPublicationError
from veriformis.workspace import Workspace, is_import_revision

FIXTURES = Path(__file__).parent / "fixtures" / "phase7"
runner = CliRunner()


def _validated_import(tmp_path: Path, service: PipelineService) -> Path:
    source = tmp_path / "text.jsonl"
    source.write_bytes((FIXTURES / "text.jsonl").read_bytes())
    workspace = tmp_path / "ws"
    service.parse([source], workspace, source_root=tmp_path, mode="dataset-row")
    head = Workspace.open(workspace).head()
    assert is_import_revision(head.schema_version)
    mappings = [FieldMapping.create(source_path="text", target_key="text")]
    plan = MappingPlan.create(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        container_kind="jsonl",
        confirmation_digest=mapping_confirmation_digest(
            goal_id="learn-the-text",
            representation_id="whole-text",
            row_schema="text",
            field_mappings=mappings,
            source_digests=tuple(
                (item.logical_path, item.sha256) for item in head.sources.values()
            ),
        ),
        field_mappings=mappings,
    )
    service.map_rows(
        workspace,
        goal="learn-the-text",
        representation="whole-text",
        mapping_plan=plan,
    )
    service.curate(workspace, goal="learn-the-text")
    service.split(workspace)
    service.format(workspace)
    assert service.validate(workspace).exit_status == 0
    return workspace


def _fail_head_promotion(path: Path, data: bytes) -> bool:
    raise OSError(f"injected HEAD failure for {path}")


def test_imported_seal_partial_publication_carries_the_receipt(tmp_path, monkeypatch):
    service = PipelineService()
    workspace = _validated_import(tmp_path, service)
    bundle = tmp_path / "partial.vfbundle"
    monkeypatch.setattr(workspace_module, "_promote_commit_pointer", _fail_head_promotion)

    with pytest.raises(SealPartialPublicationError) as info:
        service.seal(workspace, bundle)

    assert bundle.is_dir()
    receipt = info.value.publication
    assert Path(receipt.bundle_path) == bundle.resolve()
    assert receipt.manifest_sha256 == sha256_digest((bundle / "manifest.json").read_bytes())
    assert isinstance(info.value.cause, OSError)


def test_imported_seal_cli_reports_partial_publication_guidance(tmp_path, monkeypatch):
    workspace = _validated_import(tmp_path, PipelineService())
    bundle = tmp_path / "cli-partial.vfbundle"
    monkeypatch.setattr(workspace_module, "_promote_commit_pointer", _fail_head_promotion)

    result = runner.invoke(app, ["seal", str(workspace), "-o", str(bundle)])

    assert result.exit_code == 1, result.output
    assert "published bundle remains visible at" in result.output
    assert "workspace receipt did not commit" in result.output
    assert sha256_digest((bundle / "manifest.json").read_bytes()) in result.output


def test_imported_seal_adopts_an_exact_prior_publication(tmp_path):
    service = PipelineService()
    workspace = _validated_import(tmp_path, service)
    bundle = tmp_path / "prior.vfbundle"
    first = service.seal(workspace, bundle)
    assert first.publication is not None
    # Roll the workspace back to the validated revision so seal runs again
    # against the same visible destination.
    store = Workspace.open(workspace)
    head = store.head()
    parent = head.parent_revision_id
    assert parent is not None
    workspace_module._atomic_write(workspace / "HEAD", (parent + "\n").encode("utf-8"))

    second = service.seal(workspace, bundle)

    assert second.publication is not None
    assert second.publication.manifest_sha256 == first.publication.manifest_sha256
    assert bundle.is_dir()


def test_imported_seal_refuses_a_different_visible_destination(tmp_path):
    service = PipelineService()
    workspace = _validated_import(tmp_path, service)
    bundle = tmp_path / "foreign.vfbundle"
    bundle.mkdir()
    (bundle / "manifest.json").write_bytes(b"{}")

    with pytest.raises(Exception) as info:
        service.seal(workspace, bundle)

    assert not isinstance(info.value, SealPartialPublicationError)
    # The foreign destination is untouched.
    assert (bundle / "manifest.json").read_bytes() == b"{}"
    assert sorted(item.name for item in bundle.iterdir()) == ["manifest.json"]


def test_map_rows_writes_the_rejection_report_before_head_advances(tmp_path, monkeypatch):
    """Post-20 defect D-08: a report-write failure must not follow a durable commit."""
    from veriformis.mapping import reject as reject_module

    service = PipelineService()
    source = tmp_path / "text.jsonl"
    source.write_bytes((FIXTURES / "text.jsonl").read_bytes())
    workspace = tmp_path / "ws"
    service.parse([source], workspace, source_root=tmp_path, mode="dataset-row")
    head_before = Workspace.open(workspace).head_id
    head = Workspace.open(workspace).head()
    mappings = [FieldMapping.create(source_path="text", target_key="text")]
    plan = MappingPlan.create(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        container_kind="jsonl",
        confirmation_digest=mapping_confirmation_digest(
            goal_id="learn-the-text",
            representation_id="whole-text",
            row_schema="text",
            field_mappings=mappings,
            source_digests=tuple(
                (item.logical_path, item.sha256) for item in head.sources.values()
            ),
        ),
        field_mappings=mappings,
    )

    def refuse_write(*args, **kwargs):
        raise OSError("injected rejection-report write failure")

    monkeypatch.setattr(reject_module, "write_mapping_rejection_report", refuse_write)

    with pytest.raises(OSError, match="injected rejection-report write failure"):
        service.map_rows(
            workspace,
            goal="learn-the-text",
            representation="whole-text",
            mapping_plan=plan,
        )

    assert Workspace.open(workspace).head_id == head_before
    assert not list(tmp_path.glob("ws.mapping-rejection-*.json"))
