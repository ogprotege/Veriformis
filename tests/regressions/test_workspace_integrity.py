import fcntl
import hashlib
import json
from copy import deepcopy
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.contracts import (
    CONSTRUCTION_STAGE_SCHEMA_ID,
    CURATION_STAGE_SCHEMA_ID,
    FORMAT_STAGE_SCHEMA_ID,
    SEAL_STAGE_SCHEMA_ID,
    SPLIT_STAGE_SCHEMA_ID,
    VALIDATION_STAGE_SCHEMA_ID,
)
from veriformis.errors import (
    ArtifactDigestMismatchError,
    DuplicateIdentityError,
    MissingStageInputError,
    StaleStageError,
    UnsupportedWorkspaceVersionError,
    WorkspaceCorruptError,
    WorkspaceLockedError,
    WorkspaceRevisionConflict,
)
from veriformis.diagnostics import make_parse_report, parse_report_to_dict
from veriformis.identity import (
    canonical_digest,
    derive_id,
    derive_source_id,
    lossless_json_bytes,
)
from veriformis.ir import document_to_dict
from veriformis.parsers.text import parse_text
from veriformis.workspace import (
    STAGES,
    STAGE_DEPENDENCIES,
    SourceDescriptor,
    StageState,
    Workspace,
)


_V3_STAGE_OUTPUTS = {
    "parse": {"registry": "source-registry"},
    "clean": {"transforms": "transform-records"},
    "chunk": {"chunks": "chunks"},
    "construct": {
        "recipe": "dataset-recipe",
        "result": "construction-result",
    },
    "curate": {
        "plan": "finished-dataset-plan",
        "result": "curation-result",
    },
    "split": {"result": "split-result"},
    "format": {
        "row-set": "formatted-row-set",
        "train": "training-partition",
        "evaluation": "evaluation-partition",
        "provenance": "row-provenance",
    },
    "validate": {
        "snapshot": "dataset-snapshot",
        "report": "dataset-validation-report",
    },
    "seal": {
        "manifest": "finished-bundle-manifest",
        "attestation": "finished-bundle-attestation",
    },
}

_V3_FINISHED_STAGE_SCHEMAS = {
    "curate": CURATION_STAGE_SCHEMA_ID,
    "split": SPLIT_STAGE_SCHEMA_ID,
    "format": FORMAT_STAGE_SCHEMA_ID,
    "validate": VALIDATION_STAGE_SCHEMA_ID,
    "seal": SEAL_STAGE_SCHEMA_ID,
}


def _synthetic_commit(transaction, **kwargs):
    """Bypass domain replay only; retain revision, output, and lineage checks."""
    with patch.object(transaction, "_validate_stage_semantics", return_value=None):
        return transaction.commit(**kwargs)


def _finished_plan_id(workspace):
    revision = workspace.head(verify_objects=False)
    curate = revision.stages["curate"]
    if curate.status == "complete":
        return curate.config["plan_id"]
    construct = revision.stages["construct"]
    assert construct.status == "complete"
    return derive_id(
        "fdp",
        {
            "schema_version": "veriformis.synthetic-finished-plan/v1",
            "recipe_id": construct.config["recipe_id"],
        },
    )


def _default_stage_config(workspace, stage, text=None):
    if stage == "parse":
        return {"sources": []}
    if stage == "clean":
        return {
            "rules": ["lowercase"]
            if text is not None
            else ["page-numbers", "whitespace"],
            "custom": None,
            "max_remove_ppm": 300_000,
        }
    if stage == "chunk":
        return {"strategy": "paragraph", "size": 1000, "overlap": 100}
    if stage == "construct":
        selected_source_ids = tuple(
            sorted(workspace.head(verify_objects=False).sources)
        )
        assert selected_source_ids, "synthetic construct requires a captured source"
        recipe_id = derive_id(
            "rcp",
            {
                "schema_version": "veriformis.synthetic-recipe/v1",
                "selected_source_ids": selected_source_ids,
            },
        )
        return {
            "schema_version": CONSTRUCTION_STAGE_SCHEMA_ID,
            "recipe_id": recipe_id,
            "selected_source_ids": list(selected_source_ids),
        }
    if stage in _V3_FINISHED_STAGE_SCHEMAS:
        return {
            "schema_version": _V3_FINISHED_STAGE_SCHEMAS[stage],
            "plan_id": _finished_plan_id(workspace),
        }
    raise AssertionError(f"unsupported synthetic stage {stage}")


def _commit_stage(
    workspace,
    stage,
    text=None,
    *,
    config=None,
    status="complete",
    lineage_forgery=None,
):
    payload = (text or stage).encode()
    stage_config = (
        _default_stage_config(workspace, stage, text) if config is None else config
    )
    with workspace.begin(stage) as transaction:
        if stage == "parse" and text is not None:
            source, outputs = _put_parsed_source(
                transaction,
                "source.txt",
                payload,
            )
            transaction.set_sources((source,))
            outputs["registry"] = _put_registry(transaction, (source,))
            return _synthetic_commit(
                transaction,
                outputs=outputs,
                config={"sources": ["source.txt"]},
                status=status,
            )
        schemas = dict(_V3_STAGE_OUTPUTS[stage])
        all_source_ids = tuple(sorted(transaction.sources))
        if stage == "clean":
            for source_id in all_source_ids:
                schemas.update(
                    {
                        f"source/{source_id}/document": "cleaned-document-ir",
                        f"source/{source_id}/cleaning-plan": "cleaning-plan",
                        f"source/{source_id}/block-derivations": ("block-derivations"),
                    }
                )
        if stage == "construct":
            stage_source_ids = tuple(stage_config["selected_source_ids"])
        elif stage in {"curate", "split", "format", "validate", "seal"}:
            stage_source_ids = tuple(
                transaction.base.stages["construct"].config["selected_source_ids"]
            )
        else:
            stage_source_ids = all_source_ids
        if stage == "parse":
            producer_id, artifact_config = (
                "veriformis.parse-stage",
                {"source_count": len(all_source_ids)},
            )
        elif stage == "clean":
            producer_id, artifact_config = "veriformis.cleaning", stage_config
        elif stage == "chunk":
            producer_id, artifact_config = (
                f"veriformis.chunker.{stage_config['strategy']}",
                stage_config,
            )
        else:
            producer_id, artifact_config = None, stage_config
        outputs = {}
        for name, kind in schemas.items():
            expected_producer = (
                producer_id
                if producer_id is not None
                else {
                    "construct": f"veriformis.construction.{name}",
                    "curate": f"veriformis.curation.{name}",
                    "split": f"veriformis.splitting.{name}",
                    "format": f"veriformis.dataset-serializer.{name}",
                    "validate": f"veriformis.dataset-validation.{name}",
                    "seal": f"veriformis.bundle.{name}",
                }[stage]
            )
            output_producer = expected_producer
            output_version = "1"
            output_config = artifact_config
            if lineage_forgery is not None and name == lineage_forgery[0]:
                forgery = lineage_forgery[1]
                if forgery == "producer":
                    output_producer = "forged.producer"
                elif forgery == "version":
                    output_version = "999"
                elif forgery == "config":
                    output_config = {**artifact_config, "forged": True}
                else:  # pragma: no cover - test helper contract
                    raise AssertionError(f"unknown lineage forgery {forgery}")
            outputs[name] = transaction.put_artifact(
                (
                    b"[]"
                    if (stage, name)
                    in {
                        ("parse", "registry"),
                        ("clean", "transforms"),
                        ("chunk", "chunks"),
                        ("format", "provenance"),
                    }
                    else payload + name.encode()
                ),
                kind=kind,
                media_type="application/octet-stream",
                source_ids=(
                    (name.split("/")[1],)
                    if name.startswith("source/")
                    else stage_source_ids
                ),
                producer_id=output_producer,
                producer_version=output_version,
                config=output_config,
            )
        return _synthetic_commit(
            transaction,
            outputs=outputs,
            config=stage_config,
            status=status,
        )


