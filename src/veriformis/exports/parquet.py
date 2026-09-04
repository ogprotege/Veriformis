"""Generic Parquet export container v1. PyArrow is imported only at render time."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from veriformis.contracts import V1_ROW_SCHEMA_KINDS
from veriformis.datasets import ProductRow, RowProvenance, RowSet
from veriformis.datasets.serialization import row_provenance_from_json_bytes
from veriformis.errors import ExportContractError, ExportVerificationError, VeriformisError
from veriformis.exports._implementation import (
    _ExportImplementation,
    _RenderedDerivative,
    _ReplayedDerivative,
)
from veriformis.exports._json import canonical_export_object_from_bytes
from veriformis.exports.api import ExportProfileDescriptor
from veriformis.exports.columnar_fingerprint import columnar_partition_preimage_bytes
from veriformis.exports.columnar_schemas import PAYLOAD_FIELDS, columnar_schema_catalog
from veriformis.exports.models import (
    EXPORT_RECEIPT_PATH,
    ExportContainerProfile,
    ExportDependencyBinding,
    ExportFilePlan,
    ExportPlan,
)
from veriformis.exports.paths import validate_export_path_set
from veriformis.identity import lossless_json_bytes, sha256_digest, validate_id
from veriformis.taxonomy import LOSS_POLICY_IDS, loss_policy_for_row

PARQUET_CONTAINER_ID = "parquet"
PARQUET_CONTAINER_VERSION = 1
PARQUET_DATA_CARD_SCHEMA = "veriformis.parquet-data-card/v1"
PARQUET_TRAIN_PATH = "data/train.parquet"
PARQUET_EVALUATION_PATH = "data/evaluation.parquet"
PARQUET_DATA_CARD_PATH = "metadata/dataset-card.json"
PARQUET_PROVENANCE_PATH = "metadata/row-provenance.jsonl"
PARQUET_README_PATH = "README.md"
PARQUET_MEDIA_TYPE = "application/vnd.apache.parquet"
_SUPPORTED_ROW_SCHEMAS = tuple(sorted(V1_ROW_SCHEMA_KINDS))
_PYARROW_VERSION_RANGE = ">=19.0.0,<26.0.0"


class _StrictParquetModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )

    @classmethod
    def from_json_bytes(cls, data: bytes) -> Self:
        try:
            canonical_export_object_from_bytes(data, label=cls.__name__)
            checked = cls.model_validate_json(data)
        except (TypeError, UnicodeError, ValueError) as exc:
            raise ExportVerificationError(f"invalid {cls.__name__}: {exc}") from exc
        if checked.canonical_bytes() != data:
            raise ExportVerificationError(f"{cls.__name__} does not round-trip exactly")
        return checked

    def canonical_bytes(self) -> bytes:
        data = lossless_json_bytes(self.model_dump(mode="json"))
        try:
            checked = type(self).model_validate_json(data)
        except (TypeError, UnicodeError, ValueError) as exc:
            raise ExportContractError(f"invalid {type(self).__name__}: {exc}") from exc
        if checked != self:
            raise ExportContractError(
                f"{type(self).__name__} does not round-trip exactly"
            )
        return data


class ParquetDataCard(_StrictParquetModel):
    schema_version: Literal["veriformis.parquet-data-card/v1"] = PARQUET_DATA_CARD_SCHEMA
    container_id: Literal["parquet"] = PARQUET_CONTAINER_ID
    container_version: Literal[1] = PARQUET_CONTAINER_VERSION
    determinism_claim: Literal["semantic_content_only"] = "semantic_content_only"
    encoding: Literal["utf-8"] = "utf-8"
    row_schema: str
    columns: tuple[str, ...]
    objective_id: str
    loss_policy: str
    row_set_id: str
    split_result_id: str
    train_path: Literal["data/train.parquet"] = PARQUET_TRAIN_PATH
    train_row_count: int
    evaluation_path: Literal["data/evaluation.parquet"] = PARQUET_EVALUATION_PATH
    evaluation_row_count: int
    provenance_path: Literal["metadata/row-provenance.jsonl"] = PARQUET_PROVENANCE_PATH
    provenance_row_count: int
    provenance_alignment: Literal["train_then_evaluation"] = "train_then_evaluation"
    receipt_path: Literal["export-receipt.json"] = EXPORT_RECEIPT_PATH
    consumer_profile: None = None
    trainer_compatibility_claimed: Literal[False] = False

    @field_validator("columns", mode="before")
    @classmethod
    def _tuple_columns(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @field_validator("row_schema")
    @classmethod
    def _valid_row_schema(cls, value: str) -> str:
        if value not in V1_ROW_SCHEMA_KINDS:
            raise ValueError("data card names an unsupported row schema")
        return value

    @field_validator("objective_id")
    @classmethod
    def _valid_objective_id(cls, value: str) -> str:
        return validate_id(value, kind="obj")

    @field_validator("loss_policy")
    @classmethod
    def _valid_loss_policy(cls, value: str) -> str:
        if value not in LOSS_POLICY_IDS:
            raise ValueError("data card names an unsupported loss policy")
        return value

    @field_validator("row_set_id")
    @classmethod
    def _valid_row_set_id(cls, value: str) -> str:
        return validate_id(value, kind="rws")

    @field_validator("split_result_id")
    @classmethod
    def _valid_split_result_id(cls, value: str) -> str:
        return validate_id(value, kind="spt")

    @field_validator("train_row_count", "evaluation_row_count", "provenance_row_count")
    @classmethod
    def _valid_count(cls, value: int) -> int:
        if type(value) is not int or value < 0:
            raise ValueError("data card row counts must be non-negative integers")
        return value

    @model_validator(mode="after")
    def _closed_layout(self) -> Self:
        if self.train_row_count < 1:
            raise ValueError("parquet export requires a non-empty train partition")
        if self.columns != PAYLOAD_FIELDS[self.row_schema]:
            raise ValueError("data card columns differ from its row schema")
        if self.loss_policy != loss_policy_for_row(self.row_schema):
            raise ValueError("data card loss policy differs from its row schema")
        if self.provenance_row_count != (
            self.train_row_count + self.evaluation_row_count
        ):
            raise ValueError("data card provenance count is not aligned")
        validate_export_path_set(
            tuple(
                sorted(
                    (
                        self.receipt_path,
                        PARQUET_README_PATH,
                        self.train_path,
                        self.evaluation_path,
                        PARQUET_DATA_CARD_PATH,
                        self.provenance_path,
                    )
                )
            ),
            label="parquet data card paths",
        )
        return self


def _require_pyarrow() -> tuple[Any, Any]:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise ExportContractError(
            "physical container 'parquet' requires PyArrow; install optional extra "
            "'columnar'"
        ) from exc
    return pa, pq


def _row_pin(row_schema: str) -> Any:
    for item in columnar_schema_catalog().row_schemas:
        if item.source_row_schema == row_schema:
            return item
    raise ExportContractError(f"no columnar schema pin for {row_schema!r}")


def _pa_type(arrow: Any, pa: Any) -> Any:
    if arrow.kind == "utf8":
        return pa.string()
    if arrow.kind == "list":
        item = pa.field("item", _pa_type(arrow.item, pa), nullable=False)
        return pa.list_(item)
    fields = [
        pa.field(field.name, _pa_type(field.arrow_type, pa), nullable=False)
        for field in arrow.fields
    ]
    return pa.struct(fields)


def _arrow_schema(row_schema: str) -> Any:
    pa, _ = _require_pyarrow()
    pin = _row_pin(row_schema)
    return pa.schema(
        [
            pa.field(
                column.name,
                _pa_type(column.arrow_type, pa),
                nullable=False,
            )
            for column in pin.fields
        ]
    )


def _payloads(rows: Sequence[ProductRow]) -> tuple[dict[str, Any], ...]:
    return tuple(dict(row.payload) for row in rows)


def _partition_parquet_bytes(rows: Sequence[ProductRow], row_schema: str) -> bytes:
    pa, pq = _require_pyarrow()
    schema = _arrow_schema(row_schema)
    table = pa.Table.from_pylist(list(_payloads(rows)), schema=schema)
    sink = pa.BufferOutputStream()
    pq.write_table(
        table,
        sink,
        compression="none",
        use_dictionary=False,
        write_statistics=False,
    )
    return bytes(sink.getvalue())


def _read_partition_payloads(data: bytes, row_schema: str) -> tuple[dict[str, Any], ...]:
    pa, pq = _require_pyarrow()
    table = pq.read_table(pa.BufferReader(data))
    expected = _arrow_schema(row_schema)
    if table.schema != expected:
        raise ExportVerificationError("parquet schema differs from the pinned Arrow schema")
    return tuple(table.to_pylist())


def _provenance_jsonl(provenance: Sequence[RowProvenance]) -> bytes:
    return b"".join(
        lossless_json_bytes(item.model_dump(mode="json")) + b"\n" for item in provenance
    )


def _provenance_from_jsonl_bytes(data: bytes) -> tuple[RowProvenance, ...]:
    if not data.endswith(b"\n"):
        raise ExportVerificationError("parquet provenance must end with one canonical LF")
    rows: list[RowProvenance] = []
    for line in data.split(b"\n")[:-1]:
        if not line:
            raise ExportVerificationError("parquet provenance must have one object per line")
        try:
            payload = json.loads(line.decode("utf-8"))
            if (
                isinstance(payload, dict)
                and payload.get("schema_version") == "veriformis.imported-row-provenance/v1"
            ):
                from veriformis.mapping.finish import ImportedRowProvenance

                rows.append(ImportedRowProvenance.model_validate(payload))
            else:
                rows.append(row_provenance_from_json_bytes(line))
        except (
            RecursionError,
            TypeError,
            UnicodeError,
            ValueError,
            VeriformisError,
        ) as exc:
            raise ExportVerificationError(
                f"invalid parquet provenance row: {exc}"
            ) from exc
    checked = tuple(rows)
    if _provenance_jsonl(checked) != data:
        raise ExportVerificationError("parquet provenance bytes are not canonical")
    return checked


def _data_card(row_set: RowSet) -> ParquetDataCard:
    objective_ids = {item.objective_id for item in row_set.provenance}
    if len(objective_ids) != 1:
        raise ExportContractError(
            "parquet export requires one objective identity across the source row set"
        )
    return ParquetDataCard(
        row_schema=row_set.row_schema,
        columns=PAYLOAD_FIELDS[row_set.row_schema],
        objective_id=next(iter(objective_ids)),
        loss_policy=loss_policy_for_row(row_set.row_schema),
        row_set_id=row_set.row_set_id,
        split_result_id=row_set.split_result_id,
        train_row_count=row_set.train_row_count,
        evaluation_row_count=row_set.evaluation_row_count,
        provenance_row_count=row_set.total_row_count,
    )


def _readme_bytes(card: ParquetDataCard) -> bytes:
    columns = ", ".join(f"`{column}`" for column in card.columns)
    text = (
        "# Veriformis Parquet export\n\n"
        "This trainer-neutral export preserves the verified dataset's semantic "
        "rows and authoritative partitions as Parquet files.\n\n"
        f"- Container: `{card.container_id}` v{card.container_version}\n"
        f"- Determinism: `{card.determinism_claim}`\n"
        f"- Row schema: `{card.row_schema}`\n"
        f"- Columns: {columns}\n"
        f"- Loss policy: `{card.loss_policy}`\n"
        f"- Train: `{card.train_path}` ({card.train_row_count} rows)\n"
        f"- Evaluation: `{card.evaluation_path}` "
        f"({card.evaluation_row_count} rows)\n"
        f"- Provenance: `{card.provenance_path}` "
        f"({card.provenance_row_count} aligned rows)\n"
        f"- Source row set: `{card.row_set_id}`\n"
        f"- Source split: `{card.split_result_id}`\n\n"
        "Semantic identity is the versioned payload fingerprint from item 9.3. "
        "On-disk Parquet bytes of this pinned extra are bound by the export "
        "receipt and are not portable exact bytes across PyArrow versions. "
        "Null product fields are unrepresentable. Nested `messages` is in "
        "scope as a list of role/content structs.\n\n"
        "This generic container does not select a training objective or claim "
        "compatibility with a trainer. There is no Hub upload.\n"
    )
    return text.encode("utf-8")


def _sidecar_files(row_set: RowSet) -> dict[str, bytes]:
    card = _data_card(row_set)
    return {
        PARQUET_README_PATH: _readme_bytes(card),
        PARQUET_DATA_CARD_PATH: card.canonical_bytes(),
        PARQUET_PROVENANCE_PATH: _provenance_jsonl(row_set.provenance),
    }


def _semantic_contents(row_set: RowSet) -> dict[str, bytes]:
    files = _sidecar_files(row_set)
    files[PARQUET_TRAIN_PATH] = columnar_partition_preimage_bytes(
        row_schema=row_set.row_schema,  # type: ignore[arg-type]
        partition="train",
        payloads=_payloads(row_set.train_rows),
    )
    files[PARQUET_EVALUATION_PATH] = columnar_partition_preimage_bytes(
        row_schema=row_set.row_schema,  # type: ignore[arg-type]
        partition="evaluation",
        payloads=_payloads(row_set.evaluation_rows),
    )
    return files


def _file_plans(
    descriptor: ExportProfileDescriptor,
    row_set: RowSet,
) -> tuple[ExportFilePlan, ...]:
    if descriptor.selector != (
        PARQUET_CONTAINER_ID,
        PARQUET_CONTAINER_VERSION,
        None,
        None,
    ):
        raise ExportContractError("parquet descriptor selector changed")
    if row_set.row_schema not in descriptor.supported_row_schemas:
        raise ExportContractError(
            f"parquet v1 does not support source row schema {row_set.row_schema!r}"
        )
    contents = _semantic_contents(row_set)
    roles = {
        PARQUET_README_PATH: "readme",
        PARQUET_TRAIN_PATH: "training-partition",
        PARQUET_EVALUATION_PATH: "evaluation-partition",
        PARQUET_DATA_CARD_PATH: "dataset-card",
        PARQUET_PROVENANCE_PATH: "row-provenance",
    }
    media_types = {
        PARQUET_README_PATH: "text/markdown",
        PARQUET_TRAIN_PATH: PARQUET_MEDIA_TYPE,
        PARQUET_EVALUATION_PATH: PARQUET_MEDIA_TYPE,
        PARQUET_DATA_CARD_PATH: "application/json",
        PARQUET_PROVENANCE_PATH: "application/jsonl",
    }
    scopes = {
        PARQUET_TRAIN_PATH: "train",
        PARQUET_EVALUATION_PATH: "evaluation",
    }
    counts: dict[str, int | None] = {
        PARQUET_TRAIN_PATH: row_set.train_row_count,
        PARQUET_EVALUATION_PATH: row_set.evaluation_row_count,
        PARQUET_PROVENANCE_PATH: row_set.total_row_count,
    }
    return tuple(
        ExportFilePlan.create(
            path=path,
            role=roles[path],
            media_type=media_types[path],
            membership_scope=scopes.get(path, "none"),
            record_count=counts.get(path),
            semantic_content_sha256=sha256_digest(data),
            expected_sha256=None,
            expected_byte_size=None,
        )
        for path, data in sorted(contents.items())
    )


def _render(plan: ExportPlan, row_set: RowSet) -> _RenderedDerivative:
    if (
        plan.container_profile.container_id != PARQUET_CONTAINER_ID
        or plan.container_profile.container_version != PARQUET_CONTAINER_VERSION
        or plan.container_profile.determinism_claim != "semantic_content_only"
        or plan.consumer_profile is not None
    ):
        raise ExportVerificationError("parquet renderer received another profile")
    expected = _file_plans(PARQUET_DESCRIPTOR, row_set)
    if plan.file_plans != expected:
        raise ExportVerificationError("parquet plan differs from the pinned file contract")
    sidecars = _sidecar_files(row_set)
    files = {
        PARQUET_TRAIN_PATH: _partition_parquet_bytes(
            row_set.train_rows, row_set.row_schema
        ),
        PARQUET_EVALUATION_PATH: _partition_parquet_bytes(
            row_set.evaluation_rows, row_set.row_schema
        ),
        **sidecars,
    }
    return _RenderedDerivative(
        files=tuple(sorted(files.items())),
        train_rows=row_set.train_rows,
        evaluation_rows=row_set.evaluation_rows,
        provenance=row_set.provenance,
    )


def _replay(
    plan: ExportPlan,
    files: tuple[tuple[str, bytes], ...],
) -> _ReplayedDerivative:
    by_path = dict(files)
    card = ParquetDataCard.from_json_bytes(by_path[PARQUET_DATA_CARD_PATH])
    if card.row_schema not in V1_ROW_SCHEMA_KINDS:
        raise ExportVerificationError("parquet data card row schema is unsupported")
    train_payloads = _read_partition_payloads(by_path[PARQUET_TRAIN_PATH], card.row_schema)
    evaluation_payloads = _read_partition_payloads(
        by_path[PARQUET_EVALUATION_PATH], card.row_schema
    )
    provenance = _provenance_from_jsonl_bytes(by_path[PARQUET_PROVENANCE_PATH])
    if len(train_payloads) != card.train_row_count:
        raise ExportVerificationError("parquet train count differs from its data card")
    if len(evaluation_payloads) != card.evaluation_row_count:
        raise ExportVerificationError(
            "parquet evaluation count differs from its data card"
        )
    payloads = (*train_payloads, *evaluation_payloads)
    rows: list[ProductRow] = []
    for payload, item in zip(payloads, provenance, strict=True):
        row = ProductRow.create(
            record_id=item.record_id,
            row_schema=card.row_schema,  # type: ignore[arg-type]
            payload=payload,
        )
        if row.row_id != item.row_id or row.payload_sha256 != item.payload_sha256:
            raise ExportVerificationError(
                "parquet payload differs from aligned provenance"
            )
        rows.append(row)
    train_rows = tuple(rows[: card.train_row_count])
    evaluation_rows = tuple(rows[card.train_row_count :])
    semantic = {
        PARQUET_TRAIN_PATH: columnar_partition_preimage_bytes(
            row_schema=card.row_schema,  # type: ignore[arg-type]
            partition="train",
            payloads=train_payloads,
        ),
        PARQUET_EVALUATION_PATH: columnar_partition_preimage_bytes(
            row_schema=card.row_schema,  # type: ignore[arg-type]
            partition="evaluation",
            payloads=evaluation_payloads,
        ),
        PARQUET_DATA_CARD_PATH: by_path[PARQUET_DATA_CARD_PATH],
        PARQUET_PROVENANCE_PATH: by_path[PARQUET_PROVENANCE_PATH],
        PARQUET_README_PATH: by_path[PARQUET_README_PATH],
    }
    expected_readme = _readme_bytes(card)
    if semantic[PARQUET_README_PATH] != expected_readme:
        raise ExportVerificationError("parquet README differs from its data card")
    return _ReplayedDerivative(
        semantic_contents=tuple(sorted(semantic.items())),
        train_rows=train_rows,
        evaluation_rows=evaluation_rows,
        provenance=provenance,
    )


PARQUET_DESCRIPTOR = ExportProfileDescriptor(
    container_profile=ExportContainerProfile.create(
        container_id=PARQUET_CONTAINER_ID,
        container_version=PARQUET_CONTAINER_VERSION,
        determinism_claim="semantic_content_only",
    ),
    consumer_profile=None,
    dependencies=(
        ExportDependencyBinding.create(
            dependency_name="pyarrow",
            dependency_version=_PYARROW_VERSION_RANGE,
            dependency_role="parquet-renderer",
        ),
    ),
    supported_row_schemas=_SUPPORTED_ROW_SCHEMAS,
)

PARQUET_IMPLEMENTATION = _ExportImplementation(
    descriptor=PARQUET_DESCRIPTOR,
    file_planner=_file_plans,
    renderer=_render,
    semantic_replayer=_replay,
)


validate_export_path_set(
    (
        PARQUET_README_PATH,
        PARQUET_TRAIN_PATH,
        PARQUET_EVALUATION_PATH,
        PARQUET_DATA_CARD_PATH,
        PARQUET_PROVENANCE_PATH,
        EXPORT_RECEIPT_PATH,
    ),
    label="parquet output tree",
    require_sorted=False,
)
