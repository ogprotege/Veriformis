import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import veriformis.workspace as workspace_module
from veriformis.chunkers.base import Chunk
from veriformis.cli import (
    _load_chunks,
    _load_sources,
    _load_transform_records,
    _output_bytes,
    app,
)
from veriformis.construction import (
    ConstructionInputs,
    ConstructionPass,
    DatasetRecipe,
    IRArtifactInput,
    SegmentationPolicy,
    TrainingObjective,
    construct_dataset,
    construction_result_to_dict,
    dataset_recipe_to_dict,
)
from veriformis.errors import (
    UnsupportedWorkspaceVersionError,
    WorkspaceCorruptError,
    WorkspaceRevisionConflict,
)
from veriformis.identity import (
    canonical_digest,
    derive_id,
    lossless_json_bytes,
    sha256_digest,
)
from veriformis.workspace import (
    CONSTRUCTION_STAGE_CONFIG_SCHEMA_VERSION,
    LEGACY_REVISION_SCHEMA_VERSION,
    LEGACY_STAGES,
    STAGES,
    WORKSPACE_LAYOUT_SCHEMA_VERSION,
    WORKSPACE_REVISION_SCHEMA_VERSION,
    StageState,
    Workspace,
    WorkspaceMetadata,
    WorkspaceRevision,
    _new_revision,
)


# Produced by the merged Group 1 implementation at dc718fb. The test never
# reconstructs it through the current revision factory.
FROZEN_GROUP1_REVISION = (
    Path(__file__).parents[1]
    / "fixtures"
    / "workspace"
    / "v1"
    / "nontrivial-parse-revision.json"
)
FROZEN_GROUP1_MANIFEST_SHA256 = (
    "a1a8d7cc67b0465896211b0b7c5f7a8b3679a6345a9814613130c67871485d09"
)
FROZEN_GROUP1_STATE_DIGEST = (
    "c6fadfc325b7ea7d7cdc8d0522d5e3a204082e9aefc9442bc4158ec072e87c13"
)
FROZEN_GROUP1_REVISION_ID = (
    "rev-v1-b2b99391005a95ff67d4d91eb9d77febd8f1ed21af6351a5745bb8412602ea4a"
)


def _legacy_workspace(
    root: Path,
    *,
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
        workspace_id=derive_id("ws", {"legacy-test-root": str(root)}),
        created_at="2026-01-01T00:00:00+00:00",
    )
    (root / "workspace.json").write_bytes(lossless_json_bytes(metadata))
    initial = _new_revision(
        schema_version=LEGACY_REVISION_SCHEMA_VERSION,
        parent_revision_id=None,
        committed_stage="init",
        committed_at="1970-01-01T00:00:00+00:00",
        sources={},
        artifacts={},
        stages={stage: StageState.absent(stage) for stage in LEGACY_STAGES},
    )
    revision_dir = root / "revisions" / initial.revision_id
    revision_dir.mkdir()
    (revision_dir / "revision.json").write_bytes(lossless_json_bytes(initial))
    (root / "HEAD").write_text(initial.revision_id + "\n", encoding="ascii")
    return Workspace.open(root, failure_injector=failure_injector)


def _commit_empty_legacy_stage(workspace: Workspace, stage: str):
    configs = {
        "parse": {"sources": []},
        "clean": {
            "rules": ["page-numbers", "whitespace"],
            "custom": None,
            "max_remove_ppm": 300_000,
        },
        "chunk": {"strategy": "paragraph", "size": 1000, "overlap": 100},
        "format": {"format": "completion"},
        "validate": {"format": "completion"},
        "seal": {},
    }
    output_schemas = {
        "parse": {"registry": "source-registry"},
        "clean": {"transforms": "transform-records"},
        "chunk": {"chunks": "chunks"},
        "format": {
            "records": "formatted-records",
            "records-meta": "records-metadata",
        },
        "validate": {"validations": "validation-report"},
        "seal": {"seal": "seal-output"},
    }
    config = configs[stage]
    if stage == "parse":
        producer_id = "veriformis.parse-stage"
        artifact_config = {"source_count": 0}
    elif stage == "clean":
        producer_id = "veriformis.cleaning"
        artifact_config = config
    elif stage == "chunk":
        producer_id = "veriformis.chunker.paragraph"
        artifact_config = config
    elif stage == "format":
        producer_id = "veriformis.serializer.completion"
        artifact_config = config
    elif stage == "validate":
        producer_id = "veriformis.validation"
        artifact_config = config
    else:
        producer_id = "legacy-seal-test"
        artifact_config = config

    with workspace.begin(stage) as transaction:
        outputs = {}
        for output_name, kind in output_schemas[stage].items():
            payload = (
                b"[]"
                if (stage, output_name)
                in {
                    ("parse", "registry"),
                    ("clean", "transforms"),
                    ("chunk", "chunks"),
                    ("validate", "validations"),
                }
                else b"{}"
            )
            outputs[output_name] = transaction.put_artifact(
                payload,
                kind=kind,
                media_type="application/json",
                producer_id=producer_id,
                producer_version="1",
                config=artifact_config,
            )
        return transaction.commit(outputs=outputs, config=config)


