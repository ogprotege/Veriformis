"""Structurally lossless generic constrained-CSV export container v1."""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal, Self, get_origin

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationInfo,
    field_validator,
    model_validator,
)

from veriformis.datasets import (
    ProductRow,
    RowProvenance,
    RowSet,
    row_provenance_from_json_bytes,
)
from veriformis.errors import (
    ExportContractError,
    ExportVerificationError,
    VeriformisError,
)
from veriformis.exports._implementation import (
    _ExportImplementation,
    _RenderedDerivative,
)
from veriformis.exports._json import canonical_export_object_from_bytes
from veriformis.exports.api import ExportProfileDescriptor
from veriformis.exports.models import (
    EXPORT_RECEIPT_PATH,
    ExportContainerProfile,
    ExportDependencyBinding,
    ExportFilePlan,
    ExportPlan,
)
from veriformis.exports.paths import validate_export_path_set
from veriformis.identity import derive_id, lossless_json_bytes, sha256_digest, validate_id
from veriformis.taxonomy import LOSS_POLICY_IDS, loss_policy_for_row


CONSTRAINED_CSV_CONTAINER_ID = "constrained-csv"
CONSTRAINED_CSV_CONTAINER_VERSION = 1
CONSTRAINED_CSV_DIALECT_SCHEMA = "veriformis.constrained-csv-dialect/v1"
CONSTRAINED_CSV_DATA_CARD_SCHEMA = "veriformis.constrained-csv-data-card/v1"
CONSTRAINED_CSV_TRAIN_PATH = "data/train.csv"
CONSTRAINED_CSV_EVALUATION_PATH = "data/evaluation.csv"
CONSTRAINED_CSV_DATA_CARD_PATH = "metadata/dataset-card.json"
CONSTRAINED_CSV_PROVENANCE_PATH = "metadata/row-provenance.jsonl"
CONSTRAINED_CSV_README_PATH = "README.md"

_COLUMNS_BY_ROW_SCHEMA: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "instruction_output": ("instruction", "input", "output"),
        "prompt_completion": ("prompt", "completion"),
        "text": ("text",),
    }
)
_SUPPORTED_ROW_SCHEMAS = tuple(sorted(_COLUMNS_BY_ROW_SCHEMA))


class _StrictConstrainedCsvModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )

    @model_validator(mode="before")
    @classmethod
    def _require_exact_fields(cls, value: Any, info: ValidationInfo) -> Any:
        if (
            info.mode != "json"
            or isinstance(value, cls)
            or not isinstance(value, Mapping)
        ):
            return value
        expected = set(cls.model_fields)
        actual = set(value)
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            raise ValueError(
                f"{cls.__name__} fields do not match its persisted schema; "
                f"missing={missing!r}, extra={extra!r}"
            )
        normalized = dict(value)
        for name, field in cls.model_fields.items():
            if get_origin(field.annotation) is tuple and isinstance(
                normalized[name], list
            ):
                normalized[name] = tuple(normalized[name])
        return normalized

    @classmethod
    def from_json_bytes(cls, data: bytes) -> Self:
        try:
            canonical_export_object_from_bytes(data, label=cls.__name__)
            checked = cls.model_validate_json(data)
        except ExportVerificationError:
            raise
        except (TypeError, UnicodeError, ValueError) as exc:
            raise ExportVerificationError(f"invalid {cls.__name__}: {exc}") from exc
        if checked.canonical_bytes() != data:
            raise ExportVerificationError(
                f"{cls.__name__} does not round-trip exactly"
            )
        return checked

    def canonical_bytes(self) -> bytes:
        data = lossless_json_bytes(self.model_dump(mode="json"))
        try:
            checked = type(self).model_validate_json(data)
        except (TypeError, UnicodeError, ValueError) as exc:
            raise ExportContractError(
                f"invalid {type(self).__name__}: {exc}"
            ) from exc
        if checked != self:
            raise ExportContractError(
                f"{type(self).__name__} does not round-trip exactly"
            )
        return data


