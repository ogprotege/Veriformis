"""Propose mapping plans from captured JSONL. Never auto-publishes."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, Literal

from pydantic import field_validator, model_validator

from veriformis.errors import MappingError
from veriformis.identity import lossless_json_bytes, sha256_digest
from veriformis.mapping.capture import CapturedRow, JsonlCapture, capture_row_source
from veriformis.mapping.execute import _require_two_turn_messages, resolve_json_pointer
from veriformis.mapping.models import FieldMapping, MappingPlan, _StrictModel

DETECTOR_DATA_NAME = "detectors-v1.json"
DETECT_SCHEMA = "veriformis.mapping-detect/v1"
CONFIRMATION_SCHEMA = "veriformis.mapping-confirmation/v1"


class MappingDetector(_StrictModel):
    detector_id: str
    goal_id: str
    representation_id: str
    row_schema: Literal[
        "text",
        "prompt_completion",
        "instruction_output",
        "messages",
    ]
    required_paths: tuple[str, ...]
    plain_language: str

    @field_validator("required_paths", mode="before")
    @classmethod
    def _paths(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> MappingDetector:
        if not self.detector_id.strip() or not self.plain_language.strip():
            raise MappingError("mapping detector fields must be non-empty")
        if not self.required_paths:
            raise MappingError("mapping detector requires at least one source path")
        return self


class MappingDetectorCatalog(_StrictModel):
    schema_id: Literal["veriformis.mapping-detector-discovery/v1"]
    contract_id: Literal["veriformis.mapping-detector"]
    contract_version: Literal[1]
    detectors: tuple[MappingDetector, ...]

    @field_validator("detectors", mode="before")
    @classmethod
    def _detectors(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value


@lru_cache(maxsize=1)
def _load_detectors() -> tuple[str, MappingDetectorCatalog]:
    raw = (
        resources.files("veriformis.mapping")
        .joinpath(DETECTOR_DATA_NAME)
        .read_text(encoding="utf-8")
    )
    payload = json.loads(raw)
    canonical = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if canonical != raw:
        raise MappingError("mapping detector catalog is not canonical JSON")
    return canonical, MappingDetectorCatalog.model_validate(payload)


def mapping_detector_catalog() -> MappingDetectorCatalog:
    return _load_detectors()[1]


def mapping_detector_catalog_json() -> str:
    return _load_detectors()[0]


def mapping_confirmation_digest(
    *,
    goal_id: str,
    representation_id: str,
    row_schema: str,
    field_mappings: tuple[FieldMapping, ...] | list[FieldMapping],
    source_digests: tuple[tuple[str, str], ...] | list[tuple[str, str]],
) -> str:
    """Digest an operator must return before map mutates a workspace."""
    mappings = tuple(field_mappings)
    sources = tuple(sorted(source_digests))
    body = {
        "schema_version": CONFIRMATION_SCHEMA,
        "goal_id": goal_id,
        "representation_id": representation_id,
        "row_schema": row_schema,
        "field_mappings": [
            {"source_path": item.source_path, "target_key": item.target_key}
            for item in mappings
        ],
        "source_digests": [
            {"logical_path": path, "sha256": digest} for path, digest in sources
        ],
    }
    return sha256_digest(lossless_json_bytes(body))


def confirm_mapping_plan(
    plan: MappingPlan,
    source_digests: tuple[tuple[str, str], ...] | list[tuple[str, str]],
) -> None:
    expected = mapping_confirmation_digest(
        goal_id=plan.goal_id,
        representation_id=plan.representation_id,
        row_schema=plan.row_schema,
        field_mappings=plan.field_mappings,
        source_digests=source_digests,
    )
    if plan.confirmation_digest != expected:
        raise MappingError(
            "mapping plan is not confirmed for these captured files; "
            "run mapping-detect and pass the chosen proposal unchanged"
        )


def detect_mapping_capture(
    capture: JsonlCapture,
    *,
    goal_id: str | None = None,
    representation_id: str | None = None,
) -> dict[str, Any]:
    """Return zero or more confirmed-ready mapping proposals for one capture."""
    proposals: list[MappingPlan] = []
    seen: set[str] = set()
    source_digests = ((capture.row_source.logical_path, capture.row_source.sha256),)
    for detector in mapping_detector_catalog().detectors:
        if goal_id is not None and detector.goal_id != goal_id:
            continue
        if (
            representation_id is not None
            and detector.representation_id != representation_id
        ):
            continue
        if (
            capture.row_source.container_kind == "csv"
            and detector.row_schema == "messages"
        ):
            continue
        if not _detector_matches(detector, capture.records):
            continue
        plan = _plan_from_detector(
            detector,
            source_digests=source_digests,
            container_kind=capture.row_source.container_kind,
        )
        if plan.mapping_plan_id in seen:
            continue
        seen.add(plan.mapping_plan_id)
        proposals.append(plan)
    if not proposals:
        return {
            "schema_version": DETECT_SCHEMA,
            "proposals": [],
            "refusal": (
                "no mapping detector matched this file; "
                "the detector will not invent a summary, translation, or Q&A mapping"
            ),
        }
    return {
        "schema_version": DETECT_SCHEMA,
        "proposals": [plan.model_dump(mode="json") for plan in proposals],
        "refusal": None,
    }


def detect_mapping(
    path: Path,
    *,
    logical_path: str | None = None,
    goal_id: str | None = None,
    representation_id: str | None = None,
) -> dict[str, Any]:
    capture = capture_row_source(path, logical_path=logical_path or path.name)
    return detect_mapping_capture(
        capture,
        goal_id=goal_id,
        representation_id=representation_id,
    )


def _detector_matches(
    detector: MappingDetector,
    records: tuple[CapturedRow, ...],
) -> bool:
    for record in records:
        for pointer in detector.required_paths:
            try:
                value = resolve_json_pointer(record.payload, pointer)
            except MappingError:
                return False
            if detector.row_schema == "messages" and pointer in {"messages", "/messages"}:
                try:
                    _require_two_turn_messages(value, row_index=record.row_index)
                except MappingError:
                    return False
                continue
            if not isinstance(value, str) or value == "":
                return False
    return True


def _plan_from_detector(
    detector: MappingDetector,
    *,
    source_digests: tuple[tuple[str, str], ...],
    container_kind: str,
) -> MappingPlan:
    from veriformis.mapping.models import ROW_SCHEMA_PAYLOAD_KEYS

    expected = ROW_SCHEMA_PAYLOAD_KEYS[detector.row_schema]
    if tuple(detector.required_paths) != expected:
        raise MappingError(
            f"detector {detector.detector_id!r} required_paths drifted from payload keys"
        )
    mappings = tuple(
        FieldMapping.create(source_path=path, target_key=path)
        for path in detector.required_paths
    )
    confirmation = mapping_confirmation_digest(
        goal_id=detector.goal_id,
        representation_id=detector.representation_id,
        row_schema=detector.row_schema,
        field_mappings=mappings,
        source_digests=source_digests,
    )
    return MappingPlan.create(
        goal_id=detector.goal_id,
        representation_id=detector.representation_id,
        row_schema=detector.row_schema,
        container_kind=container_kind,
        confirmation_digest=confirmation,
        field_mappings=mappings,
    )