def _complete_legacy_pipeline(workspace: Workspace) -> None:
    for stage in LEGACY_STAGES:
        revision = _commit_empty_legacy_stage(workspace, stage)
        assert revision.schema_version == LEGACY_REVISION_SCHEMA_VERSION


def _workspace_with_chunks(tmp_path: Path) -> Workspace:
    source = tmp_path / "source.txt"
    source.write_text("First paragraph.\n\nSecond paragraph.", encoding="utf-8")
    root = tmp_path / "workspace"
    runner = CliRunner()
    for command in (
        [
            "parse",
            str(source),
            "-o",
            str(root),
            "--source-root",
            str(tmp_path),
        ],
        ["clean", str(root)],
        ["chunk", str(root)],
        ["format", str(root), "--format", "completion"],
    ):
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.output
    return Workspace.open(root)


def _construct_config(
    source_ids: list[str],
    *,
    recipe_id: str | None = None,
) -> dict[str, object]:
    return {
        "schema_version": CONSTRUCTION_STAGE_CONFIG_SCHEMA_VERSION,
        "recipe_id": recipe_id or derive_id("rcp", {"migration-test": True}),
        "selected_source_ids": source_ids,
    }


def _construction_payloads(
    workspace: Workspace,
    revision: WorkspaceRevision,
    source_ids: tuple[str, ...],
):
    selected = set(source_ids)
    sources_by_id = _load_sources(workspace, revision)
    sources = tuple(sources_by_id[source_id] for source_id in source_ids)
    chunks = tuple(
        chunk
        for chunk in _load_chunks(workspace, revision)
        if chunk.source_id in selected
    )
    assert all(isinstance(chunk, Chunk) for chunk in chunks)
    transforms = tuple(
        record
        for record in _load_transform_records(workspace, revision)
        if record.source_id in selected
    )
    clean_state = revision.stages["clean"]
    ir_artifacts = []
    for source_id in source_ids:
        artifact_id = clean_state.outputs[f"source/{source_id}/document"]
        artifact = revision.artifacts[artifact_id]
        ir_artifacts.append(
            IRArtifactInput.create(
                source_id=source_id,
                artifact_id=artifact_id,
                artifact_kind="cleaned-document-ir",
                document_json=_output_bytes(
                    workspace,
                    revision,
                    "clean",
                    f"source/{source_id}/document",
                ),
                producer_id=artifact.producer_id,
                producer_version=artifact.producer_version,
                config_digest=artifact.config_digest,
            )
        )
    objective = TrainingObjective.create("full_text")
    construction_pass = ConstructionPass.create(
        sequence=1,
        objective_kind="full_text",
    )
    chunk_config = revision.stages["chunk"].config
    recipe = DatasetRecipe.create(
        objective=objective,
        source_ids=source_ids,
        cleaning_config_digest=clean_state.config_digest,
        segmentation=SegmentationPolicy(
            schema_version="veriformis.segmentation-policy/v1",
            strategy=chunk_config["strategy"],
            size=chunk_config["size"],
            overlap=chunk_config["overlap"],
        ),
        passes=(construction_pass,),
        target_row_schema="text",
    )
    inputs = ConstructionInputs.create(
        cleaning_config_digest=clean_state.config_digest,
        sources=sources,
        chunks=chunks,
        transforms=transforms,
        ir_artifacts=ir_artifacts,
    )
    result = construct_dataset(recipe, inputs)
    config = _construct_config(list(source_ids), recipe_id=recipe.recipe_id)
    return (
        config,
        lossless_json_bytes(dataset_recipe_to_dict(recipe)),
        lossless_json_bytes(construction_result_to_dict(result)),
    )


