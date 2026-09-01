"""Phase 20.3: every supported version still loads or has an upgrade path."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path, PurePosixPath

import pytest
from typer.testing import CliRunner

from veriformis.automation.spec import load_project_spec
from veriformis.bundle import FinishedBundleManifest
from veriformis.cli import app
from veriformis.datasets.validation import dataset_validation_report_from_json_bytes
from veriformis.errors import (
    MappingError,
    ProjectSpecError,
    UnsupportedWorkspaceVersionError,
)
from veriformis.exports.api import (
    EXPORT_SURFACE_REQUEST_SCHEMA,
    EXPORT_SURFACE_REQUEST_SCHEMA_V2,
)
from veriformis.identity import derive_id, lossless_json_bytes, sha256_digest
from veriformis.mapping.models import MappingPlan
from veriformis.pipeline import PipelineService
from veriformis.profiles import discover_profile_admissions
from veriformis.recipes.pipeline_spec import (
    PIPELINE_SCHEMA_VERSION,
    PipelineSpecError,
    pipeline_spec_from_dict,
)
from veriformis.workspace import (
    GROUP2_REVISION_SCHEMA_VERSION,
    GROUP2_STAGES,
    IMPORT_REVISION_SCHEMA_VERSION,
    IMPORT_STAGES,
    LEGACY_REVISION_SCHEMA_VERSION,
    LEGACY_STAGES,
    STAGES,
    WORKSPACE_LAYOUT_SCHEMA_VERSION,
    WORKSPACE_REVISION_SCHEMA_VERSION,
    StageState,
    Workspace,
    WorkspaceMetadata,
    _new_revision,
)


ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs/migration.md"
PHASE3_WORKSPACE = (
    ROOT / "tests/regressions/fixtures/phase3/pre-taxonomy-default-clean.json"
)
PHASE3_BUNDLE = (
    ROOT / "tests/regressions/fixtures/phase3/pre-taxonomy-full-text.vfbundle.json"
)
EXPECTED_BUNDLE_MANIFEST_SHA256 = (
    "2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733"
)
RUNNER = CliRunner()


def _workspace_at_schema(root: Path, *, schema_version: int) -> Workspace:
    for directory in (
        root / "objects" / "sha256",
        root / "revisions",
        root / ".txn",
    ):
        directory.mkdir(parents=True, exist_ok=True)
    (root / "LOCK").touch()
    metadata = WorkspaceMetadata(
        schema_version=WORKSPACE_LAYOUT_SCHEMA_VERSION,
        workspace_id=derive_id("ws", {"schema-fixture": schema_version}),
        created_at="2026-01-01T00:00:00+00:00",
    )
    (root / "workspace.json").write_bytes(lossless_json_bytes(metadata))
    stages = {
        LEGACY_REVISION_SCHEMA_VERSION: LEGACY_STAGES,
        GROUP2_REVISION_SCHEMA_VERSION: GROUP2_STAGES,
        WORKSPACE_REVISION_SCHEMA_VERSION: STAGES,
        IMPORT_REVISION_SCHEMA_VERSION: IMPORT_STAGES,
    }[schema_version]
    initial = _new_revision(
        schema_version=schema_version,
        parent_revision_id=None,
        committed_stage="init",
        committed_at="1970-01-01T00:00:00+00:00",
        sources={},
        artifacts={},
        stages={stage: StageState.absent(stage) for stage in stages},
    )
    revision_dir = root / "revisions" / initial.revision_id
    revision_dir.mkdir()
    (revision_dir / "revision.json").write_bytes(lossless_json_bytes(initial))
    (root / "HEAD").write_text(initial.revision_id + "\n", encoding="ascii")
    return Workspace.open(root)


def test_migration_guide_names_every_supported_family() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    for required in (
        "Physical layout schema is **1**",
        "upgrade-workspace",
        "minimal-v1",
        "deterministic-vfbundle-zip-v1",
        "deterministic-export-pack-zip-v1",
        "veriformis.mapping-plan/v1",
        "veriformis.pipeline/v1",
        "veriformis.project-spec/v1",
        "veriformis.project-lock/v1",
        "veriformis.export-surface-request/v1",
        "veriformis.export-surface-request/v2",
        "veriformis.profile-admission-discovery/v1",
        "Unknown versions fail closed",
        "Do not hand-edit content-addressed objects",
    ):
        assert required in text, required


def test_workspace_layout_and_revision_paths(tmp_path: Path) -> None:
    assert WORKSPACE_LAYOUT_SCHEMA_VERSION == 1
    assert LEGACY_REVISION_SCHEMA_VERSION == 1
    assert GROUP2_REVISION_SCHEMA_VERSION == 2
    assert WORKSPACE_REVISION_SCHEMA_VERSION == 3
    assert IMPORT_REVISION_SCHEMA_VERSION == 4
    current = Workspace.create(tmp_path / "current")
    assert current.head().schema_version == 3
    outcome = PipelineService().upgrade_workspace(tmp_path / "current")
    assert outcome.already_current is True

    v1 = _workspace_at_schema(tmp_path / "v1", schema_version=1)
    migrated_v1 = v1.migrate_to_current(v1.head().revision_id)
    assert migrated_v1.schema_version == 3

    v2 = _workspace_at_schema(tmp_path / "v2", schema_version=2)
    migrated_v2 = v2.migrate_to_current(v2.head().revision_id)
    assert migrated_v2.schema_version == 3

    v4 = Workspace.create(tmp_path / "v4", schema_version=4)
    assert v4.head().schema_version == 4
    same = v4.migrate_to_current(v4.head().revision_id)
    assert same.revision_id == v4.head().revision_id
    assert same.schema_version == 4

    with pytest.raises(UnsupportedWorkspaceVersionError, match="not supported"):
        Workspace.create(tmp_path / "v5", schema_version=5)

    foreign = tmp_path / "layout2"
    foreign.mkdir()
    for directory in ("objects/sha256", "revisions", ".txn"):
        (foreign / directory).mkdir(parents=True, exist_ok=True)
    (foreign / "LOCK").touch()
    metadata = WorkspaceMetadata(
        schema_version=2,
        workspace_id=derive_id("ws", {"layout": 2}),
        created_at="2026-01-01T00:00:00+00:00",
    )
    (foreign / "workspace.json").write_bytes(lossless_json_bytes(metadata))
    (foreign / "HEAD").write_text("rev-v1-dead\n", encoding="ascii")
    with pytest.raises(UnsupportedWorkspaceVersionError, match="layout schema"):
        Workspace.open(foreign)

    flat = tmp_path / "flat"
    flat.mkdir()
    (flat / "registry.json").write_text("{}", encoding="utf-8")
    with pytest.raises(UnsupportedWorkspaceVersionError, match="legacy flat"):
        Workspace.create(flat)


def test_pre_taxonomy_workspace_and_bundle_still_load(tmp_path: Path) -> None:
    payload = json.loads(PHASE3_WORKSPACE.read_text(encoding="utf-8"))
    workspace_root = tmp_path / "pre-taxonomy"
    for raw_path, encoded_file in sorted(payload["files"].items()):
        relative_path = PurePosixPath(raw_path)
        contents = base64.b64decode("".join(encoded_file["base64"]), validate=True)
        assert hashlib.sha256(contents).hexdigest() == encoded_file["sha256"]
        destination = workspace_root.joinpath(*relative_path.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(contents)
    (workspace_root / ".txn").mkdir()
    opened = Workspace.open(workspace_root)
    assert opened.metadata.schema_version == 1
    assert opened.head().schema_version == 3

    encoded_fixture = json.loads(PHASE3_BUNDLE.read_text(encoding="utf-8"))
    bundle = tmp_path / "sealed.vfbundle"
    for relative, encoded in encoded_fixture["files_base64"].items():
        destination = bundle.joinpath(*relative.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(base64.b64decode(encoded, validate=True))
    manifest_bytes = (bundle / "manifest.json").read_bytes()
    assert sha256_digest(manifest_bytes) == EXPECTED_BUNDLE_MANIFEST_SHA256
    manifest = FinishedBundleManifest.from_json_bytes(manifest_bytes)
    assert manifest.schema_version == "veriformis.finished-bundle-manifest/v1"
    dataset_validation_report_from_json_bytes((bundle / "validation.json").read_bytes())
    outcome = PipelineService().verify(
        bundle,
        manifest_sha256=EXPECTED_BUNDLE_MANIFEST_SHA256,
    )
    assert outcome.exit_status == 0


def test_mapping_recipe_export_and_profile_versions_still_load() -> None:
    with pytest.raises(MappingError, match="persisted schema"):
        MappingPlan.model_validate({"schema_version": "veriformis.mapping-plan/v0"})

    with pytest.raises(PipelineSpecError, match="unsupported pipeline schema"):
        pipeline_spec_from_dict(
            {
                "schema_version": "veriformis.pipeline/v0",
                "workspace": "/tmp/ws",
                "sources": ["a.md"],
                "stages": {"parse": {}, "seal": {"out": "/tmp/out.vfbundle"}},
            },
            base_dir=Path("/tmp"),
        )
    loaded = pipeline_spec_from_dict(
        {
            "schema_version": PIPELINE_SCHEMA_VERSION,
            "workspace": "/tmp/ws",
            "sources": ["a.md"],
            "stages": {"parse": {}, "seal": {"out": "/tmp/out.vfbundle"}},
        },
        base_dir=Path("/tmp"),
    )
    assert loaded.schema_version == "veriformis.pipeline/v1"

    with pytest.raises(ProjectSpecError, match="unknown project spec contract"):
        load_project_spec(
            {
                "schema_id": "veriformis.project-spec/v0",
                "contract_id": "veriformis.project-spec",
                "contract_version": 1,
            }
        )
    admissions = discover_profile_admissions()
    assert admissions["schema_id"] == "veriformis.profile-admission-discovery/v1"
    assert admissions["contract_version"] == 1
    assert EXPORT_SURFACE_REQUEST_SCHEMA == "veriformis.export-surface-request/v1"
    assert EXPORT_SURFACE_REQUEST_SCHEMA_V2 == "veriformis.export-surface-request/v2"


def test_upgrade_workspace_cli_is_a_noop_on_current(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    Workspace.create(workspace)
    result = RUNNER.invoke(app, ["upgrade-workspace", str(workspace)])
    assert result.exit_code == 0, result.output
    assert "already current" in result.output
