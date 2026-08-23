"""Phase 9.2 packaged Arrow and Hugging Face feature schema pins."""

from __future__ import annotations

import json
from collections.abc import Mapping as MappingABC
from functools import lru_cache
from importlib import resources
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from veriformis.contracts import (
    COLUMNAR_SCHEMA_CONTRACT_ID,
    COLUMNAR_SCHEMA_SCHEMA_ID,
    COLUMNAR_SCHEMA_CONTRACT_VERSION,
    V1_ROW_SCHEMA_KINDS,
)
from veriformis.errors import ExportContractError
from veriformis.identity import sha256_digest
from veriformis.taxonomy import UNEXECUTABLE_PHYSICAL_CONTAINER_ITEMS

COLUMNAR_SCHEMA_DATA_NAME = "columnar_schemas-v1.json"
RowSchema = Literal["instruction_output", "messages", "prompt_completion", "text"]
ArrowKind = Literal["list", "struct", "utf8"]
HfKind = Literal["list", "struct", "value"]
PackageName = Literal["datasets", "pyarrow"]
PackageRole = Literal["hugging-face-dataset", "parquet-and-arrow-ipc"]
ContainerId = Literal["arrow", "hugging-face-dataset", "parquet"]

PAYLOAD_FIELDS: dict[str, tuple[str, ...]] = {
    "instruction_output": ("instruction", "input", "output"),
    "messages": ("messages",),
    "prompt_completion": ("prompt", "completion"),
    "text": ("text",),
}
MESSAGE_STRUCT_FIELDS: tuple[str, ...] = ("role", "content")
MESSAGE_ROLES: tuple[str, ...] = ("user", "assistant")
SORTED_ROW_SCHEMAS: tuple[str, ...] = tuple(sorted(V1_ROW_SCHEMA_KINDS))
SORTED_PACKAGES: tuple[str, ...] = ("datasets", "pyarrow")
SORTED_CONTAINERS: tuple[str, ...] = tuple(sorted(UNEXECUTABLE_PHYSICAL_CONTAINER_ITEMS))


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class ArrowType(_StrictModel):
    kind: ArrowKind
    item: ArrowType | None = None
    item_nullable: Literal[False] | None = None
    fields: tuple[ArrowField, ...] | None = None

    @field_validator("fields", mode="before")
    @classmethod
    def _tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> ArrowType:
        if self.kind == "utf8":
            if self.item is not None or self.fields is not None or self.item_nullable is not None:
                raise ExportContractError("utf8 Arrow type must not nest")
            return self
        if self.kind == "list":
            if self.item is None or self.item_nullable is not False or self.fields is not None:
                raise ExportContractError("list Arrow type requires a non-null item")
            return self
        if self.item is not None or self.item_nullable is not None or self.fields is None:
            raise ExportContractError("struct Arrow type requires named fields")
        names = tuple(field.name for field in self.fields)
        if not names:
            raise ExportContractError("struct Arrow type must not be empty")
        if len(names) != len(set(names)):
            raise ExportContractError("struct Arrow fields must be unique")
        return self


class ArrowField(_StrictModel):
    arrow_type: ArrowType
    name: str
    nullable: Literal[False]

    @model_validator(mode="after")
    def _closed(self) -> ArrowField:
        if not self.name.strip():
            raise ExportContractError("Arrow field name must be nonempty")
        return self


class HfFeature(_StrictModel):
    kind: HfKind
    dtype: Literal["string"] | None = None
    item: HfFeature | None = None
    item_nullable: Literal[False] | None = None
    fields: tuple[HfField, ...] | None = None

    @field_validator("fields", mode="before")
    @classmethod
    def _tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> HfFeature:
        if self.kind == "value":
            if self.dtype != "string":
                raise ExportContractError("value feature dtype must be string")
            if self.item is not None or self.fields is not None or self.item_nullable is not None:
                raise ExportContractError("value feature must not nest")
            return self
        if self.dtype is not None:
            raise ExportContractError("nested Hugging Face features must not set dtype")
        if self.kind == "list":
            if self.item is None or self.item_nullable is not False or self.fields is not None:
                raise ExportContractError("list feature requires a non-null item")
            return self
        if self.item is not None or self.item_nullable is not None or self.fields is None:
            raise ExportContractError("struct feature requires named fields")
        names = tuple(field.name for field in self.fields)
        if not names:
            raise ExportContractError("struct feature must not be empty")
        if len(names) != len(set(names)):
            raise ExportContractError("struct feature fields must be unique")
        return self


