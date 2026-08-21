"""Phase 4.6 atomic publication and independent-tree verification tests."""

from __future__ import annotations

import base64
import importlib.util
import json
import os
from pathlib import Path

import pytest

from veriformis.bundle import inspect_finished_bundle
from veriformis.errors import (
    BundleVerificationError,
    ExportContractError,
    ExportVerificationError,
)
from veriformis.exports import (
    ExportConsumerProfile,
    ExportContainerProfile,
    ExportDependencyBinding,
    ExportFilePlan,
    ExportPlan,
    ExportService,
)
from veriformis.exports import _publication as publication_module
from veriformis.exports import service as service_module
from veriformis.exports.models import EXPORT_RECEIPT_PATH
from veriformis.exports._publication import (
    ExportPartialPublicationError,
    _verify_export_directory,
)
from veriformis.identity import sha256_digest

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "regressions"
    / "fixtures"
    / "phase3"
    / "pre-taxonomy-full-text.vfbundle.json"
)
EXPECTED_MANIFEST_SHA256 = (
    "2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733"
)
EXACT_FILES = (
    ("data/evaluation.jsonl", b'{"text":"evaluation-a"}\n{"text":"evaluation-b"}\n'),
    ("data/train.jsonl", b'{"text":"train"}\n'),
    ("metadata/schema.json", b'{"row_schema":"text"}'),
)


