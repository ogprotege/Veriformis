from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path, PurePosixPath

from veriformis.pipeline import PipelineService
from veriformis.workspace import (
    WORKSPACE_LAYOUT_SCHEMA_VERSION,
    WORKSPACE_REVISION_SCHEMA_VERSION,
    Workspace,
)


_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "phase3"
    / "pre-taxonomy-default-clean.json"
)
_PRODUCER = {
    "generated_on": "2026-08-21",
    "source_fixture": (
        "tests/fixtures/acceptance/v1/raw/adversarial/rich-cleaning.md"
    ),
    "source_revision": "f8dd1bfd49abd4e1b8746a3060eef75bf2ed5004",
    "workspace_layout_schema": 1,
    "workspace_revision_schema": 3,
}
_HEAD_REVISION_ID = (
    "rev-v1-4d0c1855ddb09d563d33c12a397a89e1fef50df20fad1f6cd149c6be3257b4e0"
)
_HEAD_STATE_DIGEST = (
    "e07a0e1f0865f82d1eab195db9e963997e49d5df48312014da74269191fc4d12"
)
_HISTORY = (
    _HEAD_REVISION_ID,
    "rev-v1-f5ed307eb2281cb5fa272b6db4f95e6c972a27fc2ed4cad80353fafaad29c356",
    "rev-v1-067c06ae71cf47e3a350b416248816e59454a49631888e76222b72911c2d57a1",
)
_DEFAULT_CLEAN_CONFIG = {
    "custom": None,
    "max_remove_ppm": 300_000,
    "rules": ["page-numbers", "whitespace"],
}
_DEFAULT_CLEAN_CONFIG_DIGEST = (
    "54bacbd948a77c58571db8d787c00deedbe323507edd988495d2b5604ee7c4b3"
)


def _materialize_frozen_workspace(tmp_path: Path) -> Path:
    payload = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    assert set(payload) == {"files", "fixture_schema", "producer"}
    assert payload["fixture_schema"] == "veriformis.test-workspace-snapshot/v1"
    assert payload["producer"] == _PRODUCER

    files = payload["files"]
    assert isinstance(files, dict)
    assert len(files) == 15

    workspace = tmp_path / "workspace"
    for raw_path, encoded_file in sorted(files.items()):
        relative_path = PurePosixPath(raw_path)
        assert not relative_path.is_absolute()
        assert relative_path.parts
        assert all(part not in {"", ".", ".."} for part in relative_path.parts)
        assert set(encoded_file) == {"base64", "sha256"}
        encoded = "".join(encoded_file["base64"])
        contents = base64.b64decode(encoded, validate=True)
        assert hashlib.sha256(contents).hexdigest() == encoded_file["sha256"]

        destination = workspace.joinpath(*relative_path.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(contents)

    # Git cannot retain the empty transaction directory from the original
    # workspace. Recreate only that layout directory in pytest's temporary root.
    (workspace / ".txn").mkdir()
    return workspace


def test_pre_taxonomy_default_clean_workspace_opens_and_replays_unchanged(
    tmp_path: Path,
) -> None:
    workspace_path = _materialize_frozen_workspace(tmp_path)

    workspace = Workspace.open(workspace_path)
    head = workspace.head()
    history = workspace.verify_history()

    assert workspace.metadata.schema_version == WORKSPACE_LAYOUT_SCHEMA_VERSION == 1
    assert WORKSPACE_REVISION_SCHEMA_VERSION == 3
    assert head.schema_version == 3
    assert head.committed_stage == "clean"
    assert head.revision_id == _HEAD_REVISION_ID
    assert head.state_digest == _HEAD_STATE_DIGEST
    assert history == _HISTORY

    clean_state = head.stages["clean"]
    assert clean_state.status == "complete"
    assert clean_state.config == _DEFAULT_CLEAN_CONFIG
    assert clean_state.config_digest == _DEFAULT_CLEAN_CONFIG_DIGEST
    transforms = json.loads(
        workspace.read_artifact(
            clean_state.outputs["transforms"],
            revision=head,
        )
    )
    assert len(transforms) == 3

    outcome = PipelineService().clean(workspace_path)

    assert outcome.unchanged is True
    assert outcome.revision_id == _HEAD_REVISION_ID
    reopened = Workspace.open(workspace_path)
    assert reopened.head_id == _HEAD_REVISION_ID
    assert reopened.verify_history() == _HISTORY
    assert (workspace_path / "HEAD").read_bytes() == (
        _HEAD_REVISION_ID + "\n"
    ).encode("ascii")
