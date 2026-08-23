"""Content-addressed mapping rejection reports. Not a trainer export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import field_validator, model_validator

from veriformis.errors import MappingError
from veriformis.identity import lossless_json_bytes, sha256_digest, validate_id, validate_sha256
from veriformis.mapping.capture import CapturedRow, capture_row_source
from veriformis.mapping.detect import mapping_confirmation_digest
from veriformis.mapping.models import MappingPlan, _StrictModel

REJECTION_SCHEMA = "veriformis.mapping-rejection-report/v1"
ReasonCode = Literal[
    "empty-required-string",
    "invalid-mapped-fields",
    "invalid-messages",
    "invalid-partition",
    "missing-source-path",
    "non-string-value",
    "unmapped-keys",
]


class MappingRejection(_StrictModel):
    row_index: int
    source_path: str
    reason_code: ReasonCode
    original_value_sha256: str
    mapping_plan_id: str

    @model_validator(mode="after")
    def _closed(self) -> MappingRejection:
        if self.row_index < 1:
            raise MappingError("mapping rejection row_index must be 1-based")
        if not self.source_path.strip():
            raise MappingError("mapping rejection source_path must be non-empty")
        validate_id(self.mapping_plan_id, kind="mpl")
        validate_sha256(self.original_value_sha256)
        return self


class MappingRejectionReport(_StrictModel):
    schema_version: Literal["veriformis.mapping-rejection-report/v1"]
    report_id: str
    mapping_plan_id: str
    accepted_count: int
    rejected_count: int
    rejections: tuple[MappingRejection, ...]

    @field_validator("rejections", mode="before")
    @classmethod
    def _tuple_rejections(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> MappingRejectionReport:
        validate_id(self.mapping_plan_id, kind="mpl")
        if self.accepted_count < 0 or self.rejected_count < 0:
            raise MappingError("mapping rejection counts cannot be negative")
        if self.rejected_count != len(self.rejections):
            raise MappingError("mapping rejection count does not match its rows")
        indexes = tuple(item.row_index for item in self.rejections)
        if indexes != tuple(sorted(indexes)):
            raise MappingError("mapping rejections must be ordered by row_index")
        for item in self.rejections:
            if item.mapping_plan_id != self.mapping_plan_id:
                raise MappingError("mapping rejection names another mapping plan")
        expected = sha256_digest(
            lossless_json_bytes(self.model_dump(mode="json", exclude={"report_id"}))
        )
        if self.report_id != expected:
            raise MappingError("mapping rejection report identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        mapping_plan_id: str,
        accepted_count: int,
        rejections: tuple[MappingRejection, ...] | list[MappingRejection],
    ) -> MappingRejectionReport:
        ordered = tuple(sorted(rejections, key=lambda item: item.row_index))
        body = {
            "schema_version": REJECTION_SCHEMA,
            "mapping_plan_id": mapping_plan_id,
            "accepted_count": accepted_count,
            "rejected_count": len(ordered),
            "rejections": [item.model_dump(mode="json") for item in ordered],
        }
        return cls(report_id=sha256_digest(lossless_json_bytes(body)), **body)


def classify_mapping_error(message: str) -> str:
    text = message.lower()
    if "unmapped keys" in text:
        return "unmapped-keys"
    if "missing source path" in text:
        return "missing-source-path"
    if "empty string" in text:
        return "empty-required-string"
    if "must be a string" in text:
        return "non-string-value"
    if "partition" in text:
        return "invalid-partition"
    if "messages" in text or "turn" in text:
        return "invalid-messages"
    return "invalid-mapped-fields"


def rejection_from_error(
    *,
    record: CapturedRow,
    logical_path: str,
    mapping_plan_id: str,
    message: str,
) -> MappingRejection:
    return MappingRejection(
        row_index=record.row_index,
        source_path=logical_path,
        reason_code=classify_mapping_error(message),  # type: ignore[arg-type]
        original_value_sha256=sha256_digest(lossless_json_bytes(record.payload)),
        mapping_plan_id=mapping_plan_id,
    )


def write_mapping_rejection_report(
    report: MappingRejectionReport,
    destination: Path,
    *,
    workspace_name: str | None = None,
) -> Path:
    """Write a content-addressed rejection report beside a workspace or directory."""
    destination.mkdir(parents=True, exist_ok=True)
    prefix = f"{workspace_name}." if workspace_name else ""
    path = destination / f"{prefix}mapping-rejection-{report.report_id}.json"
    encoded = json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != encoded:
        raise MappingError(
            f"mapping rejection report {path.name} already exists with different bytes"
        )
    if not path.exists():
        path.write_text(encoded, encoding="utf-8")
    return path


def export_mapping_rejections(
    path: Path,
    plan: MappingPlan,
    destination: Path,
    *,
    logical_path: str | None = None,
) -> dict[str, Any]:
    """Write the rejection report for one confirmed plan without mutating a workspace."""
    from veriformis.identity import derive_source_id
    from veriformis.mapping.execute import execute_mapping_rows
    from veriformis.mapping.result import MappingRecipe

    capture = capture_row_source(path, logical_path=logical_path or path.name)
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
            "mapping rejection export requires a plan confirmed for this file"
        )
    source_id = derive_source_id(
        capture.row_source.logical_path, capture.row_source.sha256
    )
    recipe = MappingRecipe.create(plan=plan, source_ids=(source_id,))
    accepted, rejections = execute_mapping_rows(
        plan,
        capture,
        source_id=source_id,
        recipe=recipe,
    )
    report = MappingRejectionReport.create(
        mapping_plan_id=plan.mapping_plan_id,
        accepted_count=len(accepted),
        rejections=rejections,
    )
    written = write_mapping_rejection_report(report, destination)
    return {
        "schema_version": REJECTION_SCHEMA,
        "report_id": report.report_id,
        "mapping_plan_id": report.mapping_plan_id,
        "accepted_count": report.accepted_count,
        "rejected_count": report.rejected_count,
        "path": str(written),
    }