def _materialize_bundle(tmp_path: Path) -> Path:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bundle = tmp_path / "source.vfbundle"
    for relative_path, encoded in sorted(fixture["files_base64"].items()):
        data = base64.b64decode(encoded, validate=True)
        target = bundle.joinpath(*relative_path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return bundle


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _file_plans() -> tuple[ExportFilePlan, ...]:
    by_path = dict(EXACT_FILES)
    return (
        ExportFilePlan.create(
            path="data/evaluation.jsonl",
            role="evaluation-partition",
            media_type="application/jsonl",
            membership_scope="evaluation",
            record_count=2,
            semantic_content_sha256=None,
            expected_sha256=sha256_digest(by_path["data/evaluation.jsonl"]),
            expected_byte_size=len(by_path["data/evaluation.jsonl"]),
        ),
        ExportFilePlan.create(
            path="data/train.jsonl",
            role="training-partition",
            media_type="application/jsonl",
            membership_scope="train",
            record_count=1,
            semantic_content_sha256=None,
            expected_sha256=sha256_digest(by_path["data/train.jsonl"]),
            expected_byte_size=len(by_path["data/train.jsonl"]),
        ),
        ExportFilePlan.create(
            path="metadata/schema.json",
            role="schema-metadata",
            media_type="application/json",
            membership_scope="none",
            record_count=None,
            semantic_content_sha256=None,
            expected_sha256=sha256_digest(by_path["metadata/schema.json"]),
            expected_byte_size=len(by_path["metadata/schema.json"]),
        ),
    )


def _create_plan(service: ExportService, bundle: Path) -> ExportPlan:
    return service.create_plan(
        bundle,
        container_profile=ExportContainerProfile.create(
            container_id="phase4-conformance-directory",
            container_version=7,
            determinism_claim="portable_exact_bytes",
        ),
        consumer_profile=ExportConsumerProfile.create(
            consumer_id="phase4-conformance-consumer",
            profile_version=3,
            accepted_row_schemas=("text",),
        ),
        dependencies=(
            ExportDependencyBinding.create(
                dependency_name="phase4-conformance-renderer",
                dependency_version="1.0.0",
                dependency_role="renderer",
            ),
        ),
        file_plans=_file_plans(),
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )


class _ConformanceExportService(ExportService):
    def __init__(
        self,
        *,
        files: tuple[tuple[str, bytes], ...] = EXACT_FILES,
        drop_evaluation_row: bool = False,
    ) -> None:
        self.files = files
        self.drop_evaluation_row = drop_evaluation_row

    def _render_derivative(self, plan, source_row_set):
        del plan
        evaluation_rows = source_row_set.evaluation_rows
        if self.drop_evaluation_row:
            evaluation_rows = evaluation_rows[:-1]
        return service_module._RenderedDerivative(
            files=self.files,
            train_rows=source_row_set.train_rows,
            evaluation_rows=evaluation_rows,
            provenance=source_row_set.provenance,
        )


def _publish(
    tmp_path: Path,
    *,
    service: _ConformanceExportService | None = None,
    destination_name: str = "derivative",
    cancellation_check=None,
):
    bundle = _materialize_bundle(tmp_path)
    chosen = service or _ConformanceExportService()
    plan = _create_plan(chosen, bundle)
    destination = tmp_path / destination_name
    outcome = chosen.publish(
        plan,
        bundle,
        destination,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        cancellation_check=cancellation_check,
    )
    return bundle, plan, destination, outcome


def test_exact_export_is_receipt_bound_verified_and_deterministic_across_roots(
    tmp_path: Path,
):
    bundle = _materialize_bundle(tmp_path)
    service = _ConformanceExportService()
    plan = _create_plan(service, bundle)
    outcomes = []
    for name in ("first", "second"):
        destination = tmp_path / name
        outcome = service.publish(
            plan,
            bundle,
            destination,
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        )
        receipt, verification = _verify_export_directory(
            destination,
            expected_plan=plan,
        )
        assert receipt == outcome.receipt
        assert verification == outcome.verification
        assert set(_tree_bytes(destination)) == {
            *(path for path, _ in EXACT_FILES),
            EXPORT_RECEIPT_PATH,
        }
        outcomes.append(outcome)

    assert outcomes[0].receipt.canonical_bytes() == outcomes[1].receipt.canonical_bytes()
    assert (
        outcomes[0].verification.canonical_bytes()
        == outcomes[1].verification.canonical_bytes()
    )
    assert outcomes[0].destination_root != outcomes[1].destination_root
    assert outcomes[0].durability_warning is None


def test_default_service_has_no_shipped_renderer(tmp_path: Path):
    bundle = _materialize_bundle(tmp_path)
    service = ExportService()
    plan = _create_plan(service, bundle)
    destination = tmp_path / "unsupported"

    with pytest.raises(ExportContractError, match="test-injected only"):
        service.publish(
            plan,
            bundle,
            destination,
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        )

    assert not destination.exists()


def test_phase_4_6_publication_runtime_stays_private():
    import veriformis.exports as exports

    assert importlib.util.find_spec("veriformis.exports.publication") is None
    for name in (
        "ExportPublicationOutcome",
        "ExportPartialPublicationError",
        "publish_exact_export",
        "verify_export_directory",
    ):
        assert name not in exports.__all__
        assert not hasattr(exports, name)


def test_publication_requires_the_separately_retained_source_digest(tmp_path: Path):
    bundle = _materialize_bundle(tmp_path)
    service = _ConformanceExportService()
    plan = _create_plan(service, bundle)

    with pytest.raises(ExportContractError, match="separately retained"):
        service.publish(plan, bundle, tmp_path / "missing-evidence")
    with pytest.raises(ExportContractError, match="differs from the export plan"):
        service.publish(
            plan,
            bundle,
            tmp_path / "wrong-evidence",
            expected_manifest_sha256="0" * 64,
        )

    assert not (tmp_path / "missing-evidence").exists()
    assert not (tmp_path / "wrong-evidence").exists()


def test_semantic_only_plan_is_not_published_before_phase_4_7(tmp_path: Path):
    bundle = _materialize_bundle(tmp_path)
    service = _ConformanceExportService()
    plan = service.create_plan(
        bundle,
        container_profile=ExportContainerProfile.create(
            container_id="phase4-semantic-conformance",
            container_version=1,
            determinism_claim="semantic_content_only",
        ),
        dependencies=(
            ExportDependencyBinding.create(
                dependency_name="phase4-semantic-renderer",
                dependency_version="1.0.0",
                dependency_role="renderer",
            ),
        ),
        file_plans=(
            ExportFilePlan.create(
                path="records/all.rows",
                role="complete-dataset",
                media_type="application/json",
                membership_scope="all",
                record_count=3,
                semantic_content_sha256=sha256_digest(b"semantic rows"),
                expected_sha256=None,
                expected_byte_size=None,
            ),
        ),
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )

    with pytest.raises(ExportContractError, match="portable_exact_bytes"):
        service.publish(
            plan,
            bundle,
            tmp_path / "semantic",
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        )


@pytest.mark.parametrize(
    "files, message",
    (
        (EXACT_FILES[:-1], "missing"),
        ((*EXACT_FILES, EXACT_FILES[0]), "duplicate"),
        ((*EXACT_FILES, ("../outside", b"escape")), "unsafe"),
        (
            tuple(
                (path, b"wrong" if path == "data/train.jsonl" else data)
                for path, data in EXACT_FILES
            ),
            "differ from the exact plan",
        ),
    ),
)
def test_renderer_file_mutations_fail_before_staging(
    tmp_path: Path,
    files: tuple[tuple[str, bytes], ...],
    message: str,
):
    bundle = _materialize_bundle(tmp_path)
    service = _ConformanceExportService(files=files)
    plan = _create_plan(service, bundle)
    destination = tmp_path / "rejected"

    with pytest.raises(ExportVerificationError, match=message):
        service.publish(
            plan,
            bundle,
            destination,
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        )

    assert not destination.exists()
    assert not list(tmp_path.glob(".veriformis-export-*"))


def test_renderer_membership_change_fails_before_staging(tmp_path: Path):
    bundle = _materialize_bundle(tmp_path)
    service = _ConformanceExportService(drop_evaluation_row=True)
    plan = _create_plan(service, bundle)
    destination = tmp_path / "rejected"

    with pytest.raises(ExportVerificationError):
        service.publish(
            plan,
            bundle,
            destination,
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        )

    assert not destination.exists()
    assert not list(tmp_path.glob(".veriformis-export-*"))


@pytest.mark.parametrize(
    "kind",
    ("file", "directory", "symlink", "dangling", "fifo"),
)
def test_no_replace_preserves_every_existing_destination(tmp_path: Path, kind: str):
    bundle = _materialize_bundle(tmp_path)
    service = _ConformanceExportService()
    plan = _create_plan(service, bundle)
    destination = tmp_path / "occupied"
    sentinel = tmp_path / "sentinel"
    sentinel.write_text("untouched", encoding="utf-8")
    if kind == "file":
        destination.write_text("winner", encoding="utf-8")
    elif kind == "directory":
        destination.mkdir()
        (destination / "winner").write_text("winner", encoding="utf-8")
    elif kind == "symlink":
        destination.symlink_to(sentinel)
    elif kind == "fifo":
        os.mkfifo(destination)
    else:
        destination.symlink_to(tmp_path / "missing")

    with pytest.raises(ExportContractError, match="already exists"):
        service.publish(
            plan,
            bundle,
            destination,
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        )

    assert sentinel.read_text(encoding="utf-8") == "untouched"
    assert destination.is_symlink() if kind in {"symlink", "dangling"} else destination.exists()
    assert not list(tmp_path.glob(".veriformis-export-*"))


def test_destination_inside_source_is_rejected_without_mutating_source(tmp_path: Path):
    bundle = _materialize_bundle(tmp_path)
    before = _tree_bytes(bundle)
    service = _ConformanceExportService()
    plan = _create_plan(service, bundle)

    with pytest.raises(ExportContractError, match="inside the verified source"):
        service.publish(
            plan,
            bundle,
            bundle / "derived",
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        )

    assert _tree_bytes(bundle) == before
    assert not list(bundle.glob(".veriformis-export-*"))


class _Cancelled(Exception):
    pass


@pytest.mark.parametrize("cancel_at", (1, 3, 5, 8, 15, 24))
def test_cancellation_before_visibility_cleans_owned_staging(
    tmp_path: Path,
    cancel_at: int,
):
    calls = 0

    def cancel() -> None:
        nonlocal calls
        calls += 1
        if calls == cancel_at:
            raise _Cancelled(f"cancel {cancel_at}")

    bundle = _materialize_bundle(tmp_path)
    before = _tree_bytes(bundle)
    service = _ConformanceExportService()
    plan = _create_plan(service, bundle)
    destination = tmp_path / "cancelled"

    with pytest.raises(_Cancelled, match=f"cancel {cancel_at}"):
        service.publish(
            plan,
            bundle,
            destination,
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
            cancellation_check=cancel,
        )

    assert _tree_bytes(bundle) == before
    assert not destination.exists()
    assert not list(tmp_path.glob(".veriformis-export-*"))


def test_independent_staged_verifier_rejects_an_unexpected_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    original = publication_module._verify_staged_export

    def add_unexpected(root_descriptor, **kwargs):
        descriptor = os.open(
            "unexpected",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
            dir_fd=root_descriptor,
        )
        os.close(descriptor)
        return original(root_descriptor, **kwargs)

    monkeypatch.setattr(publication_module, "_verify_staged_export", add_unexpected)
    bundle = _materialize_bundle(tmp_path)
    service = _ConformanceExportService()
    plan = _create_plan(service, bundle)
    destination = tmp_path / "tampered"

    with pytest.warns(RuntimeWarning, match="could not remove export staging"):
        with pytest.raises(ExportVerificationError, match="file set is not closed"):
            service.publish(
                plan,
                bundle,
                destination,
                expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
            )

    assert not destination.exists()
    stages = list(tmp_path.glob(".veriformis-export-*"))
    assert len(stages) == 1
    assert (stages[0] / "unexpected").is_file()


def test_successful_verification_is_created_only_from_the_staged_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    original = publication_module.ExportVerification.create
    observed_staged_receipt = False

    def create_after_staging(*, receipt):
        nonlocal observed_staged_receipt
        stages = list(tmp_path.glob(".veriformis-export-*"))
        assert len(stages) == 1
        assert (stages[0] / EXPORT_RECEIPT_PATH).read_bytes() == receipt.canonical_bytes()
        observed_staged_receipt = True
        return original(receipt=receipt)

    monkeypatch.setattr(
        publication_module.ExportVerification,
        "create",
        create_after_staging,
    )
    _, _, destination, _ = _publish(tmp_path)

    assert observed_staged_receipt is True
    assert destination.is_dir()


def test_staging_setup_failure_cleans_the_owned_private_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    def fail_mode(descriptor: int, mode: int) -> None:
        del descriptor, mode
        raise OSError("fchmod sentinel")

    monkeypatch.setattr(publication_module.os, "fchmod", fail_mode)
    bundle = _materialize_bundle(tmp_path)
    service = _ConformanceExportService()
    plan = _create_plan(service, bundle)

    with pytest.raises(OSError, match="fchmod sentinel"):
        service.publish(
            plan,
            bundle,
            tmp_path / "not-published",
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        )

    assert not (tmp_path / "not-published").exists()
    assert not list(tmp_path.glob(".veriformis-export-*"))


def test_staging_identity_swap_is_never_adopted_or_deleted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "sentinel").write_text("keep", encoding="utf-8")
    moved_real_stage = "attacker-moved-real-stage"
    original_open = publication_module.os.open
    swapped_stage_name: str | None = None

    def swap_before_stage_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal swapped_stage_name
        if (
            swapped_stage_name is None
            and isinstance(path, str)
            and path.startswith(".veriformis-export-")
            and dir_fd is not None
            and flags == publication_module._DIRECTORY_FLAGS
        ):
            swapped_stage_name = path
            os.rename(
                path,
                moved_real_stage,
                src_dir_fd=dir_fd,
                dst_dir_fd=dir_fd,
            )
            os.rename(victim, path, dst_dir_fd=dir_fd)
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(publication_module.os, "open", swap_before_stage_open)
    bundle = _materialize_bundle(tmp_path)
    service = _ConformanceExportService()
    plan = _create_plan(service, bundle)
    destination = tmp_path / "not-published"

    with pytest.warns(RuntimeWarning, match="refused to remove.*replaced"):
        with pytest.raises(ExportVerificationError, match="changed while opening"):
            service.publish(
                plan,
                bundle,
                destination,
                expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
            )

    assert swapped_stage_name is not None
    assert not destination.exists()
    assert (tmp_path / swapped_stage_name / "sentinel").read_text(
        encoding="utf-8"
    ) == "keep"
    assert (tmp_path / moved_real_stage).is_dir()