@dataclass(frozen=True, slots=True)
class ConstrainedCsvPartition:
    """One strict canonical CSV partition decoded to payload mappings."""

    row_schema: str
    columns: tuple[str, ...]
    payloads: tuple[dict[str, str], ...]

    @classmethod
    def from_csv_bytes(
        cls,
        data: bytes,
        *,
        row_schema: str,
    ) -> Self:
        """Load only canonical constrained-CSV v1 bytes for one row schema."""
        try:
            columns = _columns_for_row_schema(row_schema)
            rows = _quote_all_rows_from_bytes(data)
            if not rows:
                raise ValueError("constrained CSV requires its canonical header row")
            if rows[0] != columns:
                raise ValueError(
                    "constrained CSV header differs from the selected row schema"
                )
            payloads: list[dict[str, str]] = []
            for ordinal, row in enumerate(rows[1:]):
                if len(row) != len(columns):
                    raise ValueError(
                        f"constrained CSV row {ordinal} has {len(row)} fields; "
                        f"expected {len(columns)}"
                    )
                payload = dict(zip(columns, row, strict=True))
                ProductRow.create(
                    record_id=derive_id(
                        "rec",
                        {"constrained_csv_partition_ordinal": ordinal},
                    ),
                    row_schema=row_schema,  # type: ignore[arg-type]
                    payload=payload,
                )
                payloads.append(payload)
            canonical = _payloads_csv_bytes(row_schema, payloads)
        except ExportVerificationError:
            raise
        except (csv.Error, RecursionError, TypeError, UnicodeError, ValueError) as exc:
            raise ExportVerificationError(
                f"invalid constrained CSV partition: {exc}"
            ) from exc
        if canonical != data:
            raise ExportVerificationError(
                "constrained CSV partition bytes are not canonical"
            )
        return cls(
            row_schema=row_schema,
            columns=columns,
            payloads=tuple(payloads),
        )


