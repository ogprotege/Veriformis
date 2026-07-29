"""Artifact-bound evidence for scalar values stored in strict document IR.

Visible text continues to use :mod:`veriformis.evidence` unchanged.  This
module covers metadata such as a link target or heading level that exists in
the immutable IR artifact but not necessarily in the canonical text stream.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from veriformis.errors import EvidenceError, InvalidIRError
from veriformis.identity import (
    canonical_digest,
    derive_id,
    lossless_json_bytes,
    sha256_digest,
    validate_id,
    validate_sha256,
)
from veriformis.ir import Document
from veriformis.ir.serde import IR_SCHEMA_VERSION, document_from_dict

from ._json import reject_floats


IRArtifactKind = Literal["document-ir", "cleaned-document-ir"]
IRFieldEncoding = Literal["identity-string", "json-scalar-v1"]
JSONScalar = str | int | bool | None


class IRFieldEvidence(BaseModel):
    """Proof that one emitted string resolves from one strict-IR scalar."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["veriformis.ir-field-evidence/v1"] = (
        "veriformis.ir-field-evidence/v1"
    )
    kind: Literal["ir_field"] = "ir_field"
    evidence_id: str
    source_id: str
    artifact_id: str
    artifact_kind: IRArtifactKind
    document_sha256: str
    ir_schema_version: Literal["veriformis.ir/v1"] = IR_SCHEMA_VERSION
    json_pointer: str
    source_value_digest: str
    encoding: IRFieldEncoding
    output_sha256: str
    context_digest: str

    @model_validator(mode="before")
    @classmethod
    def _require_exact_fields(cls, value: Any) -> Any:
        if isinstance(value, cls) or not isinstance(value, dict):
            return value
        expected = set(cls.model_fields)
        actual = set(value)
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            raise ValueError(
                "IRFieldEvidence fields do not match its persisted schema; "
                f"missing={missing!r}, extra={extra!r}"
            )
        return value

    @model_validator(mode="after")
    def _validate_evidence(self) -> IRFieldEvidence:
        validate_id(self.evidence_id, kind="evd")
        validate_id(self.source_id, kind="src")
        validate_id(self.artifact_id, kind="art")
        validate_sha256(self.document_sha256)
        validate_sha256(self.source_value_digest)
        validate_sha256(self.output_sha256)
        validate_sha256(self.context_digest)
        _parse_pointer(self.json_pointer)
        expected_id = derive_id(
            "evd",
            self.model_dump(mode="json", exclude={"evidence_id"}),
        )
        if self.evidence_id != expected_id:
            raise ValueError("IR-field evidence identity mismatch")
        return self


def make_ir_field_evidence(
    *,
    source_id: str,
    artifact_id: str,
    artifact_kind: IRArtifactKind,
    document_json: bytes,
    json_pointer: str,
    context: dict[str, Any],
) -> tuple[str, IRFieldEvidence]:
    """Resolve a strict-IR scalar and bind its emitted string to the artifact."""
    try:
        reject_floats(context)
    except (TypeError, ValueError) as exc:
        raise EvidenceError(f"invalid IR-field evidence context: {exc}") from exc
    document_value, document = load_ir_document_json(document_json)
    if document.source_id != source_id:
        raise EvidenceError("IR artifact and evidence source identities differ")
    try:
        validate_id(artifact_id, kind="art")
    except (TypeError, ValueError) as exc:
        raise EvidenceError(f"invalid IR artifact identity: {exc}") from exc
    scalar = resolve_json_pointer(document_value, json_pointer)
    output, encoding = encode_ir_scalar(scalar)
    payload = {
        "schema_version": "veriformis.ir-field-evidence/v1",
        "kind": "ir_field",
        "source_id": source_id,
        "artifact_id": artifact_id,
        "artifact_kind": artifact_kind,
        "document_sha256": sha256_digest(document_json),
        "ir_schema_version": IR_SCHEMA_VERSION,
        "json_pointer": json_pointer,
        "source_value_digest": canonical_digest(scalar),
        "encoding": encoding,
        "output_sha256": sha256_digest(output),
        "context_digest": canonical_digest(context),
    }
    try:
        evidence = IRFieldEvidence(
            evidence_id=derive_id("evd", payload),
            **payload,
        )
    except (TypeError, ValueError) as exc:
        raise EvidenceError(f"invalid IR-field evidence: {exc}") from exc
    return output, evidence


