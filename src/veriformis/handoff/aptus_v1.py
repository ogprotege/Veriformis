"""Aptus handoff contract v1 over sealed Veriformis finished bundles.

The closed minimal-v1 bundle file set is unchanged. The handoff is a sibling
descriptor that binds external-digest verification, partition digests, row
semantics, masking expectations, and a portable assignment projection that
consumers can recompute from sealed provenance alone.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from veriformis.bundle import verify_finished_bundle
from veriformis.bundle.finished import (
    EVALUATION_PATH,
    MANIFEST_NAME,
    PROVENANCE_PATH,
    TRAIN_PATH,
    VALIDATION_PATH,
    FinishedBundleManifest,
)
from veriformis.datasets.serialization import _payload_contract
from veriformis.errors import VeriformisError
from veriformis.identity import (
    canonical_digest,
    derive_id,
    lossless_json_bytes,
    sha256_digest,
    validate_id,
    validate_sha256,
)

APTUS_HANDOFF_SCHEMA_VERSION = "veriformis.aptus-handoff/v1"
_ASSIGNMENT_PROJECTION_SCHEMA = "veriformis.aptus-assignment-projection/v1"

# Current Aptus MLX intake rejects plain text rows (product contract).
_DEFAULT_ACCEPTED_SCHEMAS = (
    "prompt_completion",
    "instruction_output",
    "messages",
)
_DEFAULT_REJECTED_SCHEMAS = ("text",)


class AptusHandoffError(VeriformisError):
    code = "aptus-handoff-invalid"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PartitionBinding(_Strict):
    path: str
    role: Literal["training-partition", "evaluation-partition"]
    media_type: Literal["application/jsonl"] = "application/jsonl"
    sha256: str
    record_count: int
    byte_size: int

    @field_validator("sha256")
    @classmethod
    def _digest(cls, value: str) -> str:
        return validate_sha256(value)

    @field_validator("record_count", "byte_size")
    @classmethod
    def _nonneg(cls, value: int) -> int:
        if type(value) is not int or value < 0:
            raise ValueError("partition counts must be non-negative integers")
        return value


class FileBinding(_Strict):
    path: str
    role: str
    media_type: str
    sha256: str
    byte_size: int

    @field_validator("sha256")
    @classmethod
    def _digest(cls, value: str) -> str:
        return validate_sha256(value)


class MaskingExpectation(_Strict):
    row_schema: str
    supervised_boundary: str
    notes: str


class BackendCapabilities(_Strict):
    accepts_row_schemas: tuple[str, ...]
    rejects_row_schemas: tuple[str, ...]
    requires_external_digest: bool = True
    enforces_assignment_digest: bool = True


class AptusHandoffDescriptor(_Strict):
    """Versioned sibling descriptor for Aptus consumption of a sealed bundle."""

    schema_version: Literal["veriformis.aptus-handoff/v1"] = APTUS_HANDOFF_SCHEMA_VERSION
    handoff_id: str
    bundle_id: str
    manifest_sha256: str
    content_root_sha256: str
    dataset_snapshot_id: str
    validation_report_id: str
    plan_id: str
    recipe_id: str
    construction_result_id: str
    split_result_id: str
    objective_id: str
    row_schema: str
    assignment_digest: str
    source_ids: tuple[str, ...]
    train: PartitionBinding
    evaluation: PartitionBinding
    provenance: FileBinding
    validation: FileBinding
    masking: MaskingExpectation
    backend_capabilities: BackendCapabilities
    required_verification_grade: Literal["external_digest"] = "external_digest"

    @model_validator(mode="after")
    def _identity(self) -> AptusHandoffDescriptor:
        # The four bound paths are contract constants of the closed minimal-v1
        # bundle. Anything else (absolute paths, parent traversal, aliases)
        # is rejected before any consumer touches the filesystem. This is
        # value validation only: descriptor identity derivation is unchanged.
        for field_name, expected_path in (
            ("train", TRAIN_PATH),
            ("evaluation", EVALUATION_PATH),
            ("provenance", PROVENANCE_PATH),
            ("validation", VALIDATION_PATH),
        ):
            observed_path = getattr(self, field_name).path
            if observed_path != expected_path:
                raise AptusHandoffError(
                    f"aptus handoff {field_name} path must be the contract "
                    f"path {expected_path!r}, observed {observed_path!r}"
                )
        validate_id(self.handoff_id, kind="ahd")
        validate_id(self.bundle_id, kind="bundle")
        validate_sha256(self.manifest_sha256)
        validate_sha256(self.content_root_sha256)
        validate_sha256(self.assignment_digest)
        for field_name in (
            "dataset_snapshot_id",
            "validation_report_id",
            "plan_id",
            "recipe_id",
            "construction_result_id",
            "split_result_id",
            "objective_id",
        ):
            validate_id(getattr(self, field_name))
        payload = self.model_dump(mode="json", exclude={"handoff_id"})
        expected = derive_id("ahd", payload)
        if self.handoff_id != expected:
            raise ValueError("aptus handoff identity mismatch")
        return self

    def to_dict(self) -> dict[str, Any]:
        return json.loads(lossless_json_bytes(self.model_dump(mode="json")).decode())

    def canonical_bytes(self) -> bytes:
        return lossless_json_bytes(self.model_dump(mode="json"))


@dataclass(frozen=True)
class AptusConsumptionReport:
    status: Literal["accepted", "rejected"]
    handoff_id: str
    bundle_id: str
    assignment_digest: str
    verified_grade: str
    findings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "handoff_id": self.handoff_id,
            "bundle_id": self.bundle_id,
            "assignment_digest": self.assignment_digest,
            "verified_grade": self.verified_grade,
            "findings": list(self.findings),
        }


def handoff_path_for_bundle(bundle: Path) -> Path:
    """Default sibling path for a sealed bundle handoff descriptor."""
    return Path(f"{Path(bundle).resolve()}.aptus-handoff.json")


def write_aptus_handoff(
    handoff: AptusHandoffDescriptor,
    path: Path,
) -> Path:
    target = Path(path)
    target.write_bytes(handoff.canonical_bytes())
    return target


def build_aptus_handoff(
    bundle: Path,
    *,
    expected_manifest_sha256: str,
) -> AptusHandoffDescriptor:
    """Build a handoff after external-digest verification of a sealed bundle."""
    bundle_path = Path(bundle).resolve()
    verification = verify_finished_bundle(
        bundle_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    if verification.trust_grade != "external_digest":
        raise AptusHandoffError(
            "aptus handoff requires external_digest verification of the sealed bundle"
        )

    train_bytes = (bundle_path / "data" / "train.jsonl").read_bytes()
    evaluation_bytes = (bundle_path / "data" / "evaluation.jsonl").read_bytes()
    provenance_bytes = (
        bundle_path / "metadata" / "row-provenance.jsonl"
    ).read_bytes()
    validation_bytes = (bundle_path / "validation.json").read_bytes()

    provenance_rows = _load_jsonl_objects(provenance_bytes)
    train_rows = _load_jsonl_objects(train_bytes)
    evaluation_rows = _load_jsonl_objects(evaluation_bytes)
    if not provenance_rows:
        raise AptusHandoffError("sealed provenance stream is empty")

    first = provenance_rows[0]
    row_schema = _infer_row_schema(train_rows, evaluation_rows, first)
    assignment_digest = portable_assignment_digest(provenance_rows)
    source_ids = tuple(
        sorted({source_id for row in provenance_rows for source_id in row["source_ids"]})
    )

    body = {
        "schema_version": APTUS_HANDOFF_SCHEMA_VERSION,
        "bundle_id": verification.bundle_id,
        "manifest_sha256": expected_manifest_sha256,
        "content_root_sha256": verification.content_root_sha256,
        "dataset_snapshot_id": verification.dataset_snapshot_id,
        "validation_report_id": verification.validation_report_id,
        "plan_id": first["plan_id"],
        "recipe_id": first["recipe_id"],
        "construction_result_id": first["construction_result_id"],
        "split_result_id": first["split_result_id"],
        "objective_id": first["objective_id"],
        "row_schema": row_schema,
        "assignment_digest": assignment_digest,
        "source_ids": source_ids,
        "train": PartitionBinding(
            path="data/train.jsonl",
            role="training-partition",
            sha256=sha256_digest(train_bytes),
            record_count=len(train_rows),
            byte_size=len(train_bytes),
        ).model_dump(mode="json"),
        "evaluation": PartitionBinding(
            path="data/evaluation.jsonl",
            role="evaluation-partition",
            sha256=sha256_digest(evaluation_bytes),
            record_count=len(evaluation_rows),
            byte_size=len(evaluation_bytes),
        ).model_dump(mode="json"),
        "provenance": FileBinding(
            path="metadata/row-provenance.jsonl",
            role="row-provenance",
            media_type="application/jsonl",
            sha256=sha256_digest(provenance_bytes),
            byte_size=len(provenance_bytes),
        ).model_dump(mode="json"),
        "validation": FileBinding(
            path="validation.json",
            role="dataset-validation-report",
            media_type="application/json",
            sha256=sha256_digest(validation_bytes),
            byte_size=len(validation_bytes),
        ).model_dump(mode="json"),
        "masking": _masking_expectation(row_schema).model_dump(mode="json"),
        "backend_capabilities": BackendCapabilities(
            accepts_row_schemas=_DEFAULT_ACCEPTED_SCHEMAS,
            rejects_row_schemas=_DEFAULT_REJECTED_SCHEMAS,
        ).model_dump(mode="json"),
        "required_verification_grade": "external_digest",
    }
    return AptusHandoffDescriptor(
        handoff_id=derive_id("ahd", body),
        **body,
    )


def consume_aptus_handoff(
    handoff: AptusHandoffDescriptor | Path | Mapping[str, Any],
    *,
    bundle: Path | None = None,
) -> AptusConsumptionReport:
    """Independent consumer check for a sealed bundle + handoff descriptor.

    This is the Veriformis-side proof that a training system can accept the
    handoff without rewriting partitions: external digest, file digests, row
    schema, masking-compatible payloads, and assignment projection.
    """
    descriptor = _coerce_handoff(handoff)
    findings: list[str] = []
    bundle_path = Path(bundle) if bundle is not None else None
    if bundle_path is None:
        # Infer sibling bundle if handoff path was provided as Path-like string in future.
        findings.append("bundle-path-required")
        return AptusConsumptionReport(
            status="rejected",
            handoff_id=descriptor.handoff_id,
            bundle_id=descriptor.bundle_id,
            assignment_digest=descriptor.assignment_digest,
            verified_grade="none",
            findings=tuple(findings),
        )

    try:
        verification = verify_finished_bundle(
            bundle_path,
            expected_manifest_sha256=descriptor.manifest_sha256,
        )
    except Exception as exc:  # noqa: BLE001 - surface all verify failures as findings
        findings.append(f"bundle-verification-failed:{exc}")
        return AptusConsumptionReport(
            status="rejected",
            handoff_id=descriptor.handoff_id,
            bundle_id=descriptor.bundle_id,
            assignment_digest=descriptor.assignment_digest,
            verified_grade="none",
            findings=tuple(findings),
        )

    if verification.trust_grade != "external_digest":
        findings.append("verification-grade-not-external_digest")
    if verification.bundle_id != descriptor.bundle_id:
        findings.append("bundle-id-mismatch")
    if verification.content_root_sha256 != descriptor.content_root_sha256:
        findings.append("content-root-mismatch")
    if verification.dataset_snapshot_id != descriptor.dataset_snapshot_id:
        findings.append("snapshot-id-mismatch")
    if verification.validation_report_id != descriptor.validation_report_id:
        findings.append("validation-report-id-mismatch")

    def _rejected(verified_grade: str) -> AptusConsumptionReport:
        return AptusConsumptionReport(
            status="rejected",
            handoff_id=descriptor.handoff_id,
            bundle_id=descriptor.bundle_id,
            assignment_digest=descriptor.assignment_digest,
            verified_grade=verified_grade,
            findings=tuple(findings),
        )

    # Cross-check every binding against the externally anchored manifest the
    # verification just proved, then read each bound file exactly once. Any
    # missing or mismatched binding rejects with findings instead of raising.
    try:
        manifest_bytes = (bundle_path / MANIFEST_NAME).read_bytes()
        if sha256_digest(manifest_bytes) != descriptor.manifest_sha256:
            raise AptusHandoffError(
                "sealed manifest bytes changed after verification"
            )
        manifest = FinishedBundleManifest.from_json_bytes(manifest_bytes)
    except Exception as exc:  # noqa: BLE001 - reject, never crash post-verify
        findings.append(f"manifest-read-failed:{exc}")
        return _rejected(verification.trust_grade)
    manifest_entries = {file.path: (file.sha256, file.size) for file in manifest.files}

    payloads: dict[str, bytes] = {}
    binding_failed = False
    for binding in (
        descriptor.train,
        descriptor.evaluation,
        descriptor.provenance,
        descriptor.validation,
    ):
        manifest_entry = manifest_entries.get(binding.path)
        if manifest_entry is None:
            findings.append(f"manifest-binding-missing:{binding.path}")
            binding_failed = True
        elif manifest_entry != (binding.sha256, binding.byte_size):
            findings.append(f"manifest-binding-mismatch:{binding.path}")
            binding_failed = True
        path = bundle_path / binding.path
        try:
            data = path.read_bytes()
        except OSError as exc:
            findings.append(f"missing-file:{binding.path}:{exc}")
            binding_failed = True
            continue
        if sha256_digest(data) != binding.sha256:
            findings.append(f"digest-mismatch:{binding.path}")
            binding_failed = True
        if len(data) != binding.byte_size:
            findings.append(f"byte-size-mismatch:{binding.path}")
            binding_failed = True
        payloads[binding.path] = data
    if binding_failed:
        return _rejected(verification.trust_grade)

    train_rows = _load_jsonl_objects(payloads[descriptor.train.path])
    evaluation_rows = _load_jsonl_objects(payloads[descriptor.evaluation.path])
    if len(train_rows) != descriptor.train.record_count:
        findings.append("train-record-count-mismatch")
    if len(evaluation_rows) != descriptor.evaluation.record_count:
        findings.append("evaluation-record-count-mismatch")

    for partition_name, rows in (
        ("train", train_rows),
        ("evaluation", evaluation_rows),
    ):
        for index, row in enumerate(rows):
            try:
                _payload_contract(descriptor.row_schema, row)  # type: ignore[arg-type]
            except Exception as exc:  # noqa: BLE001
                findings.append(f"row-schema-invalid:{partition_name}:{index}:{exc}")

    if descriptor.row_schema in descriptor.backend_capabilities.rejects_row_schemas:
        findings.append(
            f"backend-rejects-row-schema:{descriptor.row_schema}"
        )
    if descriptor.row_schema not in descriptor.backend_capabilities.accepts_row_schemas:
        if descriptor.row_schema not in descriptor.backend_capabilities.rejects_row_schemas:
            findings.append(f"backend-unknown-row-schema:{descriptor.row_schema}")

    provenance_rows = _load_jsonl_objects(payloads[descriptor.provenance.path])
    recomputed = portable_assignment_digest(provenance_rows)
    if recomputed != descriptor.assignment_digest:
        findings.append("assignment-digest-mismatch")

    status: Literal["accepted", "rejected"] = (
        "accepted" if not findings else "rejected"
    )
    return AptusConsumptionReport(
        status=status,
        handoff_id=descriptor.handoff_id,
        bundle_id=descriptor.bundle_id,
        assignment_digest=descriptor.assignment_digest,
        verified_grade=verification.trust_grade,
        findings=tuple(findings),
    )


def portable_assignment_digest(provenance_rows: list[dict[str, Any]]) -> str:
    """Recompute the handoff assignment digest from sealed provenance rows."""
    entries = []
    for row in provenance_rows:
        entries.append(
            {
                "record_id": row["record_id"],
                "partition": row["partition"],
                "assignment_id": row["assignment_id"],
                "leakage_group_id": row["leakage_group_id"],
            }
        )
    entries.sort(key=lambda item: item["record_id"])
    return canonical_digest(
        {
            "schema_version": _ASSIGNMENT_PROJECTION_SCHEMA,
            "assignments": entries,
        }
    )


def _masking_expectation(row_schema: str) -> MaskingExpectation:
    if row_schema == "text":
        return MaskingExpectation(
            row_schema=row_schema,
            supervised_boundary="full-sequence",
            notes="Entire text sequence is supervised.",
        )
    if row_schema == "prompt_completion":
        return MaskingExpectation(
            row_schema=row_schema,
            supervised_boundary="completion-only",
            notes="Prompt is context; completion receives supervision.",
        )
    if row_schema == "instruction_output":
        return MaskingExpectation(
            row_schema=row_schema,
            supervised_boundary="output-only",
            notes="Instruction and input are context; output receives supervision.",
        )
    if row_schema == "messages":
        return MaskingExpectation(
            row_schema=row_schema,
            supervised_boundary="final-assistant-suffix",
            notes="Only the final assistant message receives supervision.",
        )
    raise AptusHandoffError(f"unsupported handoff row schema {row_schema!r}")


def _infer_row_schema(
    train_rows: list[dict[str, Any]],
    evaluation_rows: list[dict[str, Any]],
    first_provenance: Mapping[str, Any],
) -> str:
    sample = train_rows[0] if train_rows else (
        evaluation_rows[0] if evaluation_rows else None
    )
    if sample is None:
        raise AptusHandoffError("sealed partitions contain no rows")
    keys = set(sample)
    if keys == {"text"}:
        return "text"
    if keys == {"prompt", "completion"}:
        return "prompt_completion"
    if keys == {"instruction", "input", "output"} or keys == {
        "instruction",
        "output",
    }:
        return "instruction_output"
    if keys == {"messages"}:
        return "messages"
    raise AptusHandoffError(f"unable to infer product row schema from keys {sorted(keys)}")


def _load_jsonl_objects(data: bytes) -> list[dict[str, Any]]:
    if not data:
        return []
    rows: list[dict[str, Any]] = []
    # Sealed JSONL frames records on the single byte b"\n" only. splitlines()
    # would also break on U+2028/U+2029/U+0085, which row text legitimately
    # preserves raw (ensure_ascii=False escapes only characters below 0x20).
    for line_number, line in enumerate(data.decode("utf-8").split("\n"), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AptusHandoffError(
                f"invalid JSONL at line {line_number}: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise AptusHandoffError(
                f"JSONL line {line_number} is not a JSON object"
            )
        rows.append(value)
    return rows


def _coerce_handoff(
    value: AptusHandoffDescriptor | Path | Mapping[str, Any],
) -> AptusHandoffDescriptor:
    if isinstance(value, AptusHandoffDescriptor):
        return value
    if isinstance(value, Path):
        raw = json.loads(value.read_text(encoding="utf-8"))
        return AptusHandoffDescriptor.model_validate(raw)
    if isinstance(value, Mapping):
        return AptusHandoffDescriptor.model_validate(dict(value))
    raise AptusHandoffError("unsupported handoff input type")
