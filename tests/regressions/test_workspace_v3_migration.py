from pathlib import Path

import pytest

from veriformis.identity import derive_id, lossless_json_bytes
from veriformis.workspace import (
    GROUP2_REVISION_SCHEMA_VERSION,
    GROUP2_STAGES,
    LEGACY_REVISION_SCHEMA_VERSION,
    LEGACY_STAGES,
    STAGES,
    STAGE_DEPENDENCIES,
    WORKSPACE_LAYOUT_SCHEMA_VERSION,
    WORKSPACE_REVISION_SCHEMA_VERSION,
    StageState,
    Workspace,
    WorkspaceMetadata,
    _new_revision,
)


def _workspace_at_schema(
    root: Path,
    *,
    schema_version: int,
    failure_injector=None,
) -> Workspace:
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
    stages = (
        LEGACY_STAGES
        if schema_version == LEGACY_REVISION_SCHEMA_VERSION
        else GROUP2_STAGES
    )
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
    return Workspace.open(root, failure_injector=failure_injector)


def test_fresh_workspace_uses_finished_dataset_stage_graph(tmp_path):
    workspace = Workspace.create(tmp_path / "workspace")
    revision = workspace.head()

    assert revision.schema_version == WORKSPACE_REVISION_SCHEMA_VERSION == 3
    assert set(revision.stages) == set(STAGES)
    assert STAGE_DEPENDENCIES == {
        "parse": (),
        "clean": ("parse",),
        "chunk": ("clean",),
        "construct": ("parse", "clean", "chunk"),
        "curate": ("construct",),
        "split": ("construct", "curate"),
        "format": ("construct", "curate", "split"),
        "validate": (
            "parse",
            "clean",
            "chunk",
            "construct",
            "curate",
            "split",
            "format",
        ),
        "seal": (
            "parse",
            "clean",
            "chunk",
            "construct",
            "curate",
            "split",
            "format",
            "validate",
        ),
    }
    assert all(state.status == "absent" for state in revision.stages.values())


def test_group2_workspace_migrates_to_v3_without_rewriting_upstream(tmp_path):
    workspace = _workspace_at_schema(
        tmp_path / "workspace",
        schema_version=GROUP2_REVISION_SCHEMA_VERSION,
    )
    before = workspace.head()

    migrated = workspace.migrate_to_current(before.revision_id)

    assert migrated.schema_version == WORKSPACE_REVISION_SCHEMA_VERSION
    assert migrated.parent_revision_id == before.revision_id
    for stage in ("parse", "clean", "chunk", "construct"):
        assert migrated.stages[stage] == before.stages[stage]
    for stage in ("curate", "split", "format", "validate", "seal"):
        assert migrated.stages[stage] == StageState.absent(stage)
    assert workspace.verify_history() == (
        migrated.revision_id,
        before.revision_id,
    )


def test_v1_migration_commits_recoverable_v2_then_v3(tmp_path):
    workspace = _workspace_at_schema(
        tmp_path / "workspace",
        schema_version=LEGACY_REVISION_SCHEMA_VERSION,
    )
    legacy = workspace.head()

    current = workspace.migrate_to_current()
    history = workspace.verify_history()
    intermediate = workspace.get_revision(history[1])

    assert current.schema_version == WORKSPACE_REVISION_SCHEMA_VERSION
    assert intermediate.schema_version == GROUP2_REVISION_SCHEMA_VERSION
    assert intermediate.parent_revision_id == legacy.revision_id
    assert current.parent_revision_id == intermediate.revision_id
    assert workspace.migrate_to_current().revision_id == current.revision_id


def test_interruption_before_v3_head_leaves_valid_v2_for_retry(tmp_path):
    before_head_calls = 0

    def fail_second_head(point: str) -> None:
        nonlocal before_head_calls
        if point != "before-head":
            return
        before_head_calls += 1
        if before_head_calls == 2:
            raise RuntimeError("injected before v3 HEAD")

    workspace = _workspace_at_schema(
        tmp_path / "workspace",
        schema_version=LEGACY_REVISION_SCHEMA_VERSION,
        failure_injector=fail_second_head,
    )

    with pytest.raises(RuntimeError, match="before v3 HEAD"):
        workspace.migrate_to_current()

    intermediate = workspace.head()
    assert intermediate.schema_version == GROUP2_REVISION_SCHEMA_VERSION
    assert workspace.verify_history()[0] == intermediate.revision_id

    resumed = Workspace.open(workspace.root).migrate_to_current()
    assert resumed.schema_version == WORKSPACE_REVISION_SCHEMA_VERSION
    assert resumed.parent_revision_id == intermediate.revision_id
