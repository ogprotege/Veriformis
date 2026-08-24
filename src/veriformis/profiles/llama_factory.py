"""LLaMA-Factory SFT consumer-profile adapter over a verified bundle.

Does not import LLaMA-Factory. Sidecars are dataset-only and do not launch
training.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from veriformis.contracts import V1_ROW_SCHEMA_KINDS
from veriformis.datasets import ProductRow, RowProvenance, RowSet
from veriformis.errors import ExportContractError, ExportVerificationError
from veriformis.exports._implementation import (
    _ExportImplementation,
    _RenderedDerivative,
)
from veriformis.exports._json import canonical_export_object_from_bytes
from veriformis.exports.api import ExportProfileDescriptor
from veriformis.exports.models import (
    EXPORT_RECEIPT_PATH,
    ExportConsumerProfile,
    ExportContainerProfile,
    ExportDependencyBinding,
    ExportFilePlan,
    ExportPlan,
)
from veriformis.exports.paths import validate_export_path_set
from veriformis.exports.split_jsonl import (
    SPLIT_JSONL_CONTAINER_ID,
    SPLIT_JSONL_CONTAINER_VERSION,
)
from veriformis.identity import lossless_json_bytes, sha256_digest, validate_id
from veriformis.profiles.admission import profile_admission_catalog
from veriformis.profiles.payload import map_admitted_payload
from veriformis.taxonomy import LOSS_POLICY_IDS, loss_policy_for_row

LLAMA_FACTORY_CONSUMER_ID = "llama-factory"
LLAMA_FACTORY_PROFILE_VERSION = 1
LLAMA_FACTORY_DATA_CARD_SCHEMA = "veriformis.llama-factory-data-card/v1"
LLAMA_FACTORY_PROFILE_METADATA_SCHEMA = "veriformis.llama-factory-profile-metadata/v1"
LLAMA_FACTORY_TRAIN_PATH = "data/train.jsonl"
LLAMA_FACTORY_EVALUATION_PATH = "data/evaluation.jsonl"
LLAMA_FACTORY_DATASET_INFO_PATH = "data/dataset_info.json"
LLAMA_FACTORY_DATA_CARD_PATH = "metadata/dataset-card.json"
LLAMA_FACTORY_PROFILE_METADATA_PATH = "metadata/llama-factory-profile.json"
LLAMA_FACTORY_LAUNCH_SCHEMA = "veriformis.llama-factory-sft-launch/v1"
LLAMA_FACTORY_LAUNCH_PATH = "metadata/llama-factory-sft-launch.json"
LLAMA_FACTORY_PROVENANCE_PATH = "metadata/row-provenance.jsonl"
LLAMA_FACTORY_README_PATH = "README.md"
LLAMA_FACTORY_TRAIN_DATASET = "veriformis_train"
LLAMA_FACTORY_EVALUATION_DATASET = "veriformis_evaluation"
_SUPPORTED_ROW_SCHEMAS = tuple(sorted(V1_ROW_SCHEMA_KINDS))
_LLAMA_FACTORY_COMMAND_ARGV = ("llamafactory-cli", "train")
_LLAMA_FACTORY_OPERATOR_MUST_SUPPLY = (
    "model_name_or_path",
    "sft-training-arguments",
)
_LLAMA_FACTORY_LAUNCH_NOTES = (
    "Sidecar records dataset_info.json names and local JSONL paths. "
    "Veriformis does not launch training, select a model, or set "
    "hyperparameters."
)


def _llama_factory_pin():
    return next(
        record
        for record in profile_admission_catalog().records
        if record.profile_id == LLAMA_FACTORY_CONSUMER_ID
    )


def _mapping_for(row_schema: str):
    pin = _llama_factory_pin()
    for item in pin.row_mappings:
        if item.source_row_schema == row_schema:
            return item
    raise ExportContractError(
        f"LLaMA-Factory admission does not map source row schema {row_schema!r}"
    )


def map_llama_factory_payload(
    row_schema: str, payload: Mapping[str, Any]
) -> dict[str, Any]:
    """Map one verified payload onto LLaMA-Factory columns. Does not change membership."""
    return map_admitted_payload(_mapping_for(row_schema), payload)


def _dataset_entry(row_schema: str, file_name: str) -> dict[str, Any]:
    mapping = _mapping_for(row_schema)
    if mapping.destination_format == "alpaca":
        return {
            "columns": {
                "prompt": "instruction",
                "query": "input",
                "response": "output",
            },
            "file_name": file_name,
            "formatting": "alpaca",
        }
    if mapping.destination_format == "sharegpt":
        return {
            "columns": {"messages": "conversations"},
            "file_name": file_name,
            "formatting": "sharegpt",
            "tags": {
                "assistant_tag": "gpt",
                "content_tag": "value",
                "role_tag": "from",
                "user_tag": "human",
            },
        }
    if mapping.destination_format == "alpaca-pretrain":
        return {
            "columns": {"prompt": "text"},
            "file_name": file_name,
        }
    raise ExportContractError(
        f"LLaMA-Factory has no dataset_info entry for {mapping.destination_format!r}"
    )


def llama_factory_dataset_info(
    row_schema: str, *, has_evaluation: bool
) -> dict[str, Any]:
    info = {
        LLAMA_FACTORY_TRAIN_DATASET: _dataset_entry(row_schema, "train.jsonl"),
    }
    if has_evaluation:
        info[LLAMA_FACTORY_EVALUATION_DATASET] = _dataset_entry(
            row_schema, "evaluation.jsonl"
        )
    return info


def llama_factory_dataset_info_bytes(
    row_schema: str, *, has_evaluation: bool
) -> bytes:
    return lossless_json_bytes(
        llama_factory_dataset_info(row_schema, has_evaluation=has_evaluation)
    )


class _StrictLlamaFactoryModel(BaseModel):
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


class LlamaFactoryDataCard(_StrictLlamaFactoryModel):
    schema_version: Literal["veriformis.llama-factory-data-card/v1"] = (
        LLAMA_FACTORY_DATA_CARD_SCHEMA
    )
    container_id: Literal["split-jsonl-directory"] = SPLIT_JSONL_CONTAINER_ID
    container_version: Literal[1] = SPLIT_JSONL_CONTAINER_VERSION
    consumer_id: Literal["llama-factory"] = LLAMA_FACTORY_CONSUMER_ID
    consumer_profile_version: Literal[1] = LLAMA_FACTORY_PROFILE_VERSION
    row_schema: str
    objective_id: str
    loss_policy: str
    row_set_id: str
    split_result_id: str
    train_path: Literal["data/train.jsonl"] = LLAMA_FACTORY_TRAIN_PATH
    train_row_count: int
    evaluation_path: Literal["data/evaluation.jsonl"] = LLAMA_FACTORY_EVALUATION_PATH
    evaluation_row_count: int
    provenance_path: Literal["metadata/row-provenance.jsonl"] = (
        LLAMA_FACTORY_PROVENANCE_PATH
    )
    provenance_row_count: int
    mapping_kind: str
    destination_format: str
    destination_keys: tuple[str, ...]
    dataset_info_path: Literal["data/dataset_info.json"] = (
        LLAMA_FACTORY_DATASET_INFO_PATH
    )
    receipt_path: Literal["export-receipt.json"] = EXPORT_RECEIPT_PATH
    trainer_compatibility_claimed: Literal[False] = False

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

    @field_validator("destination_keys", mode="before")
    @classmethod
    def _tuple_keys(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

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
    def _closed(self) -> Self:
        if self.train_row_count < 1:
            raise ValueError("data card requires a non-empty train partition")
        if self.loss_policy != loss_policy_for_row(self.row_schema):
            raise ValueError("data card loss policy differs from its row schema")
        if self.provenance_row_count != (
            self.train_row_count + self.evaluation_row_count
        ):
            raise ValueError("data card provenance count is not aligned")
        mapping = _mapping_for(self.row_schema)
        if (
            self.mapping_kind != mapping.mapping_kind
            or self.destination_format != mapping.destination_format
            or self.destination_keys != mapping.destination_keys
        ):
            raise ValueError(
                "data card mapping differs from the LLaMA-Factory admission pin"
            )
        validate_export_path_set(
            tuple(
                sorted(
                    (
                        self.receipt_path,
                        LLAMA_FACTORY_README_PATH,
                        self.evaluation_path,
                        self.train_path,
                        LLAMA_FACTORY_DATASET_INFO_PATH,
                        LLAMA_FACTORY_DATA_CARD_PATH,
                        LLAMA_FACTORY_LAUNCH_PATH,
                        LLAMA_FACTORY_PROFILE_METADATA_PATH,
                        self.provenance_path,
                    )
                )
            ),
            label="LLaMA-Factory data card paths",
        )
        return self


class LlamaFactoryProfileMetadata(_StrictLlamaFactoryModel):
    schema_version: Literal["veriformis.llama-factory-profile-metadata/v1"] = (
        LLAMA_FACTORY_PROFILE_METADATA_SCHEMA
    )
    profile_id: Literal["llama-factory"] = LLAMA_FACTORY_CONSUMER_ID
    profile_version: Literal[1] = LLAMA_FACTORY_PROFILE_VERSION
    package: str
    extra: str
    version_range: str
    license: str
    primary_docs_url: str
    docs_reviewed_on: str
    workflow: str
    row_schema: str
    mapping_kind: str
    destination_format: str
    destination_keys: tuple[str, ...]
    refused_dataset_types: tuple[str, ...]
    round_trip: Literal[False] = False
    loader: str
    loss_notes: str
    executable_item: Literal["10.4"] = "10.4"
    taxonomy_state: Literal["implemented"] = "implemented"
    trainer_compatibility_claimed: Literal[False] = False

    @field_validator("destination_keys", "refused_dataset_types", mode="before")
    @classmethod
    def _tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> Self:
        pin = _llama_factory_pin()
        if (
            self.package != pin.package
            or self.extra != pin.extra
            or self.version_range != pin.version_range
            or self.license != pin.license
            or self.primary_docs_url != pin.primary_docs_url
            or self.docs_reviewed_on != pin.docs_reviewed_on
            or self.workflow != pin.workflow
            or self.loader != pin.loader
            or self.loss_notes != pin.loss_notes
            or self.refused_dataset_types != pin.refused_dataset_types
        ):
            raise ValueError("LLaMA-Factory metadata differs from the admission pin")
        mapping = _mapping_for(self.row_schema)
        if (
            self.mapping_kind != mapping.mapping_kind
            or self.destination_format != mapping.destination_format
            or self.destination_keys != mapping.destination_keys
        ):
            raise ValueError(
                "LLaMA-Factory metadata mapping differs from the admission pin"
            )
        return self


class LlamaFactoryLaunchDataFiles(_StrictLlamaFactoryModel):
    evaluation: Literal["data/evaluation.jsonl"] = LLAMA_FACTORY_EVALUATION_PATH
    train: Literal["data/train.jsonl"] = LLAMA_FACTORY_TRAIN_PATH


class LlamaFactorySftLaunchSidecar(_StrictLlamaFactoryModel):
    schema_version: Literal["veriformis.llama-factory-sft-launch/v1"] = (
        LLAMA_FACTORY_LAUNCH_SCHEMA
    )
    command_argv: tuple[
        Literal["llamafactory-cli"],
        Literal["train"],
    ] = _LLAMA_FACTORY_COMMAND_ARGV
    data_files: LlamaFactoryLaunchDataFiles
    dataset_info_path: Literal["data/dataset_info.json"] = (
        LLAMA_FACTORY_DATASET_INFO_PATH
    )
    dataset_names: tuple[str, ...]
    destination_format: str
    destination_keys: tuple[str, ...]
    docs_reviewed_on: str
    evaluation_row_count: int
    executable_item: Literal["10.8"] = "10.8"
    launches_training: Literal[False] = False
    mapping_kind: str
    notes: Literal[_LLAMA_FACTORY_LAUNCH_NOTES] = _LLAMA_FACTORY_LAUNCH_NOTES
    operator_must_supply: tuple[
        Literal["model_name_or_path"],
        Literal["sft-training-arguments"],
    ] = _LLAMA_FACTORY_OPERATOR_MUST_SUPPLY
    primary_docs_url: str
    profile_id: Literal["llama-factory"] = LLAMA_FACTORY_CONSUMER_ID
    profile_version: Literal[1] = LLAMA_FACTORY_PROFILE_VERSION
    row_schema: str
    selects_hyperparameters: Literal[False] = False
    selects_model: Literal[False] = False
    train_row_count: int
    use_eval_dataset: bool

    @field_validator("row_schema")
    @classmethod
    def _valid_row_schema(cls, value: str) -> str:
        if value not in V1_ROW_SCHEMA_KINDS:
            raise ValueError("launch sidecar names an unsupported row schema")
        return value

    @field_validator(
        "command_argv",
        "dataset_names",
        "destination_keys",
        "operator_must_supply",
        mode="before",
    )
    @classmethod
    def _tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @field_validator("train_row_count", "evaluation_row_count")
    @classmethod
    def _valid_count(cls, value: int) -> int:
        if type(value) is not int or value < 0:
            raise ValueError("launch sidecar row counts must be non-negative integers")
        return value

    @model_validator(mode="after")
    def _closed(self) -> Self:
        if self.train_row_count < 1:
            raise ValueError("launch sidecar requires a non-empty train partition")
        if self.use_eval_dataset is not (self.evaluation_row_count > 0):
            raise ValueError(
                "use_eval_dataset must match a nonempty evaluation partition"
            )
        if self.command_argv != _LLAMA_FACTORY_COMMAND_ARGV:
            raise ValueError(
                "LLaMA-Factory launch command_argv is not the dataset-only fragment"
            )
        if self.operator_must_supply != _LLAMA_FACTORY_OPERATOR_MUST_SUPPLY:
            raise ValueError("LLaMA-Factory launch operator_must_supply is not closed")
        if "--train" in self.command_argv:
            raise ValueError("LLaMA-Factory launch sidecar must not include --train")
        expected_names = (LLAMA_FACTORY_TRAIN_DATASET,)
        if self.use_eval_dataset:
            expected_names = (
                LLAMA_FACTORY_EVALUATION_DATASET,
                LLAMA_FACTORY_TRAIN_DATASET,
            )
        if self.dataset_names != expected_names:
            raise ValueError("LLaMA-Factory dataset_names are not closed")
        pin = _llama_factory_pin()
        if (
            self.primary_docs_url != pin.primary_docs_url
            or self.docs_reviewed_on != pin.docs_reviewed_on
        ):
            raise ValueError(
                "LLaMA-Factory launch sidecar docs differ from the admission pin"
            )
        mapping = _mapping_for(self.row_schema)
        if (
            self.mapping_kind != mapping.mapping_kind
            or self.destination_format != mapping.destination_format
            or self.destination_keys != mapping.destination_keys
        ):
            raise ValueError(
                "LLaMA-Factory launch mapping differs from the admission pin"
            )
        return self


def _payload_jsonl(row_schema: str, rows: Sequence[ProductRow]) -> bytes:
    return b"".join(
        lossless_json_bytes(map_llama_factory_payload(row_schema, row.payload))
        + b"\n"
        for row in rows
    )


def _provenance_jsonl(provenance: Sequence[RowProvenance]) -> bytes:
    return b"".join(
        lossless_json_bytes(item.model_dump(mode="json")) + b"\n" for item in provenance
    )


def _data_card(row_set: RowSet) -> LlamaFactoryDataCard:
    objective_ids = {item.objective_id for item in row_set.provenance}
    if len(objective_ids) != 1:
        raise ExportContractError(
            "LLaMA-Factory export requires one objective identity across the source row set"
        )
    mapping = _mapping_for(row_set.row_schema)
    return LlamaFactoryDataCard(
        row_schema=row_set.row_schema,
        objective_id=next(iter(objective_ids)),
        loss_policy=loss_policy_for_row(row_set.row_schema),
        row_set_id=row_set.row_set_id,
        split_result_id=row_set.split_result_id,
        train_row_count=row_set.train_row_count,
        evaluation_row_count=row_set.evaluation_row_count,
        provenance_row_count=row_set.total_row_count,
        mapping_kind=mapping.mapping_kind,
        destination_format=mapping.destination_format,
        destination_keys=mapping.destination_keys,
    )


def _profile_metadata(row_set: RowSet) -> LlamaFactoryProfileMetadata:
    pin = _llama_factory_pin()
    mapping = _mapping_for(row_set.row_schema)
    return LlamaFactoryProfileMetadata(
        package=pin.package,
        extra=pin.extra,
        version_range=pin.version_range,
        license=pin.license,
        primary_docs_url=pin.primary_docs_url,
        docs_reviewed_on=pin.docs_reviewed_on,
        workflow=pin.workflow,
        row_schema=row_set.row_schema,
        mapping_kind=mapping.mapping_kind,
        destination_format=mapping.destination_format,
        destination_keys=mapping.destination_keys,
        refused_dataset_types=pin.refused_dataset_types,
        loader=pin.loader,
        loss_notes=pin.loss_notes,
    )


def _dataset_names(row_set: RowSet) -> tuple[str, ...]:
    if row_set.evaluation_row_count > 0:
        return (LLAMA_FACTORY_EVALUATION_DATASET, LLAMA_FACTORY_TRAIN_DATASET)
    return (LLAMA_FACTORY_TRAIN_DATASET,)


def _launch_sidecar(row_set: RowSet) -> LlamaFactorySftLaunchSidecar:
    pin = _llama_factory_pin()
    mapping = _mapping_for(row_set.row_schema)
    return LlamaFactorySftLaunchSidecar(
        command_argv=_LLAMA_FACTORY_COMMAND_ARGV,
        data_files=LlamaFactoryLaunchDataFiles(),
        dataset_names=_dataset_names(row_set),
        destination_format=mapping.destination_format,
        destination_keys=mapping.destination_keys,
        docs_reviewed_on=pin.docs_reviewed_on,
        evaluation_row_count=row_set.evaluation_row_count,
        mapping_kind=mapping.mapping_kind,
        operator_must_supply=_LLAMA_FACTORY_OPERATOR_MUST_SUPPLY,
        primary_docs_url=pin.primary_docs_url,
        row_schema=row_set.row_schema,
        train_row_count=row_set.train_row_count,
        use_eval_dataset=row_set.evaluation_row_count > 0,
    )


def _readme_bytes(card: LlamaFactoryDataCard) -> bytes:
    mapping = _mapping_for(card.row_schema)
    text = (
        "# Veriformis LLaMA-Factory SFT export\n\n"
        "This optional adapter maps a verified Veriformis bundle onto "
        "LLaMA-Factory alpaca or sharegpt JSONL plus `dataset_info.json`. "
        "It does not curate, resplit, or change membership or loss-policy IDs.\n\n"
        f"- Container: `{card.container_id}` v{card.container_version}\n"
        f"- Consumer: `{card.consumer_id}` v{card.consumer_profile_version}\n"
        f"- Row schema: `{card.row_schema}`\n"
        f"- Destination format: `{mapping.destination_format}`\n"
        f"- Mapping: `{mapping.mapping_kind}`\n"
        f"- Loss policy: `{card.loss_policy}` (unchanged Veriformis ID)\n"
        f"- Train: `{card.train_path}` ({card.train_row_count} rows)\n"
        f"- Evaluation: `{card.evaluation_path}` "
        f"({card.evaluation_row_count} rows)\n"
        f"- Dataset info: `{card.dataset_info_path}`\n"
        f"- Provenance: `{card.provenance_path}` "
        f"({card.provenance_row_count} aligned rows)\n"
        f"- Source row set: `{card.row_set_id}`\n\n"
        "Load `data/dataset_info.json` with `file_name` relative to `data/`. "
        "Do not glob `metadata/` into the loader. Veriformis does not launch "
        "`llamafactory-cli train`, select a model, or set hyperparameters. "
        "Loader conformance is item 10.7; this export does not claim that "
        "LLaMA-Factory has loaded the files.\n\n"
        "History, KTO, preference, ranking, tools, unpaired preference, and "
        "vision types are refused. `round_trip` is false.\n"
    )
    return text.encode("utf-8")


def _rendered_files(row_set: RowSet) -> tuple[tuple[str, bytes], ...]:
    card = _data_card(row_set)
    metadata = _profile_metadata(row_set)
    launch = _launch_sidecar(row_set)
    files = {
        LLAMA_FACTORY_README_PATH: _readme_bytes(card),
        LLAMA_FACTORY_EVALUATION_PATH: _payload_jsonl(
            row_set.row_schema, row_set.evaluation_rows
        ),
        LLAMA_FACTORY_TRAIN_PATH: _payload_jsonl(
            row_set.row_schema, row_set.train_rows
        ),
        LLAMA_FACTORY_DATASET_INFO_PATH: llama_factory_dataset_info_bytes(
            row_set.row_schema,
            has_evaluation=row_set.evaluation_row_count > 0,
        ),
        LLAMA_FACTORY_DATA_CARD_PATH: card.canonical_bytes(),
        LLAMA_FACTORY_LAUNCH_PATH: launch.canonical_bytes(),
        LLAMA_FACTORY_PROFILE_METADATA_PATH: metadata.canonical_bytes(),
        LLAMA_FACTORY_PROVENANCE_PATH: _provenance_jsonl(row_set.provenance),
    }
    return tuple(sorted(files.items()))


def _file_plans(
    descriptor: ExportProfileDescriptor,
    row_set: RowSet,
) -> tuple[ExportFilePlan, ...]:
    if descriptor.selector != (
        SPLIT_JSONL_CONTAINER_ID,
        SPLIT_JSONL_CONTAINER_VERSION,
        LLAMA_FACTORY_CONSUMER_ID,
        LLAMA_FACTORY_PROFILE_VERSION,
    ):
        raise ExportContractError("LLaMA-Factory descriptor selector changed")
    if row_set.row_schema not in descriptor.supported_row_schemas:
        raise ExportContractError(
            "LLaMA-Factory does not support the source row schema"
        )
    by_path = dict(_rendered_files(row_set))
    roles = {
        LLAMA_FACTORY_README_PATH: "readme",
        LLAMA_FACTORY_EVALUATION_PATH: "evaluation-partition",
        LLAMA_FACTORY_TRAIN_PATH: "training-partition",
        LLAMA_FACTORY_DATASET_INFO_PATH: "dataset-info",
        LLAMA_FACTORY_DATA_CARD_PATH: "dataset-card",
        LLAMA_FACTORY_LAUNCH_PATH: "launch-sidecar",
        LLAMA_FACTORY_PROFILE_METADATA_PATH: "consumer-profile-metadata",
        LLAMA_FACTORY_PROVENANCE_PATH: "row-provenance",
    }
    media_types = {
        LLAMA_FACTORY_README_PATH: "text/markdown",
        LLAMA_FACTORY_EVALUATION_PATH: "application/jsonl",
        LLAMA_FACTORY_TRAIN_PATH: "application/jsonl",
        LLAMA_FACTORY_DATASET_INFO_PATH: "application/json",
        LLAMA_FACTORY_DATA_CARD_PATH: "application/json",
        LLAMA_FACTORY_LAUNCH_PATH: "application/json",
        LLAMA_FACTORY_PROFILE_METADATA_PATH: "application/json",
        LLAMA_FACTORY_PROVENANCE_PATH: "application/jsonl",
    }
    scopes = {
        LLAMA_FACTORY_EVALUATION_PATH: "evaluation",
        LLAMA_FACTORY_TRAIN_PATH: "train",
    }
    counts: dict[str, int | None] = {
        LLAMA_FACTORY_EVALUATION_PATH: row_set.evaluation_row_count,
        LLAMA_FACTORY_TRAIN_PATH: row_set.train_row_count,
        LLAMA_FACTORY_PROVENANCE_PATH: row_set.total_row_count,
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
    consumer = plan.consumer_profile
    if (
        plan.container_profile.container_id != SPLIT_JSONL_CONTAINER_ID
        or plan.container_profile.container_version != SPLIT_JSONL_CONTAINER_VERSION
        or plan.container_profile.determinism_claim != "portable_exact_bytes"
        or consumer is None
        or consumer.consumer_id != LLAMA_FACTORY_CONSUMER_ID
        or consumer.profile_version != LLAMA_FACTORY_PROFILE_VERSION
    ):
        raise ExportVerificationError(
            "LLaMA-Factory renderer received another profile"
        )
    return _RenderedDerivative(
        files=_rendered_files(row_set),
        train_rows=row_set.train_rows,
        evaluation_rows=row_set.evaluation_rows,
        provenance=row_set.provenance,
    )


LLAMA_FACTORY_DESCRIPTOR = ExportProfileDescriptor(
    container_profile=ExportContainerProfile.create(
        container_id=SPLIT_JSONL_CONTAINER_ID,
        container_version=SPLIT_JSONL_CONTAINER_VERSION,
        determinism_claim="portable_exact_bytes",
    ),
    consumer_profile=ExportConsumerProfile.create(
        consumer_id=LLAMA_FACTORY_CONSUMER_ID,
        profile_version=LLAMA_FACTORY_PROFILE_VERSION,
        accepted_row_schemas=_SUPPORTED_ROW_SCHEMAS,
    ),
    dependencies=(
        ExportDependencyBinding.create(
            dependency_name="veriformis-llama-factory-sft-renderer",
            dependency_version="1",
            dependency_role="renderer",
        ),
    ),
    supported_row_schemas=_SUPPORTED_ROW_SCHEMAS,
)

LLAMA_FACTORY_IMPLEMENTATION = _ExportImplementation(
    descriptor=LLAMA_FACTORY_DESCRIPTOR,
    file_planner=_file_plans,
    renderer=_render,
    semantic_replayer=None,
)


__all__ = [
    "LLAMA_FACTORY_CONSUMER_ID",
    "LLAMA_FACTORY_DATA_CARD_PATH",
    "LLAMA_FACTORY_DATA_CARD_SCHEMA",
    "LLAMA_FACTORY_DATASET_INFO_PATH",
    "LLAMA_FACTORY_DESCRIPTOR",
    "LLAMA_FACTORY_EVALUATION_DATASET",
    "LLAMA_FACTORY_EVALUATION_PATH",
    "LLAMA_FACTORY_IMPLEMENTATION",
    "LLAMA_FACTORY_LAUNCH_PATH",
    "LLAMA_FACTORY_LAUNCH_SCHEMA",
    "LLAMA_FACTORY_PROFILE_METADATA_PATH",
    "LLAMA_FACTORY_PROFILE_METADATA_SCHEMA",
    "LLAMA_FACTORY_PROFILE_VERSION",
    "LLAMA_FACTORY_PROVENANCE_PATH",
    "LLAMA_FACTORY_README_PATH",
    "LLAMA_FACTORY_TRAIN_DATASET",
    "LLAMA_FACTORY_TRAIN_PATH",
    "LlamaFactoryDataCard",
    "LlamaFactoryLaunchDataFiles",
    "LlamaFactoryProfileMetadata",
    "LlamaFactorySftLaunchSidecar",
    "llama_factory_dataset_info",
    "llama_factory_dataset_info_bytes",
    "map_llama_factory_payload",
]
