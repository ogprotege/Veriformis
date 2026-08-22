"""Lossless generic canonical-JSON export container v1."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal, Self, get_origin

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationInfo,
    field_validator,
    model_validator,
)

from veriformis.contracts import V1_ROW_SCHEMA_KINDS
from veriformis.datasets import ProductRow, RowProvenance, RowSet
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


CANONICAL_JSON_CONTAINER_ID = "json"
CANONICAL_JSON_CONTAINER_VERSION = 1
CANONICAL_JSON_DATASET_SCHEMA = "veriformis.canonical-json-dataset/v1"
CANONICAL_JSON_PROVENANCE_SCHEMA = "veriformis.canonical-json-provenance/v1"
CANONICAL_JSON_DATASET_PATH = "dataset.json"
CANONICAL_JSON_PROVENANCE_PATH = "metadata/row-provenance.json"
CANONICAL_JSON_README_PATH = "README.md"

_SUPPORTED_ROW_SCHEMAS = tuple(sorted(V1_ROW_SCHEMA_KINDS))


class _StrictCanonicalJsonModel(BaseModel):
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


class CanonicalJsonSplits(_StrictCanonicalJsonModel):
    """The two authoritative payload-only partitions."""

    train: tuple[dict[str, Any], ...]
    evaluation: tuple[dict[str, Any], ...]


def _validate_payloads(
    row_schema: str,
    payloads: Sequence[dict[str, Any]],
) -> None:
    for ordinal, payload in enumerate(payloads):
        try:
            ProductRow.create(
                record_id=derive_id("rec", {"ordinal": ordinal}),
                row_schema=row_schema,  # type: ignore[arg-type]
                payload=payload,
            )
        except (TypeError, UnicodeError, ValueError) as exc:
            raise ValueError(
                f"canonical JSON payload {ordinal} violates row schema "
                f"{row_schema!r}: {exc}"
            ) from exc


class CanonicalJsonProvenance(_StrictCanonicalJsonModel):
    """Complete provenance aligned to train rows followed by evaluation rows."""

    schema_version: Literal["veriformis.canonical-json-provenance/v1"] = (
        CANONICAL_JSON_PROVENANCE_SCHEMA
    )
    container_id: Literal["json"] = CANONICAL_JSON_CONTAINER_ID
    container_version: Literal[1] = CANONICAL_JSON_CONTAINER_VERSION
    row_schema: str
    objective_id: str
    row_set_id: str
    split_result_id: str
    train_row_count: int
    evaluation_row_count: int
    alignment: Literal["train_then_evaluation"] = "train_then_evaluation"
    rows: tuple[RowProvenance, ...]

    @field_validator("row_schema")
    @classmethod
    def _valid_row_schema(cls, value: str) -> str:
        if value not in V1_ROW_SCHEMA_KINDS:
            raise ValueError("provenance names an unsupported row schema")
        return value

    @field_validator("objective_id")
    @classmethod
    def _valid_objective_id(cls, value: str) -> str:
        return validate_id(value, kind="obj")

    @field_validator("row_set_id")
    @classmethod
    def _valid_row_set_id(cls, value: str) -> str:
        return validate_id(value, kind="rws")

    @field_validator("split_result_id")
    @classmethod
    def _valid_split_result_id(cls, value: str) -> str:
        return validate_id(value, kind="spt")

    @field_validator("train_row_count", "evaluation_row_count")
    @classmethod
    def _valid_count(cls, value: int) -> int:
        if type(value) is not int or value < 0:
            raise ValueError("provenance row counts must be non-negative integers")
        return value

    @model_validator(mode="after")
    def _closed_alignment(self) -> Self:
        if self.train_row_count < 1:
            raise ValueError("canonical JSON provenance requires non-empty train")
        if len(self.rows) != self.train_row_count + self.evaluation_row_count:
            raise ValueError("canonical JSON provenance count is not aligned")
        if {item.objective_id for item in self.rows} != {self.objective_id}:
            raise ValueError("provenance objective differs from its metadata")
        identity_sets = (
            {item.provenance_id for item in self.rows},
            {item.row_id for item in self.rows},
            {item.record_id for item in self.rows},
        )
        if any(len(values) != len(self.rows) for values in identity_sets):
            raise ValueError("canonical JSON provenance contains duplicate rows")
        for index, item in enumerate(self.rows):
            if index < self.train_row_count:
                expected_partition = "train"
                expected_ordinal = index
            else:
                expected_partition = "evaluation"
                expected_ordinal = index - self.train_row_count
            if (
                item.split_result_id != self.split_result_id
                or item.partition != expected_partition
                or item.ordinal != expected_ordinal
            ):
                raise ValueError(
                    "canonical JSON provenance violates train-then-evaluation "
                    "alignment or split binding"
                )
        return self


class CanonicalJsonDataset(_StrictCanonicalJsonModel):
    """One trainer-neutral canonical JSON dataset with explicit partitions."""

    schema_version: Literal["veriformis.canonical-json-dataset/v1"] = (
        CANONICAL_JSON_DATASET_SCHEMA
    )
    container_id: Literal["json"] = CANONICAL_JSON_CONTAINER_ID
    container_version: Literal[1] = CANONICAL_JSON_CONTAINER_VERSION
    row_schema: str
    objective_id: str
    loss_policy: str
    row_set_id: str
    split_result_id: str
    partition_order: tuple[Literal["train"], Literal["evaluation"]] = (
        "train",
        "evaluation",
    )
    train_row_count: int
    evaluation_row_count: int
    splits: CanonicalJsonSplits
    provenance_path: Literal["metadata/row-provenance.json"] = (
        CANONICAL_JSON_PROVENANCE_PATH
    )
    provenance_alignment: Literal["train_then_evaluation"] = (
        "train_then_evaluation"
    )
    consumer_profile: None = None
    trainer_compatibility_claimed: Literal[False] = False

    @field_validator("row_schema")
    @classmethod
    def _valid_row_schema(cls, value: str) -> str:
        if value not in V1_ROW_SCHEMA_KINDS:
            raise ValueError("dataset names an unsupported row schema")
        return value

    @field_validator("objective_id")
    @classmethod
    def _valid_objective_id(cls, value: str) -> str:
        return validate_id(value, kind="obj")

    @field_validator("loss_policy")
    @classmethod
    def _valid_loss_policy(cls, value: str) -> str:
        if value not in LOSS_POLICY_IDS:
            raise ValueError("dataset names an unsupported loss policy")
        return value

    @field_validator("row_set_id")
    @classmethod
    def _valid_row_set_id(cls, value: str) -> str:
        return validate_id(value, kind="rws")

    @field_validator("split_result_id")
    @classmethod
    def _valid_split_result_id(cls, value: str) -> str:
        return validate_id(value, kind="spt")

    @field_validator("train_row_count", "evaluation_row_count")
    @classmethod
    def _valid_count(cls, value: int) -> int:
        if type(value) is not int or value < 0:
            raise ValueError("dataset row counts must be non-negative integers")
        return value

    @model_validator(mode="after")
    def _closed_dataset(self) -> Self:
        if self.train_row_count < 1:
            raise ValueError("canonical JSON dataset requires non-empty train")
        if self.loss_policy != loss_policy_for_row(self.row_schema):
            raise ValueError("dataset loss policy differs from its row schema")
        if len(self.splits.train) != self.train_row_count:
            raise ValueError("dataset train count differs from its split")
        if len(self.splits.evaluation) != self.evaluation_row_count:
            raise ValueError("dataset evaluation count differs from its split")
        _validate_payloads(
            self.row_schema,
            (*self.splits.train, *self.splits.evaluation),
        )
        return self

    def validate_provenance(self, provenance: CanonicalJsonProvenance) -> None:
        """Require a sidecar to bind every payload and partition exactly."""
        if not isinstance(provenance, CanonicalJsonProvenance):
            raise ExportVerificationError(
                "canonical JSON provenance has the wrong runtime type"
            )
        metadata = (
            provenance.container_id,
            provenance.container_version,
            provenance.row_schema,
            provenance.objective_id,
            provenance.row_set_id,
            provenance.split_result_id,
            provenance.train_row_count,
            provenance.evaluation_row_count,
            provenance.alignment,
        )
        expected = (
            self.container_id,
            self.container_version,
            self.row_schema,
            self.objective_id,
            self.row_set_id,
            self.split_result_id,
            self.train_row_count,
            self.evaluation_row_count,
            self.provenance_alignment,
        )
        if metadata != expected:
            raise ExportVerificationError(
                "canonical JSON dataset and provenance metadata differ"
            )
        payloads = (*self.splits.train, *self.splits.evaluation)
        rows: list[ProductRow] = []
        for payload, item in zip(payloads, provenance.rows, strict=True):
            try:
                row = ProductRow.create(
                    record_id=item.record_id,
                    row_schema=self.row_schema,  # type: ignore[arg-type]
                    payload=payload,
                )
            except (TypeError, UnicodeError, ValueError) as exc:
                raise ExportVerificationError(
                    f"canonical JSON payload cannot bind provenance: {exc}"
                ) from exc
            if (
                row.row_id != item.row_id
                or row.payload_sha256 != item.payload_sha256
            ):
                raise ExportVerificationError(
                    "canonical JSON payload differs from aligned provenance"
                )
            rows.append(row)

        first = provenance.rows[0]
        try:
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
                provenance=provenance.rows,
            )
        except (TypeError, UnicodeError, ValueError, VeriformisError) as exc:
            raise ExportVerificationError(
                f"canonical JSON rows do not reconstruct one source row set: {exc}"
            ) from exc
        if rebuilt.row_set_id != self.row_set_id:
            raise ExportVerificationError(
                "canonical JSON row-set identity does not close over its rows"
            )


def _documents(
    row_set: RowSet,
) -> tuple[CanonicalJsonDataset, CanonicalJsonProvenance]:
    objective_ids = {item.objective_id for item in row_set.provenance}
    if len(objective_ids) != 1:
        raise ExportContractError(
            "canonical JSON requires one objective identity across the source row set"
        )
    objective_id = next(iter(objective_ids))
    provenance = CanonicalJsonProvenance(
        row_schema=row_set.row_schema,
        objective_id=objective_id,
        row_set_id=row_set.row_set_id,
        split_result_id=row_set.split_result_id,
        train_row_count=row_set.train_row_count,
        evaluation_row_count=row_set.evaluation_row_count,
        rows=row_set.provenance,
    )
    dataset = CanonicalJsonDataset(
        row_schema=row_set.row_schema,
        objective_id=objective_id,
        loss_policy=loss_policy_for_row(row_set.row_schema),
        row_set_id=row_set.row_set_id,
        split_result_id=row_set.split_result_id,
        train_row_count=row_set.train_row_count,
        evaluation_row_count=row_set.evaluation_row_count,
        splits=CanonicalJsonSplits(
            train=tuple(row.payload for row in row_set.train_rows),
            evaluation=tuple(row.payload for row in row_set.evaluation_rows),
        ),
    )
    dataset.validate_provenance(provenance)
    return dataset, provenance


def _readme_bytes(dataset: CanonicalJsonDataset) -> bytes:
    text = (
        "# Veriformis canonical JSON export\n\n"
        "This trainer-neutral export preserves the verified dataset's semantic "
        "rows and authoritative partitions.\n\n"
        f"- Container: `{dataset.container_id}` v{dataset.container_version}\n"
        f"- Row schema: `{dataset.row_schema}`\n"
        f"- Objective: `{dataset.objective_id}`\n"
        f"- Loss policy: `{dataset.loss_policy}`\n"
        f"- Train: `dataset.json#/splits/train` "
        f"({dataset.train_row_count} rows)\n"
        f"- Evaluation: `dataset.json#/splits/evaluation` "
        f"({dataset.evaluation_row_count} rows)\n"
        f"- Provenance: `{dataset.provenance_path}` "
        f"({dataset.provenance_alignment})\n"
        f"- Source row set: `{dataset.row_set_id}`\n"
        f"- Source split: `{dataset.split_result_id}`\n\n"
        "`dataset.json` is one canonical UTF-8 JSON object with explicit train "
        "and evaluation arrays. Array elements are payload objects only. Full "
        "row identity and provenance remain separate and align to every train "
        "row followed by every evaluation row. `export-receipt.json` binds "
        "every planned derivative file.\n\n"
        "This generic container does not select a training objective or claim "
        "compatibility with every trainer.\n"
    )
    return text.encode("utf-8")


def _rendered_files(row_set: RowSet) -> tuple[tuple[str, bytes], ...]:
    dataset, provenance = _documents(row_set)
    files = {
        CANONICAL_JSON_README_PATH: _readme_bytes(dataset),
        CANONICAL_JSON_DATASET_PATH: dataset.canonical_bytes(),
        CANONICAL_JSON_PROVENANCE_PATH: provenance.canonical_bytes(),
    }
    return tuple(sorted(files.items()))


def _file_plans(
    descriptor: ExportProfileDescriptor,
    row_set: RowSet,
) -> tuple[ExportFilePlan, ...]:
    if descriptor.selector != (
        CANONICAL_JSON_CONTAINER_ID,
        CANONICAL_JSON_CONTAINER_VERSION,
        None,
        None,
    ):
        raise ExportContractError("canonical JSON descriptor selector changed")
    if row_set.row_schema not in descriptor.supported_row_schemas:
        raise ExportContractError(
            "canonical JSON does not support the source row schema"
        )
    by_path = dict(_rendered_files(row_set))
    roles = {
        CANONICAL_JSON_README_PATH: "readme",
        CANONICAL_JSON_DATASET_PATH: "dataset",
        CANONICAL_JSON_PROVENANCE_PATH: "row-provenance",
    }
    counts: dict[str, int | None] = {
        CANONICAL_JSON_DATASET_PATH: row_set.total_row_count,
        CANONICAL_JSON_PROVENANCE_PATH: row_set.total_row_count,
    }
    return tuple(
        ExportFilePlan.create(
            path=path,
            role=roles[path],
            media_type=(
                "text/markdown"
                if path == CANONICAL_JSON_README_PATH
                else "application/json"
            ),
            membership_scope=(
                "all" if path == CANONICAL_JSON_DATASET_PATH else "none"
            ),
            record_count=counts.get(path),
            semantic_content_sha256=None,
            expected_sha256=sha256_digest(data),
            expected_byte_size=len(data),
        )
        for path, data in sorted(by_path.items())
    )


def _render(plan: ExportPlan, row_set: RowSet) -> _RenderedDerivative:
    if (
        plan.container_profile.container_id != CANONICAL_JSON_CONTAINER_ID
        or plan.container_profile.container_version
        != CANONICAL_JSON_CONTAINER_VERSION
        or plan.container_profile.determinism_claim != "portable_exact_bytes"
        or plan.consumer_profile is not None
    ):
        raise ExportVerificationError(
            "canonical JSON renderer received another profile"
        )
    expected_file_plans = _file_plans(CANONICAL_JSON_DESCRIPTOR, row_set)
    if plan.file_plans != expected_file_plans:
        raise ExportVerificationError(
            "canonical JSON plan differs from the fixed file contract"
        )
    return _RenderedDerivative(
        files=_rendered_files(row_set),
        train_rows=row_set.train_rows,
        evaluation_rows=row_set.evaluation_rows,
        provenance=row_set.provenance,
    )


CANONICAL_JSON_DESCRIPTOR = ExportProfileDescriptor(
    container_profile=ExportContainerProfile.create(
        container_id=CANONICAL_JSON_CONTAINER_ID,
        container_version=CANONICAL_JSON_CONTAINER_VERSION,
        determinism_claim="portable_exact_bytes",
    ),
    consumer_profile=None,
    dependencies=(
        ExportDependencyBinding.create(
            dependency_name="veriformis-canonical-json-renderer",
            dependency_version="1",
            dependency_role="renderer",
        ),
    ),
    supported_row_schemas=_SUPPORTED_ROW_SCHEMAS,
)

CANONICAL_JSON_IMPLEMENTATION = _ExportImplementation(
    descriptor=CANONICAL_JSON_DESCRIPTOR,
    file_planner=_file_plans,
    renderer=_render,
    semantic_replayer=None,
)


validate_export_path_set(
    (
        CANONICAL_JSON_README_PATH,
        CANONICAL_JSON_DATASET_PATH,
        EXPORT_RECEIPT_PATH,
        CANONICAL_JSON_PROVENANCE_PATH,
    ),
    label="canonical JSON output tree",
    require_sorted=False,
)


__all__ = [
    "CANONICAL_JSON_CONTAINER_ID",
    "CANONICAL_JSON_CONTAINER_VERSION",
    "CANONICAL_JSON_DATASET_PATH",
    "CANONICAL_JSON_DATASET_SCHEMA",
    "CANONICAL_JSON_PROVENANCE_PATH",
    "CANONICAL_JSON_PROVENANCE_SCHEMA",
    "CANONICAL_JSON_README_PATH",
    "CanonicalJsonDataset",
    "CanonicalJsonProvenance",
    "CanonicalJsonSplits",
]
