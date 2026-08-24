"""Axolotl SFT consumer-profile adapter over a verified bundle.

Does not import Axolotl. Sidecars are dataset-only and do not launch training.
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

AXOLOTL_CONSUMER_ID = "axolotl"
AXOLOTL_PROFILE_VERSION = 1
AXOLOTL_DATA_CARD_SCHEMA = "veriformis.axolotl-data-card/v1"
AXOLOTL_PROFILE_METADATA_SCHEMA = "veriformis.axolotl-profile-metadata/v1"
AXOLOTL_TRAIN_PATH = "data/train.jsonl"
AXOLOTL_EVALUATION_PATH = "data/evaluation.jsonl"
AXOLOTL_DATA_CARD_PATH = "metadata/dataset-card.json"
AXOLOTL_PROFILE_METADATA_PATH = "metadata/axolotl-profile.json"
AXOLOTL_LAUNCH_SCHEMA = "veriformis.axolotl-sft-launch/v1"
AXOLOTL_LAUNCH_PATH = "metadata/axolotl-sft-launch.json"
AXOLOTL_YAML_PATH = "metadata/axolotl-sft.yaml"
AXOLOTL_PROVENANCE_PATH = "metadata/row-provenance.jsonl"
AXOLOTL_README_PATH = "README.md"
_SUPPORTED_ROW_SCHEMAS = tuple(sorted(V1_ROW_SCHEMA_KINDS))
_AXOLOTL_COMMAND_ARGV = ("axolotl", "train", AXOLOTL_YAML_PATH)
_AXOLOTL_OPERATOR_MUST_SUPPLY = ("base_model", "training-hyperparameters")
_AXOLOTL_LAUNCH_NOTES = (
    "Sidecar records a dataset-only Axolotl YAML with local JSONL paths. "
    "Veriformis does not launch training, select a model, or set "
    "hyperparameters."
)
_AXOLOTL_TYPE_BY_FORMAT = {
    "alpaca": "alpaca",
    "chat_template-openai": "chat_template",
    "completion": "completion",
}


def _axolotl_pin():
    return next(
        record
        for record in profile_admission_catalog().records
        if record.profile_id == AXOLOTL_CONSUMER_ID
    )


def _mapping_for(row_schema: str):
    pin = _axolotl_pin()
    for item in pin.row_mappings:
        if item.source_row_schema == row_schema:
            return item
    raise ExportContractError(
        f"Axolotl admission does not map source row schema {row_schema!r}"
    )


def map_axolotl_payload(row_schema: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Map one verified payload onto Axolotl SFT columns. Does not change membership."""
    return map_admitted_payload(_mapping_for(row_schema), payload)


def axolotl_dataset_type(row_schema: str) -> str:
    mapping = _mapping_for(row_schema)
    try:
        return _AXOLOTL_TYPE_BY_FORMAT[mapping.destination_format]
    except KeyError as exc:
        raise ExportContractError(
            f"Axolotl has no YAML type for {mapping.destination_format!r}"
        ) from exc


def _yaml_dataset_entry(path: str, dataset_type: str) -> str:
    fields = {"ds_type": "json", "path": path, "split": "train", "type": dataset_type}
    if dataset_type == "chat_template":
        fields["field_messages"] = "messages"
        fields["message_field_content"] = "content"
        fields["message_field_role"] = "role"
    elif dataset_type == "completion":
        fields["field"] = "text"
    first_key = sorted(fields)[0]
    body = [f"  - {first_key}: {fields[first_key]}"]
    for key in sorted(fields):
        if key == first_key:
            continue
        body.append(f"    {key}: {fields[key]}")
    return "\n".join(body)