class HfField(_StrictModel):
    hf_feature: HfFeature
    name: str
    nullable: Literal[False]

    @model_validator(mode="after")
    def _closed(self) -> HfField:
        if not self.name.strip():
            raise ExportContractError("Hugging Face field name must be nonempty")
        return self


ArrowType.model_rebuild()
ArrowField.model_rebuild()
HfFeature.model_rebuild()
HfField.model_rebuild()


class ColumnarField(_StrictModel):
    arrow_type: ArrowType
    hf_feature: HfFeature
    name: str
    nullable: Literal[False]

    @model_validator(mode="after")
    def _closed(self) -> ColumnarField:
        if not self.name.strip():
            raise ExportContractError("column name must be nonempty")
        if not _arrow_matches_hf(self.arrow_type, self.hf_feature):
            raise ExportContractError(
                f"column {self.name!r} Arrow type does not match its Hugging Face feature"
            )
        return self


class RowSchemaPin(_StrictModel):
    fields: tuple[ColumnarField, ...]
    notes: str
    source_row_schema: RowSchema
    message_roles: tuple[str, ...] | None = None
    message_turn_count: Literal[2] | None = None

    @field_validator("fields", "message_roles", mode="before")
    @classmethod
    def _tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> RowSchemaPin:
        expected = PAYLOAD_FIELDS[self.source_row_schema]
        names = tuple(field.name for field in self.fields)
        if names != expected:
            raise ExportContractError(
                f"{self.source_row_schema} columns must be {expected} in product order"
            )
        if not self.notes.strip():
            raise ExportContractError("row-schema notes must be nonempty")
        if self.source_row_schema == "messages":
            if self.message_roles != MESSAGE_ROLES:
                raise ExportContractError("messages roles must be user then assistant")
            if self.message_turn_count != 2:
                raise ExportContractError("messages require exactly two turns")
            messages = self.fields[0]
            if messages.arrow_type.kind != "list" or messages.arrow_type.item is None:
                raise ExportContractError("messages must be a list of structs")
            item = messages.arrow_type.item
            if item.kind != "struct" or item.fields is None:
                raise ExportContractError("messages list item must be a struct")
            nested = tuple(nested_field.name for nested_field in item.fields)
            if nested != MESSAGE_STRUCT_FIELDS:
                raise ExportContractError(
                    "messages struct fields must be role then content"
                )
            for nested_field in item.fields:
                if nested_field.arrow_type.kind != "utf8":
                    raise ExportContractError("messages struct fields must be utf8")
        else:
            if self.message_roles is not None or self.message_turn_count is not None:
                raise ExportContractError("only messages pin turn facts")
            for column in self.fields:
                if column.arrow_type.kind != "utf8":
                    raise ExportContractError(
                        f"{self.source_row_schema} columns must be utf8"
                    )
        return self


class ColumnarPackagePin(_StrictModel):
    docs_reviewed_on: str
    extra: Literal["columnar"]
    license: Literal["Apache-2.0"]
    package: PackageName
    primary_docs_url: str
    role: PackageRole
    version_range: str

    @model_validator(mode="after")
    def _closed(self) -> ColumnarPackagePin:
        if self.docs_reviewed_on != "2026-08-23":
            raise ExportContractError("package docs_reviewed_on must be 2026-08-23")
        if not self.primary_docs_url.startswith("https://"):
            raise ExportContractError("package docs URL must be https")
        if not self.version_range.strip() or "," not in self.version_range:
            raise ExportContractError("package version_range must be a bounded range")
        expected_role = (
            "hugging-face-dataset" if self.package == "datasets" else "parquet-and-arrow-ipc"
        )
        if self.role != expected_role:
            raise ExportContractError(f"{self.package} role must be {expected_role}")
        return self