class ConstrainedCsvDataCard(_StrictConstrainedCsvModel):
    """Machine-readable description of one constrained-CSV export pack."""

    schema_version: Literal["veriformis.constrained-csv-data-card/v1"] = (
        CONSTRAINED_CSV_DATA_CARD_SCHEMA
    )
    container_id: Literal["constrained-csv"] = CONSTRAINED_CSV_CONTAINER_ID
    container_version: Literal[1] = CONSTRAINED_CSV_CONTAINER_VERSION
    dialect: Literal["veriformis.constrained-csv-dialect/v1"] = (
        CONSTRAINED_CSV_DIALECT_SCHEMA
    )
    encoding: Literal["utf-8"] = "utf-8"
    byte_order_mark: Literal[False] = False
    delimiter: Literal[","] = ","
    quote_character: Literal['"'] = '"'
    quoting: Literal["all"] = "all"
    doublequote: Literal[True] = True
    record_terminator: Literal["lf"] = "lf"
    null_encoding: None = None
    empty_string_encoding: Literal["quoted-empty-field"] = "quoted-empty-field"
    row_schema: str
    columns: tuple[str, ...]
    objective_id: str
    loss_policy: str
    row_set_id: str
    split_result_id: str
    train_path: Literal["data/train.csv"] = CONSTRAINED_CSV_TRAIN_PATH
    train_row_count: int
    evaluation_path: Literal["data/evaluation.csv"] = (
        CONSTRAINED_CSV_EVALUATION_PATH
    )
    evaluation_row_count: int
    provenance_path: Literal["metadata/row-provenance.jsonl"] = (
        CONSTRAINED_CSV_PROVENANCE_PATH
    )
    provenance_row_count: int
    provenance_alignment: Literal["train_then_evaluation"] = (
        "train_then_evaluation"
    )
    receipt_path: Literal["export-receipt.json"] = EXPORT_RECEIPT_PATH
    consumer_profile: None = None
    trainer_compatibility_claimed: Literal[False] = False

    @field_validator("row_schema")
    @classmethod
    def _valid_row_schema(cls, value: str) -> str:
        _columns_for_row_schema(value)
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

    @field_validator(
        "train_row_count",
        "evaluation_row_count",
        "provenance_row_count",
    )
    @classmethod
    def _valid_count(cls, value: int) -> int:
        if type(value) is not int or value < 0:
            raise ValueError("data card row counts must be non-negative integers")
        return value

    @model_validator(mode="after")
    def _closed_layout(self) -> Self:
        if self.train_row_count < 1:
            raise ValueError("constrained CSV requires a non-empty train partition")
        if self.columns != _columns_for_row_schema(self.row_schema):
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
                        CONSTRAINED_CSV_README_PATH,
                        self.train_path,
                        self.evaluation_path,
                        CONSTRAINED_CSV_DATA_CARD_PATH,
                        self.provenance_path,
                    )
                )
            ),
            label="constrained CSV data card paths",
        )
        return self

    def validate_row_set(
        self,
        *,
        train: ConstrainedCsvPartition,
        evaluation: ConstrainedCsvPartition,
        provenance: Sequence[RowProvenance],
    ) -> RowSet:
        """Reconstruct and close one source row set from CSV and provenance."""
        if type(train) is not ConstrainedCsvPartition or type(
            evaluation
        ) is not ConstrainedCsvPartition:
            raise ExportVerificationError(
                "constrained CSV row-set validation requires strict partitions"
            )
        if (
            train.row_schema != self.row_schema
            or evaluation.row_schema != self.row_schema
            or train.columns != self.columns
            or evaluation.columns != self.columns
        ):
            raise ExportVerificationError(
                "constrained CSV partition schema differs from its data card"
            )
        if (
            len(train.payloads) != self.train_row_count
            or len(evaluation.payloads) != self.evaluation_row_count
        ):
            raise ExportVerificationError(
                "constrained CSV partition count differs from its data card"
            )
        try:
            checked_provenance = tuple(provenance)
            if len(checked_provenance) != self.provenance_row_count:
                raise ExportVerificationError(
                    "constrained CSV provenance count differs from its data card"
                )
            if {item.objective_id for item in checked_provenance} != {
                self.objective_id
            }:
                raise ExportVerificationError(
                    "constrained CSV provenance objective differs from its data card"
                )
            payloads = (*train.payloads, *evaluation.payloads)
            rows: list[ProductRow] = []
            for payload, item in zip(payloads, checked_provenance, strict=True):
                row = ProductRow.create(
                    record_id=item.record_id,
                    row_schema=self.row_schema,  # type: ignore[arg-type]
                    payload=payload,
                )
                if (
                    row.row_id != item.row_id
                    or row.payload_sha256 != item.payload_sha256
                ):
                    raise ExportVerificationError(
                        "constrained CSV payload differs from aligned provenance"
                    )
                rows.append(row)
            first = checked_provenance[0]
            rebuilt = RowSet.create(
                plan_id=first.plan_id,
                serialization_plan_id=first.serialization_plan_id,
                recipe_id=first.recipe_id,
                construction_result_id=first.construction_result_id,
                curation_result_id=first.curation_result_id,
                split_result_id=self.split_result_id,
                row_schema=self.row_schema,  # type: ignore[arg-type]
                train_rows=rows[: self.train_row_count],
                evaluation_rows=rows[self.train_row_count :],
                provenance=checked_provenance,
            )
        except ExportVerificationError:
            raise
        except (
            AttributeError,
            RecursionError,
            TypeError,
            UnicodeError,
            ValueError,
            VeriformisError,
        ) as exc:
            raise ExportVerificationError(
                f"constrained CSV rows do not reconstruct one source row set: {exc}"
            ) from exc
        if rebuilt.row_set_id != self.row_set_id:
            raise ExportVerificationError(
                "constrained CSV row-set identity does not close over its rows"
            )
        return rebuilt


def _columns_for_row_schema(row_schema: str) -> tuple[str, ...]:
    if type(row_schema) is not str or row_schema not in _COLUMNS_BY_ROW_SCHEMA:
        raise ValueError(
            "constrained CSV supports only flat text, prompt_completion, and "
            "instruction_output rows; use split-jsonl-directory or json for "
            "nested values"
        )
    return _COLUMNS_BY_ROW_SCHEMA[row_schema]