def _complete_pipeline(workspace):
    for stage in STAGES:
        _commit_stage(
            workspace,
            stage,
            "captured source" if stage == "parse" else None,
        )


def _put_parsed_source(transaction, logical_path, raw, *, original_path=None):
    parsed = parse_text(
        original_path or logical_path,
        logical_path=logical_path,
        raw_bytes=raw,
    )
    source_id = parsed.source.id
    parser_config = {
        "parser": parsed.source.parser,
        "parser_version": parsed.source.parser_version,
        "canonical_stream_contract_version": (
            parsed.source.canonical_stream_contract_version
        ),
    }
    artifacts = {
        "raw": transaction.put_artifact(
            raw,
            kind="raw-source",
            media_type="application/octet-stream",
            source_ids=(source_id,),
            producer_id="veriformis.source-capture",
            producer_version="1",
            config={"logical_path": logical_path},
        ),
        "canonical": transaction.put_artifact(
            parsed.source.extracted_text,
            kind="canonical-source-text",
            media_type="text/plain",
            source_ids=(source_id,),
            producer_id="veriformis.parser.text",
            producer_version=parsed.source.parser_version,
            config=parser_config,
        ),
        "document": transaction.put_artifact(
            lossless_json_bytes(document_to_dict(parsed.document)),
            kind="document-ir",
            media_type="application/json",
            source_ids=(source_id,),
            producer_id="veriformis.parser.text",
            producer_version=parsed.source.parser_version,
            config=parser_config,
        ),
        "diagnostics": transaction.put_artifact(
            lossless_json_bytes(parse_report_to_dict(parsed.diagnostics)),
            kind="parse-report",
            media_type="application/json",
            source_ids=(source_id,),
            producer_id="veriformis.parser.text",
            producer_version=parsed.source.parser_version,
            config=parser_config,
        ),
    }
    source = SourceDescriptor.create(
        logical_path=logical_path,
        original_path=original_path,
        sha256=parsed.source.sha256,
        size=len(raw),
        parser_id=parsed.source.parser,
        parser_version=parsed.source.parser_version,
        raw_artifact_id=artifacts["raw"].id,
        extracted_artifact_id=artifacts["canonical"].id,
        document_artifact_id=artifacts["document"].id,
    )
    outputs = {
        f"source/{source_id}/{role}": artifact for role, artifact in artifacts.items()
    }
    return source, outputs


def _put_registry(transaction, sources, *, payload=None):
    if payload is None:
        payload = lossless_json_bytes(
            [
                source.model_dump(mode="json", exclude={"original_path"})
                for source in sorted(sources, key=lambda item: item.id)
            ]
        )
    return transaction.put_artifact(
        payload,
        kind="source-registry",
        media_type="application/json",
        source_ids=tuple(source.id for source in sources),
        producer_id="veriformis.parse-stage",
        producer_version="1",
        config={"source_count": len(sources)},
    )


def _commit_captured_source(workspace, *, original_path="/tmp/source.txt"):
    raw = b"raw source bytes"
    with workspace.begin("parse") as transaction:
        source, outputs = _put_parsed_source(
            transaction,
            "source.txt",
            raw,
            original_path=original_path,
        )
        transaction.set_sources((source,))
        outputs["registry"] = _put_registry(transaction, (source,))
        revision = transaction.commit(
            outputs=outputs,
            config={"sources": ["source.txt"]},
        )
    return revision, source


def _install_rehashed_manifest(workspace, revision, mutate):
    """Install a tampered manifest whose state and revision hashes still agree."""
    path = workspace.root / "revisions" / revision.revision_id / "revision.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    mutate(manifest)

    semantic_sources = {
        source_id: {
            key: value for key, value in source.items() if key != "original_path"
        }
        for source_id, source in sorted(manifest["sources"].items())
    }
    semantic_stages = {
        stage: {
            key: value for key, value in state.items() if key != "prior_revision_id"
        }
        for stage, state in sorted(manifest["stages"].items())
    }
    manifest["state_digest"] = canonical_digest(
        {
            "schema_version": manifest["schema_version"],
            "sources": semantic_sources,
            "artifacts": manifest["artifacts"],
            "stages": semantic_stages,
        }
    )
    revision_payload = {
        key: manifest[key]
        for key in (
            "schema_version",
            "state_digest",
            "parent_revision_id",
            "committed_stage",
            "committed_at",
            "sources",
            "artifacts",
            "stages",
        )
    }
    manifest["revision_id"] = derive_id("rev", revision_payload)
    tampered_path = (
        workspace.root / "revisions" / manifest["revision_id"] / "revision.json"
    )
    tampered_path.parent.mkdir()
    tampered_path.write_bytes(lossless_json_bytes(manifest))
    (workspace.root / "HEAD").write_text(
        manifest["revision_id"] + "\n", encoding="ascii"
    )
    return manifest


