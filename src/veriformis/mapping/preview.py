"""Runtime-only full-file mapping preview. No workspace mutation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from veriformis.errors import MappingError
from veriformis.identity import lossless_json_bytes
from veriformis.mapping.capture import JsonlCapture, capture_jsonl
from veriformis.mapping.detect import mapping_confirmation_digest
from veriformis.mapping.execute import execute_mapping
from veriformis.mapping.models import MappingPlan
from veriformis.mapping.result import MappingRecipe

PREVIEW_SCHEMA = "veriformis.mapping-preview/v1"
MAX_SAMPLE_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 256 * 1024


def preview_mapping(
    path: Path,
    plan: MappingPlan,
    *,
    logical_path: str | None = None,
) -> dict[str, Any]:
    """Walk every JSONL object and report accept/reject with samples."""
    from veriformis.identity import derive_source_id
    from veriformis.mapping.finish import imported_payload

    capture = capture_jsonl(path, logical_path=logical_path or path.name)
    source_id = derive_source_id(
        capture.row_source.logical_path, capture.row_source.sha256
    )
    expected = mapping_confirmation_digest(
        goal_id=plan.goal_id,
        representation_id=plan.representation_id,
        row_schema=plan.row_schema,
        field_mappings=plan.field_mappings,
        source_digests=(
            (capture.row_source.logical_path, capture.row_source.sha256),
        ),
    )
    if plan.confirmation_digest != expected:
        raise MappingError(
            "mapping preview requires a plan confirmed for this file"
        )
    recipe = MappingRecipe.create(plan=plan, source_ids=(source_id,))
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for captured in capture.records:
        try:
            records = execute_mapping(
                plan,
                JsonlCapture(
                    row_source=capture.row_source,
                    records=(captured,),
                    raw_bytes=capture.raw_bytes,
                ),
                source_id=source_id,
                recipe=recipe,
            )
            payload = imported_payload(records[0], plan.row_schema)
            sample_bytes = lossless_json_bytes(payload)
            sample: dict[str, Any] | None = payload
            omit = None
            if len(sample_bytes) > MAX_SAMPLE_BYTES:
                sample = None
                omit = "sample-exceeds-64-kib"
            accepted.append(
                {
                    "row_index": captured.row_index,
                    "status": "accepted",
                    "payload": sample,
                    "omission": omit,
                }
            )
        except MappingError as exc:
            rejected.append(
                {
                    "row_index": captured.row_index,
                    "status": "rejected",
                    "reason": exc.message,
                    "payload": None,
                    "omission": None,
                }
            )
    body = {
        "schema_version": PREVIEW_SCHEMA,
        "mapping_plan_id": plan.mapping_plan_id,
        "row_schema": plan.row_schema,
        "record_count": capture.row_source.record_count,
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "accepted": accepted,
        "rejected": rejected,
    }
    encoded = json.dumps(body, ensure_ascii=True, sort_keys=True).encode("ascii")
    if len(encoded) > MAX_RESPONSE_BYTES:
        body["accepted"] = []
        body["rejected"] = []
        body["omission"] = "response-exceeds-256-kib"
    else:
        body["omission"] = None
    return body