def resolve_ir_field_evidence(
    evidence: IRFieldEvidence,
    *,
    source_id: str,
    artifact_id: str,
    artifact_kind: IRArtifactKind,
    document_json: bytes,
    context: dict[str, Any],
) -> str:
    """Replay an IR-field proof against the exact declared artifact bytes."""
    try:
        reject_floats(context)
    except (TypeError, ValueError) as exc:
        raise EvidenceError(f"invalid IR-field evidence context: {exc}") from exc
    # Revalidate even when callers produced an object through an unsafe copy.
    try:
        checked = IRFieldEvidence.model_validate_json(
            lossless_json_bytes(evidence.model_dump(mode="json"))
        )
    except (TypeError, ValueError) as exc:
        raise EvidenceError(f"invalid IR-field evidence: {exc}") from exc
    if checked.source_id != source_id:
        raise EvidenceError("IR-field evidence names a different source")
    if checked.artifact_id != artifact_id:
        raise EvidenceError("IR-field evidence names a different artifact")
    if checked.artifact_kind != artifact_kind:
        raise EvidenceError("IR-field evidence artifact kind mismatch")
    if checked.document_sha256 != sha256_digest(document_json):
        raise EvidenceError("IR artifact content digest mismatch")
    value, document = load_ir_document_json(document_json)
    if document.source_id != source_id:
        raise EvidenceError("IR artifact and evidence source identities differ")
    scalar = resolve_json_pointer(value, checked.json_pointer)
    if canonical_digest(scalar) != checked.source_value_digest:
        raise EvidenceError("IR-field source value digest mismatch")
    output, encoding = encode_ir_scalar(scalar)
    if encoding != checked.encoding:
        raise EvidenceError("IR-field evidence encoding mismatch")
    if sha256_digest(output) != checked.output_sha256:
        raise EvidenceError("IR-field evidence output digest mismatch")
    if canonical_digest(context) != checked.context_digest:
        raise EvidenceError("IR-field evidence context mismatch")
    return output


def load_ir_document_json(document_json: bytes) -> tuple[dict[str, Any], Document]:
    """Load one UTF-8 JSON IR artifact with duplicate and non-finite rejection."""
    if not isinstance(document_json, bytes):
        raise EvidenceError("IR artifact content must be exact bytes")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON object key {key!r}")
            value[key] = item
        return value

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number {value!r}")

    try:
        decoded = document_json.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise EvidenceError(f"invalid strict IR JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError("IR artifact root must be an object")
    try:
        document = document_from_dict(value)
    except (InvalidIRError, TypeError, ValueError) as exc:
        raise EvidenceError(f"invalid document IR artifact: {exc}") from exc
    return value, document


def resolve_json_pointer(value: Any, pointer: str) -> JSONScalar:
    """Resolve a canonical RFC 6901 pointer and require a JSON scalar leaf."""
    try:
        tokens = _parse_pointer(pointer)
    except (TypeError, ValueError) as exc:
        raise EvidenceError(str(exc)) from exc
    current = value
    for token in tokens:
        if isinstance(current, dict):
            if token not in current:
                raise EvidenceError(f"IR JSON Pointer key {token!r} does not exist")
            current = current[token]
        elif isinstance(current, list):
            if token == "-" or not token.isascii() or not token.isdecimal():
                raise EvidenceError("IR JSON Pointer array index is not canonical")
            if len(token) > 1 and token.startswith("0"):
                raise EvidenceError("IR JSON Pointer array index has a leading zero")
            index = int(token)
            if index >= len(current):
                raise EvidenceError("IR JSON Pointer array index is out of bounds")
            current = current[index]
        else:
            raise EvidenceError("IR JSON Pointer traverses through a scalar")
    if current is not None and type(current) not in (str, int, bool):
        raise EvidenceError("IR JSON Pointer must resolve to a scalar leaf")
    return current


def encode_ir_scalar(value: JSONScalar) -> tuple[str, IRFieldEncoding]:
    """Encode one IR scalar without normalizing its exact string content."""
    if isinstance(value, str):
        return value, "identity-string"
    if value is not None and type(value) not in (int, bool):
        raise EvidenceError("unsupported IR scalar type")
    return lossless_json_bytes(value).decode("utf-8"), "json-scalar-v1"


def _parse_pointer(pointer: str) -> tuple[str, ...]:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("IR JSON Pointer must be a non-empty RFC 6901 pointer")
    tokens: list[str] = []
    for raw in pointer[1:].split("/"):
        token: list[str] = []
        index = 0
        while index < len(raw):
            character = raw[index]
            if character != "~":
                token.append(character)
                index += 1
                continue
            if index + 1 >= len(raw) or raw[index + 1] not in ("0", "1"):
                raise ValueError("IR JSON Pointer contains an invalid escape")
            token.append("~" if raw[index + 1] == "0" else "/")
            index += 2
        tokens.append("".join(token))
    return tuple(tokens)


__all__ = [
    "IRArtifactKind",
    "IRFieldEncoding",
    "IRFieldEvidence",
    "encode_ir_scalar",
    "load_ir_document_json",
    "make_ir_field_evidence",
    "resolve_ir_field_evidence",
    "resolve_json_pointer",
]
