"""Aptus consumer-profile adapter over a verified bundle.

Identity-maps admitted product rows. Does not import Aptus. The sibling
handoff CLI remains; default seal still does not write the descriptor.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

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

APTUS_CONSUMER_ID = "aptus"
APTUS_PROFILE_VERSION = 1
APTUS_DATA_CARD_SCHEMA = "veriformis.aptus-data-card/v1"
APTUS_PROFILE_METADATA_SCHEMA = "veriformis.aptus-profile-metadata/v1"
APTUS_TRAIN_PATH = "data/train.jsonl"
APTUS_EVALUATION_PATH = "data/evaluation.jsonl"
APTUS_DATA_CARD_PATH = "metadata/dataset-card.json"
APTUS_PROFILE_METADATA_PATH = "metadata/aptus-profile.json"
APTUS_LAUNCH_SCHEMA = "veriformis.aptus-launch/v1"
APTUS_LAUNCH_PATH = "metadata/aptus-launch.json"
APTUS_PROVENANCE_PATH = "metadata/row-provenance.jsonl"
APTUS_README_PATH = "README.md"
_SUPPORTED_ROW_SCHEMAS = ("instruction_output", "messages", "prompt_completion")
_APTUS_COMMAND_ARGV = ("veriformis", "handoff")
_APTUS_OPERATOR_MUST_SUPPLY = ("assignment-digest", "external-digest")
_APTUS_LAUNCH_NOTES = (
    "Sidecar records identity JSONL paths for Aptus-admitted schemas. "
    "The sibling *.aptus-handoff.json CLI remains optional. Default seal "
    "does not write that descriptor. Veriformis does not launch Aptus."
)


def _aptus_pin():
    return next(
        record
        for record in profile_admission_catalog().records
        if record.profile_id == APTUS_CONSUMER_ID
    )


def _mapping_for(row_schema: str):
    pin = _aptus_pin()
    for item in pin.row_mappings:
        if item.source_row_schema == row_schema:
            return item
    raise ExportContractError(
        f"Aptus admission does not map source row schema {row_schema!r}"
    )


def map_aptus_payload(row_schema: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Map one verified payload by identity. Does not change membership."""
    return map_admitted_payload(_mapping_for(row_schema), payload)


class _StrictAptusModel(BaseModel):
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


class AptusDataCard(_StrictAptusModel):
    schema_version: Literal["veriformis.aptus-data-card/v1"] = APTUS_DATA_CARD_SCHEMA
    container_id: Literal["split-jsonl-directory"] = SPLIT_JSONL_CONTAINER_ID
    container_version: Literal[1] = SPLIT_JSONL_CONTAINER_VERSION
    consumer_id: Literal["aptus"] = APTUS_CONSUMER_ID
    consumer_profile_version: Literal[1] = APTUS_PROFILE_VERSION
    row_schema: str
    objective_id: str
    loss_policy: str
    row_set_id: str
    split_result_id: str
    train_path: Literal["data/train.jsonl"] = APTUS_TRAIN_PATH
    train_row_count: int
    evaluation_path: Literal["data/evaluation.jsonl"] = APTUS_EVALUATION_PATH
    evaluation_row_count: int
    provenance_path: Literal["metadata/row-provenance.jsonl"] = APTUS_PROVENANCE_PATH
    provenance_row_count: int
    mapping_kind: str
    destination_format: str
    destination_keys: tuple[str, ...]
    receipt_path: Literal["export-receipt.json"] = EXPORT_RECEIPT_PATH
    trainer_compatibility_claimed: Literal[False] = False

    @field_validator("row_schema")
    @classmethod
    def _valid_row_schema(cls, value: str) -> str:
        if value not in _SUPPORTED_ROW_SCHEMAS:
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
            raise ValueError("data card mapping differs from the Aptus admission pin")
        validate_export_path_set(
            tuple(
                sorted(
                    (
                        self.receipt_path,
                        APTUS_README_PATH,
                        self.evaluation_path,
                        self.train_path,
                        APTUS_DATA_CARD_PATH,
                        APTUS_LAUNCH_PATH,
                        APTUS_PROFILE_METADATA_PATH,
                        self.provenance_path,
                    )
                )
            ),
            label="Aptus data card paths",
        )
        return self


