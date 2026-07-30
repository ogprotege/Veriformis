"""Complete, content-addressed plan for one finished dataset build."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, get_origin

from pydantic import BaseModel, ConfigDict, ValidationInfo, model_validator

from veriformis.contracts import (
    V1_DATASET_PARTITIONS,
    V1_FINISHED_DATASET_GATES,
)
from veriformis.errors import CurationError, DuplicateIdentityError
from veriformis.identity import derive_id, lossless_json_bytes, validate_id

from ._json import canonical_json_object_from_bytes, reject_floats
from .models import CurationPolicy
from .serialization import SerializationPlan
from .splitting import SplitPolicy

V1_BUNDLE_RETENTION_PROFILE = "minimal-v1"


class FinishedDatasetPlan(BaseModel):
    """All executable Group 3 policy fixed before curation begins."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )

    schema_version: Literal["veriformis.finished-dataset-plan/v1"] = (
        "veriformis.finished-dataset-plan/v1"
    )
    plan_id: str
    recipe_id: str
    construction_result_id: str
    curation_policy: CurationPolicy
    split_policy: SplitPolicy
    serialization_plan: SerializationPlan
    required_validation_gates: tuple[str, ...]
    required_partitions: tuple[Literal["train", "evaluation"], ...]
    bundle_retention_profile: Literal["minimal-v1"]

    @model_validator(mode="before")
    @classmethod
    def _require_exact_fields(cls, value: Any, info: ValidationInfo) -> Any:
        reject_floats(value)
        if isinstance(value, cls) or not isinstance(value, Mapping):
            return value
        expected = set(cls.model_fields)
        actual = set(value)
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            raise ValueError(
                "FinishedDatasetPlan fields do not match its persisted schema; "
                f"missing={missing!r}, extra={extra!r}"
            )
        if info.mode != "json":
            return value
        normalized = dict(value)
        for name, field in cls.model_fields.items():
            if get_origin(field.annotation) is tuple and isinstance(
                normalized[name], list
            ):
                normalized[name] = tuple(normalized[name])
        return normalized

    @model_validator(mode="after")
    def _validate_plan(self) -> FinishedDatasetPlan:
        validate_id(self.plan_id, kind="fdp")
        validate_id(self.recipe_id, kind="rcp")
        validate_id(self.construction_result_id, kind="run")
        _revalidate_nested(
            self.curation_policy,
            CurationPolicy,
            label="curation policy",
        )
        _revalidate_nested(
            self.split_policy,
            SplitPolicy,
            label="split policy",
        )
        _revalidate_nested(
            self.serialization_plan,
            SerializationPlan,
            label="serialization plan",
        )
        if self.required_validation_gates != V1_FINISHED_DATASET_GATES:
            raise ValueError(
                "finished dataset plan requires the exact v1 validation gates"
            )
        if self.required_partitions != V1_DATASET_PARTITIONS:
            raise ValueError(
                "finished dataset plan requires train then evaluation partitions"
            )
        if self.bundle_retention_profile != V1_BUNDLE_RETENTION_PROFILE:
            raise ValueError("unsupported finished dataset retention profile")
        expected_id = derive_id(
            "fdp",
            self.model_dump(mode="json", exclude={"plan_id"}),
        )
        if self.plan_id != expected_id:
            raise ValueError("finished dataset plan identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        recipe_id: str,
        construction_result_id: str,
        curation_policy: CurationPolicy,
        split_policy: SplitPolicy,
        serialization_plan: SerializationPlan,
    ) -> FinishedDatasetPlan:
        payload = {
            "schema_version": "veriformis.finished-dataset-plan/v1",
            "recipe_id": recipe_id,
            "construction_result_id": construction_result_id,
            "curation_policy": curation_policy,
            "split_policy": split_policy,
            "serialization_plan": serialization_plan,
            "required_validation_gates": V1_FINISHED_DATASET_GATES,
            "required_partitions": V1_DATASET_PARTITIONS,
            "bundle_retention_profile": V1_BUNDLE_RETENTION_PROFILE,
        }
        return cls(plan_id=derive_id("fdp", payload), **payload)


def _revalidate_nested(
    value: BaseModel,
    model_type: type[BaseModel],
    *,
    label: str,
) -> None:
    try:
        checked = model_type.model_validate_json(
            lossless_json_bytes(value.model_dump(mode="json"))
        )
    except DuplicateIdentityError:
        raise
    except (AttributeError, TypeError, UnicodeError, ValueError) as exc:
        raise ValueError(f"invalid nested {label}: {exc}") from exc
    if checked != value:
        raise ValueError(f"nested {label} does not round-trip exactly")


def finished_dataset_plan_to_dict(value: FinishedDatasetPlan) -> dict[str, Any]:
    try:
        payload = value.model_dump(mode="json")
        reject_floats(payload)
        checked = FinishedDatasetPlan.model_validate_json(lossless_json_bytes(payload))
    except DuplicateIdentityError:
        raise
    except (AttributeError, TypeError, UnicodeError, ValueError) as exc:
        raise CurationError(f"invalid finished dataset plan: {exc}") from exc
    if checked != value:
        raise CurationError("finished dataset plan does not round-trip exactly")
    return payload


def finished_dataset_plan_from_json_bytes(data: bytes) -> FinishedDatasetPlan:
    try:
        canonical_json_object_from_bytes(data, label="finished dataset plan")
        return FinishedDatasetPlan.model_validate_json(data)
    except DuplicateIdentityError:
        raise
    except (TypeError, UnicodeError, ValueError) as exc:
        raise CurationError(f"invalid finished dataset plan: {exc}") from exc


def finished_dataset_plan_from_dict(
    value: dict[str, Any],
) -> FinishedDatasetPlan:
    try:
        return finished_dataset_plan_from_json_bytes(lossless_json_bytes(value))
    except (DuplicateIdentityError, CurationError):
        raise
    except (TypeError, UnicodeError, ValueError) as exc:
        raise CurationError(f"invalid finished dataset plan: {exc}") from exc


__all__ = [
    "V1_BUNDLE_RETENTION_PROFILE",
    "FinishedDatasetPlan",
    "finished_dataset_plan_from_dict",
    "finished_dataset_plan_from_json_bytes",
    "finished_dataset_plan_to_dict",
]