def _put_construct_outputs(
    transaction,
    config: dict[str, object],
    *,
    source_ids: tuple[str, ...],
    producer_prefix: str = "veriformis.construction",
    recipe_bytes: bytes = b'{"recipe":true}',
    result_bytes: bytes = b'{"result":true}',
):
    return {
        "recipe": transaction.put_artifact(
            recipe_bytes,
            kind="dataset-recipe",
            media_type="application/json",
            source_ids=source_ids,
            producer_id=f"{producer_prefix}.recipe",
            producer_version="1",
            config=config,
        ),
        "result": transaction.put_artifact(
            result_bytes,
            kind="construction-result",
            media_type="application/json",
            source_ids=source_ids,
            producer_id=f"{producer_prefix}.result",
            producer_version="1",
            config=config,
        ),
    }


def test_new_workspace_separates_layout_and_revision_versions(tmp_path):
    workspace = Workspace.create(tmp_path / "workspace")

    assert workspace.metadata.schema_version == WORKSPACE_LAYOUT_SCHEMA_VERSION
    assert workspace.head().schema_version == WORKSPACE_REVISION_SCHEMA_VERSION
    assert set(workspace.head().stages) == set(STAGES)


def test_frozen_group1_revision_preserves_canonical_bytes_and_identity():
    stored = FROZEN_GROUP1_REVISION.read_bytes()
    canonical = stored.removesuffix(b"\n")

    assert sha256_digest(canonical) == FROZEN_GROUP1_MANIFEST_SHA256
    revision = WorkspaceRevision.model_validate_json(canonical)
    assert revision.schema_version == LEGACY_REVISION_SCHEMA_VERSION
    assert revision.state_digest == FROZEN_GROUP1_STATE_DIGEST
    assert revision.revision_id == FROZEN_GROUP1_REVISION_ID
    assert revision.stages["parse"].status == "complete"
    assert len(revision.sources) == 1
    assert len(revision.artifacts) == 5
    assert lossless_json_bytes(revision) == canonical


def test_schema_less_frozen_group1_revision_dispatches_to_v1(tmp_path):
    payload = json.loads(FROZEN_GROUP1_REVISION.read_text(encoding="utf-8"))
    payload.pop("schema_version")
    schema_less_bytes = lossless_json_bytes(payload)
    model_revision = WorkspaceRevision.model_validate_json(schema_less_bytes)
    workspace = _legacy_workspace(tmp_path / "legacy")
    revision_dir = workspace.root / "revisions" / FROZEN_GROUP1_REVISION_ID
    revision_dir.mkdir()
    (revision_dir / "revision.json").write_bytes(schema_less_bytes)

    revision = workspace.get_revision(
        FROZEN_GROUP1_REVISION_ID,
        verify_objects=False,
    )

    assert revision.schema_version == LEGACY_REVISION_SCHEMA_VERSION
    assert revision.state_digest == FROZEN_GROUP1_STATE_DIGEST
    assert revision.revision_id == FROZEN_GROUP1_REVISION_ID
    assert model_revision == revision


def test_schema_less_v2_revision_is_rejected_as_ambiguous(tmp_path):
    workspace = Workspace.create(tmp_path / "workspace")
    current = workspace.head()
    payload = current.model_dump(mode="json")
    payload.pop("schema_version")
    manifest = workspace.root / "revisions" / current.revision_id / "revision.json"
    manifest.write_bytes(lossless_json_bytes(payload))

    with pytest.raises(
        UnsupportedWorkspaceVersionError,
        match="schema-less workspace revisions.*exact legacy stage set",
    ):
        workspace.get_revision(current.revision_id, verify_objects=False)


def test_legacy_history_opens_and_normal_commits_remain_v1(tmp_path):
    workspace = _legacy_workspace(tmp_path / "legacy")
    _complete_legacy_pipeline(workspace)

    revision_ids = workspace.verify_history()
    assert len(revision_ids) == len(LEGACY_STAGES) + 1
    for revision_id in revision_ids:
        revision = workspace.get_revision(revision_id)
        assert revision.schema_version == LEGACY_REVISION_SCHEMA_VERSION
        assert set(revision.stages) == set(LEGACY_STAGES)


