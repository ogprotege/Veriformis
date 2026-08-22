"""Lossless generic split-JSONL export container v1."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Literal, Self

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
    ExportContainerProfile,
    ExportDependencyBinding,
    ExportFilePlan,
    ExportPlan,
)
from veriformis.exports.paths import (
    validate_export_path_set,
    validate_export_relative_path,
)
from veriformis.identity import lossless_json_bytes, sha256_digest, validate_id
from veriformis.taxonomy import LOSS_POLICY_IDS, loss_policy_for_row


SPLIT_JSONL_CONTAINER_ID = "split-jsonl-directory"
SPLIT_JSONL_CONTAINER_VERSION = 1
SPLIT_JSONL_OPTIONS_SCHEMA = "veriformis.split-jsonl-options/v1"
SPLIT_JSONL_DATA_CARD_SCHEMA = "veriformis.split-jsonl-data-card/v1"
SPLIT_JSONL_DATA_CARD_PATH = "metadata/dataset-card.json"
SPLIT_JSONL_PROVENANCE_PATH = "metadata/row-provenance.jsonl"
SPLIT_JSONL_README_PATH = "README.md"

_PARTITION_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_SUPPORTED_ROW_SCHEMAS = tuple(sorted(V1_ROW_SCHEMA_KINDS))


def _validate_partition_name(value: str) -> str:
    if type(value) is not str or _PARTITION_NAME.fullmatch(value) is None:
        raise ValueError(
            "partition names must be 1-64 lowercase ASCII letters, digits, "
            "underscores, or hyphens and begin with a letter or digit"
        )
    validate_export_relative_path(f"data/{value}.jsonl")
    return value


class _StrictSplitJsonlModel(BaseModel):
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


class SplitJsonlOptions(_StrictSplitJsonlModel):
    """Versioned safe layout options for split JSONL v1."""

    schema_version: Literal["veriformis.split-jsonl-options/v1"] = (
        SPLIT_JSONL_OPTIONS_SCHEMA
    )
    train_partition_name: str = "train"
    evaluation_partition_name: str = "evaluation"
    include_provenance: bool = True

    @field_validator("train_partition_name", "evaluation_partition_name")
    @classmethod
    def _valid_partition_name(cls, value: str) -> str:
        return _validate_partition_name(value)

    @model_validator(mode="after")
    def _distinct_partition_names(self) -> Self:
        if self.train_partition_name == self.evaluation_partition_name:
            raise ValueError("train and evaluation partition names must differ")
        paths = [
            EXPORT_RECEIPT_PATH,
            SPLIT_JSONL_DATA_CARD_PATH,
            SPLIT_JSONL_README_PATH,
            self.evaluation_path,
            self.train_path,
        ]
        if self.include_provenance:
            paths.append(SPLIT_JSONL_PROVENANCE_PATH)
        validate_export_path_set(
            tuple(sorted(paths)),
            label="split JSONL partition paths",
        )
        return self

    @property
    def train_path(self) -> str:
        return f"data/{self.train_partition_name}.jsonl"

    @property
    def evaluation_path(self) -> str:
        return f"data/{self.evaluation_partition_name}.jsonl"

    @classmethod
    def from_container_options(
        cls,
        value: Mapping[str, object],
    ) -> Self:
        if not isinstance(value, Mapping):
            raise ExportContractError("split JSONL options must be an object")
        if not value:
            raise ExportContractError(
                "split JSONL v2 options require the complete versioned options object"
            )
        try:
            return cls.from_json_bytes(lossless_json_bytes(dict(value)))
        except ExportVerificationError as exc:
            raise ExportContractError(str(exc)) from exc


class SplitJsonlDataCard(_StrictSplitJsonlModel):
    """Machine-readable description of one split JSONL export pack."""

    schema_version: Literal["veriformis.split-jsonl-data-card/v1"] = (
        SPLIT_JSONL_DATA_CARD_SCHEMA
    )
    container_id: Literal["split-jsonl-directory"] = SPLIT_JSONL_CONTAINER_ID
    container_version: Literal[1] = SPLIT_JSONL_CONTAINER_VERSION
    row_schema: str
    objective_id: str
    loss_policy: str
    row_set_id: str
    split_result_id: str
    train_path: str
    train_row_count: int
    evaluation_path: str
    evaluation_row_count: int
    provenance_path: str | None
    provenance_row_count: int | None
    provenance_alignment: Literal["train_then_evaluation"] = (
        "train_then_evaluation"
    )
    receipt_path: Literal["export-receipt.json"] = EXPORT_RECEIPT_PATH
    consumer_profile: None = None
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

    @field_validator("train_path", "evaluation_path")
    @classmethod
    def _valid_partition_path(cls, value: str) -> str:
        validate_export_relative_path(value)
        if value.count("/") != 1 or not value.startswith("data/"):
            raise ValueError("partition paths must be data/<safe-stem>.jsonl")
        filename = value.removeprefix("data/")
        if not filename.endswith(".jsonl"):
            raise ValueError("partition paths must be data/<safe-stem>.jsonl")
        stem = filename.removesuffix(".jsonl")
        _validate_partition_name(stem)
        if value != f"data/{stem}.jsonl":
            raise ValueError("partition paths must be data/<safe-stem>.jsonl")
        return value

    @field_validator("provenance_path")
    @classmethod
    def _valid_provenance_path(cls, value: str | None) -> str | None:
        if value is not None and value != SPLIT_JSONL_PROVENANCE_PATH:
            raise ValueError("data card provenance path is not canonical")
        return value

    @field_validator(
        "train_row_count",
        "evaluation_row_count",
        "provenance_row_count",
    )
    @classmethod
    def _valid_count(cls, value: int | None) -> int | None:
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError("data card row counts must be non-negative integers")
        return value

    @model_validator(mode="after")
    def _closed_layout(self) -> Self:
        if self.train_row_count < 1:
            raise ValueError("data card requires a non-empty train partition")
        if self.loss_policy != loss_policy_for_row(self.row_schema):
            raise ValueError("data card loss policy differs from its row schema")
        if (self.provenance_path is None) != (self.provenance_row_count is None):
            raise ValueError(
                "data card provenance path and count must be present together"
            )
        if self.provenance_row_count is not None and self.provenance_row_count != (
            self.train_row_count + self.evaluation_row_count
        ):
            raise ValueError("data card provenance count is not aligned")
        paths = [
            self.receipt_path,
            SPLIT_JSONL_README_PATH,
            self.evaluation_path,
            self.train_path,
            SPLIT_JSONL_DATA_CARD_PATH,
        ]
        if self.provenance_path is not None:
            paths.append(self.provenance_path)
        validate_export_path_set(
            tuple(sorted(paths)),
            label="split JSONL data card paths",
        )
        return self


def _payload_jsonl(rows: Sequence[ProductRow]) -> bytes:
    return b"".join(lossless_json_bytes(row.payload) + b"\n" for row in rows)


def _provenance_jsonl(provenance: Sequence[RowProvenance]) -> bytes:
    return b"".join(
        lossless_json_bytes(item.model_dump(mode="json")) + b"\n"
        for item in provenance
    )


def _data_card(row_set: RowSet, options: SplitJsonlOptions) -> SplitJsonlDataCard:
    objective_ids = {item.objective_id for item in row_set.provenance}
    if len(objective_ids) != 1:
        raise ExportContractError(
            "split JSONL requires one objective identity across the source row set"
        )
    return SplitJsonlDataCard(
        row_schema=row_set.row_schema,
        objective_id=next(iter(objective_ids)),
        loss_policy=loss_policy_for_row(row_set.row_schema),
        row_set_id=row_set.row_set_id,
        split_result_id=row_set.split_result_id,
        train_path=options.train_path,
        train_row_count=row_set.train_row_count,
        evaluation_path=options.evaluation_path,
        evaluation_row_count=row_set.evaluation_row_count,
        provenance_path=(
            SPLIT_JSONL_PROVENANCE_PATH if options.include_provenance else None
        ),
        provenance_row_count=(
            row_set.total_row_count if options.include_provenance else None
        ),
    )


def _readme_bytes(card: SplitJsonlDataCard) -> bytes:
    provenance = (
        f"`{card.provenance_path}` ({card.provenance_row_count} aligned rows)"
        if card.provenance_path is not None
        else "omitted"
    )
    text = (
        "# Veriformis split JSONL export\n\n"
        "This trainer-neutral export preserves the verified dataset's semantic "
        "rows and authoritative partitions.\n\n"
        f"- Container: `{card.container_id}` v{card.container_version}\n"
        f"- Row schema: `{card.row_schema}`\n"
        f"- Loss policy: `{card.loss_policy}`\n"
        f"- Train: `{card.train_path}` ({card.train_row_count} rows)\n"
        f"- Evaluation: `{card.evaluation_path}` "
        f"({card.evaluation_row_count} rows)\n"
        f"- Provenance: {provenance}\n"
        f"- Source row set: `{card.row_set_id}`\n"
        f"- Source split: `{card.split_result_id}`\n\n"
        "Each partition contains one canonical UTF-8 JSON payload object per "
        "line, uses LF line endings, has no blank lines, and contains no row "
        "identity or provenance fields added by this container. The optional "
        "provenance stream is separate and aligned in train-then-evaluation "
        "order. `metadata/dataset-card.json` describes this layout and "
        "`export-receipt.json` binds every planned derivative file.\n\n"
        "This generic container does not select a training objective or claim "
        "compatibility with every trainer.\n"
    )
    return text.encode("utf-8")


def _rendered_files(
    row_set: RowSet,
    options: SplitJsonlOptions,
) -> tuple[tuple[str, bytes], ...]:
    card = _data_card(row_set, options)
    files: dict[str, bytes] = {
        SPLIT_JSONL_README_PATH: _readme_bytes(card),
        options.evaluation_path: _payload_jsonl(row_set.evaluation_rows),
        options.train_path: _payload_jsonl(row_set.train_rows),
        SPLIT_JSONL_DATA_CARD_PATH: card.canonical_bytes(),
    }
    if options.include_provenance:
        files[SPLIT_JSONL_PROVENANCE_PATH] = _provenance_jsonl(row_set.provenance)
    return tuple(sorted(files.items()))


def _file_plans(
    descriptor: ExportProfileDescriptor,
    row_set: RowSet,
    parsed_options: object,
) -> tuple[ExportFilePlan, ...]:
    if not isinstance(parsed_options, SplitJsonlOptions):
        raise ExportContractError("split JSONL planner received invalid options")
    if descriptor.selector != (
        SPLIT_JSONL_CONTAINER_ID,
        SPLIT_JSONL_CONTAINER_VERSION,
        None,
        None,
    ):
        raise ExportContractError("split JSONL descriptor selector changed")
    if row_set.row_schema not in descriptor.supported_row_schemas:
        raise ExportContractError("split JSONL does not support the source row schema")
    by_path = dict(_rendered_files(row_set, parsed_options))
    roles = {
        SPLIT_JSONL_README_PATH: "readme",
        parsed_options.evaluation_path: "evaluation-partition",
        parsed_options.train_path: "training-partition",
        SPLIT_JSONL_DATA_CARD_PATH: "dataset-card",
        SPLIT_JSONL_PROVENANCE_PATH: "row-provenance",
    }
    media_types = {
        SPLIT_JSONL_README_PATH: "text/markdown",
        parsed_options.evaluation_path: "application/jsonl",
        parsed_options.train_path: "application/jsonl",
        SPLIT_JSONL_DATA_CARD_PATH: "application/json",
        SPLIT_JSONL_PROVENANCE_PATH: "application/jsonl",
    }
    scopes = {
        parsed_options.evaluation_path: "evaluation",
        parsed_options.train_path: "train",
    }
    counts: dict[str, int | None] = {
        parsed_options.evaluation_path: row_set.evaluation_row_count,
        parsed_options.train_path: row_set.train_row_count,
        SPLIT_JSONL_PROVENANCE_PATH: row_set.total_row_count,
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


def _default_file_plans(
    descriptor: ExportProfileDescriptor,
    row_set: RowSet,
) -> tuple[ExportFilePlan, ...]:
    return _file_plans(descriptor, row_set, SplitJsonlOptions())


def _options_from_plan(plan: ExportPlan) -> SplitJsonlOptions:
    paths_by_role: dict[str, str] = {}
    for item in plan.file_plans:
        if item.role in paths_by_role:
            raise ExportVerificationError(
                f"split JSONL plan repeats file role {item.role!r}"
            )
        paths_by_role[item.role] = item.path
    required_roles = {
        "dataset-card",
        "evaluation-partition",
        "readme",
        "training-partition",
    }
    allowed_roles = {*required_roles, "row-provenance"}
    if not required_roles.issubset(paths_by_role) or not set(paths_by_role).issubset(
        allowed_roles
    ):
        raise ExportVerificationError("split JSONL plan has an invalid file-role set")
    train_path = paths_by_role["training-partition"]
    evaluation_path = paths_by_role["evaluation-partition"]
    if (
        not train_path.startswith("data/")
        or not train_path.endswith(".jsonl")
        or not evaluation_path.startswith("data/")
        or not evaluation_path.endswith(".jsonl")
    ):
        raise ExportVerificationError("split JSONL plan has invalid partition paths")
    if paths_by_role["readme"] != SPLIT_JSONL_README_PATH or paths_by_role[
        "dataset-card"
    ] != SPLIT_JSONL_DATA_CARD_PATH:
        raise ExportVerificationError("split JSONL plan has invalid metadata paths")
    provenance_path = paths_by_role.get("row-provenance")
    if provenance_path not in {None, SPLIT_JSONL_PROVENANCE_PATH}:
        raise ExportVerificationError("split JSONL plan has invalid provenance path")
    try:
        return SplitJsonlOptions(
            train_partition_name=train_path.removeprefix("data/").removesuffix(
                ".jsonl"
            ),
            evaluation_partition_name=evaluation_path.removeprefix(
                "data/"
            ).removesuffix(".jsonl"),
            include_provenance=provenance_path is not None,
        )
    except ValueError as exc:
        raise ExportVerificationError(
            f"split JSONL plan contains invalid layout options: {exc}"
        ) from exc


def _render(plan: ExportPlan, row_set: RowSet) -> _RenderedDerivative:
    if (
        plan.container_profile.container_id != SPLIT_JSONL_CONTAINER_ID
        or plan.container_profile.container_version != SPLIT_JSONL_CONTAINER_VERSION
        or plan.container_profile.determinism_claim != "portable_exact_bytes"
        or plan.consumer_profile is not None
    ):
        raise ExportVerificationError("split JSONL renderer received another profile")
    options = _options_from_plan(plan)
    return _RenderedDerivative(
        files=_rendered_files(row_set, options),
        train_rows=row_set.train_rows,
        evaluation_rows=row_set.evaluation_rows,
        provenance=row_set.provenance,
    )


SPLIT_JSONL_DESCRIPTOR = ExportProfileDescriptor(
    container_profile=ExportContainerProfile.create(
        container_id=SPLIT_JSONL_CONTAINER_ID,
        container_version=SPLIT_JSONL_CONTAINER_VERSION,
        determinism_claim="portable_exact_bytes",
    ),
    consumer_profile=None,
    dependencies=(
        ExportDependencyBinding.create(
            dependency_name="veriformis-split-jsonl-renderer",
            dependency_version="1",
            dependency_role="renderer",
        ),
    ),
    supported_row_schemas=_SUPPORTED_ROW_SCHEMAS,
)

SPLIT_JSONL_IMPLEMENTATION = _ExportImplementation(
    descriptor=SPLIT_JSONL_DESCRIPTOR,
    file_planner=_default_file_plans,
    renderer=_render,
    semantic_replayer=None,
    options_parser=SplitJsonlOptions.from_container_options,
    configured_file_planner=_file_plans,
)


__all__ = [
    "SPLIT_JSONL_CONTAINER_ID",
    "SPLIT_JSONL_CONTAINER_VERSION",
    "SPLIT_JSONL_DATA_CARD_PATH",
    "SPLIT_JSONL_DATA_CARD_SCHEMA",
    "SPLIT_JSONL_OPTIONS_SCHEMA",
    "SPLIT_JSONL_PROVENANCE_PATH",
    "SPLIT_JSONL_README_PATH",
    "SplitJsonlDataCard",
    "SplitJsonlOptions",
]