def test_initial_empty_revision_is_deterministic(tmp_path):
    first = Workspace.create(tmp_path / "first").head()
    second = Workspace.create(tmp_path / "second").head()

    assert first.revision_id == second.revision_id
    assert first.state_digest == second.state_digest
    assert tuple(sorted(first.stages)) == tuple(sorted(STAGES))
    assert all(state.status == "absent" for state in first.stages.values())


def test_stage_state_requires_exact_invalidation_and_input_binding():
    absent = StageState.absent("clean")
    stray = absent.model_dump(mode="python")
    stray["invalidated_by"] = "parse"
    stray["prior_revision_id"] = derive_id("rev", {"test": "prior"})
    with pytest.raises(WorkspaceCorruptError, match="carries invalidation"):
        StageState.model_validate(stray)

    stale = absent.as_stale(
        invalidated_by="parse",
        prior_revision_id=derive_id("rev", {"test": "stale"}),
    ).model_dump(mode="python")
    stale["prior_revision_id"] = None
    with pytest.raises(WorkspaceCorruptError, match="lacks invalidation"):
        StageState.model_validate(stale)

    altered = absent.model_dump(mode="python")
    altered["input_digest"] = "0" * 64
    with pytest.raises(WorkspaceCorruptError, match="input digest"):
        StageState.model_validate(altered)


def test_rehashed_manifest_rejects_upstream_invalidation_by_downstream_stage(
    tmp_path,
):
    workspace = Workspace.create(tmp_path / "ws")
    _complete_pipeline(workspace)
    revision = _commit_stage(workspace, "clean", "changed")

    def reverse_dependency_direction(manifest):
        state = manifest["stages"]["chunk"]
        state["invalidated_by"] = "format"
        state["input_digest"] = canonical_digest(
            {
                "stage": "chunk",
                "status": "stale",
                "invalidated_by": "format",
            }
        )

    _install_rehashed_manifest(workspace, revision, reverse_dependency_direction)

    with pytest.raises(WorkspaceCorruptError, match="not downstream"):
        workspace.head(verify_objects=False)


@pytest.mark.parametrize("lineage_field", ("invalidated_by", "prior_revision_id"))
def test_rehashed_manifest_rejects_stale_descendant_with_wrong_commit_lineage(
    tmp_path, lineage_field
):
    workspace = Workspace.create(tmp_path / "ws")
    _complete_pipeline(workspace)
    revision = _commit_stage(workspace, "clean", "changed")

    def forge_lineage(manifest):
        state = manifest["stages"]["chunk"]
        if lineage_field == "invalidated_by":
            state["invalidated_by"] = "parse"
            state["input_digest"] = canonical_digest(
                {
                    "stage": "chunk",
                    "status": "stale",
                    "invalidated_by": "parse",
                }
            )
        else:
            grandparent = workspace.get_revision(
                manifest["parent_revision_id"], verify_objects=False
            ).parent_revision_id
            assert grandparent is not None
            state["prior_revision_id"] = grandparent

    _install_rehashed_manifest(workspace, revision, forge_lineage)

    with pytest.raises(WorkspaceCorruptError, match="commit lineage"):
        workspace.head(verify_objects=False)