class AptusProfileMetadata(_StrictAptusModel):
    schema_version: Literal["veriformis.aptus-profile-metadata/v1"] = (
        APTUS_PROFILE_METADATA_SCHEMA
    )
    profile_id: Literal["aptus"] = APTUS_CONSUMER_ID
    profile_version: Literal[1] = APTUS_PROFILE_VERSION
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
    executable_item: Literal["10.6"] = "10.6"
    taxonomy_state: Literal["implemented"] = "implemented"
    trainer_compatibility_claimed: Literal[False] = False
    writes_sibling_handoff: Literal[False] = False

    @field_validator("destination_keys", "refused_dataset_types", mode="before")
    @classmethod
    def _tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> Self:
        pin = _aptus_pin()
        if self.extra != "":
            raise ValueError("Aptus extra must be empty")
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
            raise ValueError("Aptus metadata differs from the admission pin")
        mapping = _mapping_for(self.row_schema)
        if (
            self.mapping_kind != mapping.mapping_kind
            or self.destination_format != mapping.destination_format
            or self.destination_keys != mapping.destination_keys
        ):
            raise ValueError("Aptus metadata mapping differs from the admission pin")
        return self


class AptusLaunchDataFiles(_StrictAptusModel):
    evaluation: Literal["data/evaluation.jsonl"] = APTUS_EVALUATION_PATH
    train: Literal["data/train.jsonl"] = APTUS_TRAIN_PATH


class AptusLaunchSidecar(_StrictAptusModel):
    schema_version: Literal["veriformis.aptus-launch/v1"] = APTUS_LAUNCH_SCHEMA
    command_argv: tuple[
        Literal["veriformis"],
        Literal["handoff"],
    ] = _APTUS_COMMAND_ARGV
    data_files: AptusLaunchDataFiles
    destination_format: str
    destination_keys: tuple[str, ...]
    docs_reviewed_on: str
    evaluation_row_count: int
    executable_item: Literal["10.8"] = "10.8"
    launches_training: Literal[False] = False
    mapping_kind: str
    notes: Literal[_APTUS_LAUNCH_NOTES] = _APTUS_LAUNCH_NOTES
    operator_must_supply: tuple[
        Literal["assignment-digest"],
        Literal["external-digest"],
    ] = _APTUS_OPERATOR_MUST_SUPPLY
    primary_docs_url: str
    profile_id: Literal["aptus"] = APTUS_CONSUMER_ID
    profile_version: Literal[1] = APTUS_PROFILE_VERSION
    row_schema: str
    selects_hyperparameters: Literal[False] = False
    selects_model: Literal[False] = False
    train_row_count: int
    use_eval_dataset: bool
    writes_sibling_handoff: Literal[False] = False

    @field_validator("row_schema")
    @classmethod
    def _valid_row_schema(cls, value: str) -> str:
        if value not in _SUPPORTED_ROW_SCHEMAS:
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
        if self.command_argv != _APTUS_COMMAND_ARGV:
            raise ValueError("Aptus launch command_argv is not the dataset-only fragment")
        if self.operator_must_supply != _APTUS_OPERATOR_MUST_SUPPLY:
            raise ValueError("Aptus launch operator_must_supply is not closed")
        if "--train" in self.command_argv:
            raise ValueError("Aptus launch sidecar must not include --train")
        pin = _aptus_pin()
        if (
            self.primary_docs_url != pin.primary_docs_url
            or self.docs_reviewed_on != pin.docs_reviewed_on
        ):
            raise ValueError("Aptus launch sidecar docs differ from the admission pin")
        mapping = _mapping_for(self.row_schema)
        if (
            self.mapping_kind != mapping.mapping_kind
            or self.destination_format != mapping.destination_format
            or self.destination_keys != mapping.destination_keys
        ):
            raise ValueError("Aptus launch mapping differs from the admission pin")
        return self