def _quote_all_rows_from_bytes(data: bytes) -> tuple[tuple[str, ...], ...]:
    """Parse the small canonical QUOTE_ALL grammar without a global field limit."""
    if type(data) is not bytes:
        raise TypeError("constrained CSV must be loaded from exact bytes")
    text = data.decode("utf-8")
    if text.startswith("\ufeff"):
        raise ValueError("constrained CSV must not contain a byte-order mark")
    if not text:
        raise ValueError("constrained CSV cannot be empty")

    rows: list[tuple[str, ...]] = []
    current_row: list[str] = []
    index = 0
    while index < len(text):
        if text[index] != '"':
            raise ValueError(
                "every constrained CSV field must begin with a double quote"
            )
        index += 1
        field: list[str] = []
        while True:
            if index >= len(text):
                raise ValueError("constrained CSV contains an unterminated field")
            character = text[index]
            if character != '"':
                field.append(character)
                index += 1
                continue
            if index + 1 < len(text) and text[index + 1] == '"':
                field.append('"')
                index += 2
                continue
            index += 1
            break

        current_row.append("".join(field))
        if index >= len(text):
            raise ValueError("every constrained CSV record must end with LF")
        separator = text[index]
        index += 1
        if separator == ",":
            if index >= len(text):
                raise ValueError("constrained CSV ends before its next quoted field")
            continue
        if separator == "\n":
            rows.append(tuple(current_row))
            current_row = []
            continue
        raise ValueError(
            "a constrained CSV closing quote must be followed by comma or LF"
        )
    if current_row:
        raise ValueError("constrained CSV contains an incomplete final record")
    return tuple(rows)


def _payloads_csv_bytes(
    row_schema: str,
    payloads: Sequence[Mapping[str, object]],
) -> bytes:
    columns = _columns_for_row_schema(row_schema)
    rows: list[tuple[str, ...]] = [columns]
    for ordinal, payload in enumerate(payloads):
        if not isinstance(payload, Mapping) or set(payload) != set(columns):
            raise ValueError(
                f"constrained CSV payload {ordinal} differs from the exact columns"
            )
        values = tuple(payload[column] for column in columns)
        if any(type(value) is not str for value in values):
            raise ValueError(
                "constrained CSV values must be exact strings; null and nested "
                "values are unrepresentable, so use split-jsonl-directory or json"
            )
        rows.append(values)  # type: ignore[arg-type]

    stream = io.StringIO(newline="")
    writer = csv.writer(
        stream,
        delimiter=",",
        quotechar='"',
        doublequote=True,
        escapechar=None,
        lineterminator="\n",
        quoting=csv.QUOTE_ALL,
        skipinitialspace=False,
        strict=True,
    )
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _partition_bytes(rows: Sequence[ProductRow], row_schema: str) -> bytes:
    payloads: list[Mapping[str, object]] = []
    for ordinal, row in enumerate(rows):
        if row.row_schema != row_schema:
            raise ExportContractError(
                f"constrained CSV row {ordinal} differs from the source row schema"
            )
        payloads.append(row.payload)
    try:
        return _payloads_csv_bytes(row_schema, payloads)
    except (csv.Error, RecursionError, TypeError, UnicodeError, ValueError) as exc:
        raise ExportContractError(f"cannot render constrained CSV: {exc}") from exc


def _provenance_jsonl(provenance: Sequence[RowProvenance]) -> bytes:
    return b"".join(
        lossless_json_bytes(item.model_dump(mode="json")) + b"\n"
        for item in provenance
    )


def _provenance_from_jsonl_bytes(data: bytes) -> tuple[RowProvenance, ...]:
    if type(data) is not bytes or not data or not data.endswith(b"\n"):
        raise ExportVerificationError(
            "constrained CSV provenance must be non-empty canonical JSONL"
        )
    parts = data.split(b"\n")
    if parts[-1] != b"":
        raise ExportVerificationError(
            "constrained CSV provenance must end with one canonical LF"
        )
    rows: list[RowProvenance] = []
    for line in parts[:-1]:
        if not line:
            raise ExportVerificationError(
                "constrained CSV provenance must have one canonical object per line"
            )
        try:
            rows.append(row_provenance_from_json_bytes(line))
        except (RecursionError, TypeError, UnicodeError, ValueError, VeriformisError) as exc:
            raise ExportVerificationError(
                f"invalid constrained CSV provenance row: {exc}"
            ) from exc
    checked = tuple(rows)
    if _provenance_jsonl(checked) != data:
        raise ExportVerificationError(
            "constrained CSV provenance bytes are not canonical"
        )
    return checked


def _data_card(row_set: RowSet) -> ConstrainedCsvDataCard:
    objective_ids = {item.objective_id for item in row_set.provenance}
    if len(objective_ids) != 1:
        raise ExportContractError(
            "constrained CSV requires one objective identity across the source row set"
        )
    return ConstrainedCsvDataCard(
        row_schema=row_set.row_schema,
        columns=_columns_for_row_schema(row_set.row_schema),
        objective_id=next(iter(objective_ids)),
        loss_policy=loss_policy_for_row(row_set.row_schema),
        row_set_id=row_set.row_set_id,
        split_result_id=row_set.split_result_id,
        train_row_count=row_set.train_row_count,
        evaluation_row_count=row_set.evaluation_row_count,
        provenance_row_count=row_set.total_row_count,
    )


