"""Shared export semantic fixtures, separate from collected tests."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from veriformis.bundle import inspect_finished_bundle
from veriformis.datasets import (
    ProductRow,
    RowProvenance,
    RowSet,
    product_row_from_json_bytes,
    row_provenance_from_json_bytes,
)
from veriformis.exports import (
    ExportConsumerProfile,
    ExportContainerProfile,
    ExportDependencyBinding,
    ExportFilePlan,
    ExportPlan,
    ExportService,
)
from veriformis.exports import service as service_module
from veriformis.identity import lossless_json_bytes, sha256_digest
from support.bundles import (
    EXPECTED_MANIFEST_SHA256,
)

SEMANTIC_DATA_PATH = "data/rows.json"

SEMANTIC_SCHEMA_PATH = "metadata/schema.json"

SEMANTIC_FILE_SCHEMA = "veriformis.export-semantic-file/v1"

SEMANTIC_DATA_SCHEMA = "phase4-conformance-semantic-dataset/v1"

SEMANTIC_SCHEMA_SCHEMA = "phase4-conformance-semantic-schema/v1"

def _source_row_set(bundle: Path) -> RowSet:
    return inspect_finished_bundle(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    ).row_set

def _clone_rows(rows: tuple[ProductRow, ...]) -> tuple[ProductRow, ...]:
    return tuple(
        product_row_from_json_bytes(lossless_json_bytes(row.model_dump(mode="json")))
        for row in rows
    )

def _clone_provenance(
    provenance: tuple[RowProvenance, ...],
) -> tuple[RowProvenance, ...]:
    return tuple(
        row_provenance_from_json_bytes(
            lossless_json_bytes(item.model_dump(mode="json"))
        )
        for item in provenance
    )

def _consumer() -> ExportConsumerProfile:
    return ExportConsumerProfile.create(
        consumer_id="phase4-conformance-consumer",
        profile_version=3,
        accepted_row_schemas=("text",),
    )

def _dependencies() -> tuple[ExportDependencyBinding, ...]:
    bindings = (
        ExportDependencyBinding.create(
            dependency_name="phase4-conformance-renderer",
            dependency_version="1.0.0",
            dependency_role="renderer",
        ),
        ExportDependencyBinding.create(
            dependency_name="phase4-conformance-semantic-replayer",
            dependency_version="1.0.0",
            dependency_role="semantic-replayer",
        ),
    )
    return tuple(sorted(bindings, key=lambda item: item.dependency_id))

def _semantic_dataset_content(row_set: RowSet) -> dict[str, Any]:
    return {
        "evaluation_rows": [
            row.model_dump(mode="json") for row in row_set.evaluation_rows
        ],
        "provenance": [item.model_dump(mode="json") for item in row_set.provenance],
        "schema_version": SEMANTIC_DATA_SCHEMA,
        "train_rows": [row.model_dump(mode="json") for row in row_set.train_rows],
    }

def _semantic_schema_content(row_schema: str) -> dict[str, Any]:
    return {
        "row_schema": row_schema,
        "schema_version": SEMANTIC_SCHEMA_SCHEMA,
    }

def _semantic_envelope(
    *,
    container_profile_id: str,
    dependency_ids: tuple[str, ...],
    path: str,
    role: str,
    media_type: str,
    membership_scope: str,
    record_count: int | None,
    row_schema: str,
    canonical_content: dict[str, Any],
) -> bytes:
    return lossless_json_bytes(
        {
            "canonical_content": canonical_content,
            "container_profile_id": container_profile_id,
            "dependency_ids": list(dependency_ids),
            "media_type": media_type,
            "membership_scope": membership_scope,
            "path": path,
            "record_count": record_count,
            "role": role,
            "row_schema": row_schema,
            "schema_version": SEMANTIC_FILE_SCHEMA,
        }
    )

def _semantic_plan(service: ExportService, bundle: Path) -> ExportPlan:
    row_set = _source_row_set(bundle)
    container = ExportContainerProfile.create(
        container_id="phase4-conformance-semantic-directory",
        container_version=2,
        determinism_claim="semantic_content_only",
    )
    dependencies = _dependencies()
    dependency_ids = tuple(item.dependency_id for item in dependencies)
    specs = (
        (
            SEMANTIC_DATA_PATH,
            "complete-dataset",
            "application/json",
            "all",
            row_set.total_row_count,
            _semantic_dataset_content(row_set),
        ),
        (
            SEMANTIC_SCHEMA_PATH,
            "schema-metadata",
            "application/json",
            "none",
            None,
            _semantic_schema_content(row_set.row_schema),
        ),
    )
    plans = tuple(
        ExportFilePlan.create(
            path=path,
            role=role,
            media_type=media_type,
            membership_scope=membership_scope,
            record_count=record_count,
            semantic_content_sha256=sha256_digest(
                _semantic_envelope(
                    container_profile_id=container.container_profile_id,
                    dependency_ids=dependency_ids,
                    path=path,
                    role=role,
                    media_type=media_type,
                    membership_scope=membership_scope,
                    record_count=record_count,
                    row_schema=row_set.row_schema,
                    canonical_content=canonical_content,
                )
            ),
            expected_sha256=None,
            expected_byte_size=None,
        )
        for (
            path,
            role,
            media_type,
            membership_scope,
            record_count,
            canonical_content,
        ) in specs
    )
    return service.create_plan(
        bundle,
        container_profile=container,
        consumer_profile=_consumer(),
        dependencies=dependencies,
        file_plans=plans,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )

def _json_bytes(value: Any, *, pretty: bool) -> bytes:
    if pretty:
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                indent=2,
            ).encode("utf-8")
            + b"\n"
        )
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

def _semantic_files(
    row_set: RowSet,
    *,
    pretty: bool,
    omit_last_evaluation: bool = False,
) -> tuple[tuple[str, bytes], ...]:
    dataset = _semantic_dataset_content(row_set)
    if omit_last_evaluation:
        dataset["evaluation_rows"] = dataset["evaluation_rows"][:-1]
        omitted_row_id = row_set.evaluation_rows[-1].row_id
        dataset["provenance"] = [
            item for item in dataset["provenance"] if item["row_id"] != omitted_row_id
        ]
    return (
        (SEMANTIC_DATA_PATH, _json_bytes(dataset, pretty=pretty)),
        (
            SEMANTIC_SCHEMA_PATH,
            _json_bytes(_semantic_schema_content(row_set.row_schema), pretty=pretty),
        ),
    )

def _strict_json_object(data: bytes) -> dict[str, Any]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key {key!r}")
            result[key] = value
        return result

    def reject_number(value: str) -> None:
        raise ValueError(f"unsupported JSON number {value!r}")

    value = json.loads(
        data.decode("utf-8"),
        object_pairs_hook=unique_object,
        parse_float=reject_number,
        parse_constant=reject_number,
    )
    if type(value) is not dict:
        raise ValueError("conformance JSON root must be an object")
    return value

def _decode_semantic_files(
    plan: ExportPlan,
    files: tuple[tuple[str, bytes], ...],
) -> service_module._ReplayedDerivative:
    by_path = dict(files)
    dataset = _strict_json_object(by_path[SEMANTIC_DATA_PATH])
    if (
        set(dataset)
        != {
            "evaluation_rows",
            "provenance",
            "schema_version",
            "train_rows",
        }
        or dataset["schema_version"] != SEMANTIC_DATA_SCHEMA
    ):
        raise ValueError("invalid conformance semantic dataset envelope")
    schema = _strict_json_object(by_path[SEMANTIC_SCHEMA_PATH])
    if (
        set(schema) != {"row_schema", "schema_version"}
        or schema["schema_version"] != SEMANTIC_SCHEMA_SCHEMA
    ):
        raise ValueError("invalid conformance schema envelope")
    if schema["row_schema"] != plan.row_schema:
        raise ValueError("rendered schema differs from the export plan")

    train_rows = tuple(
        product_row_from_json_bytes(lossless_json_bytes(item))
        for item in dataset["train_rows"]
    )
    evaluation_rows = tuple(
        product_row_from_json_bytes(lossless_json_bytes(item))
        for item in dataset["evaluation_rows"]
    )
    provenance = tuple(
        row_provenance_from_json_bytes(lossless_json_bytes(item))
        for item in dataset["provenance"]
    )
    normalized_contents = {
        SEMANTIC_DATA_PATH: {
            "evaluation_rows": [row.model_dump(mode="json") for row in evaluation_rows],
            "provenance": [item.model_dump(mode="json") for item in provenance],
            "schema_version": SEMANTIC_DATA_SCHEMA,
            "train_rows": [row.model_dump(mode="json") for row in train_rows],
        },
        SEMANTIC_SCHEMA_PATH: _semantic_schema_content(plan.row_schema),
    }
    dependency_ids = tuple(item.dependency_id for item in plan.dependencies)
    semantic_contents = tuple(
        (
            file_plan.path,
            _semantic_envelope(
                container_profile_id=plan.container_profile.container_profile_id,
                dependency_ids=dependency_ids,
                path=file_plan.path,
                role=file_plan.role,
                media_type=file_plan.media_type,
                membership_scope=file_plan.membership_scope,
                record_count=file_plan.record_count,
                row_schema=plan.row_schema,
                canonical_content=normalized_contents[file_plan.path],
            ),
        )
        for file_plan in plan.file_plans
    )
    return service_module._ReplayedDerivative(
        semantic_contents=semantic_contents,
        train_rows=train_rows,
        evaluation_rows=evaluation_rows,
        provenance=provenance,
    )

class _SemanticService(ExportService):
    def __init__(
        self,
        *,
        first_pretty: bool = False,
        omit_last_evaluation: bool = False,
        change_second_preimage: bool = False,
        replay_membership_mutation: str | None = None,
    ) -> None:
        self.first_pretty = first_pretty
        self.omit_last_evaluation = omit_last_evaluation
        self.change_second_preimage = change_second_preimage
        self.replay_membership_mutation = replay_membership_mutation
        self.render_count = 0
        self.replay_count = 0
        self.replay_inputs: list[tuple[tuple[str, bytes], ...]] = []
        self.original_preimages: tuple[tuple[str, bytes], ...] | None = None
        self.changed_preimages: tuple[tuple[str, bytes], ...] | None = None

    def _render_derivative(
        self,
        plan: ExportPlan,
        source_row_set: RowSet,
    ) -> service_module._RenderedDerivative:
        del plan
        self.render_count += 1
        pretty = self.first_pretty if self.render_count == 1 else not self.first_pretty
        files = _semantic_files(
            source_row_set,
            pretty=pretty,
            omit_last_evaluation=self.omit_last_evaluation,
        )
        return service_module._RenderedDerivative(
            files=files,
            train_rows=_clone_rows(source_row_set.train_rows),
            evaluation_rows=_clone_rows(source_row_set.evaluation_rows),
            provenance=_clone_provenance(source_row_set.provenance),
        )

    def _replay_derivative(
        self,
        plan: ExportPlan,
        files: tuple[tuple[str, bytes], ...],
    ) -> service_module._ReplayedDerivative:
        self.replay_count += 1
        self.replay_inputs.append(files)
        replayed = _decode_semantic_files(plan, files)
        if self.original_preimages is None:
            self.original_preimages = replayed.semantic_contents
        if self.change_second_preimage and self.replay_count == 2:
            changed = list(replayed.semantic_contents)
            path, data = changed[0]
            changed[0] = (path, data + b" ")
            replayed = service_module._ReplayedDerivative(
                semantic_contents=tuple(changed),
                train_rows=replayed.train_rows,
                evaluation_rows=replayed.evaluation_rows,
                provenance=replayed.provenance,
            )
            self.changed_preimages = replayed.semantic_contents
        if self.replay_membership_mutation == "rows":
            replayed = service_module._ReplayedDerivative(
                semantic_contents=replayed.semantic_contents,
                train_rows=replayed.train_rows,
                evaluation_rows=replayed.evaluation_rows[:-1],
                provenance=replayed.provenance,
            )
        elif self.replay_membership_mutation == "provenance":
            replayed = service_module._ReplayedDerivative(
                semantic_contents=replayed.semantic_contents,
                train_rows=replayed.train_rows,
                evaluation_rows=replayed.evaluation_rows,
                provenance=replayed.provenance[:-1],
            )
        return replayed