def _payload_jsonl(row_schema: str, rows: Sequence[ProductRow]) -> bytes:
    return b"".join(
        lossless_json_bytes(map_aptus_payload(row_schema, row.payload)) + b"\n"
        for row in rows
    )


def _provenance_jsonl(provenance: Sequence[RowProvenance]) -> bytes:
    return b"".join(
        lossless_json_bytes(item.model_dump(mode="json")) + b"\n" for item in provenance
    )


def _data_card(row_set: RowSet) -> AptusDataCard:
    if row_set.row_schema not in _SUPPORTED_ROW_SCHEMAS:
        raise ExportContractError(
            f"Aptus does not support the source row schema {row_set.row_schema!r}"
        )
    objective_ids = {item.objective_id for item in row_set.provenance}
    if len(objective_ids) != 1:
        raise ExportContractError(
            "Aptus export requires one objective identity across the source row set"
        )
    mapping = _mapping_for(row_set.row_schema)
    return AptusDataCard(
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


def _profile_metadata(row_set: RowSet) -> AptusProfileMetadata:
    pin = _aptus_pin()
    mapping = _mapping_for(row_set.row_schema)
    return AptusProfileMetadata(
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


def _launch_sidecar(row_set: RowSet) -> AptusLaunchSidecar:
    pin = _aptus_pin()
    mapping = _mapping_for(row_set.row_schema)
    return AptusLaunchSidecar(
        command_argv=_APTUS_COMMAND_ARGV,
        data_files=AptusLaunchDataFiles(),
        destination_format=mapping.destination_format,
        destination_keys=mapping.destination_keys,
        docs_reviewed_on=pin.docs_reviewed_on,
        evaluation_row_count=row_set.evaluation_row_count,
        mapping_kind=mapping.mapping_kind,
        operator_must_supply=_APTUS_OPERATOR_MUST_SUPPLY,
        primary_docs_url=pin.primary_docs_url,
        row_schema=row_set.row_schema,
        train_row_count=row_set.train_row_count,
        use_eval_dataset=row_set.evaluation_row_count > 0,
    )


def _readme_bytes(card: AptusDataCard) -> bytes:
    mapping = _mapping_for(card.row_schema)
    text = (
        "# Veriformis Aptus export\n\n"
        "This optional adapter maps a verified Veriformis bundle onto identity "
        "JSONL for Aptus-admitted schemas. It does not curate, resplit, or "
        "change membership or loss-policy IDs. The sibling "
        "`*.aptus-handoff.json` CLI remains. Default seal still does not write "
        "that descriptor.\n\n"
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
        "Plain `text` rows are refused. Use the sibling `veriformis handoff` "
        "command when an Aptus assignment digest is required. This export does "
        "not write that sibling descriptor and does not launch Aptus.\n\n"
        "Preference, tools, unpaired preference, vision, and text types are "
        "refused. `round_trip` is false.\n"
    )
    return text.encode("utf-8")


def _rendered_files(row_set: RowSet) -> tuple[tuple[str, bytes], ...]:
    card = _data_card(row_set)
    metadata = _profile_metadata(row_set)
    launch = _launch_sidecar(row_set)
    files = {
        APTUS_README_PATH: _readme_bytes(card),
        APTUS_EVALUATION_PATH: _payload_jsonl(
            row_set.row_schema, row_set.evaluation_rows
        ),
        APTUS_TRAIN_PATH: _payload_jsonl(row_set.row_schema, row_set.train_rows),
        APTUS_DATA_CARD_PATH: card.canonical_bytes(),
        APTUS_LAUNCH_PATH: launch.canonical_bytes(),
        APTUS_PROFILE_METADATA_PATH: metadata.canonical_bytes(),
        APTUS_PROVENANCE_PATH: _provenance_jsonl(row_set.provenance),
    }
    return tuple(sorted(files.items()))


def _file_plans(
    descriptor: ExportProfileDescriptor,
    row_set: RowSet,
) -> tuple[ExportFilePlan, ...]:
    if descriptor.selector != (
        SPLIT_JSONL_CONTAINER_ID,
        SPLIT_JSONL_CONTAINER_VERSION,
        APTUS_CONSUMER_ID,
        APTUS_PROFILE_VERSION,
    ):
        raise ExportContractError("Aptus descriptor selector changed")
    if row_set.row_schema not in descriptor.supported_row_schemas:
        raise ExportContractError("Aptus does not support the source row schema")
    by_path = dict(_rendered_files(row_set))
    roles = {
        APTUS_README_PATH: "readme",
        APTUS_EVALUATION_PATH: "evaluation-partition",
        APTUS_TRAIN_PATH: "training-partition",
        APTUS_DATA_CARD_PATH: "dataset-card",
        APTUS_LAUNCH_PATH: "launch-sidecar",
        APTUS_PROFILE_METADATA_PATH: "consumer-profile-metadata",
        APTUS_PROVENANCE_PATH: "row-provenance",
    }
    media_types = {
        APTUS_README_PATH: "text/markdown",
        APTUS_EVALUATION_PATH: "application/jsonl",
        APTUS_TRAIN_PATH: "application/jsonl",
        APTUS_DATA_CARD_PATH: "application/json",
        APTUS_LAUNCH_PATH: "application/json",
        APTUS_PROFILE_METADATA_PATH: "application/json",
        APTUS_PROVENANCE_PATH: "application/jsonl",
    }
    scopes = {
        APTUS_EVALUATION_PATH: "evaluation",
        APTUS_TRAIN_PATH: "train",
    }
    counts: dict[str, int | None] = {
        APTUS_EVALUATION_PATH: row_set.evaluation_row_count,
        APTUS_TRAIN_PATH: row_set.train_row_count,
        APTUS_PROVENANCE_PATH: row_set.total_row_count,
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
        or consumer.consumer_id != APTUS_CONSUMER_ID
        or consumer.profile_version != APTUS_PROFILE_VERSION
    ):
        raise ExportVerificationError("Aptus renderer received another profile")
    return _RenderedDerivative(
        files=_rendered_files(row_set),
        train_rows=row_set.train_rows,
        evaluation_rows=row_set.evaluation_rows,
        provenance=row_set.provenance,
    )


APTUS_DESCRIPTOR = ExportProfileDescriptor(
    container_profile=ExportContainerProfile.create(
        container_id=SPLIT_JSONL_CONTAINER_ID,
        container_version=SPLIT_JSONL_CONTAINER_VERSION,
        determinism_claim="portable_exact_bytes",
    ),
    consumer_profile=ExportConsumerProfile.create(
        consumer_id=APTUS_CONSUMER_ID,
        profile_version=APTUS_PROFILE_VERSION,
        accepted_row_schemas=_SUPPORTED_ROW_SCHEMAS,
    ),
    dependencies=(
        ExportDependencyBinding.create(
            dependency_name="veriformis-aptus-renderer",
            dependency_version="1",
            dependency_role="renderer",
        ),
    ),
    supported_row_schemas=_SUPPORTED_ROW_SCHEMAS,
)

APTUS_IMPLEMENTATION = _ExportImplementation(
    descriptor=APTUS_DESCRIPTOR,
    file_planner=_file_plans,
    renderer=_render,
    semantic_replayer=None,
)


__all__ = [
    "APTUS_CONSUMER_ID",
    "APTUS_DATA_CARD_PATH",
    "APTUS_DATA_CARD_SCHEMA",
    "APTUS_DESCRIPTOR",
    "APTUS_EVALUATION_PATH",
    "APTUS_IMPLEMENTATION",
    "APTUS_LAUNCH_PATH",
    "APTUS_LAUNCH_SCHEMA",
    "APTUS_PROFILE_METADATA_PATH",
    "APTUS_PROFILE_METADATA_SCHEMA",
    "APTUS_PROFILE_VERSION",
    "APTUS_PROVENANCE_PATH",
    "APTUS_README_PATH",
    "APTUS_TRAIN_PATH",
    "AptusDataCard",
    "AptusLaunchDataFiles",
    "AptusLaunchSidecar",
    "AptusProfileMetadata",
    "map_aptus_payload",
]