def _readme_bytes(card: ConstrainedCsvDataCard) -> bytes:
    columns = ", ".join(f"`{column}`" for column in card.columns)
    text = (
        "# Veriformis constrained CSV export\n\n"
        "This trainer-neutral export preserves the verified dataset's flat "
        "semantic rows and authoritative partitions.\n\n"
        f"- Container: `{card.container_id}` v{card.container_version}\n"
        f"- Dialect: `{card.dialect}`\n"
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
        "Both CSV partitions are UTF-8 without a byte-order mark. They use a "
        "comma delimiter, LF records, a fixed header, double quotes around every "
        "field, doubled embedded quotes, and no escape character. Empty strings "
        "are quoted empty fields. Null and nested values are unrepresentable; use "
        "`split-jsonl-directory` v1 or `json` v1 for those values. Unicode code "
        "points are preserved without normalization. The nested `messages` row "
        "schema is unsupported.\n\n"
        "Complete provenance is separate and aligned in train-then-evaluation "
        "order. `metadata/dataset-card.json` describes this layout and "
        "`export-receipt.json` binds every planned derivative file.\n\n"
        "This generic container does not select a training objective or claim "
        "compatibility with every trainer. Treat untrusted cell text as data; CSV "
        "quoting does not make spreadsheet formula text safe to execute.\n"
    )
    return text.encode("utf-8")


def _rendered_files(row_set: RowSet) -> tuple[tuple[str, bytes], ...]:
    card = _data_card(row_set)
    train_bytes = _partition_bytes(row_set.train_rows, row_set.row_schema)
    evaluation_bytes = _partition_bytes(
        row_set.evaluation_rows,
        row_set.row_schema,
    )
    provenance_bytes = _provenance_jsonl(row_set.provenance)

    checked_card = ConstrainedCsvDataCard.from_json_bytes(card.canonical_bytes())
    checked_train = ConstrainedCsvPartition.from_csv_bytes(
        train_bytes,
        row_schema=row_set.row_schema,
    )
    checked_evaluation = ConstrainedCsvPartition.from_csv_bytes(
        evaluation_bytes,
        row_schema=row_set.row_schema,
    )
    checked_provenance = _provenance_from_jsonl_bytes(provenance_bytes)
    rebuilt = checked_card.validate_row_set(
        train=checked_train,
        evaluation=checked_evaluation,
        provenance=checked_provenance,
    )
    if rebuilt != row_set:
        raise ExportVerificationError(
            "constrained CSV render does not reconstruct the source row set"
        )

    files = {
        CONSTRAINED_CSV_README_PATH: _readme_bytes(card),
        CONSTRAINED_CSV_TRAIN_PATH: train_bytes,
        CONSTRAINED_CSV_EVALUATION_PATH: evaluation_bytes,
        CONSTRAINED_CSV_DATA_CARD_PATH: card.canonical_bytes(),
        CONSTRAINED_CSV_PROVENANCE_PATH: provenance_bytes,
    }
    return tuple(sorted(files.items()))


