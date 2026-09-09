"""Shared export api fixtures, separate from collected tests."""

from __future__ import annotations
from pathlib import Path
from veriformis.exports import (
    ExportConsumerProfile,
    ExportContainerProfile,
    ExportDependencyBinding,
    ExportFilePlan,
    ExportPlan,
    ExportService,
)
from veriformis.exports import service as service_module
from veriformis.exports.api import (
    EXPORT_SURFACE_REQUEST_SCHEMA,
    ExportDryRunRequest,
    ExportExecuteRequest,
    ExportProfileDescriptor,
    ExportVerifyRequest,
)
from veriformis.identity import sha256_digest
from support.bundles import (
    EXPECTED_MANIFEST_SHA256,
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
