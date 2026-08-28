"""Advanced-family admission contract v1. Pins only; no execute."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from veriformis.contracts import (
    ADVANCED_FAMILY_ADMISSION_CONTRACT_ID,
    ADVANCED_FAMILY_ADMISSION_CONTRACT_VERSION,
    ADVANCED_FAMILY_ADMISSION_SCHEMA_ID,
    V1_ROW_SCHEMA_KINDS,
)
from veriformis.errors import FamilyAdmissionError
from veriformis.identity import derive_id, validate_id
from veriformis.taxonomy import (
    EXPLICITLY_UNSUPPORTED_TRAINING_FAMILIES,
    SFT_LOSS_POLICY_IDS,
)


ADMITTABLE_FAMILY_IDS: tuple[str, ...] = (
    "preference-and-ranking",
    "explicit-label-classification",
    "tool-call-conversations",
    "stepwise-supervision",
)
NOT_ADMITTED_FAMILY_IDS: tuple[str, ...] = (
    "pre-tokenized-training",
    "governed-generated-candidates",
)
FAMILY_ADMISSION_LIFECYCLES: tuple[str, ...] = (
    "planned",
    "admitted",
    "deprecated",
    "removed",
)
EVIDENCE_KINDS: tuple[str, ...] = (
    "mapped_value",
    "declared-deterministic-derivation",
)
LEAKAGE_GROUPING_KEYS: tuple[str, ...] = (
    "source",
    "shared-prompt",
    "conversation",
    "annotator",
    "entity",
)
REVIEW_HOOK_IDS: tuple[str, ...] = (
    "label-conflict",
    "preference-inconsistency",
    "tool-trace-incomplete",
    "stepwise-gap",
)
QUALITY_HOOK_IDS: tuple[str, ...] = (
    "missing-label",
    "singleton-label-set",
    "unpaired-without-policy",
    "ranking-tie",
    "tool-role-gap",
)
MISSING_INVALID_POLICIES: tuple[str, ...] = ("refuse",)
FAMILY_ADMISSION_LIMITATIONS: tuple[str, ...] = (
    "no-execute",
    "no-taxonomy-promotion",
    "no-invented-supervision",
    "no-sft-schema-overload",
    "no-generation",
    "no-profile-mapping",
    "no-extension-protocol-admission",
    "no-mac-family-ui",
)

FamilyId = Literal[
    "explicit-label-classification",
    "preference-and-ranking",
    "stepwise-supervision",
    "tool-call-conversations",
]
FamilyAdmissionLifecycle = Literal["admitted", "deprecated", "planned", "removed"]
EvidenceKind = Literal["declared-deterministic-derivation", "mapped_value"]
LeakageGroupingKey = Literal[
    "annotator",
    "conversation",
    "entity",
    "shared-prompt",
    "source",
]
MissingInvalidPolicy = Literal["refuse"]

_TOKEN = re.compile(r"^[a-z][a-z0-9-]*$")


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


def _tuple_str(value: Any) -> Any:
    return tuple(value) if isinstance(value, list) else value


def _require_token(value: str, label: str) -> str:
    if not value or value.strip() != value or _TOKEN.fullmatch(value) is None:
        raise FamilyAdmissionError(f"{label} must be a lowercase hyphenated token")
    return value


def _require_sorted_unique(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    if values != tuple(sorted(set(values))):
        raise FamilyAdmissionError(f"{label} must be unique and sorted")
    return values


def _require_sorted_tokens(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    for item in values:
        _require_token(item, label)
    return _require_sorted_unique(values, label)


def _require_closed_subset(
    values: tuple[str, ...],
    admitted: tuple[str, ...],
    label: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    _require_sorted_unique(values, label)
    if not values and not allow_empty:
        raise FamilyAdmissionError(f"{label} must be a non-empty subset")
    unknown = [item for item in values if item not in admitted]
    if unknown:
        raise FamilyAdmissionError(
            f"unknown {label}: {unknown[0]!r}; admitted {label}s are "
            + ", ".join(admitted)
        )
    return values


class FamilyAdmission(_StrictModel):
    """One advanced-family pin. Loading a pin is not an execute."""

    admission_id: str
    contract_id: Literal["veriformis.advanced-family-admission"]
    contract_version: Literal[1]
    evidence_kinds: tuple[EvidenceKind, ...]
    family_id: FamilyId
    generation_allowed: bool
    leakage_grouping_keys: tuple[LeakageGroupingKey, ...]
    lifecycle: FamilyAdmissionLifecycle
    loss_policy_id: str
    missing_invalid_policy: MissingInvalidPolicy
    profile_eligibility: tuple[str, ...]
    quality_hook_ids: tuple[str, ...]
    review_hook_ids: tuple[str, ...]
    row_schema_ids: tuple[str, ...]
    schema_id: Literal["veriformis.advanced-family-admission/v1"]

    @field_validator(
        "evidence_kinds",
        "leakage_grouping_keys",
        "profile_eligibility",
        "quality_hook_ids",
        "review_hook_ids",
        "row_schema_ids",
        mode="before",
    )
    @classmethod
    def _tuple_fields(cls, value: Any) -> Any:
        return _tuple_str(value)

    @model_validator(mode="after")
    def _closed(self) -> FamilyAdmission:
        if self.contract_id != ADVANCED_FAMILY_ADMISSION_CONTRACT_ID:
            raise FamilyAdmissionError("family admission contract_id mismatch")
        if self.contract_version != ADVANCED_FAMILY_ADMISSION_CONTRACT_VERSION:
            raise FamilyAdmissionError("family admission contract_version mismatch")
        if self.schema_id != ADVANCED_FAMILY_ADMISSION_SCHEMA_ID:
            raise FamilyAdmissionError("family admission schema_id mismatch")
        if self.family_id not in ADMITTABLE_FAMILY_IDS:
            raise FamilyAdmissionError(
                f"unknown family: {self.family_id!r}; admitted families are "
                + ", ".join(ADMITTABLE_FAMILY_IDS)
            )
        if self.generation_allowed is not False:
            raise FamilyAdmissionError(
                "advanced-family-admission/v1 cannot allow generation; "
                "ADR-0018 Decision A forbids a compile-path generator"
            )
        _require_closed_subset(
            self.evidence_kinds,
            EVIDENCE_KINDS,
            "evidence kind",
            allow_empty=False,
        )
        if "mapped_value" not in self.evidence_kinds:
            raise FamilyAdmissionError(
                "family admission evidence_kinds must include mapped_value"
            )
        keys = _require_closed_subset(
            self.leakage_grouping_keys,
            LEAKAGE_GROUPING_KEYS,
            "leakage grouping key",
            allow_empty=False,
        )
        if "source" not in keys:
            raise FamilyAdmissionError(
                "family admission leakage_grouping_keys must include source"
            )
        if self.missing_invalid_policy != "refuse":
            raise FamilyAdmissionError(
                "family admission missing_invalid_policy must be refuse"
            )
        if self.profile_eligibility:
            raise FamilyAdmissionError(
                "family admission profile_eligibility waits for an "
                "independently admitted mapping"
            )
        _require_closed_subset(
            self.review_hook_ids,
            REVIEW_HOOK_IDS,
            "review hook",
            allow_empty=True,
        )
        _require_closed_subset(
            self.quality_hook_ids,
            QUALITY_HOOK_IDS,
            "quality hook",
            allow_empty=True,
        )
        schemas = _require_sorted_tokens(self.row_schema_ids, "row schema id")
        if not schemas:
            raise FamilyAdmissionError("family admission row_schema_ids cannot be empty")
        overlap = [item for item in schemas if item in V1_ROW_SCHEMA_KINDS]
        if overlap:
            raise FamilyAdmissionError(
                "family admission cannot overload SFT row schema "
                f"{overlap[0]!r}; new families require new row schemas"
            )
        policy = _require_token(self.loss_policy_id, "loss policy id")
        if policy in SFT_LOSS_POLICY_IDS:
            raise FamilyAdmissionError(
                "family admission cannot reuse SFT loss policy "
                f"{policy!r}; new families require new loss policies"
            )
        validate_id(self.admission_id, kind="afa")
        expected = derive_id(
            "afa",
            self.model_dump(mode="json", exclude={"admission_id"}),
        )
        if self.admission_id != expected:
            raise FamilyAdmissionError("family admission identity mismatch")
        return self


def create_family_admission(
    *,
    family_id: str,
    lifecycle: str,
    row_schema_ids: tuple[str, ...],
    loss_policy_id: str,
    evidence_kinds: tuple[str, ...] = ("mapped_value",),
    leakage_grouping_keys: tuple[str, ...] = ("source",),
    review_hook_ids: tuple[str, ...] = (),
    quality_hook_ids: tuple[str, ...] = (),
    generation_allowed: bool = False,
    profile_eligibility: tuple[str, ...] = (),
    missing_invalid_policy: str = "refuse",
) -> FamilyAdmission:
    """Build one pin with a derived identity. This is not an execute."""
    payload = {
        "contract_id": ADVANCED_FAMILY_ADMISSION_CONTRACT_ID,
        "contract_version": ADVANCED_FAMILY_ADMISSION_CONTRACT_VERSION,
        "schema_id": ADVANCED_FAMILY_ADMISSION_SCHEMA_ID,
        "family_id": family_id,
        "lifecycle": lifecycle,
        "row_schema_ids": list(row_schema_ids),
        "loss_policy_id": loss_policy_id,
        "evidence_kinds": list(evidence_kinds),
        "missing_invalid_policy": missing_invalid_policy,
        "leakage_grouping_keys": list(leakage_grouping_keys),
        "review_hook_ids": list(review_hook_ids),
        "quality_hook_ids": list(quality_hook_ids),
        "generation_allowed": generation_allowed,
        "profile_eligibility": list(profile_eligibility),
    }
    return FamilyAdmission(
        admission_id=derive_id("afa", payload),
        **payload,
    )


def _supported_contract_label() -> str:
    return (
        f"contract_id={ADVANCED_FAMILY_ADMISSION_CONTRACT_ID!r} "
        f"contract_version={ADVANCED_FAMILY_ADMISSION_CONTRACT_VERSION} "
        f"schema_id={ADVANCED_FAMILY_ADMISSION_SCHEMA_ID!r}"
    )


def _require_known_contract(payload: dict[str, Any]) -> None:
    missing = [
        name
        for name in ("contract_id", "contract_version", "schema_id")
        if name not in payload
    ]
    if missing:
        raise FamilyAdmissionError(
            "unknown family admission contract version: requested missing "
            f"{', '.join(missing)}, supported {_supported_contract_label()}"
        )
    requested_id = payload["contract_id"]
    requested_version = payload["contract_version"]
    requested_schema = payload["schema_id"]
    if (
        requested_id != ADVANCED_FAMILY_ADMISSION_CONTRACT_ID
        or requested_version != ADVANCED_FAMILY_ADMISSION_CONTRACT_VERSION
        or requested_schema != ADVANCED_FAMILY_ADMISSION_SCHEMA_ID
    ):
        raise FamilyAdmissionError(
            "unknown family admission contract version: requested "
            f"contract_id={requested_id!r} "
            f"contract_version={requested_version!r} "
            f"schema_id={requested_schema!r}, supported "
            f"{_supported_contract_label()}"
        )


def _require_known_family(payload: dict[str, Any]) -> None:
    if "family_id" not in payload:
        raise FamilyAdmissionError("family admission missing family_id")
    family_id = payload["family_id"]
    if family_id in EXPLICITLY_UNSUPPORTED_TRAINING_FAMILIES:
        raise FamilyAdmissionError(
            f"family {family_id!r} is explicitly unsupported; admitted families are "
            + ", ".join(ADMITTABLE_FAMILY_IDS)
        )
    if family_id in NOT_ADMITTED_FAMILY_IDS:
        raise FamilyAdmissionError(
            f"family {family_id!r} is not admitted by "
            f"{ADVANCED_FAMILY_ADMISSION_SCHEMA_ID}; admitted families are "
            + ", ".join(ADMITTABLE_FAMILY_IDS)
        )
    if family_id not in ADMITTABLE_FAMILY_IDS:
        raise FamilyAdmissionError(
            f"unknown family: {family_id!r}; admitted families are "
            + ", ".join(ADMITTABLE_FAMILY_IDS)
        )


def _admission_error_from_validation(exc: ValidationError) -> FamilyAdmissionError:
    for error in exc.errors():
        loc = ".".join(str(part) for part in error.get("loc", ()))
        error_type = error.get("type")
        if error_type == "extra_forbidden":
            return FamilyAdmissionError(
                f"family admission contains unknown field {loc}"
            )
        if error_type == "missing":
            return FamilyAdmissionError(
                f"family admission missing {loc or 'required field'}"
            )
        if loc == "family_id":
            return FamilyAdmissionError(
                f"unknown family: {error.get('input')!r}; admitted families are "
                + ", ".join(ADMITTABLE_FAMILY_IDS)
            )
        if loc == "lifecycle":
            return FamilyAdmissionError(
                f"unknown family admission lifecycle: {error.get('input')!r}; "
                "admitted lifecycles are " + ", ".join(FAMILY_ADMISSION_LIFECYCLES)
            )
        if loc in {"contract_version", "contract_id", "schema_id"}:
            return FamilyAdmissionError(
                "unknown family admission contract version: requested "
                f"{error.get('input')!r}, supported "
                f"{_supported_contract_label()}"
            )
    return FamilyAdmissionError("family admission is invalid")


def load_family_admission(payload: object) -> FamilyAdmission:
    """Load one pin. Unknown families, versions, and fields fail closed."""
    if not isinstance(payload, dict):
        raise FamilyAdmissionError("family admission must be an object")
    _require_known_contract(payload)
    _require_known_family(payload)
    if "lifecycle" not in payload:
        raise FamilyAdmissionError("family admission missing lifecycle")
    if payload["lifecycle"] not in FAMILY_ADMISSION_LIFECYCLES:
        raise FamilyAdmissionError(
            f"unknown family admission lifecycle: {payload['lifecycle']!r}; "
            "admitted lifecycles are " + ", ".join(FAMILY_ADMISSION_LIFECYCLES)
        )
    try:
        return FamilyAdmission.model_validate(payload)
    except FamilyAdmissionError:
        raise
    except ValidationError as exc:
        raise _admission_error_from_validation(exc) from exc
