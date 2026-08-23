"""TRL SFT consumer-profile adapter over a verified bundle. Does not import TRL."""

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
from veriformis.profiles.admission import (
    profile_admission_catalog,
    require_profile_messages_payload,
)
from veriformis.taxonomy import LOSS_POLICY_IDS, loss_policy_for_row

TRL_CONSUMER_ID = "trl"
TRL_PROFILE_VERSION = 1
TRL_DATA_CARD_SCHEMA = "veriformis.trl-data-card/v1"
TRL_PROFILE_METADATA_SCHEMA = "veriformis.trl-profile-metadata/v1"
TRL_TRAIN_PATH = "data/train.jsonl"
TRL_EVALUATION_PATH = "data/evaluation.jsonl"
TRL_DATA_CARD_PATH = "metadata/dataset-card.json"
TRL_PROFILE_METADATA_PATH = "metadata/trl-profile.json"
TRL_LAUNCH_SCHEMA = "veriformis.trl-sft-launch/v1"
TRL_LAUNCH_PATH = "metadata/trl-sft-launch.json"
TRL_PROVENANCE_PATH = "metadata/row-provenance.jsonl"
TRL_README_PATH = "README.md"
_SUPPORTED_ROW_SCHEMAS = tuple(sorted(V1_ROW_SCHEMA_KINDS))
_TRL_COMMAND_ARGV = ("trl", "sft", "--dataset_name", "json")
_TRL_OPERATOR_MUST_SUPPLY = ("model", "sft-training-arguments")
_TRL_LAUNCH_NOTES = (
    "Sidecar records DatasetDict data_files for TRL SFTTrainer. "
    "Veriformis does not launch training, select a model, or set "
    "hyperparameters."
)


def _trl_pin():
    return next(
        record
        for record in profile_admission_catalog().records
        if record.profile_id == TRL_CONSUMER_ID
    )


def _mapping_for(row_schema: str):
    pin = _trl_pin()
    for item in pin.row_mappings:
        if item.source_row_schema == row_schema:
            return item
    raise ExportContractError(
        f"TRL admission does not map source row schema {row_schema!r}"
    )