def test_construct_requires_an_explicit_legacy_migration(tmp_path):
    workspace = _legacy_workspace(tmp_path / "legacy")
    _complete_legacy_pipeline(workspace)
    before = workspace.head()

    with pytest.raises(
        UnsupportedWorkspaceVersionError,
        match=r"construct requires workspace revision schema 2.*migrate_to_current",
    ):
        workspace.begin("construct")

    command = CliRunner().invoke(
        app,
        ["construct", str(workspace.root), "--objective", "full_text"],
    )
    assert command.exit_code == 2
    assert "upgrade-workspace" in command.output
    assert workspace.head() == before


def test_migration_appends_v2_without_rewriting_any_v1_fact(tmp_path):
    workspace = _legacy_workspace(tmp_path / "legacy")
    _complete_legacy_pipeline(workspace)
    before = workspace.head()
    before_history = workspace.verify_history()

    migrated = workspace.migrate_to_current(expected_revision_id=before.revision_id)

    assert migrated.schema_version == WORKSPACE_REVISION_SCHEMA_VERSION
    assert migrated.parent_revision_id == before.revision_id
    assert migrated.committed_stage == "migration"
    assert migrated.sources == before.sources
    assert migrated.artifacts == before.artifacts
    assert {
        stage: migrated.stages[stage] for stage in LEGACY_STAGES
    } == before.stages
    assert migrated.stages["construct"] == StageState.absent("construct")
    assert workspace.verify_history() == (migrated.revision_id, *before_history)


def test_migration_is_idempotent_after_reaching_current_schema(tmp_path):
    workspace = _legacy_workspace(tmp_path / "legacy")
    first = workspace.migrate_to_current()
    first_history = workspace.verify_history()

    second = workspace.migrate_to_current()

    assert second == first
    assert workspace.verify_history() == first_history


def test_migration_rejects_a_stale_expected_head(tmp_path):
    workspace = _legacy_workspace(tmp_path / "legacy")
    stale_id = workspace.head().revision_id
    current = _commit_empty_legacy_stage(workspace, "parse")

    with pytest.raises(WorkspaceRevisionConflict) as error:
        workspace.migrate_to_current(expected_revision_id=stale_id)

    assert error.value.actual == current.revision_id
    assert workspace.head() == current


def test_history_rejects_a_fabricated_v2_to_v2_migration(tmp_path):
    workspace = Workspace.create(tmp_path / "workspace")
    parent = workspace.head()
    fabricated = _new_revision(
        schema_version=WORKSPACE_REVISION_SCHEMA_VERSION,
        parent_revision_id=parent.revision_id,
        committed_stage="migration",
        committed_at="2026-01-01T00:00:00+00:00",
        sources=parent.sources,
        artifacts=parent.artifacts,
        stages=parent.stages,
    )
    revision_dir = workspace.root / "revisions" / fabricated.revision_id
    revision_dir.mkdir()
    (revision_dir / "revision.json").write_bytes(lossless_json_bytes(fabricated))
    (workspace.root / "HEAD").write_text(
        fabricated.revision_id + "\n", encoding="ascii"
    )

    with pytest.raises(UnsupportedWorkspaceVersionError, match="migration contract"):
        Workspace.open(workspace.root)


def test_history_rejects_a_v1_to_v2_migration_that_alters_legacy_state(tmp_path):
    workspace = _legacy_workspace(tmp_path / "legacy")
    parent = workspace.head()
    altered_config = {"tampered": True}
    stages = dict(parent.stages)
    stages["clean"] = StageState(
        stage="clean",
        status="absent",
        input_artifact_ids=(),
        input_digest=canonical_digest(
            {"stage": "clean", "inputs": (), "status": "absent"}
        ),
        config=altered_config,
        config_digest=canonical_digest(altered_config),
        outputs={},
    )
    stages["construct"] = StageState.absent("construct")
    fabricated = _new_revision(
        schema_version=WORKSPACE_REVISION_SCHEMA_VERSION,
        parent_revision_id=parent.revision_id,
        committed_stage="migration",
        committed_at="2026-01-01T00:00:00+00:00",
        sources=parent.sources,
        artifacts=parent.artifacts,
        stages=stages,
    )
    revision_dir = workspace.root / "revisions" / fabricated.revision_id
    revision_dir.mkdir()
    (revision_dir / "revision.json").write_bytes(lossless_json_bytes(fabricated))
    (workspace.root / "HEAD").write_text(
        fabricated.revision_id + "\n", encoding="ascii"
    )

    with pytest.raises(UnsupportedWorkspaceVersionError, match="migration contract"):
        Workspace.open(workspace.root)