def axolotl_yaml_bytes(row_schema: str, *, has_evaluation: bool) -> bytes:
    """Exact-byte dataset-only YAML. Does not call yaml.dump."""
    dataset_type = axolotl_dataset_type(row_schema)
    lines = [
        "# Veriformis dataset-only Axolotl sidecar. Operator must supply",
        "# base_model and training hyperparameters. Veriformis does not",
        "# launch training.",
        "datasets:",
        _yaml_dataset_entry(AXOLOTL_TRAIN_PATH, dataset_type),
    ]
    if has_evaluation:
        lines.extend(
            [
                "test_datasets:",
                _yaml_dataset_entry(AXOLOTL_EVALUATION_PATH, dataset_type),
            ]
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


class _StrictAxolotlModel(BaseModel):
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


class AxolotlDataCard(_StrictAxolotlModel):
    schema_version: Literal["veriformis.axolotl-data-card/v1"] = AXOLOTL_DATA_CARD_SCHEMA
    container_id: Literal["split-jsonl-directory"] = SPLIT_JSONL_CONTAINER_ID
    container_version: Literal[1] = SPLIT_JSONL_CONTAINER_VERSION
    consumer_id: Literal["axolotl"] = AXOLOTL_CONSUMER_ID
    consumer_profile_version: Literal[1] = AXOLOTL_PROFILE_VERSION
    row_schema: str
    objective_id: str
    loss_policy: str
    row_set_id: str
    split_result_id: str
    train_path: Literal["data/train.jsonl"] = AXOLOTL_TRAIN_PATH
    train_row_count: int
    evaluation_path: Literal["data/evaluation.jsonl"] = AXOLOTL_EVALUATION_PATH
    evaluation_row_count: int
    provenance_path: Literal["metadata/row-provenance.jsonl"] = AXOLOTL_PROVENANCE_PATH
    provenance_row_count: int
    mapping_kind: str
    destination_format: str
    destination_keys: tuple[str, ...]
    yaml_path: Literal["metadata/axolotl-sft.yaml"] = AXOLOTL_YAML_PATH
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
            raise ValueError("data card mapping differs from the Axolotl admission pin")
        validate_export_path_set(
            tuple(
                sorted(
                    (
                        self.receipt_path,
                        AXOLOTL_README_PATH,
                        self.evaluation_path,
                        self.train_path,
                        AXOLOTL_DATA_CARD_PATH,
                        AXOLOTL_LAUNCH_PATH,
                        AXOLOTL_PROFILE_METADATA_PATH,
                        AXOLOTL_YAML_PATH,
                        self.provenance_path,
                    )
                )
            ),
            label="Axolotl data card paths",
        )
        return self


class AxolotlProfileMetadata(_StrictAxolotlModel):
    schema_version: Literal["veriformis.axolotl-profile-metadata/v1"] = (
        AXOLOTL_PROFILE_METADATA_SCHEMA
    )
    profile_id: Literal["axolotl"] = AXOLOTL_CONSUMER_ID
    profile_version: Literal[1] = AXOLOTL_PROFILE_VERSION
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
    executable_item: Literal["10.3"] = "10.3"
    taxonomy_state: Literal["implemented"] = "implemented"
    trainer_compatibility_claimed: Literal[False] = False

    @field_validator("destination_keys", "refused_dataset_types", mode="before")
    @classmethod
    def _tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> Self:
        pin = _axolotl_pin()
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
            raise ValueError("Axolotl metadata differs from the admission pin")
        mapping = _mapping_for(self.row_schema)
        if (
            self.mapping_kind != mapping.mapping_kind
            or self.destination_format != mapping.destination_format
            or self.destination_keys != mapping.destination_keys
        ):
            raise ValueError(
                "Axolotl metadata mapping differs from the admission pin"
            )
        return self


class AxolotlLaunchDataFiles(_StrictAxolotlModel):
    evaluation: Literal["data/evaluation.jsonl"] = AXOLOTL_EVALUATION_PATH
    train: Literal["data/train.jsonl"] = AXOLOTL_TRAIN_PATH


class AxolotlSftLaunchSidecar(_StrictAxolotlModel):
    schema_version: Literal["veriformis.axolotl-sft-launch/v1"] = AXOLOTL_LAUNCH_SCHEMA
    command_argv: tuple[
        Literal["axolotl"],
        Literal["train"],
        Literal["metadata/axolotl-sft.yaml"],
    ] = _AXOLOTL_COMMAND_ARGV
    data_files: AxolotlLaunchDataFiles
    destination_format: str
    destination_keys: tuple[str, ...]
    docs_reviewed_on: str
    evaluation_row_count: int
    executable_item: Literal["10.8"] = "10.8"
    launches_training: Literal[False] = False
    mapping_kind: str
    notes: Literal[_AXOLOTL_LAUNCH_NOTES] = _AXOLOTL_LAUNCH_NOTES
    operator_must_supply: tuple[
        Literal["base_model"],
        Literal["training-hyperparameters"],
    ] = _AXOLOTL_OPERATOR_MUST_SUPPLY
    primary_docs_url: str
    profile_id: Literal["axolotl"] = AXOLOTL_CONSUMER_ID
    profile_version: Literal[1] = AXOLOTL_PROFILE_VERSION
    row_schema: str
    selects_hyperparameters: Literal[False] = False
    selects_model: Literal[False] = False
    train_row_count: int
    use_eval_dataset: bool
    yaml_path: Literal["metadata/axolotl-sft.yaml"] = AXOLOTL_YAML_PATH
    yaml_type: str

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
        if self.command_argv != _AXOLOTL_COMMAND_ARGV:
            raise ValueError(
                "Axolotl launch command_argv is not the dataset-only fragment"
            )
        if self.operator_must_supply != _AXOLOTL_OPERATOR_MUST_SUPPLY:
            raise ValueError("Axolotl launch operator_must_supply is not closed")
        if "--train" in self.command_argv:
            raise ValueError("Axolotl launch sidecar must not include --train")
        pin = _axolotl_pin()
        if (
            self.primary_docs_url != pin.primary_docs_url
            or self.docs_reviewed_on != pin.docs_reviewed_on
        ):
            raise ValueError(
                "Axolotl launch sidecar docs differ from the admission pin"
            )
        mapping = _mapping_for(self.row_schema)
        if (
            self.mapping_kind != mapping.mapping_kind
            or self.destination_format != mapping.destination_format
            or self.destination_keys != mapping.destination_keys
        ):
            raise ValueError("Axolotl launch mapping differs from the admission pin")
        if self.yaml_type != axolotl_dataset_type(self.row_schema):
            raise ValueError("Axolotl yaml_type differs from the admission pin")
        return self


def _payload_jsonl(row_schema: str, rows: Sequence[ProductRow]) -> bytes:
    return b"".join(
        lossless_json_bytes(map_axolotl_payload(row_schema, row.payload)) + b"\n"
        for row in rows
    )


def _provenance_jsonl(provenance: Sequence[RowProvenance]) -> bytes:
    return b"".join(
        lossless_json_bytes(item.model_dump(mode="json")) + b"\n" for item in provenance
    )


def _data_card(row_set: RowSet) -> AxolotlDataCard:
    objective_ids = {item.objective_id for item in row_set.provenance}
    if len(objective_ids) != 1:
        raise ExportContractError(
            "Axolotl export requires one objective identity across the source row set"
        )
    mapping = _mapping_for(row_set.row_schema)
    return AxolotlDataCard(
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


def _profile_metadata(row_set: RowSet) -> AxolotlProfileMetadata:
    pin = _axolotl_pin()
    mapping = _mapping_for(row_set.row_schema)
    return AxolotlProfileMetadata(
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


def _launch_sidecar(row_set: RowSet) -> AxolotlSftLaunchSidecar:
    pin = _axolotl_pin()
    mapping = _mapping_for(row_set.row_schema)
    return AxolotlSftLaunchSidecar(
        command_argv=_AXOLOTL_COMMAND_ARGV,
        data_files=AxolotlLaunchDataFiles(),
        destination_format=mapping.destination_format,
        destination_keys=mapping.destination_keys,
        docs_reviewed_on=pin.docs_reviewed_on,
        evaluation_row_count=row_set.evaluation_row_count,
        mapping_kind=mapping.mapping_kind,
        operator_must_supply=_AXOLOTL_OPERATOR_MUST_SUPPLY,
        primary_docs_url=pin.primary_docs_url,
        row_schema=row_set.row_schema,
        train_row_count=row_set.train_row_count,
        use_eval_dataset=row_set.evaluation_row_count > 0,
        yaml_type=axolotl_dataset_type(row_set.row_schema),
    )


def _readme_bytes(card: AxolotlDataCard) -> bytes:
    mapping = _mapping_for(card.row_schema)
    text = (
        "# Veriformis Axolotl SFT export\n\n"
        "This optional adapter maps a verified Veriformis bundle onto Axolotl "
        "JSONL plus a dataset-only YAML sidecar. It does not curate, resplit, "
        "or change membership or loss-policy IDs.\n\n"
        f"- Container: `{card.container_id}` v{card.container_version}\n"
        f"- Consumer: `{card.consumer_id}` v{card.consumer_profile_version}\n"
        f"- Row schema: `{card.row_schema}`\n"
        f"- Destination format: `{mapping.destination_format}`\n"
        f"- Mapping: `{mapping.mapping_kind}`\n"
        f"- YAML type: `{axolotl_dataset_type(card.row_schema)}`\n"
        f"- Loss policy: `{card.loss_policy}` (unchanged Veriformis ID)\n"
        f"- Train: `{card.train_path}` ({card.train_row_count} rows)\n"
        f"- Evaluation: `{card.evaluation_path}` "
        f"({card.evaluation_row_count} rows)\n"
        f"- Provenance: `{card.provenance_path}` "
        f"({card.provenance_row_count} aligned rows)\n"
        f"- Source row set: `{card.row_set_id}`\n\n"
        "Point Axolotl `datasets.path` at the local JSONL files. Do not glob "
        "`metadata/` into the loader. The YAML sidecar at "
        "`metadata/axolotl-sft.yaml` repeats those dataset paths. Veriformis "
        "does not launch `axolotl train`, select a model, or set "
        "hyperparameters. Loader conformance is item 10.7; this export does "
        "not claim that Axolotl has loaded the files.\n\n"
        "Preference, pre-tokenized, stepwise-supervision, template-free "
        "segments, tools, unpaired preference, and vision types are refused. "
        "`round_trip` is false.\n"
    )
    return text.encode("utf-8")


def _rendered_files(row_set: RowSet) -> tuple[tuple[str, bytes], ...]:
    card = _data_card(row_set)
    metadata = _profile_metadata(row_set)
    launch = _launch_sidecar(row_set)
    files = {
        AXOLOTL_README_PATH: _readme_bytes(card),
        AXOLOTL_EVALUATION_PATH: _payload_jsonl(
            row_set.row_schema, row_set.evaluation_rows
        ),
        AXOLOTL_TRAIN_PATH: _payload_jsonl(row_set.row_schema, row_set.train_rows),
        AXOLOTL_DATA_CARD_PATH: card.canonical_bytes(),
        AXOLOTL_LAUNCH_PATH: launch.canonical_bytes(),
        AXOLOTL_PROFILE_METADATA_PATH: metadata.canonical_bytes(),
        AXOLOTL_YAML_PATH: axolotl_yaml_bytes(
            row_set.row_schema,
            has_evaluation=row_set.evaluation_row_count > 0,
        ),
        AXOLOTL_PROVENANCE_PATH: _provenance_jsonl(row_set.provenance),
    }
    return tuple(sorted(files.items()))


def _file_plans(
    descriptor: ExportProfileDescriptor,
    row_set: RowSet,
) -> tuple[ExportFilePlan, ...]:
    if descriptor.selector != (
        SPLIT_JSONL_CONTAINER_ID,
        SPLIT_JSONL_CONTAINER_VERSION,
        AXOLOTL_CONSUMER_ID,
        AXOLOTL_PROFILE_VERSION,
    ):
        raise ExportContractError("Axolotl descriptor selector changed")
    if row_set.row_schema not in descriptor.supported_row_schemas:
        raise ExportContractError("Axolotl does not support the source row schema")
    by_path = dict(_rendered_files(row_set))
    roles = {
        AXOLOTL_README_PATH: "readme",
        AXOLOTL_EVALUATION_PATH: "evaluation-partition",
        AXOLOTL_TRAIN_PATH: "training-partition",
        AXOLOTL_DATA_CARD_PATH: "dataset-card",
        AXOLOTL_LAUNCH_PATH: "launch-sidecar",
        AXOLOTL_PROFILE_METADATA_PATH: "consumer-profile-metadata",
        AXOLOTL_YAML_PATH: "config-sidecar",
        AXOLOTL_PROVENANCE_PATH: "row-provenance",
    }
    media_types = {
        AXOLOTL_README_PATH: "text/markdown",
        AXOLOTL_EVALUATION_PATH: "application/jsonl",
        AXOLOTL_TRAIN_PATH: "application/jsonl",
        AXOLOTL_DATA_CARD_PATH: "application/json",
        AXOLOTL_LAUNCH_PATH: "application/json",
        AXOLOTL_PROFILE_METADATA_PATH: "application/json",
        AXOLOTL_YAML_PATH: "application/yaml",
        AXOLOTL_PROVENANCE_PATH: "application/jsonl",
    }
    scopes = {
        AXOLOTL_EVALUATION_PATH: "evaluation",
        AXOLOTL_TRAIN_PATH: "train",
    }
    counts: dict[str, int | None] = {
        AXOLOTL_EVALUATION_PATH: row_set.evaluation_row_count,
        AXOLOTL_TRAIN_PATH: row_set.train_row_count,
        AXOLOTL_PROVENANCE_PATH: row_set.total_row_count,
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
        or consumer.consumer_id != AXOLOTL_CONSUMER_ID
        or consumer.profile_version != AXOLOTL_PROFILE_VERSION
    ):
        raise ExportVerificationError("Axolotl renderer received another profile")
    return _RenderedDerivative(
        files=_rendered_files(row_set),
        train_rows=row_set.train_rows,
        evaluation_rows=row_set.evaluation_rows,
        provenance=row_set.provenance,
    )


AXOLOTL_DESCRIPTOR = ExportProfileDescriptor(
    container_profile=ExportContainerProfile.create(
        container_id=SPLIT_JSONL_CONTAINER_ID,
        container_version=SPLIT_JSONL_CONTAINER_VERSION,
        determinism_claim="portable_exact_bytes",
    ),
    consumer_profile=ExportConsumerProfile.create(
        consumer_id=AXOLOTL_CONSUMER_ID,
        profile_version=AXOLOTL_PROFILE_VERSION,
        accepted_row_schemas=_SUPPORTED_ROW_SCHEMAS,
    ),
    dependencies=(
        ExportDependencyBinding.create(
            dependency_name="veriformis-axolotl-sft-renderer",
            dependency_version="1",
            dependency_role="renderer",
        ),
    ),
    supported_row_schemas=_SUPPORTED_ROW_SCHEMAS,
)

AXOLOTL_IMPLEMENTATION = _ExportImplementation(
    descriptor=AXOLOTL_DESCRIPTOR,
    file_planner=_file_plans,
    renderer=_render,
    semantic_replayer=None,
)


__all__ = [
    "AXOLOTL_CONSUMER_ID",
    "AXOLOTL_DATA_CARD_PATH",
    "AXOLOTL_DATA_CARD_SCHEMA",
    "AXOLOTL_DESCRIPTOR",
    "AXOLOTL_EVALUATION_PATH",
    "AXOLOTL_IMPLEMENTATION",
    "AXOLOTL_LAUNCH_PATH",
    "AXOLOTL_LAUNCH_SCHEMA",
    "AXOLOTL_PROFILE_METADATA_PATH",
    "AXOLOTL_PROFILE_METADATA_SCHEMA",
    "AXOLOTL_PROFILE_VERSION",
    "AXOLOTL_PROVENANCE_PATH",
    "AXOLOTL_README_PATH",
    "AXOLOTL_TRAIN_PATH",
    "AXOLOTL_YAML_PATH",
    "AxolotlDataCard",
    "AxolotlLaunchDataFiles",
    "AxolotlProfileMetadata",
    "AxolotlSftLaunchSidecar",
    "axolotl_dataset_type",
    "axolotl_yaml_bytes",
    "map_axolotl_payload",
]