def map_trl_payload(row_schema: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Map one verified payload onto TRL SFT columns. Does not change membership."""
    mapping = _mapping_for(row_schema)
    if mapping.mapping_kind == "identity":
        if row_schema == "messages":
            require_profile_messages_payload(payload)
        mapped = dict(payload)
    elif mapping.mapping_kind == "assemble-prompt":
        instruction = payload["instruction"]
        context = payload["input"]
        prompt = (
            f"{instruction}\n{context}" if str(context) else str(instruction)
        )
        mapped = {"completion": payload["output"], "prompt": prompt}
    else:
        raise ExportContractError(
            f"TRL mapping kind {mapping.mapping_kind!r} is not executable"
        )
    keys = tuple(sorted(mapped))
    if keys != mapping.destination_keys:
        raise ExportContractError(
            "TRL mapped keys differ from the admission pin "
            f"{mapping.destination_keys!r}: {keys!r}"
        )
    return mapped


class _StrictTrlModel(BaseModel):
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


class TrlDataCard(_StrictTrlModel):
    schema_version: Literal["veriformis.trl-data-card/v1"] = TRL_DATA_CARD_SCHEMA
    container_id: Literal["split-jsonl-directory"] = SPLIT_JSONL_CONTAINER_ID
    container_version: Literal[1] = SPLIT_JSONL_CONTAINER_VERSION
    consumer_id: Literal["trl"] = TRL_CONSUMER_ID
    consumer_profile_version: Literal[1] = TRL_PROFILE_VERSION
    row_schema: str
    objective_id: str
    loss_policy: str
    row_set_id: str
    split_result_id: str
    train_path: Literal["data/train.jsonl"] = TRL_TRAIN_PATH
    train_row_count: int
    evaluation_path: Literal["data/evaluation.jsonl"] = TRL_EVALUATION_PATH
    evaluation_row_count: int
    provenance_path: Literal["metadata/row-provenance.jsonl"] = TRL_PROVENANCE_PATH
    provenance_row_count: int
    mapping_kind: str
    destination_format: str
    destination_keys: tuple[str, ...]
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
            raise ValueError("data card mapping differs from the TRL admission pin")
        validate_export_path_set(
            tuple(
                sorted(
                    (
                        self.receipt_path,
                        TRL_README_PATH,
                        self.evaluation_path,
                        self.train_path,
                        TRL_DATA_CARD_PATH,
                        TRL_LAUNCH_PATH,
                        TRL_PROFILE_METADATA_PATH,
                        self.provenance_path,
                    )
                )
            ),
            label="TRL data card paths",
        )
        return self


class TrlProfileMetadata(_StrictTrlModel):
    schema_version: Literal["veriformis.trl-profile-metadata/v1"] = (
        TRL_PROFILE_METADATA_SCHEMA
    )
    profile_id: Literal["trl"] = TRL_CONSUMER_ID
    profile_version: Literal[1] = TRL_PROFILE_VERSION
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
    executable_item: Literal["8.3"] = "8.3"
    taxonomy_state: Literal["implemented"] = "implemented"
    trainer_compatibility_claimed: Literal[False] = False

    @field_validator("destination_keys", "refused_dataset_types", mode="before")
    @classmethod
    def _tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> Self:
        pin = _trl_pin()
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
            raise ValueError("TRL metadata differs from the admission pin")
        mapping = _mapping_for(self.row_schema)
        if (
            self.mapping_kind != mapping.mapping_kind
            or self.destination_format != mapping.destination_format
            or self.destination_keys != mapping.destination_keys
        ):
            raise ValueError("TRL metadata mapping differs from the admission pin")
        return self


class TrlLaunchDataFiles(_StrictTrlModel):
    evaluation: Literal["data/evaluation.jsonl"] = TRL_EVALUATION_PATH
    train: Literal["data/train.jsonl"] = TRL_TRAIN_PATH


class TrlSftLaunchSidecar(_StrictTrlModel):
    schema_version: Literal["veriformis.trl-sft-launch/v1"] = TRL_LAUNCH_SCHEMA
    command_argv: tuple[
        Literal["trl"],
        Literal["sft"],
        Literal["--dataset_name"],
        Literal["json"],
    ] = _TRL_COMMAND_ARGV
    data_files: TrlLaunchDataFiles
    destination_format: str
    destination_keys: tuple[str, ...]
    docs_reviewed_on: str
    evaluation_row_count: int
    executable_item: Literal["8.6"] = "8.6"
    huggingface_builder: Literal["json"] = "json"
    launches_training: Literal[False] = False
    mapping_kind: str
    notes: Literal[_TRL_LAUNCH_NOTES] = _TRL_LAUNCH_NOTES
    operator_must_supply: tuple[
        Literal["model"],
        Literal["sft-training-arguments"],
    ] = _TRL_OPERATOR_MUST_SUPPLY
    primary_docs_url: str
    profile_id: Literal["trl"] = TRL_CONSUMER_ID
    profile_version: Literal[1] = TRL_PROFILE_VERSION
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
        if self.command_argv != _TRL_COMMAND_ARGV:
            raise ValueError("TRL launch command_argv is not the dataset-only fragment")
        if self.operator_must_supply != _TRL_OPERATOR_MUST_SUPPLY:
            raise ValueError("TRL launch operator_must_supply is not closed")
        pin = _trl_pin()
        if (
            self.primary_docs_url != pin.primary_docs_url
            or self.docs_reviewed_on != pin.docs_reviewed_on
        ):
            raise ValueError("TRL launch sidecar docs differ from the admission pin")
        mapping = _mapping_for(self.row_schema)
        if (
            self.mapping_kind != mapping.mapping_kind
            or self.destination_format != mapping.destination_format
            or self.destination_keys != mapping.destination_keys
        ):
            raise ValueError("TRL launch mapping differs from the admission pin")
        return self


def _payload_jsonl(row_schema: str, rows: Sequence[ProductRow]) -> bytes:
    return b"".join(
        lossless_json_bytes(map_trl_payload(row_schema, row.payload)) + b"\n"
        for row in rows
    )


def _provenance_jsonl(provenance: Sequence[RowProvenance]) -> bytes:
    return b"".join(
        lossless_json_bytes(item.model_dump(mode="json")) + b"\n" for item in provenance
    )


def _data_card(row_set: RowSet) -> TrlDataCard:
    objective_ids = {item.objective_id for item in row_set.provenance}
    if len(objective_ids) != 1:
        raise ExportContractError(
            "TRL export requires one objective identity across the source row set"
        )
    mapping = _mapping_for(row_set.row_schema)
    return TrlDataCard(
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


def _profile_metadata(row_set: RowSet) -> TrlProfileMetadata:
    pin = _trl_pin()
    mapping = _mapping_for(row_set.row_schema)
    return TrlProfileMetadata(
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


def _launch_sidecar(row_set: RowSet) -> TrlSftLaunchSidecar:
    pin = _trl_pin()
    mapping = _mapping_for(row_set.row_schema)
    return TrlSftLaunchSidecar(
        command_argv=_TRL_COMMAND_ARGV,
        data_files=TrlLaunchDataFiles(),
        destination_format=mapping.destination_format,
        destination_keys=mapping.destination_keys,
        docs_reviewed_on=pin.docs_reviewed_on,
        evaluation_row_count=row_set.evaluation_row_count,
        mapping_kind=mapping.mapping_kind,
        operator_must_supply=_TRL_OPERATOR_MUST_SUPPLY,
        primary_docs_url=pin.primary_docs_url,
        row_schema=row_set.row_schema,
        train_row_count=row_set.train_row_count,
        use_eval_dataset=row_set.evaluation_row_count > 0,
    )


def _readme_bytes(card: TrlDataCard) -> bytes:
    mapping = _mapping_for(card.row_schema)
    text = (
        "# Veriformis TRL SFT export\n\n"
        "This optional adapter maps a verified Veriformis bundle onto TRL "
        "SFTTrainer language-modeling or prompt-completion columns. It does "
        "not curate, resplit, or change membership or loss-policy IDs.\n\n"
        f"- Container: `{card.container_id}` v{card.container_version}\n"
        f"- Consumer: `{card.consumer_id}` v{card.consumer_profile_version}\n"
        f"- Row schema: `{card.row_schema}`\n"
        f"- Destination format: `{mapping.destination_format}`\n"
        f"- Mapping: `{mapping.mapping_kind}`\n"
        f"- Loss policy: `{card.loss_policy}` (unchanged Veriformis ID)\n"
        f"- Train: `{card.train_path}` ({card.train_row_count} rows)\n"
        f"- Evaluation: `{card.evaluation_path}` "
        f"({card.evaluation_row_count} rows)\n"
        f"- Provenance: `{card.provenance_path}` "
        f"({card.provenance_row_count} aligned rows)\n"
        f"- Source row set: `{card.row_set_id}`\n\n"
        "Load the partitions as a Hugging Face `DatasetDict` with explicit "
        "`data_files` for `train` and `evaluation`. Do not glob `metadata/` "
        "into the loader. The launch sidecar at `metadata/trl-sft-launch.json` "
        "repeats those dataset paths. Veriformis does not launch `trl sft`, "
        "select a model, or set hyperparameters. Loader conformance is item "
        "8.5; this export does not claim that TRL has loaded the files.\n\n"
        "Preference, prompt-only, stepwise-supervision, tools, unpaired "
        "preference, and vision types are refused. `round_trip` is false.\n"
    )
    return text.encode("utf-8")


def _rendered_files(row_set: RowSet) -> tuple[tuple[str, bytes], ...]:
    card = _data_card(row_set)
    metadata = _profile_metadata(row_set)
    launch = _launch_sidecar(row_set)
    files = {
        TRL_README_PATH: _readme_bytes(card),
        TRL_EVALUATION_PATH: _payload_jsonl(
            row_set.row_schema, row_set.evaluation_rows
        ),
        TRL_TRAIN_PATH: _payload_jsonl(row_set.row_schema, row_set.train_rows),
        TRL_DATA_CARD_PATH: card.canonical_bytes(),
        TRL_LAUNCH_PATH: launch.canonical_bytes(),
        TRL_PROFILE_METADATA_PATH: metadata.canonical_bytes(),
        TRL_PROVENANCE_PATH: _provenance_jsonl(row_set.provenance),
    }
    return tuple(sorted(files.items()))


def _file_plans(
    descriptor: ExportProfileDescriptor,
    row_set: RowSet,
) -> tuple[ExportFilePlan, ...]:
    if descriptor.selector != (
        SPLIT_JSONL_CONTAINER_ID,
        SPLIT_JSONL_CONTAINER_VERSION,
        TRL_CONSUMER_ID,
        TRL_PROFILE_VERSION,
    ):
        raise ExportContractError("TRL descriptor selector changed")
    if row_set.row_schema not in descriptor.supported_row_schemas:
        raise ExportContractError("TRL does not support the source row schema")
    by_path = dict(_rendered_files(row_set))
    roles = {
        TRL_README_PATH: "readme",
        TRL_EVALUATION_PATH: "evaluation-partition",
        TRL_TRAIN_PATH: "training-partition",
        TRL_DATA_CARD_PATH: "dataset-card",
        TRL_LAUNCH_PATH: "config-sidecar",
        TRL_PROFILE_METADATA_PATH: "consumer-profile-metadata",
        TRL_PROVENANCE_PATH: "row-provenance",
    }
    media_types = {
        TRL_README_PATH: "text/markdown",
        TRL_EVALUATION_PATH: "application/jsonl",
        TRL_TRAIN_PATH: "application/jsonl",
        TRL_DATA_CARD_PATH: "application/json",
        TRL_LAUNCH_PATH: "application/json",
        TRL_PROFILE_METADATA_PATH: "application/json",
        TRL_PROVENANCE_PATH: "application/jsonl",
    }
    scopes = {
        TRL_EVALUATION_PATH: "evaluation",
        TRL_TRAIN_PATH: "train",
    }
    counts: dict[str, int | None] = {
        TRL_EVALUATION_PATH: row_set.evaluation_row_count,
        TRL_TRAIN_PATH: row_set.train_row_count,
        TRL_PROVENANCE_PATH: row_set.total_row_count,
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
        or consumer.consumer_id != TRL_CONSUMER_ID
        or consumer.profile_version != TRL_PROFILE_VERSION
    ):
        raise ExportVerificationError("TRL renderer received another profile")
    return _RenderedDerivative(
        files=_rendered_files(row_set),
        train_rows=row_set.train_rows,
        evaluation_rows=row_set.evaluation_rows,
        provenance=row_set.provenance,
    )


TRL_DESCRIPTOR = ExportProfileDescriptor(
    container_profile=ExportContainerProfile.create(
        container_id=SPLIT_JSONL_CONTAINER_ID,
        container_version=SPLIT_JSONL_CONTAINER_VERSION,
        determinism_claim="portable_exact_bytes",
    ),
    consumer_profile=ExportConsumerProfile.create(
        consumer_id=TRL_CONSUMER_ID,
        profile_version=TRL_PROFILE_VERSION,
        accepted_row_schemas=_SUPPORTED_ROW_SCHEMAS,
    ),
    dependencies=(
        ExportDependencyBinding.create(
            dependency_name="veriformis-trl-sft-renderer",
            dependency_version="1",
            dependency_role="renderer",
        ),
    ),
    supported_row_schemas=_SUPPORTED_ROW_SCHEMAS,
)

TRL_IMPLEMENTATION = _ExportImplementation(
    descriptor=TRL_DESCRIPTOR,
    file_planner=_file_plans,
    renderer=_render,
    semantic_replayer=None,
)


__all__ = [
    "TRL_CONSUMER_ID",
    "TRL_DATA_CARD_PATH",
    "TRL_DATA_CARD_SCHEMA",
    "TRL_DESCRIPTOR",
    "TRL_EVALUATION_PATH",
    "TRL_IMPLEMENTATION",
    "TRL_LAUNCH_PATH",
    "TRL_LAUNCH_SCHEMA",
    "TRL_PROFILE_METADATA_PATH",
    "TRL_PROFILE_METADATA_SCHEMA",
    "TRL_PROFILE_VERSION",
    "TRL_PROVENANCE_PATH",
    "TRL_README_PATH",
    "TRL_TRAIN_PATH",
    "TrlDataCard",
    "TrlLaunchDataFiles",
    "TrlProfileMetadata",
    "TrlSftLaunchSidecar",
    "map_trl_payload",
]