def test_cleanup_preserves_an_unowned_directory_injected_during_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "sentinel").write_text("keep", encoding="utf-8")
    original_mkdir = publication_module.os.mkdir
    swapped = False

    def inject_victim(path, mode=0o777, *, dir_fd=None):
        nonlocal swapped
        if path == "data" and dir_fd is not None and not swapped:
            swapped = True
            os.rename(victim, path, dst_dir_fd=dir_fd)
            raise FileExistsError("injected directory winner")
        return original_mkdir(path, mode, dir_fd=dir_fd)

    monkeypatch.setattr(publication_module.os, "mkdir", inject_victim)
    bundle = _materialize_bundle(tmp_path)
    service = _ConformanceExportService()
    plan = _create_plan(service, bundle)
    destination = tmp_path / "not-published"

    with pytest.warns(RuntimeWarning, match="could not remove export staging"):
        with pytest.raises(FileExistsError, match="injected directory winner"):
            service.publish(
                plan,
                bundle,
                destination,
                expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
            )

    assert swapped is True
    assert not destination.exists()
    stages = list(tmp_path.glob(".veriformis-export-*"))
    assert len(stages) == 1
    assert (stages[0] / "data" / "sentinel").read_text(encoding="utf-8") == "keep"


def test_final_precommit_scan_rejects_change_after_staged_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    original = publication_module._rename_no_replace

    def mutate_before_rename(staging, **kwargs):
        def mutate_at_final_checkpoint() -> None:
            descriptor = os.open(
                "late-extra",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=staging.descriptor,
            )
            os.close(descriptor)

        return original(
            staging,
            expected_tree=kwargs["expected_tree"],
            cancellation_check=mutate_at_final_checkpoint,
        )

    monkeypatch.setattr(publication_module, "_rename_no_replace", mutate_before_rename)
    bundle = _materialize_bundle(tmp_path)
    service = _ConformanceExportService()
    plan = _create_plan(service, bundle)
    destination = tmp_path / "late-tamper"

    with pytest.warns(RuntimeWarning, match="could not remove export staging"):
        with pytest.raises(ExportVerificationError, match="immediately before"):
            service.publish(
                plan,
                bundle,
                destination,
                expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
            )

    assert not destination.exists()
    stages = list(tmp_path.glob(".veriformis-export-*"))
    assert len(stages) == 1
    assert (stages[0] / "late-extra").is_file()