def test_history_rejects_a_v2_to_v1_downgrade(tmp_path):
    workspace = _workspace_with_chunks(tmp_path)
    parent = workspace.head()
    downgraded = _new_revision(
        schema_version=LEGACY_REVISION_SCHEMA_VERSION,
        parent_revision_id=parent.revision_id,
        committed_stage="format",
        committed_at="2026-01-01T00:00:00+00:00",
        sources=parent.sources,
        artifacts=parent.artifacts,
        stages={stage: parent.stages[stage] for stage in LEGACY_STAGES},
    )
    revision_dir = workspace.root / "revisions" / downgraded.revision_id
    revision_dir.mkdir()
    (revision_dir / "revision.json").write_bytes(lossless_json_bytes(downgraded))
    (workspace.root / "HEAD").write_text(
        downgraded.revision_id + "\n", encoding="ascii"
    )

    with pytest.raises(
        UnsupportedWorkspaceVersionError,
        match="schema changes require the v1-to-v2 migration contract",
    ):
        Workspace.open(workspace.root)


def test_migration_failure_before_head_keeps_legacy_head_visible(tmp_path):
    failure_injected = False

    def fail_before_head(point: str) -> None:
        nonlocal failure_injected
        if point == "before-head" and not failure_injected:
            failure_injected = True
            raise RuntimeError("injected before HEAD")

    workspace = _legacy_workspace(
        tmp_path / "legacy",
        failure_injector=fail_before_head,
    )
    before = workspace.head()

    with pytest.raises(RuntimeError, match="injected before HEAD"):
        workspace.migrate_to_current()

    assert workspace.head() == before

    history_ids = set(workspace.verify_history())
    revision_ids = {path.name for path in (workspace.root / "revisions").iterdir()}
    orphan_ids = revision_ids - history_ids
    assert len(orphan_ids) == 1
    assert not any((workspace.root / ".txn").iterdir())

    migrated = workspace.migrate_to_current()

    assert workspace.head() == migrated
    assert workspace.verify_history()[1] == before.revision_id
    assert orphan_ids.isdisjoint(workspace.verify_history())
    assert not any((workspace.root / ".txn").iterdir())


def test_upgrade_workspace_cli_migrates_verified_v1_head(tmp_path):
    root = tmp_path / "legacy"
    workspace = _legacy_workspace(root)
    before = workspace.head()

    result = CliRunner().invoke(app, ["upgrade-workspace", str(root)])

    assert result.exit_code == 0, result.output
    migrated = workspace.head()
    assert before.schema_version == LEGACY_REVISION_SCHEMA_VERSION
    assert migrated.schema_version == WORKSPACE_REVISION_SCHEMA_VERSION
    assert migrated.parent_revision_id == before.revision_id
    assert migrated.stages["construct"] == StageState.absent("construct")


def test_migration_reports_unconfirmed_post_commit_durability(tmp_path, monkeypatch):
    workspace = _legacy_workspace(tmp_path / "legacy")
    real_promote = workspace_module._promote_commit_pointer

    def promote_but_report_unconfirmed(path: Path, data: bytes) -> bool:
        assert real_promote(path, data)
        return False

    monkeypatch.setattr(
        workspace_module,
        "_promote_commit_pointer",
        promote_but_report_unconfirmed,
    )

    migrated = workspace.migrate_to_current()

    assert workspace.head() == migrated
    assert workspace.last_commit_durability_warning is not None
    assert "HEAD was committed" in workspace.last_commit_durability_warning


def test_construct_commit_binds_inputs_outputs_scope_and_lineage(tmp_path):
    workspace = _workspace_with_chunks(tmp_path)
    before = workspace.head()
    source_ids = tuple(sorted(before.sources))
    config, recipe_bytes, result_bytes = _construction_payloads(
        workspace,
        before,
        source_ids,
    )
    expected_inputs = tuple(
        sorted(
            artifact_id
            for stage in ("parse", "clean", "chunk")
            for artifact_id in before.stages[stage].outputs.values()
        )
    )

    with workspace.begin("construct") as transaction:
        outputs = _put_construct_outputs(
            transaction,
            config,
            source_ids=source_ids,
            recipe_bytes=recipe_bytes,
            result_bytes=result_bytes,
        )
        constructed = transaction.commit(outputs=outputs, config=config)

    state = constructed.stages["construct"]
    assert state.status == "complete"
    assert state.input_artifact_ids == expected_inputs
    assert set(state.outputs) == {"recipe", "result"}
    assert constructed.stages["format"] == before.stages["format"]
    for output_name, kind in {
        "recipe": "dataset-recipe",
        "result": "construction-result",
    }.items():
        artifact = constructed.artifacts[state.outputs[output_name]]
        assert artifact.kind == kind
        assert artifact.source_ids == source_ids
        assert artifact.producer_id == f"veriformis.construction.{output_name}"
        assert artifact.producer_version == "1"
        assert artifact.config_digest == state.config_digest