class PlannedContainerPin(_StrictModel):
    container_id: ContainerId
    executable_item: str

    @model_validator(mode="after")
    def _closed(self) -> PlannedContainerPin:
        expected = UNEXECUTABLE_PHYSICAL_CONTAINER_ITEMS[self.container_id]
        if self.executable_item != expected:
            raise ExportContractError(
                f"{self.container_id} must name item {expected}"
            )
        return self


class ColumnarSchemaCatalog(_StrictModel):
    contract_id: Literal["veriformis.columnar-schema-pin"]
    contract_version: Literal[1]
    extra: Literal["columnar"]
    null_policy: Literal["unrepresentable"]
    packages: tuple[ColumnarPackagePin, ...]
    planned_containers: tuple[PlannedContainerPin, ...]
    round_trip: Literal[False]
    row_schemas: tuple[RowSchemaPin, ...]
    schema_id: Literal["veriformis.columnar-schema-discovery/v1"]
    state: Literal["planned"]

    @field_validator("packages", "planned_containers", "row_schemas", mode="before")
    @classmethod
    def _tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> ColumnarSchemaCatalog:
        if self.schema_id != COLUMNAR_SCHEMA_SCHEMA_ID:
            raise ExportContractError("columnar schema_id mismatch")
        if self.contract_id != COLUMNAR_SCHEMA_CONTRACT_ID:
            raise ExportContractError("columnar contract_id mismatch")
        if self.contract_version != COLUMNAR_SCHEMA_CONTRACT_VERSION:
            raise ExportContractError("columnar contract_version mismatch")
        packages = tuple(item.package for item in self.packages)
        if packages != SORTED_PACKAGES:
            raise ExportContractError("packages must be datasets then pyarrow")
        containers = tuple(item.container_id for item in self.planned_containers)
        if containers != SORTED_CONTAINERS:
            raise ExportContractError("planned_containers must be sorted by container_id")
        schemas = tuple(item.source_row_schema for item in self.row_schemas)
        if schemas != SORTED_ROW_SCHEMAS:
            raise ExportContractError("row_schemas must cover every v1 schema in order")
        return self


def _arrow_matches_hf(arrow: ArrowType, feature: HfFeature) -> bool:
    if arrow.kind == "utf8":
        return feature.kind == "value" and feature.dtype == "string"
    if arrow.kind == "list":
        return (
            feature.kind == "list"
            and arrow.item_nullable is False
            and feature.item_nullable is False
            and arrow.item is not None
            and feature.item is not None
            and _arrow_matches_hf(arrow.item, feature.item)
        )
    if arrow.kind != "struct" or feature.kind != "struct":
        return False
    if arrow.fields is None or feature.fields is None:
        return False
    if len(arrow.fields) != len(feature.fields):
        return False
    for arrow_field, hf_field in zip(arrow.fields, feature.fields, strict=True):
        if arrow_field.name != hf_field.name:
            return False
        if not _arrow_matches_hf(arrow_field.arrow_type, hf_field.hf_feature):
            return False
    return True


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _dump_catalog(catalog: ColumnarSchemaCatalog) -> str:
    return _canonical_json(catalog.model_dump(mode="json", exclude_none=True))


@lru_cache(maxsize=1)
def columnar_schema_catalog() -> ColumnarSchemaCatalog:
    raw = (
        resources.files("veriformis.exports")
        .joinpath(COLUMNAR_SCHEMA_DATA_NAME)
        .read_text(encoding="utf-8")
    )
    payload = json.loads(raw)
    if not isinstance(payload, MappingABC):
        raise ExportContractError("columnar schema catalog must be an object")
    catalog = ColumnarSchemaCatalog.model_validate(payload)
    if raw != _dump_catalog(catalog):
        raise ExportContractError("columnar schema catalog is not canonical JSON")
    return catalog


def columnar_schema_catalog_json() -> str:
    return _dump_catalog(columnar_schema_catalog())


def discover_columnar_schemas() -> dict[str, Any]:
    return json.loads(columnar_schema_catalog_json())


def columnar_schema_digest() -> str:
    return sha256_digest(columnar_schema_catalog_json())
