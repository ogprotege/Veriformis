"""Defect-closure regressions for ``WorkspaceTransaction._commit``.

A staged-but-unreferenced artifact must not defeat exact no-op detection:
the no-op decision must be based on the artifacts the candidate revision
would actually carry, and every non-no-op commit must pass the same
revision-transition validation that history verification applies.
"""

from unittest.mock import patch

import test_workspace_integrity as twi

import veriformis.workspace as workspace_module
from veriformis.workspace import Workspace


def _recommit_parse_with_orphan(workspace, text):
    """Re-commit an identical parse stage while staging one orphan artifact."""
    with workspace.begin("parse") as transaction:
        source, outputs = twi._put_parsed_source(
            transaction,
            "source.txt",
            text.encode(),
        )
        transaction.set_sources((source,))
        outputs["registry"] = twi._put_registry(transaction, (source,))
        orphan = transaction.put_artifact(
            b"orphan payload never referenced by any output",
            kind="scratch",
            media_type="text/plain",
            producer_id="veriformis.tests.orphan-probe",
            producer_version="1",
        )
        revision = twi._synthetic_commit(
            transaction,
            outputs=outputs,
            config={"sources": ["source.txt"]},
        )
    return revision, orphan


def test_orphan_staged_artifact_does_not_defeat_exact_stage_noop(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    first = twi._commit_stage(workspace, "parse", "same")

    revision, orphan = _recommit_parse_with_orphan(workspace, "same")

    assert revision.revision_id == first.revision_id
    assert workspace.head_id == first.revision_id
    assert orphan.id not in revision.artifacts
    assert workspace.head().revision_id == first.revision_id
    reopened = Workspace.open(tmp_path / "ws")
    assert reopened.head().revision_id == first.revision_id
    with reopened.begin("clean") as transaction:
        transaction.abort()


def test_orphan_noop_recommit_preserves_complete_downstream_stages(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    twi._complete_pipeline(workspace)
    head = workspace.head()
    assert all(state.status == "complete" for state in head.stages.values())

    revision, orphan = _recommit_parse_with_orphan(workspace, "captured source")

    assert revision.revision_id == head.revision_id
    assert workspace.head_id == head.revision_id
    assert orphan.id not in revision.artifacts
    assert all(state.status == "complete" for state in revision.stages.values())
    reopened = Workspace.open(tmp_path / "ws")
    assert all(
        state.status == "complete"
        for state in reopened.head().stages.values()
    )


def test_exact_stage_noop_without_orphan_still_keeps_head_revision(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    first = twi._commit_stage(workspace, "parse", "same")
    second = twi._commit_stage(workspace, "parse", "same")

    assert second.revision_id == first.revision_id
    assert workspace.head_id == first.revision_id
    reopened = Workspace.open(tmp_path / "ws")
    assert reopened.head().revision_id == first.revision_id


def test_commit_validates_candidate_transition_against_head(tmp_path):
    workspace = Workspace.create(tmp_path / "ws")
    first = twi._commit_stage(workspace, "parse", "first source")

    real_validate = workspace_module._validate_revision_transition
    calls = []

    def recording_validate(child, parent):
        calls.append((child, parent))
        return real_validate(child, parent)

    with patch.object(
        workspace_module,
        "_validate_revision_transition",
        new=recording_validate,
    ):
        revised = twi._commit_stage(workspace, "parse", "changed source")

    assert revised.revision_id != first.revision_id
    assert any(
        child.revision_id == revised.revision_id
        and parent.revision_id == first.revision_id
        for child, parent in calls
    ), "commit did not validate its candidate transition before promoting HEAD"
