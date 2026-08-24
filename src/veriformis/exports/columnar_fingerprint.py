"""Phase 9.3 columnar semantic fingerprints, independent of library metadata."""

from __future__ import annotations

import json
from collections.abc import Mapping as MappingABC
from collections.abc import Sequence
from functools import lru_cache
from importlib import resources
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from veriformis.contracts import (
    COLUMNAR_FINGERPRINT_CONTRACT_ID,
    COLUMNAR_FINGERPRINT_CONTRACT_VERSION,
    COLUMNAR_FINGERPRINT_SCHEMA_ID,
    V1_ROW_SCHEMA_KINDS,
)
from veriformis.errors import ExportContractError
from veriformis.exports.columnar_schemas import (
    MESSAGE_ROLES,
    MESSAGE_STRUCT_FIELDS,
    PAYLOAD_FIELDS,
    columnar_schema_digest,
)
from veriformis.identity import canonical_digest, lossless_json_bytes, sha256_digest, validate_sha256

COLUMNAR_FINGERPRINT_DATA_NAME = "columnar_fingerprint-v1.json"
RowSchema = Literal["instruction_output", "messages", "prompt_completion", "text"]
Partition = Literal["evaluation", "train"]
EXCLUDED_LIBRARY_METADATA: tuple[str, ...] = (
    "arrow_endianness",
    "compression",
    "created_by",
    "dictionary_encoding",
    "large_utf8_vs_utf8",
    "parquet_key_value_metadata",
    "row_group_layout",
    "statistics",
)
PREIMAGE_FIELDS: tuple[str, ...] = (
    "partition",
    "payloads",
    "record_count",
    "row_schema",
    "schema_id",
    "schema_pin_digest",
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class ColumnarFingerprintContract(_StrictModel):
    contract_id: Literal["veriformis.columnar-semantic-fingerprint"]
    contract_version: Literal[1]
    determinism_claim: Literal["semantic_content_only"]
    excluded_library_metadata: tuple[str, ...]
    preimage_fields: tuple[str, ...]
    receipt_binds: Literal["exact_emitted_bytes"]
    schema_id: Literal["veriformis.columnar-semantic-fingerprint/v1"]
    state: Literal["implemented"]

    @field_validator("excluded_library_metadata", "preimage_fields", mode="before")
    @classmethod
    def _tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> ColumnarFingerprintContract:
        if self.schema_id != COLUMNAR_FINGERPRINT_SCHEMA_ID:
            raise ExportContractError("columnar fingerprint schema_id mismatch")
        if self.contract_id != COLUMNAR_FINGERPRINT_CONTRACT_ID:
            raise ExportContractError("columnar fingerprint contract_id mismatch")
        if self.contract_version != COLUMNAR_FINGERPRINT_CONTRACT_VERSION:
            raise ExportContractError("columnar fingerprint contract_version mismatch")
        if self.excluded_library_metadata != EXCLUDED_LIBRARY_METADATA:
            raise ExportContractError("excluded library metadata must be the closed v1 list")
        if self.preimage_fields != PREIMAGE_FIELDS:
            raise ExportContractError("preimage_fields must be the closed v1 list")
        return self


class ColumnarPartitionPreimage(_StrictModel):
    partition: Partition
    payloads: tuple[dict[str, Any], ...]
    record_count: int
    row_schema: RowSchema
    schema_id: Literal["veriformis.columnar-semantic-fingerprint/v1"]
    schema_pin_digest: str

    @field_validator("payloads", mode="before")
    @classmethod
    def _tuple_payloads(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @field_validator("schema_pin_digest")
    @classmethod
    def _digest(cls, value: str) -> str:
        return validate_sha256(value)

    @model_validator(mode="after")
    def _closed(self) -> ColumnarPartitionPreimage:
        if self.row_schema not in V1_ROW_SCHEMA_KINDS:
            raise ExportContractError("fingerprint names an unsupported row schema")
        if self.record_count != len(self.payloads):
            raise ExportContractError("fingerprint record_count must match payloads")
        if self.schema_pin_digest != columnar_schema_digest():
            raise ExportContractError("fingerprint schema_pin_digest must match item 9.2 pins")
        for ordinal, payload in enumerate(self.payloads):
            _require_product_payload(self.row_schema, payload, ordinal=ordinal)
        return self


def _require_nonempty_string(value: Any, label: str) -> None:
    if not isinstance(value, str) or value == "":
        raise ExportContractError(f"{label} must be a nonempty string")


def _refuse_null(value: Any, *, path: str) -> None:
    if value is None:
        raise ExportContractError(f"null is unrepresentable at {path}")
    if isinstance(value, MappingABC):
        for key, item in value.items():
            _refuse_null(item, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _refuse_null(item, path=f"{path}[{index}]")


def _require_product_payload(row_schema: str, payload: Any, *, ordinal: int) -> None:
    if not isinstance(payload, MappingABC):
        raise ExportContractError(f"payload {ordinal} must be an object")
    _refuse_null(payload, path=f"payload[{ordinal}]")
    expected = set(PAYLOAD_FIELDS[row_schema])
    if set(payload) != expected:
        raise ExportContractError(
            f"payload {ordinal} keys must be exactly {tuple(sorted(expected))}"
        )
    if row_schema == "messages":
        messages = payload["messages"]
        if not isinstance(messages, list) or len(messages) != 2:
            raise ExportContractError(
                f"payload {ordinal} messages require exactly two ordered turns"
            )
        for index, (message, role) in enumerate(zip(messages, MESSAGE_ROLES, strict=True)):
            if not isinstance(message, MappingABC) or set(message) != set(
                MESSAGE_STRUCT_FIELDS
            ):
                raise ExportContractError(
                    f"payload {ordinal} messages turn {index} has an invalid shape"
                )
            if message.get("role") != role:
                raise ExportContractError(
                    f"payload {ordinal} messages turn {index} must have role {role!r}"
                )
            _require_nonempty_string(
                message.get("content"),
                f"payload {ordinal} messages turn {index} content",
            )
        return
    for key in PAYLOAD_FIELDS[row_schema]:
        _require_nonempty_string(payload.get(key), f"payload {ordinal} {key}")


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _dump_contract(contract: ColumnarFingerprintContract) -> str:
    return _canonical_json(contract.model_dump(mode="json"))


@lru_cache(maxsize=1)
def columnar_fingerprint_contract() -> ColumnarFingerprintContract:
    raw = (
        resources.files("veriformis.exports")
        .joinpath(COLUMNAR_FINGERPRINT_DATA_NAME)
        .read_text(encoding="utf-8")
    )
    payload = json.loads(raw)
    if not isinstance(payload, MappingABC):
        raise ExportContractError("columnar fingerprint contract must be an object")
    contract = ColumnarFingerprintContract.model_validate(payload)
    if raw != _dump_contract(contract):
        raise ExportContractError("columnar fingerprint contract is not canonical JSON")
    return contract


def columnar_fingerprint_contract_json() -> str:
    return _dump_contract(columnar_fingerprint_contract())


def discover_columnar_fingerprint_contract() -> dict[str, Any]:
    return json.loads(columnar_fingerprint_contract_json())


def _copied_payloads(payloads: Sequence[MappingABC[str, Any]]) -> tuple[dict[str, Any], ...]:
    encoded = lossless_json_bytes(list(payloads)).decode("utf-8")
    copied = json.loads(encoded)
    if not isinstance(copied, list):
        raise ExportContractError("payloads must encode as a JSON array")
    return tuple(copied)


def columnar_partition_preimage(
    *,
    row_schema: RowSchema,
    partition: Partition,
    payloads: Sequence[MappingABC[str, Any]],
) -> ColumnarPartitionPreimage:
    """Return the versioned semantic preimage for one train or evaluation partition."""
    columnar_fingerprint_contract()
    copied = _copied_payloads(payloads)
    return ColumnarPartitionPreimage.model_validate(
        {
            "partition": partition,
            "payloads": copied,
            "record_count": len(copied),
            "row_schema": row_schema,
            "schema_id": COLUMNAR_FINGERPRINT_SCHEMA_ID,
            "schema_pin_digest": columnar_schema_digest(),
        }
    )


def columnar_partition_preimage_bytes(
    *,
    row_schema: RowSchema,
    partition: Partition,
    payloads: Sequence[MappingABC[str, Any]],
) -> bytes:
    """Lossless canonical bytes of one partition preimage."""
    preimage = columnar_partition_preimage(
        row_schema=row_schema,
        partition=partition,
        payloads=payloads,
    )
    return lossless_json_bytes(preimage.model_dump(mode="json"))


def columnar_partition_fingerprint(
    *,
    row_schema: RowSchema,
    partition: Partition,
    payloads: Sequence[MappingABC[str, Any]],
) -> str:
    """SHA-256 of the lossless canonical preimage. Independent of library bytes."""
    return sha256_digest(
        columnar_partition_preimage_bytes(
            row_schema=row_schema,
            partition=partition,
            payloads=payloads,
        )
    )


def columnar_dataset_fingerprint(
    *,
    row_schema: RowSchema,
    train_payloads: Sequence[MappingABC[str, Any]],
    evaluation_payloads: Sequence[MappingABC[str, Any]],
) -> str:
    """Compose the two partition fingerprints. Container identity is not included."""
    return canonical_digest(
        {
            "evaluation": columnar_partition_fingerprint(
                row_schema=row_schema,
                partition="evaluation",
                payloads=evaluation_payloads,
            ),
            "schema_id": COLUMNAR_FINGERPRINT_SCHEMA_ID,
            "train": columnar_partition_fingerprint(
                row_schema=row_schema,
                partition="train",
                payloads=train_payloads,
            ),
        }
    )
