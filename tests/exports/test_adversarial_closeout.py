"""Phase 4.9 consolidated adversarial export-foundation closeout harness.

The earlier Phase 4 modules pin each model, service, renderer, publication,
and adapter boundary separately.  This harness deliberately exercises the
cross-boundary acceptance matrix through one private, test-injected exact
export implementation.  It does not install or advertise a product exporter.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from veriformis.bundle import (
    BundleVerificationError,
    VerifiedFinishedBundle,
    inspect_finished_bundle,
)
from veriformis.datasets import (
    ProductRow,
    RowProvenance,
    RowSet,
    row_provenance_from_json_bytes,
)
from veriformis.errors import ExportVerificationError
from veriformis.exports import (
    DEFAULT_EXPORT_SERVICE,
    EXPORT_SURFACE_REQUEST_SCHEMA,
    ExportConsumerProfile,
    ExportContainerProfile,
    ExportDependencyBinding,
    ExportDryRunRequest,
    ExportExecuteRequest,
    ExportFilePlan,
    ExportOperationCancelled,
    ExportPartialPublicationError,
    ExportPlan,
    ExportProfileDescriptor,
    ExportPublicationOutcome,
    ExportReceipt,
    ExportService,
    ExportVerification,
    ExportVerifyRequest,
    export_error_response,
    export_execution_response,
)
from veriformis.exports import _publication as publication_module
from veriformis.exports import service as service_module
from veriformis.identity import derive_id, lossless_json_bytes, sha256_digest


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
CONTAINER_ID = "phase4-closeout-directory"
CONTAINER_VERSION = 1
CONSUMER_ID = "phase4-closeout-consumer"
CONSUMER_VERSION = 1


def _materialize_bundle(root: Path) -> Path:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bundle = root / "source.vfbundle"
    for relative_path, encoded in sorted(fixture["files_base64"].items()):
        data = base64.b64decode(encoded, validate=True)
        assert sha256_digest(data) == fixture["file_sha256"][relative_path]
        target = bundle.joinpath(*relative_path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return bundle


def _file_plan(
    path: str,
    data: bytes,
    *,
    role: str = "sidecar",
    membership_scope: str = "none",
    record_count: int | None = None,
) -> ExportFilePlan:
    return ExportFilePlan.create(
        path=path,
        role=role,
        media_type=("application/jsonl" if path.endswith(".jsonl") else "application/json"),
        membership_scope=membership_scope,
        record_count=record_count,
        semantic_content_sha256=None,
        expected_sha256=sha256_digest(data),
        expected_byte_size=len(data),
    )


def _exact_files(row_set: RowSet) -> tuple[tuple[str, bytes], ...]:
    return (
        (
            "data/evaluation.jsonl",
            b"".join(
                lossless_json_bytes(row.payload) + b"\n"
                for row in row_set.evaluation_rows
            ),
        ),
        (
            "data/train.jsonl",
            b"".join(
                lossless_json_bytes(row.payload) + b"\n"
                for row in row_set.train_rows
            ),
        ),
        (
            "metadata/schema.json",
            lossless_json_bytes({"row_schema": row_set.row_schema}),
        ),
    )


def _file_plans(row_set: RowSet) -> tuple[ExportFilePlan, ...]:
    by_path = dict(_exact_files(row_set))
    return (
        _file_plan(
            "data/evaluation.jsonl",
            by_path["data/evaluation.jsonl"],
            role="evaluation-partition",
            membership_scope="evaluation",
            record_count=len(row_set.evaluation_rows),
        ),
        _file_plan(
            "data/train.jsonl",
            by_path["data/train.jsonl"],
            role="training-partition",
            membership_scope="train",
            record_count=len(row_set.train_rows),
        ),
        _file_plan("metadata/schema.json", by_path["metadata/schema.json"]),
    )


class _ExactRuntime:
    """One bounded conformance renderer available only by test injection."""

    def __init__(
        self,
        *,
        files: tuple[tuple[str, bytes], ...] | None = None,
    ) -> None:
        self.files = files
        self.planner_calls = 0
        self.renderer_calls = 0

    def plan_files(self, descriptor, row_set):
        self.planner_calls += 1
        assert descriptor.selector == (
            CONTAINER_ID,
            CONTAINER_VERSION,
            CONSUMER_ID,
            CONSUMER_VERSION,
        )
        assert len(row_set.train_rows) == 1
        assert len(row_set.evaluation_rows) == 2
        return _file_plans(row_set)

    def render(self, plan, row_set):
        self.renderer_calls += 1
        assert isinstance(plan, ExportPlan)
        return service_module._RenderedDerivative(
            files=self.files if self.files is not None else _exact_files(row_set),
            train_rows=row_set.train_rows,
            evaluation_rows=row_set.evaluation_rows,
            provenance=row_set.provenance,
        )


def _descriptor() -> ExportProfileDescriptor:
    return ExportProfileDescriptor(
        container_profile=ExportContainerProfile.create(
            container_id=CONTAINER_ID,
            container_version=CONTAINER_VERSION,
            determinism_claim="portable_exact_bytes",
        ),
        consumer_profile=ExportConsumerProfile.create(
            consumer_id=CONSUMER_ID,
            profile_version=CONSUMER_VERSION,
            accepted_row_schemas=("text",),
        ),
        dependencies=(
            ExportDependencyBinding.create(
                dependency_name="phase4-closeout-renderer",
                dependency_version="1.0.0",
                dependency_role="renderer",
            ),
        ),
        supported_row_schemas=("text",),
    )


def _service(
    runtime: _ExactRuntime | None = None,
) -> tuple[ExportService, _ExactRuntime]:
    selected = runtime or _ExactRuntime()
    implementation = service_module._ExportImplementation(
        descriptor=_descriptor(),
        file_planner=selected.plan_files,
        renderer=selected.render,
        semantic_replayer=None,
    )
    return ExportService(_implementations=(implementation,)), selected


def _selection(bundle: Path) -> dict[str, Any]:
    return {
        "schema_version": EXPORT_SURFACE_REQUEST_SCHEMA,
        "bundle": str(bundle),
        "container_id": CONTAINER_ID,
        "container_version": CONTAINER_VERSION,
        "consumer_id": CONSUMER_ID,
        "consumer_profile_version": CONSUMER_VERSION,
        "source_trust_policy": "require_external_digest",
        "expected_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "overwrite_policy": "refuse",
    }


def _dry_run_request(bundle: Path, **updates: Any) -> ExportDryRunRequest:
    values = {**_selection(bundle), "operation": "dry_run", **updates}
    return ExportDryRunRequest(**values)


def _execute_request(
    bundle: Path,
    destination: Path,
    plan: ExportPlan,
) -> ExportExecuteRequest:
    return ExportExecuteRequest(
        operation="execute",
        destination_root=str(destination),
        expected_export_plan_id=plan.export_plan_id,
        **_selection(bundle),
    )


def _verify_request(
    bundle: Path,
    destination: Path,
    plan: ExportPlan,
) -> ExportVerifyRequest:
    return ExportVerifyRequest(
        operation="verify",
        destination_root=str(destination),
        expected_export_plan_id=plan.export_plan_id,
        **_selection(bundle),
    )


@dataclass(frozen=True, slots=True)
class _Published:
    bundle: Path
    service: ExportService
    runtime: _ExactRuntime
    plan: ExportPlan
    destination: Path
    publication: ExportPublicationOutcome


def _publish(root: Path, *, destination_name: str = "export") -> _Published:
    bundle = _materialize_bundle(root)
    service, runtime = _service()
    plan = service.dry_run_export(_dry_run_request(bundle))
    destination = root / destination_name
    publication = service.execute_export(
        _execute_request(bundle, destination, plan)
    )
    return _Published(
        bundle=bundle,
        service=service,
        runtime=runtime,
        plan=plan,
        destination=destination,
        publication=publication,
    )


def _reidentified_provenance(
    provenance: RowProvenance,
    **updates: object,
) -> RowProvenance:
    body = provenance.model_dump(mode="json", exclude={"provenance_id"})
    body.update(updates)
    return row_provenance_from_json_bytes(
        lossless_json_bytes(
            {"provenance_id": derive_id("prv", body), **body}
        )
    )


def _plan_with_added_files(
    plan: ExportPlan,
    additions: tuple[ExportFilePlan, ...],
) -> ExportPlan:
    body = plan.model_dump(mode="json", exclude={"export_plan_id"})
    body["file_plans"] = sorted(
        (
            *(item.model_dump(mode="json") for item in plan.file_plans),
            *(item.model_dump(mode="json") for item in additions),
        ),
        key=lambda item: item["path"],
    )
    return ExportPlan.from_json_bytes(
        lossless_json_bytes(
            {"export_plan_id": derive_id("export-plan", body), **body}
        )
    )


def test_closeout_contracts_are_canonical_versioned_and_identity_bound(
    tmp_path: Path,
) -> None:
    published = _publish(tmp_path)
    artifacts = (
        (
            published.plan,
            ExportPlan,
            "export_plan_id",
            "export-plan",
            "veriformis.export-plan/v1",
        ),
        (
            published.publication.receipt,
            ExportReceipt,
            "export_receipt_id",
            "export-receipt",
            "veriformis.export-receipt/v1",
        ),
        (
            published.publication.verification,
            ExportVerification,
            "export_verification_id",
            "export-verification",
            "veriformis.export-verification/v1",
        ),
    )

    for artifact, model_type, identity_field, identity_kind, schema in artifacts:
        canonical = artifact.canonical_bytes()
        value = artifact.model_dump(mode="json")
        identity_body = {key: item for key, item in value.items() if key != identity_field}
        assert canonical == lossless_json_bytes(value)
        assert model_type.from_json_bytes(canonical) == artifact
        assert value["schema_version"] == schema
        assert value[identity_field] == derive_id(identity_kind, identity_body)

        with pytest.raises(ExportVerificationError, match="not canonical"):
            model_type.from_json_bytes(canonical + b"\n")

        unsupported = dict(value)
        unsupported["schema_version"] = schema.removesuffix("v1") + "v999"
        unsupported_body = {
            key: item for key, item in unsupported.items() if key != identity_field
        }
        unsupported[identity_field] = derive_id(identity_kind, unsupported_body)
        with pytest.raises(ExportVerificationError):
            model_type.from_json_bytes(lossless_json_bytes(unsupported))

        forged = dict(value)
        forged[identity_field] = derive_id(
            identity_kind,
            {"phase4_closeout_forgery": identity_field},
        )
        with pytest.raises(ExportVerificationError, match="identity mismatch"):
            model_type.from_json_bytes(lossless_json_bytes(forged))


def test_closeout_conformance_injection_never_changes_production_discovery() -> None:
    injected, _ = _service()

    assert len(injected.discover_exports().profiles) == 1
    expected = [
        ("constrained-csv", 1, None, None),
        ("json", 1, None, None),
        ("parquet", 1, None, None),
        ("split-jsonl-directory", 1, None, None),
        ("split-jsonl-directory", 1, "mlx-lm", 1),
        ("split-jsonl-directory", 1, "trl", 1),
    ]
    assert [
        item.selector for item in DEFAULT_EXPORT_SERVICE.discover_exports().profiles
    ] == expected
    assert [item.selector for item in ExportService().discover_exports().profiles] == expected


@pytest.mark.parametrize(
    "mutation",
    ("tamper", "missing-file", "unexpected-file", "unexpected-directory"),
)
def test_closeout_verification_rejects_tamper_and_tree_mutations(
    tmp_path: Path,
    mutation: str,
) -> None:
    published = _publish(tmp_path)
    if mutation == "tamper":
        (published.destination / "data/train.jsonl").write_bytes(b"tampered\n")
    elif mutation == "missing-file":
        (published.destination / "data/train.jsonl").unlink()
    elif mutation == "unexpected-file":
        (published.destination / "unexpected.bin").write_bytes(b"unexpected")
    else:
        (published.destination / "unexpected-directory").mkdir()

    with pytest.raises(ExportVerificationError):
        published.service.verify_export(
            _verify_request(
                published.bundle,
                published.destination,
                published.plan,
            )
        )


@pytest.mark.parametrize(
    ("kind", "message"),
    (
        ("symlink", "symlink"),
        ("hardlink", "hard-linked"),
        ("fifo", "special file"),
    ),
)
def test_closeout_rejects_symlink_hardlink_and_non_regular_entries(
    tmp_path: Path,
    kind: str,
    message: str,
) -> None:
    published = _publish(tmp_path)
    target = published.destination / "data/train.jsonl"
    if kind == "symlink":
        target.unlink()
        target.symlink_to(published.bundle / "data/train.jsonl")
    elif kind == "hardlink":
        os.link(target, tmp_path / "outside-hardlink")
    else:
        target.unlink()
        os.mkfifo(target)

    with pytest.raises(ExportVerificationError, match=message):
        published.service.verify_export(
            _verify_request(
                published.bundle,
                published.destination,
                published.plan,
            )
        )


@pytest.mark.parametrize(
    "path",
    (
        "../escape.json",
        "/absolute.json",
        "data/../escape.json",
        "data\\windows.json",
        "metadata/cafe\N{COMBINING ACUTE ACCENT}.json",
        "metadata/\N{FULLWIDTH SOLIDUS}escape.json",
    ),
)
def test_closeout_rejects_traversal_and_noncanonical_unicode_paths(
    path: str,
) -> None:
    with pytest.raises(ValueError):
        _file_plan(path, b"{}")


@pytest.mark.parametrize(
    ("additions", "message"),
    (
        (
            (_file_plan("DATA/train.jsonl", b"alias"),),
            "collide by case or Unicode",
        ),
        (
            (
                _file_plan("metadata/K.json", b"a"),
                _file_plan("metadata/\N{FULLWIDTH LATIN CAPITAL LETTER K}.json", b"b"),
            ),
            "collide by case or Unicode",
        ),
        ((_file_plan("data", b"ancestor"),), "both a file and a directory"),
    ),
)
def test_closeout_rejects_case_unicode_aliases_and_ancestor_collisions(
    tmp_path: Path,
    additions: tuple[ExportFilePlan, ...],
    message: str,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service, _ = _service()
    plan = service.dry_run_export(_dry_run_request(bundle))

    with pytest.raises(ExportVerificationError, match=message):
        _plan_with_added_files(plan, additions)


@pytest.mark.parametrize("alias_kind", ("case", "unicode-casefold"))
def test_closeout_rejects_actual_on_disk_portable_path_aliases(
    tmp_path: Path,
    alias_kind: str,
) -> None:
    published = _publish(tmp_path)
    if alias_kind == "case":
        alias_directory = published.destination / "DATA"
        try:
            alias_directory.mkdir()
        except FileExistsError:
            # On a case-insensitive host the filesystem itself prevents two
            # distinct entries.  Prove that this spelling resolves to the
            # existing directory and leave the verified tree untouched.
            assert alias_directory.samefile(published.destination / "data")
            return
        (alias_directory / "alias.json").write_bytes(b"{}")
    else:
        metadata = published.destination / "metadata"
        (metadata / "K.json").write_bytes(b"{}")
        (metadata / "\N{FULLWIDTH LATIN CAPITAL LETTER K}.json").write_bytes(b"{}")

    with pytest.raises(ExportVerificationError, match="collide by case or Unicode"):
        published.service.verify_export(
            _verify_request(
                published.bundle,
                published.destination,
                published.plan,
            )
        )


def test_closeout_renderer_traversal_fails_before_any_destination_write(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    row_set = inspect_finished_bundle(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    ).row_set
    files = tuple(
        ("../escaped", data) if path == "data/train.jsonl" else (path, data)
        for path, data in _exact_files(row_set)
    )
    service, runtime = _service(_ExactRuntime(files=files))
    plan = service.dry_run_export(_dry_run_request(bundle))
    destination = tmp_path / "must-not-exist"

    with pytest.raises(ExportVerificationError, match="unsafe export path"):
        service.execute_export(_execute_request(bundle, destination, plan))

    assert runtime.renderer_calls == 1
    assert not destination.exists()
    assert not (tmp_path / "escaped").exists()
    assert not list(tmp_path.glob(".veriformis-export-*"))


def test_closeout_source_digest_mismatch_and_source_tamper_fail_before_write(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service, runtime = _service()
    with pytest.raises(BundleVerificationError, match="expected external digest"):
        service.dry_run_export(
            _dry_run_request(bundle, expected_manifest_sha256="0" * 64)
        )
    assert runtime.planner_calls == runtime.renderer_calls == 0

    plan = service.dry_run_export(_dry_run_request(bundle))
    (bundle / "data/train.jsonl").write_bytes(b"tampered source\n")
    destination = tmp_path / "must-not-exist"
    with pytest.raises(BundleVerificationError):
        service.execute_export(_execute_request(bundle, destination, plan))

    assert runtime.renderer_calls == 0
    assert not destination.exists()
    assert not list(tmp_path.glob(".veriformis-export-*"))


def _mutated_membership(
    mutation: str,
    source: VerifiedFinishedBundle,
) -> tuple[
    tuple[ProductRow, ...],
    tuple[ProductRow, ...],
    tuple[RowProvenance, ...],
]:
    train_rows = source.row_set.train_rows
    evaluation_rows = source.row_set.evaluation_rows
    provenance = source.row_set.provenance
    train_count = len(train_rows)

    if mutation == "omission":
        return train_rows, evaluation_rows[:-1], provenance[:-1]
    if mutation == "addition":
        existing_ids = {row.record_id for row in (*train_rows, *evaluation_rows)}
        final_id = max(row.record_id for row in evaluation_rows)
        added_record_id = next(
            candidate
            for index in range(10_000)
            if (candidate := derive_id("rec", {"phase4_closeout_addition": index}))
            not in existing_ids
            and candidate > final_id
        )
        added_row = ProductRow.create(
            record_id=added_record_id,
            row_schema=source.row_set.row_schema,
            payload={"text": "coherently added adversarial target"},
        )
        added_provenance = _reidentified_provenance(
            provenance[-1],
            ordinal=len(evaluation_rows),
            row_id=added_row.row_id,
            payload_sha256=added_row.payload_sha256,
            record_id=added_record_id,
            assignment_id=derive_id(
                "asg", {"phase4_closeout_addition": added_record_id}
            ),
        )
        return (
            train_rows,
            (*evaluation_rows, added_row),
            (*provenance, added_provenance),
        )
    if mutation == "duplication":
        return (
            train_rows,
            (*evaluation_rows, evaluation_rows[-1]),
            (*provenance, provenance[-1]),
        )
    if mutation == "reorder":
        reordered_rows = tuple(reversed(evaluation_rows))
        reordered_provenance = tuple(
            _reidentified_provenance(item, ordinal=index)
            for index, item in enumerate(reversed(provenance[train_count:]))
        )
        return (
            train_rows,
            reordered_rows,
            (*provenance[:train_count], *reordered_provenance),
        )
    if mutation == "ordinal":
        changed = _reidentified_provenance(
            provenance[-1],
            ordinal=provenance[-1].ordinal + 1,
        )
        return train_rows, evaluation_rows, (*provenance[:-1], changed)
    if mutation == "target":
        original = evaluation_rows[0]
        altered = ProductRow.create(
            record_id=original.record_id,
            row_schema=original.row_schema,
            payload={"text": f"{original.payload['text']} -- altered"},
        )
        altered_provenance = _reidentified_provenance(
            provenance[train_count],
            row_id=altered.row_id,
            payload_sha256=altered.payload_sha256,
        )
        return (
            train_rows,
            (altered, *evaluation_rows[1:]),
            (
                *provenance[:train_count],
                altered_provenance,
                *provenance[train_count + 1 :],
            ),
        )
    if mutation in {"assignment", "leakage-group"}:
        field = (
            "assignment_id" if mutation == "assignment" else "leakage_group_id"
        )
        kind = "asg" if mutation == "assignment" else "lkg"
        changed = _reidentified_provenance(
            provenance[-1],
            **{field: derive_id(kind, {"phase4_closeout": mutation})},
        )
        return train_rows, evaluation_rows, (*provenance[:-1], changed)
    if mutation == "partition":
        moved = evaluation_rows[0]
        moved_train = tuple(sorted((*train_rows, moved), key=lambda row: row.record_id))
        remaining_evaluation = evaluation_rows[1:]
        by_record_id = {item.record_id: item for item in provenance}
        repartitioned = tuple(
            _reidentified_provenance(
                by_record_id[row.record_id],
                partition=partition,
                ordinal=ordinal,
            )
            for partition, rows in (
                ("train", moved_train),
                ("evaluation", remaining_evaluation),
            )
            for ordinal, row in enumerate(rows)
        )
        return moved_train, remaining_evaluation, repartitioned
    if mutation == "resplit":
        replacement = derive_id("spt", {"phase4_closeout": "resplit"})
        return (
            train_rows,
            evaluation_rows,
            tuple(
                _reidentified_provenance(item, split_result_id=replacement)
                for item in provenance
            ),
        )
    raise AssertionError(f"unhandled membership mutation {mutation!r}")


@pytest.mark.parametrize(
    "mutation",
    (
        "omission",
        "addition",
        "duplication",
        "reorder",
        "ordinal",
        "target",
        "assignment",
        "leakage-group",
        "partition",
        "resplit",
    ),
)
def test_closeout_rejects_every_complete_membership_mutation(
    tmp_path: Path,
    mutation: str,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service, _ = _service()
    plan = service.dry_run_export(_dry_run_request(bundle))
    source = inspect_finished_bundle(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    train_rows, evaluation_rows, provenance = _mutated_membership(mutation, source)

    with pytest.raises(ExportVerificationError) as caught:
        service.validate_derivative_membership(
            plan,
            candidate_train_rows=train_rows,
            candidate_evaluation_rows=evaluation_rows,
            candidate_provenance=provenance,
        )

    assert caught.value.code == "export-verification-invalid"


def test_closeout_destination_winner_survives_publication_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service, _ = _service()
    plan = service.dry_run_export(_dry_run_request(bundle))
    destination = tmp_path / "race-winner"
    original = publication_module._rename_no_replace

    def install_winner(staging, **kwargs):
        os.mkdir(
            staging.destination.target_name,
            dir_fd=staging.destination.parent_descriptor,
        )
        return original(staging, **kwargs)

    monkeypatch.setattr(publication_module, "_rename_no_replace", install_winner)

    with pytest.raises(FileExistsError):
        service.execute_export(_execute_request(bundle, destination, plan))

    assert destination.is_dir()
    assert not any(destination.iterdir())
    assert not list(tmp_path.glob(".veriformis-export-*"))


def test_closeout_final_previsibility_cancellation_has_no_visible_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service, _ = _service()
    plan = service.dry_run_export(_dry_run_request(bundle))
    destination = tmp_path / "cancelled"
    original = publication_module._rename_no_replace

    def cancel_at_final_checkpoint(staging, **kwargs):
        def stop() -> None:
            raise ExportOperationCancelled("cancelled immediately before visibility")

        return original(
            staging,
            expected_tree=kwargs["expected_tree"],
            cancellation_check=stop,
        )

    monkeypatch.setattr(
        publication_module,
        "_rename_no_replace",
        cancel_at_final_checkpoint,
    )

    with pytest.raises(ExportOperationCancelled) as caught:
        service.execute_export(
            _execute_request(bundle, destination, plan),
            cancellation_check=lambda: None,
        )

    response = export_error_response("execute", caught.value)
    assert response["status"] == "cancelled"
    assert response["result"] is None
    assert not destination.exists()
    assert not list(tmp_path.glob(".veriformis-export-*"))


def test_closeout_visibility_wins_a_simultaneous_cancellation_signal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service, _ = _service()
    plan = service.dry_run_export(_dry_run_request(bundle))
    destination = tmp_path / "visible"
    original = publication_module._rename_no_replace
    cancellation_armed = False

    def rename_then_arm(staging, **kwargs):
        nonlocal cancellation_armed
        result = original(staging, **kwargs)
        cancellation_armed = True
        return result

    def cancel_if_visible() -> None:
        if cancellation_armed:
            raise ExportOperationCancelled("late cancellation")

    monkeypatch.setattr(publication_module, "_rename_no_replace", rename_then_arm)
    publication = service.execute_export(
        _execute_request(bundle, destination, plan),
        cancellation_check=cancel_if_visible,
    )

    assert cancellation_armed is True
    assert export_execution_response(publication)["status"] == "ok"
    verified = service.verify_export(_verify_request(bundle, destination, plan))
    assert verified.receipt == publication.receipt
    assert verified.verification == publication.verification


def test_closeout_post_rename_failure_reports_verifiable_visible_partial(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service, _ = _service()
    plan = service.dry_run_export(_dry_run_request(bundle))
    destination = tmp_path / "visible-partial"
    original = publication_module._rename_no_replace

    def fail_after_rename(staging, **kwargs):
        original(staging, **kwargs)
        raise OSError("phase4 closeout post-rename sentinel")

    monkeypatch.setattr(publication_module, "_rename_no_replace", fail_after_rename)

    with pytest.raises(ExportPartialPublicationError) as caught:
        service.execute_export(_execute_request(bundle, destination, plan))

    response = export_error_response("execute", caught.value)
    assert response["status"] == "visible_partial"
    assert response["error"]["code"] == "export-partial-publication"
    assert response["result"]["destination_root"] == str(
        Path(os.path.abspath(destination))
    )
    assert response["result"]["plan"]["export_plan_id"] == plan.export_plan_id
    assert response["result"]["receipt"]["export_receipt_id"] == (
        caught.value.publication.receipt.export_receipt_id
    )
    assert response["result"]["verification"]["export_verification_id"] == (
        caught.value.publication.verification.export_verification_id
    )
    verified = service.verify_export(_verify_request(bundle, destination, plan))
    assert verified.receipt == caught.value.publication.receipt
    assert verified.verification == caught.value.publication.verification