def test_target_created_during_publication_wins_the_no_replace_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    original = publication_module._rename_no_replace

    def install_winner(staging, **kwargs):
        os.mkdir(
            staging.destination.target_name,
            dir_fd=staging.destination.parent_descriptor,
        )
        return original(staging, **kwargs)

    monkeypatch.setattr(publication_module, "_rename_no_replace", install_winner)
    bundle = _materialize_bundle(tmp_path)
    service = _ConformanceExportService()
    plan = _create_plan(service, bundle)
    destination = tmp_path / "race"

    with pytest.raises(FileExistsError):
        service.publish(
            plan,
            bundle,
            destination,
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        )

    assert destination.is_dir()
    assert not any(destination.iterdir())
    assert not list(tmp_path.glob(".veriformis-export-*"))


def test_parent_fsync_failure_is_visible_warning_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    target = tmp_path / "visible"
    original = publication_module.os.fsync

    def fail_after_visibility(descriptor: int) -> None:
        if target.exists():
            raise OSError("parent sync sentinel")
        original(descriptor)

    monkeypatch.setattr(publication_module.os, "fsync", fail_after_visibility)
    with pytest.warns(RuntimeWarning, match="is visible"):
        _, plan, destination, outcome = _publish(
            tmp_path,
            destination_name="visible",
        )

    assert destination == target
    assert outcome.durability_warning is not None
    assert "parent sync sentinel" in outcome.durability_warning
    assert _verify_export_directory(destination, expected_plan=plan) == (
        outcome.receipt,
        outcome.verification,
    )


