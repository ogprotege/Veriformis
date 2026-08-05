import fcntl
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis import workspace as workspace_module
from veriformis.bundle.finished import FinishedBundleError
from veriformis.cli import app
from veriformis.errors import WorkspaceCorruptError
from veriformis.pipeline import service as pipeline_service
from veriformis.workspace import Workspace


runner = CliRunner()


def _validated_workspace(tmp_path: Path, name: str, text: str) -> Path:
    source = tmp_path / f"{name}.txt"
    source.write_text(text, encoding="utf-8")
    workspace = tmp_path / name
    commands = (
        (
            "parse",
            str(source),
            "-o",
            str(workspace),
            "--source-root",
            str(tmp_path),
        ),
        ("clean", str(workspace)),
        ("chunk", str(workspace), "--strategy", "paragraph"),
        ("construct", str(workspace), "--objective", "full_text"),
        ("curate", str(workspace), "--allow-empty-evaluation"),
        ("split", str(workspace)),
        ("format", str(workspace)),
        ("validate", str(workspace)),
    )
    for command in commands:
        result = runner.invoke(app, list(command))
        assert result.exit_code == 0, result.output
    assert Workspace.open(workspace).head().committed_stage == "validate"
    return workspace


def _file_state(root: Path) -> dict[str, tuple[int, int, int, bytes]]:
    return {
        str(path.relative_to(root)): (
            path.stat().st_ino,
            path.stat().st_mtime_ns,
            path.stat().st_size,
            path.read_bytes(),
        )
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_publication_action_is_seal_only(tmp_path):
    workspace = Workspace.create(tmp_path / "workspace")

    with workspace.begin("parse") as transaction:
        with pytest.raises(WorkspaceCorruptError, match="only the seal stage"):
            transaction._set_seal_publication_action(lambda: None)


def test_cli_publication_runs_under_commit_lock_before_head(tmp_path, monkeypatch):
    workspace_path = _validated_workspace(tmp_path, "workspace", "alpha source")
    bundle = tmp_path / "locked.vfbundle"
    before = Workspace.open(workspace_path).head_id
    observations: list[tuple[str, bool]] = []
    real_write = pipeline_service.write_finished_bundle

    def inspect_lock_then_write(*args, **kwargs):
        with (workspace_path / "LOCK").open("a+b") as lock:
            with pytest.raises(BlockingIOError):
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        observations.append((Workspace.open(workspace_path).head_id, bundle.exists()))
        receipt = real_write(*args, **kwargs)
        observations.append((Workspace.open(workspace_path).head_id, bundle.exists()))
        return receipt

    monkeypatch.setattr(
        pipeline_service, "write_finished_bundle", inspect_lock_then_write
    )
    result = runner.invoke(app, ["seal", str(workspace_path), "-o", str(bundle)])

    assert result.exit_code == 0, result.output
    assert observations == [(before, False), (before, True)]
    after = Workspace.open(workspace_path).head()
    assert after.revision_id != before
    assert after.committed_stage == "seal"


def test_publication_failure_leaves_head_and_target_unchanged(tmp_path, monkeypatch):
    workspace_path = _validated_workspace(tmp_path, "workspace", "alpha source")
    bundle = tmp_path / "failed.vfbundle"
    before = Workspace.open(workspace_path).head_id

    def fail_publication(*args, **kwargs):
        raise FinishedBundleError("injected publication failure")

    monkeypatch.setattr(pipeline_service, "write_finished_bundle", fail_publication)
    result = runner.invoke(app, ["seal", str(workspace_path), "-o", str(bundle)])

    assert result.exit_code != 0
    assert "injected publication failure" in result.output
    assert Workspace.open(workspace_path).head_id == before
    assert not bundle.exists()


def test_visible_bundle_is_recovered_exactly_after_head_failure(tmp_path, monkeypatch):
    workspace_path = _validated_workspace(tmp_path, "workspace", "alpha source")
    bundle = tmp_path / "recoverable.vfbundle"
    before = Workspace.open(workspace_path).head_id
    real_promote = workspace_module._promote_commit_pointer

    def fail_head_promotion(path: Path, data: bytes) -> bool:
        raise OSError(f"injected HEAD failure for {path}")

    monkeypatch.setattr(
        workspace_module,
        "_promote_commit_pointer",
        fail_head_promotion,
    )
    first = runner.invoke(app, ["seal", str(workspace_path), "-o", str(bundle)])

    assert first.exit_code != 0
    assert "published bundle remains visible" in first.output
    assert "workspace receipt did not commit" in first.output
    assert bundle.is_dir()
    assert Workspace.open(workspace_path).head_id == before
    published_state = _file_state(bundle)

    monkeypatch.setattr(
        workspace_module,
        "_promote_commit_pointer",
        real_promote,
    )

    def forbid_rewrite(*args, **kwargs):
        raise AssertionError("exact recovery must not invoke the bundle writer")

    monkeypatch.setattr(pipeline_service, "write_finished_bundle", forbid_rewrite)
    retry = runner.invoke(app, ["seal", str(workspace_path), "-o", str(bundle)])

    assert retry.exit_code == 0, retry.output
    assert "verification grade: external_digest" in retry.output
    assert _file_state(bundle) == published_state
    store = Workspace.open(workspace_path)
    sealed = store.head()
    assert sealed.committed_stage == "seal"
    assert (
        store.read_artifact(sealed.stages["seal"].outputs["manifest"], revision=sealed)
        == (bundle / "manifest.json").read_bytes()
    )
    assert (
        store.read_artifact(
            sealed.stages["seal"].outputs["attestation"], revision=sealed
        )
        == (bundle / "attestation.json").read_bytes()
    )


def test_retry_rejects_a_valid_bundle_for_a_different_dataset(tmp_path):
    first_workspace = _validated_workspace(tmp_path, "first", "alpha source")
    second_workspace = _validated_workspace(tmp_path, "second", "beta source")
    bundle = tmp_path / "different.vfbundle"
    published = runner.invoke(
        app,
        ["seal", str(second_workspace), "-o", str(bundle)],
    )
    assert published.exit_code == 0, published.output
    published_state = _file_state(bundle)
    before = Workspace.open(first_workspace).head_id

    rejected = runner.invoke(
        app,
        ["seal", str(first_workspace), "-o", str(bundle)],
    )

    assert rejected.exit_code != 0
    assert "does not match the expected external digest" in rejected.output
    assert Workspace.open(first_workspace).head_id == before
    assert _file_state(bundle) == published_state
