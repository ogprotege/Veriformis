"""Generic local Hugging Face DatasetDict export v1.

Hugging Face Datasets is imported only at render and replay time.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Sequence
from pathlib import Path
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

HF_DATASET_CONTAINER_ID = "hugging-face-dataset"
HF_DATASET_CONTAINER_VERSION = 1
HF_DATASET_DATA_CARD_SCHEMA = "veriformis.hugging-face-dataset-data-card/v1"
HF_DATASET_ROOT = "dataset"
HF_DATASET_DICT_PATH = "dataset/dataset_dict.json"
HF_TRAIN_ARROW_PATH = "dataset/train/data-00000-of-00001.arrow"
HF_TRAIN_INFO_PATH = "dataset/train/dataset_info.json"
HF_TRAIN_STATE_PATH = "dataset/train/state.json"
HF_EVALUATION_ARROW_PATH = "dataset/evaluation/data-00000-of-00001.arrow"
HF_EVALUATION_INFO_PATH = "dataset/evaluation/dataset_info.json"
HF_EVALUATION_STATE_PATH = "dataset/evaluation/state.json"
HF_DATA_CARD_PATH = "metadata/dataset-card.json"
HF_PROVENANCE_PATH = "metadata/row-provenance.jsonl"
HF_README_PATH = "README.md"
HF_ARROW_MEDIA_TYPE = "application/vnd.apache.arrow.file"
_SUPPORTED_ROW_SCHEMAS = tuple(sorted(V1_ROW_SCHEMA_KINDS))
_DATASETS_VERSION_RANGE = ">=3.0.0,<6.0.0"
_LIBRARY_TREE = (
    HF_DATASET_DICT_PATH,
    HF_EVALUATION_ARROW_PATH,
    HF_EVALUATION_INFO_PATH,
    HF_EVALUATION_STATE_PATH,
    HF_TRAIN_ARROW_PATH,
    HF_TRAIN_INFO_PATH,
    HF_TRAIN_STATE_PATH,
)
_METADATA_KINDS = {
    HF_DATASET_DICT_PATH: ("dataset-dict", None),
    HF_TRAIN_INFO_PATH: ("dataset-info", "train"),
    HF_TRAIN_STATE_PATH: ("dataset-state", "train"),
    HF_EVALUATION_INFO_PATH: ("dataset-info", "evaluation"),
    HF_EVALUATION_STATE_PATH: ("dataset-state", "evaluation"),
}


class _StrictHfModel(BaseModel):
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


class HuggingFaceDatasetDataCard(_StrictHfModel):
    schema_version: Literal["veriformis.hugging-face-dataset-data-card/v1"] = (
        HF_DATASET_DATA_CARD_SCHEMA
    )
    container_id: Literal["hugging-face-dataset"] = HF_DATASET_CONTAINER_ID
    container_version: Literal[1] = HF_DATASET_CONTAINER_VERSION
    determinism_claim: Literal["semantic_content_only"] = "semantic_content_only"
    encoding: Literal["utf-8"] = "utf-8"
    row_schema: str
    columns: tuple[str, ...]
    objective_id: str
    loss_policy: str
    row_set_id: str
    split_result_id: str
    dataset_dict_path: Literal["dataset/dataset_dict.json"] = HF_DATASET_DICT_PATH
    train_path: Literal["dataset/train/data-00000-of-00001.arrow"] = HF_TRAIN_ARROW_PATH
    train_row_count: int
    evaluation_path: Literal["dataset/evaluation/data-00000-of-00001.arrow"] = (
        HF_EVALUATION_ARROW_PATH
    )
    evaluation_row_count: int
    provenance_path: Literal["metadata/row-provenance.jsonl"] = HF_PROVENANCE_PATH
    provenance_row_count: int
    provenance_alignment: Literal["train_then_evaluation"] = "train_then_evaluation"
    receipt_path: Literal["export-receipt.json"] = EXPORT_RECEIPT_PATH
    consumer_profile: None = None
    trainer_compatibility_claimed: Literal[False] = False
    hub_upload: Literal[False] = False

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
            raise ValueError(
                "hugging-face-dataset export requires a non-empty train partition"
            )
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
                        HF_README_PATH,
                        self.dataset_dict_path,
                        self.train_path,
                        HF_TRAIN_INFO_PATH,
                        HF_TRAIN_STATE_PATH,
                        self.evaluation_path,
                        HF_EVALUATION_INFO_PATH,
                        HF_EVALUATION_STATE_PATH,
                        HF_DATA_CARD_PATH,
                        self.provenance_path,
                    )
                )
            ),
            label="hugging-face-dataset data card paths",
        )
        return self


def _is_hugging_face_datasets(module: Any) -> bool:
    return all(
        callable(getattr(module, name, None))
        for name in ("Dataset", "DatasetDict", "Features", "Sequence", "Value")
    )


def _require_datasets() -> Any:
    try:
        import datasets
    except ImportError as exc:
        raise ExportContractError(
            "physical container 'hugging-face-dataset' requires Hugging Face "
            "Datasets; the optional extra 'columnar' is empty in this install"
        ) from exc
    if not _is_hugging_face_datasets(datasets):
        raise ExportContractError(
            "physical container 'hugging-face-dataset' requires Hugging Face "
            "Datasets; the optional extra 'columnar' is empty in this install"
        )
    return datasets


def _row_pin(row_schema: str) -> Any:
    for item in columnar_schema_catalog().row_schemas:
        if item.source_row_schema == row_schema:
            return item
    raise ExportContractError(f"no columnar schema pin for {row_schema!r}")


def _feature(spec: Any, datasets: Any) -> Any:
    if spec.kind == "value":
        return datasets.Value("string")
    if spec.kind == "list":
        item = _feature(spec.item, datasets)
        # Sequence(dict) becomes a dict of lists; a one-element list keeps list-of-struct.
        if spec.item is not None and spec.item.kind == "struct":
            return [item]
        return datasets.Sequence(item)
    return {
        field.name: _feature(field.hf_feature, datasets) for field in spec.fields
    }


def _hf_features(row_schema: str) -> Any:
    datasets = _require_datasets()
    pin = _row_pin(row_schema)
    return datasets.Features(
        {
            field.name: _feature(field.hf_feature, datasets)
            for field in pin.fields
        }
    )


def _payloads(rows: Sequence[ProductRow]) -> tuple[dict[str, Any], ...]:
    return tuple(dict(row.payload) for row in rows)


def _dataset_from_payloads(
    payloads: Sequence[dict[str, Any]],
    features: Any,
    datasets: Any,
) -> Any:
    if payloads:
        return datasets.Dataset.from_list(list(payloads), features=features)
    return datasets.Dataset.from_dict(
        {name: [] for name in features},
        features=features,
    )


def _library_metadata_preimage(*, kind: str, split: str | None) -> bytes:
    return lossless_json_bytes(
        {
            "container_id": HF_DATASET_CONTAINER_ID,
            "kind": kind,
            "split": split,
        }
    )


def _read_partition_payloads(data: bytes) -> tuple[dict[str, Any], ...]:
    datasets = _require_datasets()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "partition.arrow"
            path.write_bytes(data)
            table = datasets.Dataset.from_file(str(path))
            payloads = tuple(dict(row) for row in table)
            del table
            return payloads
    except ExportVerificationError:
        raise
    except Exception as exc:
        raise ExportVerificationError(
            f"invalid hugging-face-dataset partition: {exc}"
        ) from exc


def _dataset_dict_files(row_set: RowSet) -> dict[str, bytes]:
    datasets = _require_datasets()
    features = _hf_features(row_set.row_schema)
    dataset_dict = datasets.DatasetDict(
        {
            "train": _dataset_from_payloads(
                _payloads(row_set.train_rows), features, datasets
            ),
            "evaluation": _dataset_from_payloads(
                _payloads(row_set.evaluation_rows), features, datasets
            ),
        }
    )
    with tempfile.TemporaryDirectory() as tmp:
        dataset_dict.save_to_disk(
            tmp,
            num_shards={"train": 1, "evaluation": 1},
        )
        produced: dict[str, bytes] = {}
        root = Path(tmp)
        for path in sorted(root.rglob("*")):
            if path.is_file():
                relative = path.relative_to(root).as_posix()
                produced[f"{HF_DATASET_ROOT}/{relative}"] = path.read_bytes()
    expected = set(_LIBRARY_TREE)
    if set(produced) != expected:
        raise ExportVerificationError(
            "hugging-face-dataset save_to_disk layout differs from the pinned "
            "tree: "
            f"missing={sorted(expected - set(produced))!r} "
            f"extra={sorted(set(produced) - expected)!r}"
        )
    return produced


def _provenance_jsonl(provenance: Sequence[RowProvenance]) -> bytes:
    return b"".join(
        lossless_json_bytes(item.model_dump(mode="json")) + b"\n" for item in provenance
    )


def _provenance_from_jsonl_bytes(data: bytes) -> tuple[RowProvenance, ...]:
    if not data.endswith(b"\n"):
        raise ExportVerificationError(
            "hugging-face-dataset provenance must end with one canonical LF"
        )
    rows: list[RowProvenance] = []
    for line in data.split(b"\n")[:-1]:
        if not line:
            raise ExportVerificationError(
                "hugging-face-dataset provenance must have one object per line"
            )
        try:
            payload = json.loads(line.decode("utf-8"))
            if (
                isinstance(payload, dict)
                and payload.get("schema_version")
                == "veriformis.imported-row-provenance/v1"
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
                f"invalid hugging-face-dataset provenance row: {exc}"
            ) from exc
    checked = tuple(rows)
    if _provenance_jsonl(checked) != data:
        raise ExportVerificationError(
            "hugging-face-dataset provenance bytes are not canonical"
        )
    return checked


def _data_card(row_set: RowSet) -> HuggingFaceDatasetDataCard:
    objective_ids = {item.objective_id for item in row_set.provenance}
    if len(objective_ids) != 1:
        raise ExportContractError(
            "hugging-face-dataset export requires one objective identity "
            "across the source row set"
        )
    return HuggingFaceDatasetDataCard(
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


def _readme_bytes(card: HuggingFaceDatasetDataCard) -> bytes:
    columns = ", ".join(f"`{column}`" for column in card.columns)
    text = (
        "# Veriformis Hugging Face dataset export\n\n"
        "This trainer-neutral export preserves the verified dataset's semantic "
        "rows and authoritative partitions as a local Hugging Face "
        "DatasetDict directory. There is no Hub upload.\n\n"
        f"- Container: `{card.container_id}` v{card.container_version}\n"
        f"- Determinism: `{card.determinism_claim}`\n"
        f"- Row schema: `{card.row_schema}`\n"
        f"- Columns: {columns}\n"
        f"- Loss policy: `{card.loss_policy}`\n"
        f"- DatasetDict: `{card.dataset_dict_path}`\n"
        f"- Train: `{card.train_path}` ({card.train_row_count} rows)\n"
        f"- Evaluation: `{card.evaluation_path}` "
        f"({card.evaluation_row_count} rows)\n"
        f"- Provenance: `{card.provenance_path}` "
        f"({card.provenance_row_count} aligned rows)\n"
        f"- Source row set: `{card.row_set_id}`\n"
        f"- Source split: `{card.split_result_id}`\n\n"
        "Semantic identity is the versioned payload fingerprint from item 9.3. "
        "On-disk DatasetDict bytes of this pinned extra are bound by the export "
        "receipt and are not portable exact bytes across Datasets versions. "
        "Null product fields are unrepresentable. Nested `messages` is in "
        "scope as a list of role/content structs.\n\n"
        "This generic container does not select a training objective or claim "
        "compatibility with a trainer.\n"
    )
    return text.encode("utf-8")


def _sidecar_files(row_set: RowSet) -> dict[str, bytes]:
    card = _data_card(row_set)
    return {
        HF_README_PATH: _readme_bytes(card),
        HF_DATA_CARD_PATH: card.canonical_bytes(),
        HF_PROVENANCE_PATH: _provenance_jsonl(row_set.provenance),
    }


def _semantic_contents(row_set: RowSet) -> dict[str, bytes]:
    files = _sidecar_files(row_set)
    files[HF_TRAIN_ARROW_PATH] = columnar_partition_preimage_bytes(
        row_schema=row_set.row_schema,  # type: ignore[arg-type]
        partition="train",
        payloads=_payloads(row_set.train_rows),
    )
    files[HF_EVALUATION_ARROW_PATH] = columnar_partition_preimage_bytes(
        row_schema=row_set.row_schema,  # type: ignore[arg-type]
        partition="evaluation",
        payloads=_payloads(row_set.evaluation_rows),
    )
    for path, (kind, split) in _METADATA_KINDS.items():
        files[path] = _library_metadata_preimage(kind=kind, split=split)
    return files


def _file_plans(
    descriptor: ExportProfileDescriptor,
    row_set: RowSet,
) -> tuple[ExportFilePlan, ...]:
    if descriptor.selector != (
        HF_DATASET_CONTAINER_ID,
        HF_DATASET_CONTAINER_VERSION,
        None,
        None,
    ):
        raise ExportContractError("hugging-face-dataset descriptor selector changed")
    if row_set.row_schema not in descriptor.supported_row_schemas:
        raise ExportContractError(
            "hugging-face-dataset v1 does not support source row schema "
            f"{row_set.row_schema!r}"
        )
    contents = _semantic_contents(row_set)
    roles = {
        HF_README_PATH: "readme",
        HF_DATASET_DICT_PATH: "dataset-dict",
        HF_TRAIN_ARROW_PATH: "training-partition",
        HF_TRAIN_INFO_PATH: "dataset-info",
        HF_TRAIN_STATE_PATH: "dataset-state",
        HF_EVALUATION_ARROW_PATH: "evaluation-partition",
        HF_EVALUATION_INFO_PATH: "dataset-info",
        HF_EVALUATION_STATE_PATH: "dataset-state",
        HF_DATA_CARD_PATH: "dataset-card",
        HF_PROVENANCE_PATH: "row-provenance",
    }
    media_types = {
        HF_README_PATH: "text/markdown",
        HF_DATASET_DICT_PATH: "application/json",
        HF_TRAIN_ARROW_PATH: HF_ARROW_MEDIA_TYPE,
        HF_TRAIN_INFO_PATH: "application/json",
        HF_TRAIN_STATE_PATH: "application/json",
        HF_EVALUATION_ARROW_PATH: HF_ARROW_MEDIA_TYPE,
        HF_EVALUATION_INFO_PATH: "application/json",
        HF_EVALUATION_STATE_PATH: "application/json",
        HF_DATA_CARD_PATH: "application/json",
        HF_PROVENANCE_PATH: "application/jsonl",
    }
    scopes = {
        HF_TRAIN_ARROW_PATH: "train",
        HF_EVALUATION_ARROW_PATH: "evaluation",
    }
    counts: dict[str, int | None] = {
        HF_TRAIN_ARROW_PATH: row_set.train_row_count,
        HF_EVALUATION_ARROW_PATH: row_set.evaluation_row_count,
        HF_PROVENANCE_PATH: row_set.total_row_count,
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
        plan.container_profile.container_id != HF_DATASET_CONTAINER_ID
        or plan.container_profile.container_version != HF_DATASET_CONTAINER_VERSION
        or plan.container_profile.determinism_claim != "semantic_content_only"
        or plan.consumer_profile is not None
    ):
        raise ExportVerificationError(
            "hugging-face-dataset renderer received another profile"
        )
    expected = _file_plans(HF_DATASET_DESCRIPTOR, row_set)
    if plan.file_plans != expected:
        raise ExportVerificationError(
            "hugging-face-dataset plan differs from the pinned file contract"
        )
    files = {
        **_dataset_dict_files(row_set),
        **_sidecar_files(row_set),
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
    card = HuggingFaceDatasetDataCard.from_json_bytes(by_path[HF_DATA_CARD_PATH])
    if card.row_schema not in V1_ROW_SCHEMA_KINDS:
        raise ExportVerificationError(
            "hugging-face-dataset data card row schema is unsupported"
        )
    train_payloads = _read_partition_payloads(by_path[HF_TRAIN_ARROW_PATH])
    evaluation_payloads = _read_partition_payloads(
        by_path[HF_EVALUATION_ARROW_PATH]
    )
    provenance = _provenance_from_jsonl_bytes(by_path[HF_PROVENANCE_PATH])
    if len(train_payloads) != card.train_row_count:
        raise ExportVerificationError(
            "hugging-face-dataset train count differs from its data card"
        )
    if len(evaluation_payloads) != card.evaluation_row_count:
        raise ExportVerificationError(
            "hugging-face-dataset evaluation count differs from its data card"
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
                "hugging-face-dataset payload differs from aligned provenance"
            )
        rows.append(row)
    train_rows = tuple(rows[: card.train_row_count])
    evaluation_rows = tuple(rows[card.train_row_count :])
    semantic = {
        HF_TRAIN_ARROW_PATH: columnar_partition_preimage_bytes(
            row_schema=card.row_schema,  # type: ignore[arg-type]
            partition="train",
            payloads=train_payloads,
        ),
        HF_EVALUATION_ARROW_PATH: columnar_partition_preimage_bytes(
            row_schema=card.row_schema,  # type: ignore[arg-type]
            partition="evaluation",
            payloads=evaluation_payloads,
        ),
        HF_DATA_CARD_PATH: by_path[HF_DATA_CARD_PATH],
        HF_PROVENANCE_PATH: by_path[HF_PROVENANCE_PATH],
        HF_README_PATH: by_path[HF_README_PATH],
    }
    for path, (kind, split) in _METADATA_KINDS.items():
        if path not in by_path:
            raise ExportVerificationError(
                f"hugging-face-dataset missing {path}"
            )
        semantic[path] = _library_metadata_preimage(kind=kind, split=split)
    expected_readme = _readme_bytes(card)
    if semantic[HF_README_PATH] != expected_readme:
        raise ExportVerificationError(
            "hugging-face-dataset README differs from its data card"
        )
    return _ReplayedDerivative(
        semantic_contents=tuple(sorted(semantic.items())),
        train_rows=train_rows,
        evaluation_rows=evaluation_rows,
        provenance=provenance,
    )


HF_DATASET_DESCRIPTOR = ExportProfileDescriptor(
    container_profile=ExportContainerProfile.create(
        container_id=HF_DATASET_CONTAINER_ID,
        container_version=HF_DATASET_CONTAINER_VERSION,
        determinism_claim="semantic_content_only",
    ),
    consumer_profile=None,
    dependencies=(
        ExportDependencyBinding.create(
            dependency_name="datasets",
            dependency_version=_DATASETS_VERSION_RANGE,
            dependency_role="hugging-face-dataset-renderer",
        ),
    ),
    supported_row_schemas=_SUPPORTED_ROW_SCHEMAS,
)

HF_DATASET_IMPLEMENTATION = _ExportImplementation(
    descriptor=HF_DATASET_DESCRIPTOR,
    file_planner=_file_plans,
    renderer=_render,
    semantic_replayer=_replay,
)


validate_export_path_set(
    (
        HF_README_PATH,
        HF_DATASET_DICT_PATH,
        HF_TRAIN_ARROW_PATH,
        HF_TRAIN_INFO_PATH,
        HF_TRAIN_STATE_PATH,
        HF_EVALUATION_ARROW_PATH,
        HF_EVALUATION_INFO_PATH,
        HF_EVALUATION_STATE_PATH,
        HF_DATA_CARD_PATH,
        HF_PROVENANCE_PATH,
        EXPORT_RECEIPT_PATH,
    ),
    label="hugging-face-dataset output tree",
    require_sorted=False,
)
