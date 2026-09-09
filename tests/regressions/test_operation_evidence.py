"""Operation caches preserve fresh evidence while avoiding repeated replay."""
from collections import Counter
from pathlib import Path

import pytest

from veriformis._operation import current_operation, operation_scope
from veriformis.errors import ArtifactDigestMismatchError, WorkspaceRevisionConflict
from veriformis.pipeline import PipelineService
from veriformis.pipeline import service as service_module
from veriformis.workspace import Workspace


def _prepared(tmp_path):
    paths = []
    for name, text in (("a", "Alpha independent document content."),
                       ("b", "Beta separate evidence for evaluation.")):
        path = tmp_path / f"{name}.txt"
        path.write_text(text)
        paths.append(path)
    service = PipelineService()
    root = tmp_path / "workspace"
    service.parse(paths, root, source_root=tmp_path)
    service.clean(root)
    service.chunk(root, goal="learn-the-text")
    return service, root


def test_construct_reads_objects_once_and_replays_each_source_once(tmp_path, monkeypatch):
    service, root = _prepared(tmp_path)
    reads, parses, histories = Counter(), Counter(), []
    original_read = Path.read_bytes
    original_parse = service_module.parse_captured_source
    original_history = Workspace.verify_history

    def read(path):
        if path.is_relative_to(root):
            reads[path] += 1
        return original_read(path)

    def parse(*args, **kwargs):
        parses[kwargs["logical_path"]] += 1
        return original_parse(*args, **kwargs)

    def history(self, **kwargs):
        histories.append(self.root)
        return original_history(self, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", read)
    monkeypatch.setattr(service_module, "parse_captured_source", parse)
    monkeypatch.setattr(Workspace, "verify_history", history)
    service.construct(root, goal="learn-the-text")
    assert len(histories) == 1
    assert len(parses) == 2 and set(parses.values()) == {1}
    assert reads and max(reads.values()) == 1
    assert current_operation() is None


def test_nested_pipeline_calls_extend_one_verified_chain(tmp_path, monkeypatch):
    service, root = _prepared(tmp_path)
    count = 0
    original = Workspace.verify_history

    def history(self, **kwargs):
        nonlocal count
        count += 1
        return original(self, **kwargs)

    monkeypatch.setattr(Workspace, "verify_history", history)
    with operation_scope():
        service.construct(root, goal="learn-the-text")
        service.curate(root)
        service.split(root)
        service.format(root)
        service.validate(root)
        service.seal(root, tmp_path / "dataset.vfbundle")
    assert count == 1
    service.preview(root)
    assert count == 2


def test_cached_loader_result_cannot_be_poisoned(tmp_path):
    _, root = _prepared(tmp_path)
    with operation_scope():
        store = Workspace.open(root)
        revision = store.head()
        sources = service_module._load_sources(store, revision)
        sources.clear()
        assert len(service_module._load_sources(store, revision)) == 2
        revision.sources.clear()
        assert len(store.head().sources) == 2


def test_mid_command_artifact_change_refuses_before_head(tmp_path, monkeypatch):
    service, root = _prepared(tmp_path)
    store = Workspace.open(root)
    head = store.head_id
    revision = store.head()
    source = next(iter(revision.sources.values()))
    artifact = revision.artifacts[source.raw_artifact_id]
    path = store._object_path(artifact.sha256)

    def mutate(self, point):
        if point == "before-head":
            path.chmod(0o644)
            path.write_bytes(b"corrupt" + path.read_bytes()[7:])

    monkeypatch.setattr(Workspace, "_inject_failure", mutate)
    with pytest.raises(ArtifactDigestMismatchError, match="changed during operation"):
        service.construct(root, goal="learn-the-text")
    assert store.head_id == head


def test_cached_history_never_masks_live_head_conflict(tmp_path):
    _, root = _prepared(tmp_path)
    with operation_scope():
        store = Workspace.open(root)
        transaction = store.begin("chunk")
        original = store.head_id
        parent = store.head().parent_revision_id
        (root / "HEAD").write_text(parent + "\n")
        try:
            with pytest.raises(WorkspaceRevisionConflict):
                transaction.commit(outputs={}, config={})
        finally:
            (root / "HEAD").write_text(original + "\n")


def test_new_command_refuses_changed_historical_artifact(tmp_path):
    service, root = _prepared(tmp_path)
    service.construct(root, goal="learn-the-text")
    store = Workspace.open(root)
    artifact = next(iter(store.head().artifacts.values()))
    path = store._object_path(artifact.sha256)
    path.chmod(0o644)
    path.write_bytes(b"broken")
    with pytest.raises(ArtifactDigestMismatchError):
        service.preview(root)


@pytest.mark.parametrize("point", ["before-objects", "after-objects"])
def test_cached_staged_bytes_cannot_mask_publication_tampering(tmp_path, monkeypatch, point):
    service, root = _prepared(tmp_path)
    store = Workspace.open(root)
    head = store.head_id

    def mutate(self, checkpoint):
        if checkpoint != point:
            return
        operation = current_operation()
        if point == "before-objects":
            path = next(path for path in operation.files if path.is_relative_to(root / ".txn"))
        else:
            path = next(path for path in operation.files if path.is_relative_to(root / "objects"))
        path.chmod(0o644)
        path.write_bytes(b"corrupt" + path.read_bytes()[7:])

    monkeypatch.setattr(Workspace, "_inject_failure", mutate)
    with pytest.raises(ArtifactDigestMismatchError):
        service.construct(root, goal="learn-the-text")
    assert store.head_id == head