def _file_plans(
    descriptor: ExportProfileDescriptor,
    row_set: RowSet,
) -> tuple[ExportFilePlan, ...]:
    if descriptor.selector != (
        CONSTRAINED_CSV_CONTAINER_ID,
        CONSTRAINED_CSV_CONTAINER_VERSION,
        None,
        None,
    ):
        raise ExportContractError("constrained CSV descriptor selector changed")
    if row_set.row_schema not in descriptor.supported_row_schemas:
        raise ExportContractError(
            "constrained CSV supports only flat row mappings; use "
            "split-jsonl-directory or json for nested values"
        )
    by_path = dict(_rendered_files(row_set))
    roles = {
        CONSTRAINED_CSV_README_PATH: "readme",
        CONSTRAINED_CSV_TRAIN_PATH: "training-partition",
        CONSTRAINED_CSV_EVALUATION_PATH: "evaluation-partition",
        CONSTRAINED_CSV_DATA_CARD_PATH: "dataset-card",
        CONSTRAINED_CSV_PROVENANCE_PATH: "row-provenance",
    }
    media_types = {
        CONSTRAINED_CSV_README_PATH: "text/markdown",
        CONSTRAINED_CSV_TRAIN_PATH: "text/csv",
        CONSTRAINED_CSV_EVALUATION_PATH: "text/csv",
        CONSTRAINED_CSV_DATA_CARD_PATH: "application/json",
        CONSTRAINED_CSV_PROVENANCE_PATH: "application/jsonl",
    }
    scopes = {
        CONSTRAINED_CSV_TRAIN_PATH: "train",
        CONSTRAINED_CSV_EVALUATION_PATH: "evaluation",
    }
    counts: dict[str, int | None] = {
        CONSTRAINED_CSV_TRAIN_PATH: row_set.train_row_count,
        CONSTRAINED_CSV_EVALUATION_PATH: row_set.evaluation_row_count,
        CONSTRAINED_CSV_PROVENANCE_PATH: row_set.total_row_count,
    }
    return tuple(
        ExportFilePlan.create(
            path=path,
            role=roles[path],
            media_type=media_types[path],
            membership_scope=scopes.get(path, "none"),
            record_count=counts.get(path),
            semantic_content_sha256=None,
            expected_sha256=sha256_digest(data),
            expected_byte_size=len(data),
        )
        for path, data in sorted(by_path.items())
    )


def _render(plan: ExportPlan, row_set: RowSet) -> _RenderedDerivative:
    if (
        plan.container_profile.container_id != CONSTRAINED_CSV_CONTAINER_ID
        or plan.container_profile.container_version
        != CONSTRAINED_CSV_CONTAINER_VERSION
        or plan.container_profile.determinism_claim != "portable_exact_bytes"
        or plan.consumer_profile is not None
    ):
        raise ExportVerificationError(
            "constrained CSV renderer received another profile"
        )
    expected_file_plans = _file_plans(CONSTRAINED_CSV_DESCRIPTOR, row_set)
    if plan.file_plans != expected_file_plans:
        raise ExportVerificationError(
            "constrained CSV plan differs from the fixed file contract"
        )
    return _RenderedDerivative(
        files=_rendered_files(row_set),
        train_rows=row_set.train_rows,
        evaluation_rows=row_set.evaluation_rows,
        provenance=row_set.provenance,
    )


CONSTRAINED_CSV_DESCRIPTOR = ExportProfileDescriptor(
    container_profile=ExportContainerProfile.create(
        container_id=CONSTRAINED_CSV_CONTAINER_ID,
        container_version=CONSTRAINED_CSV_CONTAINER_VERSION,
        determinism_claim="portable_exact_bytes",
    ),
    consumer_profile=None,
    dependencies=(
        ExportDependencyBinding.create(
            dependency_name="veriformis-constrained-csv-renderer",
            dependency_version="1",
            dependency_role="renderer",
        ),
    ),
    supported_row_schemas=_SUPPORTED_ROW_SCHEMAS,
)

CONSTRAINED_CSV_IMPLEMENTATION = _ExportImplementation(
    descriptor=CONSTRAINED_CSV_DESCRIPTOR,
    file_planner=_file_plans,
    renderer=_render,
    semantic_replayer=None,
)


validate_export_path_set(
    (
        CONSTRAINED_CSV_README_PATH,
        CONSTRAINED_CSV_TRAIN_PATH,
        CONSTRAINED_CSV_EVALUATION_PATH,
        CONSTRAINED_CSV_DATA_CARD_PATH,
        CONSTRAINED_CSV_PROVENANCE_PATH,
        EXPORT_RECEIPT_PATH,
    ),
    label="constrained CSV output tree",
    require_sorted=False,
)


__all__ = [
    "CONSTRAINED_CSV_CONTAINER_ID",
    "CONSTRAINED_CSV_CONTAINER_VERSION",
    "CONSTRAINED_CSV_DATA_CARD_PATH",
    "CONSTRAINED_CSV_DATA_CARD_SCHEMA",
    "CONSTRAINED_CSV_DIALECT_SCHEMA",
    "CONSTRAINED_CSV_EVALUATION_PATH",
    "CONSTRAINED_CSV_PROVENANCE_PATH",
    "CONSTRAINED_CSV_README_PATH",
    "CONSTRAINED_CSV_TRAIN_PATH",
    "ConstrainedCsvDataCard",
    "ConstrainedCsvPartition",
]