def test_rehashed_migration_manifest_is_rejected_without_a_contract(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    _complete_pipeline(workspace)
    revision = _commit_stage(workspace, "clean", "changed")

    def mark_as_migration(manifest):
        manifest["committed_stage"] = "migration"

    _install_rehashed_manifest(workspace, revision, mark_as_migration)

    with pytest.raises(
        UnsupportedWorkspaceVersionError,
        match="supported workspace migration",
    ):
        workspace.head(verify_objects=False)


def test_rehashed_manifest_rejects_non_active_committed_stage(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    _complete_pipeline(workspace)
    revision = _commit_stage(workspace, "clean", "changed")

    def claim_stale_stage_was_committed(manifest):
        manifest["committed_stage"] = "chunk"

    _install_rehashed_manifest(workspace, revision, claim_stale_stage_was_committed)

    with pytest.raises(WorkspaceCorruptError, match="invalid status stale"):
        workspace.head(verify_objects=False)


def test_rehashed_manifest_rejects_stale_state_outside_commit_descendants(
    tmp_path,
):
    workspace = Workspace.create(tmp_path / "ws")
    _complete_pipeline(workspace)
    revision = _commit_stage(workspace, "format", "changed")

    def forge_unrelated_stale_state(manifest):
        manifest["stages"]["clean"] = (
            StageState.absent("clean")
            .as_stale(
                invalidated_by="parse",
                prior_revision_id=manifest["parent_revision_id"],
            )
            .model_dump(mode="json")
        )

    _install_rehashed_manifest(workspace, revision, forge_unrelated_stale_state)

    with pytest.raises(WorkspaceCorruptError, match="format commit lineage"):
        workspace.head(verify_objects=False)


def test_rehashed_manifest_rejects_active_descendant_of_absent_stage(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    _complete_pipeline(workspace)
    revision = workspace.head(verify_objects=False)

    def erase_completed_dependency(manifest):
        manifest["stages"]["clean"] = StageState.absent("clean").model_dump(mode="json")

    _install_rehashed_manifest(workspace, revision, erase_completed_dependency)

    with pytest.raises(WorkspaceCorruptError, match="requires complete dependency"):
        workspace.head(verify_objects=False)


def test_rehashed_manifest_rejects_nonempty_init_revision(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    revision = _commit_stage(workspace, "parse")

    def claim_revision_is_initial(manifest):
        manifest["committed_stage"] = "init"
        manifest["parent_revision_id"] = None

    _install_rehashed_manifest(workspace, revision, claim_revision_is_initial)

    with pytest.raises(WorkspaceCorruptError, match="empty root"):
        workspace.head(verify_objects=False)


def test_historical_stale_revision_remains_valid_after_descendant_rerun(
    tmp_path,
):
    workspace = Workspace.create(tmp_path / "ws")
    _complete_pipeline(workspace)
    cleaned = _commit_stage(workspace, "clean", "changed")
    chunked = _commit_stage(workspace, "chunk", "new chunks")

    historical = workspace.get_revision(cleaned.revision_id, verify_objects=False)

    assert historical.stages["chunk"].invalidated_by == "clean"
    assert historical.stages["chunk"].prior_revision_id == cleaned.parent_revision_id
    for stage in ("construct", "curate", "split", "format", "validate", "seal"):
        assert chunked.stages[stage].invalidated_by == "chunk"
        assert chunked.stages[stage].prior_revision_id == cleaned.revision_id


def test_commit_is_immutable_and_content_addressed(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    before = workspace.head()
    after = _commit_stage(workspace, "parse", "source bytes")

    assert after.parent_revision_id == before.revision_id
    assert workspace.head().revision_id == after.revision_id
    assert workspace.get_revision(before.revision_id) == before
    source = next(iter(after.sources.values()))
    assert source.raw_artifact_id is not None
    artifact_id = source.raw_artifact_id
    artifact = after.artifacts[artifact_id]
    object_path = (
        workspace.root / "objects" / "sha256" / artifact.sha256[:2] / artifact.sha256
    )
    assert object_path.read_bytes() == b"source bytes"


def test_multi_source_parse_report_mismatch_rolls_back_atomically(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    before, _ = _commit_captured_source(workspace)

    with pytest.raises(WorkspaceCorruptError, match="parse report does not match"):
        with workspace.begin("parse") as transaction:
            first, first_outputs = _put_parsed_source(
                transaction, "first.txt", b"first"
            )
            second, second_outputs = _put_parsed_source(
                transaction, "second.txt", b"second"
            )
            wrong_report = transaction.put_artifact(
                lossless_json_bytes(
                    parse_report_to_dict(
                        make_parse_report(
                            source_id=first.id,
                            parser_name="text",
                            parser_version=first.parser_version,
                        )
                    )
                ),
                kind="parse-report",
                media_type="application/json",
                source_ids=(second.id,),
                producer_id="veriformis.parser.text",
                producer_version=second.parser_version,
                config={
                    "parser": "text",
                    "parser_version": second.parser_version,
                    "canonical_stream_contract_version": 1,
                },
            )
            outputs = {**first_outputs, **second_outputs}
            outputs[f"source/{second.id}/diagnostics"] = wrong_report
            outputs["registry"] = _put_registry(transaction, (first, second))
            transaction.set_sources((first, second))
            transaction.commit(
                outputs=outputs,
                config={
                    "sources": [
                        source.logical_path
                        for source in sorted((first, second), key=lambda item: item.id)
                    ]
                },
            )

    assert workspace.head().revision_id == before.revision_id


def test_parse_commit_rejects_canonical_substitute_disconnected_from_raw(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    before = workspace.head()
    with workspace.begin("parse") as transaction:
        source, outputs = _put_parsed_source(
            transaction,
            "source.txt",
            b"RAW SECRET ORIGINAL",
        )
        forged = parse_text(
            "source.txt",
            logical_path="source.txt",
            raw_bytes=b"FORGED SUBSTITUTE",
        )
        forged_document = deepcopy(forged.document)
        forged_document.source_id = source.id
        parser_config = {
            "parser": source.parser_id,
            "parser_version": source.parser_version,
            "canonical_stream_contract_version": (
                source.canonical_stream_contract_version
            ),
        }
        canonical = transaction.put_artifact(
            forged.source.extracted_text,
            kind="canonical-source-text",
            media_type="text/plain",
            source_ids=(source.id,),
            producer_id="veriformis.parser.text",
            producer_version=source.parser_version,
            config=parser_config,
        )
        document = transaction.put_artifact(
            lossless_json_bytes(document_to_dict(forged_document)),
            kind="document-ir",
            media_type="application/json",
            source_ids=(source.id,),
            producer_id="veriformis.parser.text",
            producer_version=source.parser_version,
            config=parser_config,
        )
        report = transaction.put_artifact(
            lossless_json_bytes(
                parse_report_to_dict(
                    make_parse_report(
                        source_id=source.id,
                        parser_name=source.parser_id,
                        parser_version=source.parser_version,
                    )
                )
            ),
            kind="parse-report",
            media_type="application/json",
            source_ids=(source.id,),
            producer_id="veriformis.parser.text",
            producer_version=source.parser_version,
            config=parser_config,
        )
        substituted = SourceDescriptor.create(
            logical_path=source.logical_path,
            sha256=source.sha256,
            size=source.size,
            parser_id=source.parser_id,
            parser_version=source.parser_version,
            raw_artifact_id=source.raw_artifact_id,
            extracted_artifact_id=canonical.id,
            document_artifact_id=document.id,
        )
        transaction.set_sources((substituted,))
        outputs[f"source/{source.id}/canonical"] = canonical
        outputs[f"source/{source.id}/document"] = document
        outputs[f"source/{source.id}/diagnostics"] = report
        outputs["registry"] = _put_registry(transaction, (substituted,))

        with pytest.raises(WorkspaceCorruptError, match="raw parser result"):
            transaction.commit(
                outputs=outputs,
                config={"sources": [source.logical_path]},
            )

    assert workspace.head_id == before.revision_id


@pytest.mark.parametrize(
    "failure_point",
    (
        "before-objects",
        "after-objects",
        "before-revision",
        "after-revision",
        "before-head",
    ),
)
def test_interrupted_stage_commit_leaves_previous_revision_current(
    tmp_path, failure_point
):
    def fail(point):
        if point == failure_point:
            raise RuntimeError("injected commit failure")

    workspace = Workspace.create(tmp_path / "ws", failure_injector=fail)
    before = workspace.head()

    with pytest.raises(RuntimeError, match="injected"):
        _commit_stage(workspace, "parse", "new source")

    assert workspace.head().revision_id == before.revision_id
    assert list((workspace.root / ".txn").iterdir()) == []


def test_post_promotion_directory_sync_error_returns_committed_outcome(
    tmp_path, monkeypatch
):
    workspace = Workspace.create(tmp_path / "ws")
    from veriformis import workspace as workspace_module

    real_fsync_dir = workspace_module._fsync_dir

    def fail_only_after_head_replace(path):
        if path == workspace.root:
            raise OSError("injected root directory fsync failure")
        return real_fsync_dir(path)

    monkeypatch.setattr(workspace_module, "_fsync_dir", fail_only_after_head_replace)

    committed = _commit_stage(workspace, "parse", "committed source")

    assert workspace.head().revision_id == committed.revision_id
    assert workspace.last_commit_durability_warning is not None
    assert "crash durability" in workspace.last_commit_durability_warning


def test_only_validation_can_persist_a_failed_result(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    before = workspace.head()

    with pytest.raises(WorkspaceCorruptError, match="only validation may persist"):
        _commit_stage(workspace, "parse", status="failed")
    assert workspace.head().revision_id == before.revision_id

    for stage in STAGES[: STAGES.index("validate")]:
        _commit_stage(
            workspace,
            stage,
            "captured source" if stage == "parse" else None,
        )
    failed = _commit_stage(workspace, "validate", status="failed")

    assert failed.stages["validate"].status == "failed"
    assert workspace.head().revision_id == failed.revision_id


def test_expected_revision_conflict_is_typed(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    first = workspace.begin("parse")
    second = workspace.begin("parse")
    first_artifact = first.put_artifact(
        b"[]",
        kind="source-registry",
        media_type="text/plain",
        producer_id="veriformis.parse-stage",
        producer_version="1",
        config={"source_count": 0},
    )
    second_artifact = second.put_artifact(
        b"[]",
        kind="source-registry",
        media_type="text/plain",
        producer_id="veriformis.parse-stage",
        producer_version="1",
        config={"source_count": 0},
    )
    committed = first.commit(
        outputs={"registry": first_artifact},
        config={"sources": []},
    )

    with pytest.raises(WorkspaceRevisionConflict) as caught:
        second.commit(
            outputs={"registry": second_artifact},
            config={"sources": []},
        )

    assert caught.value.expected != caught.value.actual
    assert caught.value.actual == committed.revision_id


def test_upstream_commit_invalidates_all_dependent_stage_records(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    _complete_pipeline(workspace)

    revised = _commit_stage(
        workspace,
        "clean",
        "changed clean output",
        config={
            "rules": ["lowercase"],
            "custom": None,
            "max_remove_ppm": 300_000,
        },
    )

    assert revised.stages["parse"].status == "complete"
    assert revised.stages["clean"].status == "complete"
    for stage in (
        "chunk",
        "construct",
        "curate",
        "split",
        "format",
        "validate",
        "seal",
    ):
        assert revised.stages[stage].status == "stale"
        assert revised.stages[stage].outputs == {}
        assert revised.stages[stage].invalidated_by == "clean"
    with pytest.raises(StaleStageError):
        workspace.begin("format")


def test_parse_change_invalidates_every_later_stage(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    _complete_pipeline(workspace)

    revised = _commit_stage(workspace, "parse", "changed raw source")

    assert revised.stages["parse"].status == "complete"
    assert all(
        revised.stages[stage].status == "stale"
        for stage in (
            "clean",
            "chunk",
            "construct",
            "curate",
            "split",
            "format",
            "validate",
            "seal",
        )
    )


def test_exact_stage_noop_keeps_head_revision(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    first = _commit_stage(workspace, "parse", "same")
    second = _commit_stage(workspace, "parse", "same")

    assert second.revision_id == first.revision_id
    assert workspace.head_id == first.revision_id


def test_workspace_lock_timeout_is_typed(tmp_path):
    workspace = Workspace.create(tmp_path / "ws", lock_timeout=0.02)
    transaction = workspace.begin("parse")
    artifact = transaction.put_artifact(
        b"source",
        kind="source-registry",
        media_type="text/plain",
        producer_id="parser",
        producer_version="1",
    )

    with (workspace.root / "LOCK").open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(WorkspaceLockedError):
            transaction.commit(
                outputs={"registry": artifact},
                config={"sources": []},
            )
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def test_object_tampering_fails_closed(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    revision = _commit_stage(workspace, "parse", "untampered")
    artifact = revision.artifacts[revision.stages["parse"].outputs["registry"]]
    path = workspace.root / "objects" / "sha256" / artifact.sha256[:2] / artifact.sha256
    path.chmod(0o644)
    path.write_bytes(b"tampered")

    with pytest.raises(ArtifactDigestMismatchError):
        Workspace.open(workspace.root)


def test_new_object_prefix_is_durable_in_its_parent_directory(
    tmp_path,
    monkeypatch,
):
    workspace = Workspace.create(tmp_path / "ws")
    from veriformis import workspace as workspace_module

    real_fsync_dir = workspace_module._fsync_dir
    synced: list = []

    def record(path):
        synced.append(path)
        real_fsync_dir(path)

    monkeypatch.setattr(workspace_module, "_fsync_dir", record)
    _commit_stage(workspace, "parse", "captured source")

    assert workspace.root / "objects" / "sha256" in synced


def test_workspace_open_rejects_a_missing_parent_revision(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    revision = _commit_stage(workspace, "parse")
    assert revision.parent_revision_id is not None
    parent_manifest = (
        workspace.root / "revisions" / revision.parent_revision_id / "revision.json"
    )
    parent_manifest.unlink()

    with pytest.raises(WorkspaceCorruptError, match="invalid workspace revision"):
        Workspace.open(workspace.root)


def test_workspace_open_rejects_non_parse_capture_fact_rewrite(tmp_path):
    source_path = tmp_path / "source.txt"
    source_path.write_text("Alpha   beta", encoding="utf-8")
    workspace_path = tmp_path / "ws"
    runner = CliRunner()
    for command in (
        [
            "parse",
            str(source_path),
            "-o",
            str(workspace_path),
            "--source-root",
            str(tmp_path),
        ],
        ["clean", str(workspace_path)],
    ):
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.output
    workspace = Workspace.open(workspace_path)
    revision = workspace.head()

    def mutate(manifest):
        source = next(iter(manifest["sources"].values()))
        source["original_path"] = "/forged/capture/path.txt"

    _install_rehashed_manifest(workspace, revision, mutate)

    with pytest.raises(WorkspaceCorruptError, match="capture facts"):
        Workspace.open(workspace.root)


def test_workspace_open_rejects_a_valid_upstream_stage_splice(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    _commit_stage(workspace, "parse")
    first_clean = _commit_stage(workspace, "clean")
    second_clean = _commit_stage(workspace, "clean", "changed")
    chunked = _commit_stage(workspace, "chunk")
    assert first_clean.revision_id != second_clean.revision_id
    old_state = first_clean.stages["clean"]
    old_artifact_id = old_state.outputs["transforms"]
    old_artifact = first_clean.artifacts[old_artifact_id]

    def mutate(manifest):
        current_artifact_id = manifest["stages"]["clean"]["outputs"]["transforms"]
        manifest["stages"]["clean"] = old_state.model_dump(mode="json")
        chunk_state = manifest["stages"]["chunk"]
        chunk_state["input_artifact_ids"] = [old_artifact_id]
        chunk_state["input_digest"] = canonical_digest(
            {
                "stage": "chunk",
                "inputs": [old_artifact_id],
                "config_digest": chunk_state["config_digest"],
            }
        )
        manifest["artifacts"].pop(current_artifact_id)
        manifest["artifacts"][old_artifact_id] = old_artifact.model_dump(mode="json")

    _install_rehashed_manifest(workspace, chunked, mutate)

    with pytest.raises(
        WorkspaceCorruptError,
        match="rewrites unaffected stage clean",
    ):
        Workspace.open(workspace.root)


def test_duplicate_json_identity_is_rejected_on_revision_load(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    revision = workspace.head()
    path = workspace.root / "revisions" / revision.revision_id / "revision.json"
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace('"sources":{}', '"sources":{},"sources":{}', 1), encoding="utf-8"
    )

    with pytest.raises(DuplicateIdentityError):
        workspace.head()


def test_same_stem_sources_have_distinct_artifact_paths(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    raw = b"identical bytes"

    with workspace.begin("parse") as transaction:
        parsed = [
            _put_parsed_source(
                transaction,
                logical_path,
                raw,
                original_path=f"/tmp/{logical_path}",
            )
            for logical_path in ("alpha/notes.txt", "beta/notes.txt")
        ]
        sources = [source for source, _ in parsed]
        outputs = {
            name: artifact
            for _, source_outputs in parsed
            for name, artifact in source_outputs.items()
        }
        outputs["registry"] = _put_registry(transaction, sources)
        transaction.set_sources(reversed(sources))
        revision = transaction.commit(
            outputs=outputs,
            config={
                "sources": [
                    source.logical_path
                    for source in sorted(sources, key=lambda item: item.id)
                ]
            },
        )

    assert len(revision.sources) == 2
    assert len({source.sha256 for source in revision.sources.values()}) == 1
    assert len({source.id for source in revision.sources.values()}) == 2
    raw_artifact_ids = {source.raw_artifact_id for source in revision.sources.values()}
    assert len(raw_artifact_ids) == 2


def test_source_order_does_not_change_semantic_state(tmp_path):
    raw = b"same bytes"

    def compile_sources(path, logical_paths):
        workspace = Workspace.create(path)
        with workspace.begin("parse") as transaction:
            parsed = [
                _put_parsed_source(
                    transaction,
                    logical_path,
                    raw,
                )
                for logical_path in logical_paths
            ]
            sources = [source for source, _ in parsed]
            outputs = {
                name: artifact
                for _, source_outputs in parsed
                for name, artifact in source_outputs.items()
            }
            outputs["registry"] = _put_registry(transaction, sources)
            transaction.set_sources(sources)
            return transaction.commit(
                outputs=outputs,
                config={
                    "sources": [
                        source.logical_path
                        for source in sorted(sources, key=lambda item: item.id)
                    ]
                },
            )

    first = compile_sources(tmp_path / "first", ["a/notes.txt", "b/notes.txt"])
    second = compile_sources(tmp_path / "second", ["b/notes.txt", "a/notes.txt"])

    assert first.state_digest == second.state_digest
    assert set(first.artifacts) == set(second.artifacts)


@pytest.mark.parametrize(
    ("link_field", "artifact_kind", "has_source_scope", "artifact_bytes"),
    (
        ("raw_artifact_id", "document-ir", True, b"raw source bytes"),
        ("raw_artifact_id", "raw-source", False, b"raw source bytes"),
        ("raw_artifact_id", "raw-source", True, b"different raw bytes"),
        ("extracted_artifact_id", "document-ir", True, b"canonical"),
        ("extracted_artifact_id", "canonical-source-text", False, b"canonical"),
        ("document_artifact_id", "canonical-source-text", True, b"{}"),
        ("document_artifact_id", "document-ir", False, b"{}"),
    ),
)
def test_source_artifact_links_are_semantically_bound(
    tmp_path,
    link_field,
    artifact_kind,
    has_source_scope,
    artifact_bytes,
):
    workspace = Workspace.create(tmp_path / "ws")
    raw = b"raw source bytes"
    raw_sha = hashlib.sha256(raw).hexdigest()
    source_id = derive_source_id("source.txt", raw_sha)
    with workspace.begin("parse") as transaction:
        source, outputs = _put_parsed_source(transaction, "source.txt", raw)
        artifact = transaction.put_artifact(
            artifact_bytes,
            kind=artifact_kind,
            media_type="application/octet-stream",
            source_ids=(source_id,) if has_source_scope else (),
            producer_id="adversarial-test",
            producer_version="1",
        )
        source = source.model_copy(update={link_field: artifact.id})
        role = {
            "raw_artifact_id": "raw",
            "extracted_artifact_id": "canonical",
            "document_artifact_id": "document",
        }[link_field]
        outputs[f"source/{source_id}/{role}"] = artifact
        outputs["registry"] = _put_registry(transaction, (source,))
        transaction.set_sources((source,))
        with pytest.raises(WorkspaceCorruptError):
            transaction.commit(
                outputs=outputs,
                config={"sources": [source.logical_path]},
            )


@pytest.mark.parametrize(
    ("producer_id", "producer_version", "parser_config"),
    (
        (
            "untrusted.parser.text",
            "1",
            {
                "parser": "text",
                "parser_version": "1",
                "canonical_stream_contract_version": 1,
            },
        ),
        (
            "veriformis.parser.text",
            "2",
            {
                "parser": "text",
                "parser_version": "1",
                "canonical_stream_contract_version": 1,
            },
        ),
        (
            "veriformis.parser.text",
            "1",
            {
                "parser": "text",
                "parser_version": "2",
                "canonical_stream_contract_version": 1,
            },
        ),
    ),
)
def test_canonical_artifact_is_bound_to_parser_identity(
    tmp_path,
    producer_id,
    producer_version,
    parser_config,
):
    workspace = Workspace.create(tmp_path / "ws")
    raw = b"raw source bytes"
    raw_sha = hashlib.sha256(raw).hexdigest()
    source_id = derive_source_id("source.txt", raw_sha)
    with workspace.begin("parse") as transaction:
        source, outputs = _put_parsed_source(transaction, "source.txt", raw)
        artifact = transaction.put_artifact(
            b"canonical",
            kind="canonical-source-text",
            media_type="text/plain",
            source_ids=(source_id,),
            producer_id=producer_id,
            producer_version=producer_version,
            config=parser_config,
        )
        source = source.model_copy(update={"extracted_artifact_id": artifact.id})
        outputs[f"source/{source_id}/canonical"] = artifact
        outputs["registry"] = _put_registry(transaction, (source,))
        transaction.set_sources((source,))

        with pytest.raises(WorkspaceCorruptError, match="parser identity"):
            transaction.commit(
                outputs=outputs,
                config={"sources": [source.logical_path]},
            )


def test_unsupported_canonical_stream_contract_fails_closed():
    raw_sha = hashlib.sha256(b"raw source bytes").hexdigest()

    with pytest.raises(UnsupportedWorkspaceVersionError, match="is not supported"):
        SourceDescriptor.create(
            logical_path="source.txt",
            sha256=raw_sha,
            size=16,
            parser_id="text",
            parser_version="1",
            canonical_stream_contract_version=2,
        )


def test_known_stage_output_name_enforces_artifact_schema(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    with workspace.begin("parse") as transaction:
        artifact = transaction.put_artifact(
            b"[]",
            kind="wrong-kind",
            media_type="application/json",
            producer_id="adversarial-test",
            producer_version="1",
        )
        with pytest.raises(WorkspaceCorruptError, match="expected 'source-registry'"):
            transaction.commit(
                outputs={"registry": artifact},
                config={"sources": []},
            )


def test_parse_stage_config_must_match_its_exact_source_inventory(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    with workspace.begin("parse") as transaction:
        registry = _put_registry(transaction, ())

        with pytest.raises(WorkspaceCorruptError, match="parse stage config"):
            transaction.commit(
                outputs={"registry": registry},
                config={"forged": True},
            )


def test_stage_inputs_reject_an_output_self_cycle(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    with workspace.begin("parse") as transaction:
        registry = _put_registry(transaction, ())

        with pytest.raises(MissingStageInputError, match="undeclared artifacts"):
            transaction.commit(
                outputs={"registry": registry},
                input_artifact_ids=(registry.id,),
                config={"sources": []},
            )


def test_stage_inputs_reject_an_unrelated_registered_artifact(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    with workspace.begin("parse") as transaction:
        registry = _put_registry(transaction, ())
        unrelated = transaction.put_artifact(
            b"unrelated",
            kind="test-only",
            media_type="application/octet-stream",
            producer_id="test",
            producer_version="1",
        )

        with pytest.raises(MissingStageInputError, match="undeclared artifacts"):
            transaction.commit(
                outputs={"registry": registry},
                input_artifact_ids=(unrelated.id,),
                config={"sources": []},
            )


def test_rehashed_manifest_rejects_an_output_input_cycle(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    revision = _commit_stage(workspace, "parse")

    def mutate(manifest):
        state = manifest["stages"]["parse"]
        registry_id = state["outputs"]["registry"]
        state["input_artifact_ids"] = [registry_id]
        state["input_digest"] = canonical_digest(
            {
                "stage": "parse",
                "inputs": [registry_id],
                "config_digest": state["config_digest"],
            }
        )

    _install_rehashed_manifest(workspace, revision, mutate)

    with pytest.raises(WorkspaceCorruptError, match="input lineage"):
        workspace.head(verify_objects=False)


def test_workspace_open_rejects_a_fabricated_noop_child(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    revision = _commit_stage(workspace, "parse")

    def mutate(manifest):
        manifest["parent_revision_id"] = revision.revision_id
        manifest["committed_at"] = "2099-01-01T00:00:00+00:00"

    _install_rehashed_manifest(workspace, revision, mutate)

    with pytest.raises(WorkspaceCorruptError, match="no-op child"):
        Workspace.open(workspace.root)


@pytest.mark.parametrize(
    (
        "stage",
        "dependencies",
        "output_name",
        "artifact_kind",
        "producer_id",
    ),
    (
        (
            "parse",
            (),
            "registry",
            "source-registry",
            "veriformis.parse-stage",
        ),
        (
            "clean",
            ("parse",),
            "transforms",
            "transform-records",
            "veriformis.cleaning",
        ),
        (
            "chunk",
            ("clean",),
            "chunks",
            "chunks",
            "veriformis.chunker.paragraph",
        ),
        (
            "construct",
            ("parse", "clean", "chunk"),
            "recipe",
            "dataset-recipe",
            "veriformis.construction.recipe",
        ),
        (
            "curate",
            ("construct",),
            "plan",
            "finished-dataset-plan",
            "veriformis.curation.plan",
        ),
        (
            "split",
            ("construct", "curate"),
            "result",
            "split-result",
            "veriformis.splitting.result",
        ),
        (
            "format",
            ("construct", "curate", "split"),
            "row-set",
            "formatted-row-set",
            "veriformis.dataset-serializer.row-set",
        ),
        (
            "validate",
            ("parse", "clean", "chunk", "construct", "curate", "split", "format"),
            "snapshot",
            "dataset-snapshot",
            "veriformis.dataset-validation.snapshot",
        ),
        (
            "seal",
            (
                "parse",
                "clean",
                "chunk",
                "construct",
                "curate",
                "split",
                "format",
                "validate",
            ),
            "manifest",
            "finished-bundle-manifest",
            "veriformis.bundle.manifest",
        ),
    ),
)
@pytest.mark.parametrize("forgery", ("producer", "version", "config"))
def test_stage_output_lineage_rejects_self_consistent_forgery(
    tmp_path,
    stage,
    dependencies,
    output_name,
    artifact_kind,
    producer_id,
    forgery,
):
    workspace = Workspace.create(tmp_path / "ws")
    assert STAGE_DEPENDENCIES[stage] == dependencies
    assert _V3_STAGE_OUTPUTS[stage][output_name] == artifact_kind
    expected_producer = {
        "parse": "veriformis.parse-stage",
        "clean": "veriformis.cleaning",
        "chunk": "veriformis.chunker.paragraph",
        "construct": f"veriformis.construction.{output_name}",
        "curate": f"veriformis.curation.{output_name}",
        "split": f"veriformis.splitting.{output_name}",
        "format": f"veriformis.dataset-serializer.{output_name}",
        "validate": f"veriformis.dataset-validation.{output_name}",
        "seal": f"veriformis.bundle.{output_name}",
    }[stage]
    assert producer_id == expected_producer
    for dependency in STAGES[: STAGES.index(stage)]:
        _commit_stage(
            workspace,
            dependency,
            "captured source" if dependency == "parse" else None,
        )
    with pytest.raises(WorkspaceCorruptError, match="artifact lineage"):
        _commit_stage(
            workspace,
            stage,
            lineage_forgery=(output_name, forgery),
        )


@pytest.mark.parametrize("stage", STAGES)
def test_complete_stage_cannot_bypass_its_required_output_schema(tmp_path, stage):
    workspace = Workspace.create(tmp_path / "ws")
    for dependency in STAGES[: STAGES.index(stage)]:
        _commit_stage(
            workspace,
            dependency,
            "captured source" if dependency == "parse" else None,
        )

    with workspace.begin(stage) as transaction:
        with pytest.raises(WorkspaceCorruptError, match="output schema mismatch"):
            _synthetic_commit(
                transaction,
                outputs={},
                config=_default_stage_config(workspace, stage),
            )


def test_complete_stage_rejects_outputs_outside_its_schema(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    with workspace.begin("parse") as transaction:
        registry = _put_registry(transaction, ())
        extra = transaction.put_artifact(
            b"extra",
            kind="extra-output",
            media_type="application/octet-stream",
            producer_id="adversarial-test",
            producer_version="1",
        )
        with pytest.raises(WorkspaceCorruptError, match=r"unexpected=\['extra'\]"):
            transaction.commit(outputs={"registry": registry, "extra": extra})


def test_complete_parse_requires_every_source_output(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    with workspace.begin("parse") as transaction:
        source, outputs = _put_parsed_source(
            transaction,
            "source.txt",
            b"raw source bytes",
        )
        transaction.set_sources((source,))
        outputs["registry"] = _put_registry(transaction, (source,))
        del outputs[f"source/{source.id}/diagnostics"]

        with pytest.raises(WorkspaceCorruptError, match="diagnostics"):
            transaction.commit(
                outputs=outputs,
                config={"sources": [source.logical_path]},
            )


def test_complete_clean_requires_every_source_output(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    _, source = _commit_captured_source(workspace)
    with workspace.begin("clean") as transaction:
        transforms = transaction.put_artifact(
            b"[]",
            kind="transform-records",
            media_type="application/json",
            source_ids=(source.id,),
            producer_id="clean-test",
            producer_version="1",
        )

        with pytest.raises(WorkspaceCorruptError, match="cleaning-plan"):
            transaction.commit(outputs={"transforms": transforms})


def test_parse_output_must_match_the_source_descriptor_link(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    raw = b"raw source bytes"
    raw_sha = hashlib.sha256(raw).hexdigest()
    source_id = derive_source_id("source.txt", raw_sha)
    with workspace.begin("parse") as transaction:
        source, outputs = _put_parsed_source(transaction, "source.txt", raw)
        substituted = transaction.put_artifact(
            raw,
            kind="raw-source",
            media_type="application/octet-stream",
            source_ids=(source_id,),
            producer_id="capture-b",
            producer_version="1",
        )
        outputs[f"source/{source_id}/raw"] = substituted
        outputs["registry"] = _put_registry(transaction, (source,))
        transaction.set_sources((source,))
        with pytest.raises(
            WorkspaceCorruptError,
            match="does not match its source link|artifact lineage",
        ):
            transaction.commit(
                outputs=outputs,
                config={"sources": [source.logical_path]},
            )


def test_original_path_mutation_invalidates_revision_identity(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    revision, source = _commit_captured_source(workspace)
    path = workspace.root / "revisions" / revision.revision_id / "revision.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["sources"][source.id]["original_path"] = "/tmp/tampered.txt"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(WorkspaceCorruptError, match="revision identity"):
        workspace.head(verify_objects=False)


def test_revision_manifest_rejects_scalar_type_coercion(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    revision, source = _commit_captured_source(workspace)
    path = workspace.root / "revisions" / revision.revision_id / "revision.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    original_size = manifest["sources"][source.id]["size"]
    manifest["sources"][source.id]["size"] = str(original_size)
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(WorkspaceCorruptError, match="invalid workspace revision"):
        workspace.head(verify_objects=False)


def test_workspace_metadata_rejects_scalar_type_coercion(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    path = workspace.root / "workspace.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata["schema_version"] = str(metadata["schema_version"])
    path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(WorkspaceCorruptError, match="invalid workspace metadata"):
        Workspace.open(workspace.root)


def test_stale_stage_prior_revision_mutation_fails_lineage_validation(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    _complete_pipeline(workspace)
    revision = _commit_stage(workspace, "clean", "changed")
    path = workspace.root / "revisions" / revision.revision_id / "revision.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    prior = manifest["stages"]["chunk"]["prior_revision_id"]
    replacement = workspace.get_revision(prior).parent_revision_id
    assert replacement is not None and replacement != prior
    manifest["stages"]["chunk"]["prior_revision_id"] = replacement
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(WorkspaceCorruptError, match="commit lineage"):
        workspace.head(verify_objects=False)


def test_original_path_remains_outside_portable_semantic_digest(tmp_path):
    first, _ = _commit_captured_source(
        Workspace.create(tmp_path / "first"),
        original_path="/machine-one/source.txt",
    )
    second, _ = _commit_captured_source(
        Workspace.create(tmp_path / "second"),
        original_path="/machine-two/source.txt",
    )

    assert first.state_digest == second.state_digest


def test_in_memory_base_mutation_cannot_rewrite_inherited_facts(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    committed = _commit_stage(workspace, "parse")
    transaction = workspace.begin("clean")
    artifact = transaction.put_artifact(
        b"cleaned",
        kind="clean-output",
        media_type="application/octet-stream",
        producer_id="clean-test",
        producer_version="1",
    )
    transaction.base.stages["parse"].config["sources"].append("forged.txt")

    with pytest.raises(WorkspaceCorruptError, match="persisted HEAD"):
        transaction.commit(outputs={"clean": artifact})

    assert workspace.head().revision_id == committed.revision_id
    assert workspace.head().stages["parse"].config == {"sources": []}