def test_construct_rejects_self_consistent_result_that_does_not_replay(tmp_path):
    workspace = _workspace_with_chunks(tmp_path)
    before = workspace.head()
    source_ids = tuple(sorted(before.sources))
    config, recipe_bytes, result_bytes = _construction_payloads(
        workspace,
        before,
        source_ids,
    )
    value = json.loads(result_bytes)
    value["input_digest"] = "0" * 64
    value["result_id"] = derive_id(
        "run",
        {key: item for key, item in value.items() if key != "result_id"},
    )
    forged_result = lossless_json_bytes(value)

    with pytest.raises(WorkspaceCorruptError, match="declared inputs"):
        with workspace.begin("construct") as transaction:
            outputs = _put_construct_outputs(
                transaction,
                config,
                source_ids=source_ids,
                recipe_bytes=recipe_bytes,
                result_bytes=forged_result,
            )
            transaction.commit(outputs=outputs, config=config)

    assert workspace.head() == before


def test_construct_rejects_noncanonical_recipe_artifact_bytes(tmp_path):
    workspace = _workspace_with_chunks(tmp_path)
    before = workspace.head()
    source_ids = tuple(sorted(before.sources))
    config, recipe_bytes, result_bytes = _construction_payloads(
        workspace,
        before,
        source_ids,
    )
    noncanonical_recipe = json.dumps(
        json.loads(recipe_bytes),
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")

    with pytest.raises(WorkspaceCorruptError, match="canonical JSON"):
        with workspace.begin("construct") as transaction:
            outputs = _put_construct_outputs(
                transaction,
                config,
                source_ids=source_ids,
                recipe_bytes=noncanonical_recipe,
                result_bytes=result_bytes,
            )
            transaction.commit(outputs=outputs, config=config)

    assert workspace.head() == before


@pytest.mark.parametrize(
    "mutate_config",
    [
        lambda config, source_id: {**config, "extra": True},
        lambda config, source_id: {**config, "schema_version": "wrong"},
        lambda config, source_id: {**config, "recipe_id": ""},
        lambda config, source_id: {**config, "selected_source_ids": []},
        lambda config, source_id: {
            **config,
            "selected_source_ids": [source_id, source_id],
        },
        lambda config, source_id: {
            **config,
            "selected_source_ids": [derive_id("src", {"unknown": True})],
        },
    ],
)
def test_construct_rejects_invalid_recipe_selection_config(
    tmp_path,
    mutate_config,
):
    workspace = _workspace_with_chunks(tmp_path)
    before = workspace.head()
    source_id = next(iter(before.sources))
    config = mutate_config(_construct_config([source_id]), source_id)

    with pytest.raises(WorkspaceCorruptError):
        with workspace.begin("construct") as transaction:
            outputs = _put_construct_outputs(
                transaction,
                config,
                source_ids=(source_id,),
            )
            transaction.commit(outputs=outputs, config=config)

    assert workspace.head() == before


@pytest.mark.parametrize(
    ("source_scope", "producer_prefix", "message"),
    [
        ((), "veriformis.construction", "incorrect source scope"),
        (("selected",), "wrong.producer", "artifact lineage"),
    ],
)
def test_construct_rejects_false_output_scope_or_lineage(
    tmp_path,
    source_scope,
    producer_prefix,
    message,
):
    workspace = _workspace_with_chunks(tmp_path)
    before = workspace.head()
    source_id = next(iter(before.sources))
    config = _construct_config([source_id])
    resolved_scope = (source_id,) if source_scope == ("selected",) else source_scope

    with pytest.raises(WorkspaceCorruptError, match=message):
        with workspace.begin("construct") as transaction:
            outputs = _put_construct_outputs(
                transaction,
                config,
                source_ids=resolved_scope,
                producer_prefix=producer_prefix,
            )
            transaction.commit(outputs=outputs, config=config)

    assert workspace.head() == before
