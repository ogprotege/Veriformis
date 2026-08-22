"""Phase 4.8 public-service behavior over a private conformance catalog."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import pytest

from veriformis.bundle import BundleVerificationError
from veriformis.errors import ExportContractError, ExportVerificationError
from veriformis.exports import (
    DEFAULT_EXPORT_SERVICE,
    ExportConsumerProfile,
    ExportContainerProfile,
    ExportDependencyBinding,
    ExportFilePlan,
    ExportPlan,
    ExportService,
)
from veriformis.exports import api as api_module
from veriformis.exports import service as service_module
from veriformis.exports.api import (
    EXPORT_DISCOVERY_SCHEMA,
    EXPORT_SURFACE_REQUEST_SCHEMA,
    EXPORT_SURFACE_REQUEST_SCHEMA_V2,
    EXPORT_SURFACE_RESPONSE_SCHEMA,
    ExportDryRunRequest,
    ExportDryRunRequestV2,
    ExportExecuteRequest,
    ExportExecuteRequestV2,
    ExportInspectRequest,
    ExportProfileDescriptor,
    ExportVerifyRequest,
    ExportVerifyRequestV2,
    export_discovery_response,
    export_dry_run_response,
    export_execution_response,
    export_inspection_response,
    export_request_from_json_bytes,
    export_response_json,
    export_verify_response,
)
from veriformis.identity import derive_id, lossless_json_bytes, sha256_digest

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "regressions"
    / "fixtures"
    / "phase3"
    / "pre-taxonomy-full-text.vfbundle.json"
)
SURFACE_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "regressions"
    / "fixtures"
    / "phase4"
    / "export-surfaces.json"
)
EXPECTED_MANIFEST_SHA256 = (
    "2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733"
)
CONTAINER_ID = "phase4-conformance-directory"
CONTAINER_VERSION = 7
CONSUMER_ID = "phase4-conformance-consumer"
CONSUMER_VERSION = 3
EXACT_FILES = (
    ("data/evaluation.jsonl", b'{"text":"evaluation-a"}\n{"text":"evaluation-b"}\n'),
    ("data/train.jsonl", b'{"text":"train"}\n'),
    ("metadata/schema.json", b'{"row_schema":"text"}'),
)
FROZEN_SURFACE = json.loads(SURFACE_FIXTURE.read_text(encoding="utf-8"))


def _materialize_bundle(tmp_path: Path) -> Path:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bundle = tmp_path / "source.vfbundle"
    for relative_path, encoded in sorted(fixture["files_base64"].items()):
        data = base64.b64decode(encoded, validate=True)
        assert sha256_digest(data) == fixture["file_sha256"][relative_path]
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


def _deep_export_tree(tmp_path: Path) -> Path:
    root = tmp_path / "deep-export"
    root.mkdir()
    cursor = root
    for index in range(130):
        cursor = cursor / f"d{index}"
        cursor.mkdir()
    return root


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


class _ExactRuntime:
    def __init__(self) -> None:
        self.planner_calls = 0
        self.render_calls = 0

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
        return _file_plans()

    def render(self, plan, row_set):
        self.render_calls += 1
        assert isinstance(plan, ExportPlan)
        return service_module._RenderedDerivative(
            files=EXACT_FILES,
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
                dependency_name="phase4-conformance-renderer",
                dependency_version="1.0.0",
                dependency_role="renderer",
            ),
        ),
        supported_row_schemas=("text",),
    )


def _service(
    runtime: _ExactRuntime | None = None,
) -> tuple[ExportService, _ExactRuntime]:
    chosen = runtime or _ExactRuntime()
    implementation = service_module._ExportImplementation(
        descriptor=_descriptor(),
        file_planner=chosen.plan_files,
        renderer=chosen.render,
        semantic_replayer=None,
    )
    return ExportService(_implementations=(implementation,)), chosen


def _selection(bundle: Path) -> dict[str, object]:
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


def _dry_run_request(bundle: Path) -> ExportDryRunRequest:
    return ExportDryRunRequest(operation="dry_run", **_selection(bundle))


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
    **updates: object,
) -> ExportVerifyRequest:
    values = {
        **_selection(bundle),
        "operation": "verify",
        "destination_root": str(destination),
        "expected_export_plan_id": plan.export_plan_id,
        **updates,
    }
    return ExportVerifyRequest(**values)


def test_production_export_discovery_is_truthfully_shipped_and_fresh() -> None:
    first = DEFAULT_EXPORT_SERVICE.discover_exports()
    second = ExportService().discover_exports()

    assert first is not second
    assert first.to_dict() == second.to_dict()
    assert first.schema_version == EXPORT_DISCOVERY_SCHEMA
    expected_production = [
        ("constrained-csv", 1, None, None),
        ("json", 1, None, None),
        ("split-jsonl-directory", 1, None, None),
    ]
    assert [item.selector for item in first.profiles] == expected_production
    expected_row_schemas = {
        "constrained-csv": (
            "instruction_output",
            "prompt_completion",
            "text",
        ),
        "json": (
            "instruction_output",
            "messages",
            "prompt_completion",
            "text",
        ),
        "split-jsonl-directory": (
            "instruction_output",
            "messages",
            "prompt_completion",
            "text",
        ),
    }
    for profile in first.profiles:
        assert (
            profile.supported_row_schemas
            == expected_row_schemas[profile.container_profile.container_id]
        )
        assert profile.overwrite_policies == ("refuse",)
    assert export_discovery_response(first) == {
        "error": None,
        "operation": "discover",
        "result": first.to_dict(),
        "schema_version": EXPORT_SURFACE_RESPONSE_SCHEMA,
        "status": "ok",
    }

    injected, _ = _service()
    assert [item.selector for item in injected.discover_exports().profiles] == [
        (CONTAINER_ID, CONTAINER_VERSION, CONSUMER_ID, CONSUMER_VERSION)
    ]
    assert [
        item.selector for item in DEFAULT_EXPORT_SERVICE.discover_exports().profiles
    ] == expected_production

    consumerless = ExportProfileDescriptor(
        container_profile=_descriptor().container_profile,
        consumer_profile=None,
        dependencies=_descriptor().dependencies,
        supported_row_schemas=("text",),
    )
    mixed = ExportService(
        _implementations=(
            service_module._ExportImplementation(
                descriptor=_descriptor(),
                file_planner=lambda _descriptor, _row_set: (),
                renderer=lambda _plan, _row_set: None,
                semantic_replayer=None,
            ),
            service_module._ExportImplementation(
                descriptor=consumerless,
                file_planner=lambda _descriptor, _row_set: (),
                renderer=lambda _plan, _row_set: None,
                semantic_replayer=None,
            ),
        )
    )
    assert [item.selector for item in mixed.discover_exports().profiles] == [
        (CONTAINER_ID, CONTAINER_VERSION, None, None),
        (CONTAINER_ID, CONTAINER_VERSION, CONSUMER_ID, CONSUMER_VERSION),
    ]


def test_surface_requests_are_canonical_strict_and_closed(tmp_path: Path) -> None:
    request = _dry_run_request(tmp_path / "bundle")
    canonical = request.canonical_bytes()

    assert (
        export_request_from_json_bytes(
            canonical,
            expected_operation="dry_run",
        )
        == request
    )
    assert {
        "destination_root",
        "expected_export_plan_id",
        "file_plans",
        "membership",
        "renderer",
        "replayer",
    }.isdisjoint(ExportDryRunRequest.model_fields)

    payload = request.model_dump(mode="json")
    malformed: list[bytes] = []
    for key, value in (
        ("unexpected", "field"),
        ("overwrite_policy", "replace"),
        ("container_version", True),
    ):
        changed = dict(payload)
        changed[key] = value
        malformed.append(lossless_json_bytes(changed))
    missing_digest = dict(payload)
    missing_digest["expected_manifest_sha256"] = None
    malformed.append(lossless_json_bytes(missing_digest))
    orphan_consumer_version = dict(payload)
    orphan_consumer_version["consumer_id"] = None
    malformed.append(lossless_json_bytes(orphan_consumer_version))
    malformed.append(canonical + b"\n")
    malformed.append(b" " * (1024 * 1024 + 1))

    for candidate in malformed:
        with pytest.raises(ExportContractError):
            export_request_from_json_bytes(
                candidate,
                expected_operation="dry_run",
            )
    with pytest.raises(ExportContractError, match="operation must be 'execute'"):
        export_request_from_json_bytes(
            canonical,
            expected_operation="execute",
        )


def test_v2_surface_requests_add_only_strict_container_options(
    tmp_path: Path,
) -> None:
    selection = {
        **_selection(tmp_path / "bundle"),
        "schema_version": EXPORT_SURFACE_REQUEST_SCHEMA_V2,
        "container_options": {
            "evaluation_partition_name": "dev",
            "include_provenance": True,
            "schema_version": "veriformis.split-jsonl-options/v1",
            "train_partition_name": "learn",
        },
    }
    requests = (
        ExportDryRunRequestV2(operation="dry_run", **selection),
        ExportExecuteRequestV2(
            operation="execute",
            destination_root=str(tmp_path / "out"),
            expected_export_plan_id="export-plan-v1-" + "0" * 64,
            **selection,
        ),
        ExportVerifyRequestV2(
            operation="verify",
            destination_root=str(tmp_path / "out"),
            expected_export_plan_id="export-plan-v1-" + "0" * 64,
            **selection,
        ),
    )

    for request in requests:
        loaded = export_request_from_json_bytes(
            request.canonical_bytes(),
            expected_operation=request.operation,
        )
        assert loaded == request
        assert type(loaded) is type(request)

    assert "container_options" not in ExportDryRunRequest.model_fields
    payload = requests[0].model_dump(mode="json")
    payload["container_options"] = {"nested": {"not": "flat"}}
    with pytest.raises(ExportContractError):
        export_request_from_json_bytes(
            lossless_json_bytes(payload),
            expected_operation="dry_run",
        )
    payload = requests[0].model_dump(mode="json")
    payload["schema_version"] = EXPORT_SURFACE_REQUEST_SCHEMA
    with pytest.raises(ExportContractError):
        export_request_from_json_bytes(
            lossless_json_bytes(payload),
            expected_operation="dry_run",
        )


def test_surface_response_and_executable_plan_budgets_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oversized = {
        "error": None,
        "operation": "discover",
        "result": {"value": "x" * (1024 * 1024)},
        "schema_version": EXPORT_SURFACE_RESPONSE_SCHEMA,
        "status": "ok",
    }
    with pytest.raises(ExportContractError, match="1 MiB"):
        export_response_json(oversized)

    bundle = _materialize_bundle(tmp_path)
    service, runtime = _service()
    monkeypatch.setattr(api_module, "_MAX_EXECUTABLE_PLAN_RESPONSE_BYTES", 1)
    with pytest.raises(ExportContractError, match="response budget"):
        service.dry_run_export(_dry_run_request(bundle))
    assert runtime.planner_calls == 1
    assert runtime.render_calls == 0

    class DeepPlanRuntime(_ExactRuntime):
        def plan_files(self, descriptor, row_set):
            plans = list(super().plan_files(descriptor, row_set))
            original = plans[1]
            plans[1] = ExportFilePlan.create(
                path="/".join((*("d" for _ in range(129)), "train.jsonl")),
                role=original.role,
                media_type=original.media_type,
                membership_scope=original.membership_scope,
                record_count=original.record_count,
                semantic_content_sha256=original.semantic_content_sha256,
                expected_sha256=original.expected_sha256,
                expected_byte_size=original.expected_byte_size,
            )
            return tuple(sorted(plans, key=lambda item: item.path))

    deep_service, deep_runtime = _service(DeepPlanRuntime())
    with pytest.raises(ExportContractError, match="directory depth"):
        deep_service.dry_run_export(_dry_run_request(bundle))
    assert deep_runtime.render_calls == 0


def test_error_response_sanitizes_unpaired_unicode() -> None:
    response = api_module.export_error_response(
        "dry_run",
        ValueError("invalid \ud800 detail"),
    )

    assert "\ud800" not in response["error"]["message"]
    assert "?" in response["error"]["message"]
    assert json.loads(export_response_json(response)) == response


def test_visible_partial_error_response_does_not_reload_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service, _ = _service()
    plan = service.dry_run_export(_dry_run_request(bundle))
    destination = tmp_path / "published"
    publication = service.execute_export(
        _execute_request(bundle, destination, plan)
    )

    def reject_reload(cls, data):
        raise ExportContractError(f"{cls.__name__} strict loader unavailable")

    for model_type in (
        type(publication.receipt.export_plan),
        type(publication.receipt),
        type(publication.verification),
    ):
        monkeypatch.setattr(
            model_type,
            "from_json_bytes",
            classmethod(reject_reload),
        )

    response = api_module.export_error_response(
        "execute",
        api_module.ExportPartialPublicationError(
            publication,
            OSError("post-publication bookkeeping failed"),
        ),
    )

    assert response["status"] == "visible_partial"
    assert response["result"]["destination_root"] == str(
        Path(os.path.abspath(destination))
    )
    assert response["result"]["plan"]["export_plan_id"] == plan.export_plan_id
    assert response["result"]["receipt"]["export_receipt_id"] == (
        publication.receipt.export_receipt_id
    )
    assert response["result"]["verification"]["export_verification_id"] == (
        publication.verification.export_verification_id
    )
    assert json.loads(export_response_json(response)) == response


def test_unknown_selector_fails_before_source_or_destination_access(
    tmp_path: Path,
) -> None:
    service, runtime = _service()
    missing_bundle = tmp_path / "must-not-be-opened.vfbundle"
    values = _selection(missing_bundle)
    values["container_id"] = "unknown-container"
    request = ExportDryRunRequest(operation="dry_run", **values)

    with pytest.raises(ExportContractError, match="exact selector"):
        service.dry_run_export(request)

    assert runtime.planner_calls == runtime.render_calls == 0
    assert not missing_bundle.exists()


def test_inspect_rejects_excessive_tree_depth_without_python_recursion(
    tmp_path: Path,
) -> None:
    root = _deep_export_tree(tmp_path)
    request = ExportInspectRequest(
        schema_version=EXPORT_SURFACE_REQUEST_SCHEMA,
        operation="inspect",
        destination_root=str(root),
    )

    with pytest.raises(ExportVerificationError, match="maximum directory depth"):
        ExportService().inspect_export(request)


def test_dry_run_derives_stable_plan_without_render_or_destination_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    source_before = _tree_bytes(bundle)
    destination = tmp_path / "dry-run-must-not-exist"
    service, runtime = _service()

    def publication_bomb(*args, **kwargs):
        raise AssertionError("dry run reached destination publication")

    monkeypatch.setattr(service_module, "_publish_exact_export", publication_bomb)
    first = service.dry_run_export(_dry_run_request(bundle))
    second = service.dry_run_export(_dry_run_request(bundle))

    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.export_plan_id == second.export_plan_id
    assert first.source_trust_policy == "require_external_digest"
    assert first.source_trust_grade == "external_digest"
    assert first.overwrite_policy == "refuse"
    assert runtime.planner_calls == 2
    assert runtime.render_calls == 0
    assert not destination.exists()
    assert _tree_bytes(bundle) == source_before
    response = export_dry_run_response(first)
    assert response["result"]["plan"]["export_plan_id"] == first.export_plan_id


def test_execute_requires_confirmed_plan_and_refuses_existing_destination(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service, runtime = _service()
    plan = service.dry_run_export(_dry_run_request(bundle))

    rejected_destination = tmp_path / "wrong-plan"
    wrong_plan_id = derive_id("export-plan", {"not": plan.export_plan_id})
    wrong = ExportExecuteRequest(
        operation="execute",
        destination_root=str(rejected_destination),
        expected_export_plan_id=wrong_plan_id,
        **_selection(bundle),
    )
    with pytest.raises(ExportVerificationError, match="operator-confirmed dry run"):
        service.execute_export(wrong)
    assert runtime.render_calls == 0
    assert not rejected_destination.exists()

    destination = tmp_path / "published"
    request = _execute_request(bundle, destination, plan)
    publication = service.execute_export(request)

    assert publication.destination_root == Path(os.path.abspath(destination))
    assert publication.receipt.export_plan.canonical_bytes() == plan.canonical_bytes()
    assert publication.verification.export_plan_id == plan.export_plan_id
    assert runtime.render_calls == 2
    published_before = _tree_bytes(destination)

    with pytest.raises(ExportContractError, match="already exists"):
        service.execute_export(request)

    assert _tree_bytes(destination) == published_before
    assert not list(tmp_path.glob(".veriformis-export-*"))


def test_execute_cancellation_after_source_admission_stops_before_planning(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service, runtime = _service()
    plan = service.dry_run_export(_dry_run_request(bundle))
    planner_calls_before = runtime.planner_calls
    destination = tmp_path / "cancelled"
    checks = 0

    def cancel_after_admission() -> None:
        nonlocal checks
        checks += 1
        if checks == 2:
            raise api_module.ExportOperationCancelled("cancelled after admission")

    with pytest.raises(
        api_module.ExportOperationCancelled,
        match="cancelled after admission",
    ):
        service.execute_export(
            _execute_request(bundle, destination, plan),
            cancellation_check=cancel_after_admission,
        )

    assert checks == 2
    assert runtime.planner_calls == planner_calls_before
    assert runtime.render_calls == 0
    assert not destination.exists()


def test_inspect_is_self_described_read_only_and_never_constructs_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service, _ = _service()
    plan = service.dry_run_export(_dry_run_request(bundle))
    destination = tmp_path / "published"
    publication = service.execute_export(_execute_request(bundle, destination, plan))
    before = _tree_bytes(destination)

    def verification_bomb(*args, **kwargs):
        raise AssertionError("self-described inspection attempted verification")

    monkeypatch.setattr(service_module, "_verify_export_directory", verification_bomb)
    inspection = ExportService().inspect_export(
        ExportInspectRequest(
            schema_version=EXPORT_SURFACE_REQUEST_SCHEMA,
            operation="inspect",
            destination_root=str(destination),
        )
    )

    assert inspection.inspection_scope == "self_described_physical"
    assert inspection.receipt == publication.receipt
    assert not hasattr(inspection, "verification")
    assert _tree_bytes(destination) == before
    response = export_inspection_response(inspection)
    assert "verification" not in response["result"]
    assert response["result"]["receipt"]["export_receipt_id"] == (
        publication.receipt.export_receipt_id
    )

    (destination / "data/train.jsonl").write_bytes(b"tampered")
    with pytest.raises(ExportVerificationError, match="self-described receipt"):
        ExportService().inspect_export(
            ExportInspectRequest(
                schema_version=EXPORT_SURFACE_REQUEST_SCHEMA,
                operation="inspect",
                destination_root=str(destination),
            )
        )


def test_source_bound_verify_rederives_plan_and_matches_execution_evidence(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service, runtime = _service()
    plan = service.dry_run_export(_dry_run_request(bundle))
    destination = tmp_path / "published"
    publication = service.execute_export(_execute_request(bundle, destination, plan))
    render_calls = runtime.render_calls
    before = _tree_bytes(destination)

    verified = service.verify_export(_verify_request(bundle, destination, plan))

    assert verified.receipt == publication.receipt
    assert verified.verification == publication.verification
    assert verified.receipt.export_plan.canonical_bytes() == plan.canonical_bytes()
    assert runtime.render_calls == render_calls
    assert _tree_bytes(destination) == before

    summaries = (
        export_dry_run_response(plan)["result"]["plan"],
        export_execution_response(publication)["result"]["plan"],
        export_verify_response(verified)["result"]["plan"],
    )
    assert summaries[0] == summaries[1] == summaries[2]
    response_json = export_response_json(export_verify_response(verified))
    assert response_json.encode("utf-8") == lossless_json_bytes(
        export_verify_response(verified)
    )
    assert not response_json.endswith("\n")
    assert FROZEN_SURFACE["exact"] == {
        "export_plan_id": plan.export_plan_id,
        "export_receipt_id": publication.receipt.export_receipt_id,
        "export_verification_id": publication.verification.export_verification_id,
        "plan_canonical_sha256": sha256_digest(plan.canonical_bytes()),
        "receipt_canonical_sha256": sha256_digest(
            publication.receipt.canonical_bytes()
        ),
        "verification_canonical_sha256": sha256_digest(
            publication.verification.canonical_bytes()
        ),
    }


def test_source_bound_verify_rejects_wrong_anchor_before_destination_read(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service, _ = _service()
    plan = service.dry_run_export(_dry_run_request(bundle))
    destination = tmp_path / "must-not-be-read"
    request = _verify_request(
        bundle,
        destination,
        plan,
        expected_manifest_sha256="0" * 64,
    )

    with pytest.raises(BundleVerificationError, match="expected external digest"):
        service.verify_export(request)

    assert not destination.exists()


def test_source_bound_verify_rejects_visible_byte_tamper(tmp_path: Path) -> None:
    bundle = _materialize_bundle(tmp_path)
    service, _ = _service()
    plan = service.dry_run_export(_dry_run_request(bundle))
    destination = tmp_path / "published"
    service.execute_export(_execute_request(bundle, destination, plan))
    (destination / "data/evaluation.jsonl").write_bytes(b"tampered")

    with pytest.raises(ExportVerificationError):
        service.verify_export(_verify_request(bundle, destination, plan))


def test_catalog_binding_preserves_semantic_render_and_replay(tmp_path: Path) -> None:
    from test_determinism import _SemanticService, _semantic_plan

    bundle = _materialize_bundle(tmp_path)
    runtime = _SemanticService(first_pretty=True)
    seed_plan = _semantic_plan(runtime, bundle)
    assert seed_plan.consumer_profile is not None
    descriptor = ExportProfileDescriptor(
        container_profile=seed_plan.container_profile,
        consumer_profile=seed_plan.consumer_profile,
        dependencies=seed_plan.dependencies,
        supported_row_schemas=(seed_plan.row_schema,),
    )
    implementation = service_module._ExportImplementation(
        descriptor=descriptor,
        file_planner=lambda _descriptor, _row_set: seed_plan.file_plans,
        renderer=runtime._render_derivative,
        semantic_replayer=runtime._replay_derivative,
    )
    service = ExportService(_implementations=(implementation,))
    selected = {
        "schema_version": EXPORT_SURFACE_REQUEST_SCHEMA,
        "bundle": str(bundle),
        "container_id": seed_plan.container_profile.container_id,
        "container_version": seed_plan.container_profile.container_version,
        "consumer_id": seed_plan.consumer_profile.consumer_id,
        "consumer_profile_version": seed_plan.consumer_profile.profile_version,
        "source_trust_policy": "require_external_digest",
        "expected_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "overwrite_policy": "refuse",
    }
    plan = service.dry_run_export(
        ExportDryRunRequest(operation="dry_run", **selected)
    )
    assert plan.canonical_bytes() == seed_plan.canonical_bytes()

    destination = tmp_path / "semantic"
    publication = service.execute_export(
        ExportExecuteRequest(
            operation="execute",
            destination_root=str(destination),
            expected_export_plan_id=plan.export_plan_id,
            **selected,
        )
    )
    verified = service.verify_export(
        ExportVerifyRequest(
            operation="verify",
            destination_root=str(destination),
            expected_export_plan_id=plan.export_plan_id,
            **selected,
        )
    )

    assert verified.verification == publication.verification
    assert runtime.render_count == 2
    assert runtime.replay_count == 4