def test_no_cancellation_checkpoint_runs_after_atomic_visibility(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    original = publication_module._rename_no_replace
    committed = False

    def cancel() -> None:
        if committed:
            raise _Cancelled("post-commit cancellation must not run")

    def mark_commit(staging, **kwargs):
        nonlocal committed
        result = original(staging, **kwargs)
        committed = True
        return result

    monkeypatch.setattr(publication_module, "_rename_no_replace", mark_commit)
    _, plan, destination, outcome = _publish(
        tmp_path,
        cancellation_check=cancel,
    )

    assert committed is True
    assert _verify_export_directory(destination, expected_plan=plan) == (
        outcome.receipt,
        outcome.verification,
    )


def test_post_commit_bookkeeping_failure_reports_visible_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    def fail_replace(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("post-commit bookkeeping sentinel")

    monkeypatch.setattr(publication_module, "replace", fail_replace)
    bundle = _materialize_bundle(tmp_path)
    service = _ConformanceExportService()
    plan = _create_plan(service, bundle)
    destination = tmp_path / "visible-partial"

    with pytest.raises(ExportPartialPublicationError) as caught:
        service.publish(
            plan,
            bundle,
            destination,
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        )

    assert destination.is_dir()
    assert caught.value.publication.destination_root == destination
    assert isinstance(caught.value.cause, RuntimeError)
    assert _verify_export_directory(destination, expected_plan=plan) == (
        caught.value.publication.receipt,
        caught.value.publication.verification,
    )


def test_exception_after_rename_is_reported_as_partial_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    original = publication_module._rename_no_replace

    def fail_after_rename(staging, **kwargs):
        original(staging, **kwargs)
        raise RuntimeError("after-rename sentinel")

    monkeypatch.setattr(publication_module, "_rename_no_replace", fail_after_rename)
    bundle = _materialize_bundle(tmp_path)
    service = _ConformanceExportService()
    plan = _create_plan(service, bundle)
    destination = tmp_path / "visible-after-rename"

    with pytest.raises(ExportPartialPublicationError) as caught:
        service.publish(
            plan,
            bundle,
            destination,
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        )

    assert isinstance(caught.value.cause, RuntimeError)
    assert destination.is_dir()
    assert _verify_export_directory(destination, expected_plan=plan) == (
        caught.value.publication.receipt,
        caught.value.publication.verification,
    )


def test_target_substitution_after_commit_never_returns_false_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    original = publication_module._rename_no_replace
    moved_name = "moved-verified-export"

    def substitute_target(staging, **kwargs):
        original(staging, **kwargs)
        parent_descriptor = staging.destination.parent_descriptor
        os.rename(
            staging.destination.target_name,
            moved_name,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
        )
        os.mkdir(staging.destination.target_name, dir_fd=parent_descriptor)
        attacker = os.open(
            staging.destination.target_name,
            publication_module._DIRECTORY_FLAGS,
            dir_fd=parent_descriptor,
        )
        try:
            marker = os.open(
                "attacker",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=attacker,
            )
            os.close(marker)
        finally:
            os.close(attacker)

    monkeypatch.setattr(publication_module, "_rename_no_replace", substitute_target)
    bundle = _materialize_bundle(tmp_path)
    service = _ConformanceExportService()
    plan = _create_plan(service, bundle)
    destination = tmp_path / "substituted"

    with pytest.raises(ExportPartialPublicationError) as caught:
        service.publish(
            plan,
            bundle,
            destination,
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        )

    assert isinstance(caught.value.cause, ExportVerificationError)
    assert (destination / "attacker").is_file()
    moved = tmp_path / moved_name
    assert _verify_export_directory(moved, expected_plan=plan) == (
        caught.value.publication.receipt,
        caught.value.publication.verification,
    )


def test_visible_tree_tamper_fails_independent_verification(tmp_path: Path):
    _, plan, destination, _ = _publish(tmp_path)
    (destination / EXPORT_RECEIPT_PATH).write_bytes(b"{}")

    with pytest.raises(ExportVerificationError):
        _verify_export_directory(destination, expected_plan=plan)


def test_source_is_reverified_before_any_destination_write(tmp_path: Path):
    bundle = _materialize_bundle(tmp_path)
    service = _ConformanceExportService()
    plan = _create_plan(service, bundle)
    source = inspect_finished_bundle(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    assert source.verification.bundle_id == plan.source_bundle_id
    (bundle / "data" / "train.jsonl").write_bytes(b"tampered\n")

    with pytest.raises(BundleVerificationError):
        service.publish(
            plan,
            bundle,
            tmp_path / "not-written",
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        )

    assert not (tmp_path / "not-written").exists()
    assert not list(tmp_path.glob(".veriformis-export-*"))
