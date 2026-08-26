"""Versioned review contracts. Item 14.2 records the schema only.

Queues, submit paths, and seal blocking land in later items. Waivers cannot
change bytes. Corrections are transforms or mapping revisions. Default
review policy stays none. The bundle does not block seal in 14.2.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from veriformis.contracts import (
    REVIEW_BUNDLE_SCHEMA_ID,
    REVIEW_CONTRACT_ID,
    REVIEW_CONTRACT_VERSION,
)
from veriformis.errors import ReviewError
from veriformis.identity import derive_id, validate_id


CORE_QUEUE_KINDS: tuple[str, ...] = (
    "conflict",
    "construction-pending",
    "mapping",
    "ocr-review",
    "parser-degradation",
)
OPT_IN_QUEUE_KINDS: tuple[str, ...] = (
    "detector-finding",
    "near-duplicate",
)
SAMPLING_QUEUE_KIND = "sample-acceptance"
QUEUE_KINDS: tuple[str, ...] = tuple(
    sorted((*CORE_QUEUE_KINDS, *OPT_IN_QUEUE_KINDS, SAMPLING_QUEUE_KIND))
)

REVIEW_LIMITATIONS: tuple[str, ...] = (
    "default-review-none",
    "no-default-heuristic-required-review",
    "no-mac-review",
    "no-seal-block",
    "unsigned-reviewer",
    "waiver-does-not-change-bytes",
)

QueueKind = Literal[
    "conflict",
    "construction-pending",
    "detector-finding",
    "mapping",
    "near-duplicate",
    "ocr-review",
    "parser-degradation",
    "sample-acceptance",
]
ReviewVerdict = Literal["accepted", "rejected"]
CorrectionKind = Literal["mapping-revision", "transform"]


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
    if not value.strip() or value.strip() != value:
        raise ReviewError(f"{label} must be a non-empty exact token")
    return value


class ReviewerRef(_StrictModel):
    reviewer_id: str

    @model_validator(mode="after")
    def _closed(self) -> ReviewerRef:
        _require_token(self.reviewer_id, "reviewer_id")
        return self


class ReviewWaiver(_StrictModel):
    changes_bytes: Literal[False]
    item_id: str
    rationale: str
    reviewer_id: str
    schema_version: Literal["veriformis.review-waiver/v1"] = (
        "veriformis.review-waiver/v1"
    )
    waiver_id: str

    @model_validator(mode="after")
    def _closed(self) -> ReviewWaiver:
        if self.changes_bytes:
            raise ReviewError("waiver cannot change dataset bytes")
        _require_token(self.reviewer_id, "reviewer_id")
        _require_token(self.rationale, "waiver rationale")
        validate_id(self.item_id, kind="rit")
        validate_id(self.waiver_id, kind="rwv")
        expected = derive_id(
            "rwv",
            self.model_dump(mode="json", exclude={"waiver_id"}),
        )
        if self.waiver_id != expected:
            raise ReviewError("waiver identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        item_id: str,
        reviewer_id: str,
        rationale: str,
    ) -> ReviewWaiver:
        payload = {
            "changes_bytes": False,
            "item_id": item_id,
            "rationale": rationale,
            "reviewer_id": reviewer_id,
            "schema_version": "veriformis.review-waiver/v1",
        }
        return cls(waiver_id=derive_id("rwv", payload), **payload)


class ReviewCorrection(_StrictModel):
    correction_id: str
    item_id: str
    kind: CorrectionKind
    schema_version: Literal["veriformis.review-correction/v1"] = (
        "veriformis.review-correction/v1"
    )

    @model_validator(mode="after")
    def _closed(self) -> ReviewCorrection:
        if self.kind not in {"mapping-revision", "transform"}:
            raise ReviewError("correction must be a transform or mapping revision")
        validate_id(self.item_id, kind="rit")
        validate_id(self.correction_id, kind="rcr")
        expected = derive_id(
            "rcr",
            self.model_dump(mode="json", exclude={"correction_id"}),
        )
        if self.correction_id != expected:
            raise ReviewError("correction identity mismatch")
        return self

    @classmethod
    def create(cls, *, item_id: str, kind: CorrectionKind) -> ReviewCorrection:
        payload = {
            "item_id": item_id,
            "kind": kind,
            "schema_version": "veriformis.review-correction/v1",
        }
        return cls(correction_id=derive_id("rcr", payload), **payload)


class ReviewSupersession(_StrictModel):
    prior_review_id: str
    schema_version: Literal["veriformis.review-supersession/v1"] = (
        "veriformis.review-supersession/v1"
    )
    successor_review_id: str
    supersession_id: str

    @model_validator(mode="after")
    def _closed(self) -> ReviewSupersession:
        validate_id(self.prior_review_id, kind="rvw")
        validate_id(self.successor_review_id, kind="rvw")
        if self.prior_review_id == self.successor_review_id:
            raise ReviewError("supersession cannot name the same review twice")
        validate_id(self.supersession_id, kind="rsp")
        expected = derive_id(
            "rsp",
            self.model_dump(mode="json", exclude={"supersession_id"}),
        )
        if self.supersession_id != expected:
            raise ReviewError("supersession identity mismatch")
        return self


class ReviewBundle(_StrictModel):
    assignments: tuple[str, ...]
    blocks_seal: Literal[False]
    bundle_id: str
    contract_id: str
    contract_version: int
    corrections: tuple[ReviewCorrection, ...]
    items: tuple[str, ...]
    limitations: tuple[str, ...]
    plan_id: str
    queues: tuple[str, ...]
    schema_id: str
    supersessions: tuple[ReviewSupersession, ...]
    verdicts: tuple[str, ...]
    waivers: tuple[ReviewWaiver, ...]

    @field_validator(
        "assignments",
        "corrections",
        "items",
        "limitations",
        "queues",
        "supersessions",
        "verdicts",
        "waivers",
        mode="before",
    )
    @classmethod
    def _tuples(cls, value: Any) -> Any:
        return _tuple_str(value)

    @model_validator(mode="after")
    def _closed(self) -> ReviewBundle:
        if self.contract_id != REVIEW_CONTRACT_ID:
            raise ReviewError("review contract_id is invalid")
        if self.contract_version != REVIEW_CONTRACT_VERSION:
            raise ReviewError("review contract_version is invalid")
        if self.schema_id != REVIEW_BUNDLE_SCHEMA_ID:
            raise ReviewError("review schema_id is invalid")
        if self.blocks_seal:
            raise ReviewError("review bundle cannot block seal in 14.2")
        if self.limitations != REVIEW_LIMITATIONS:
            raise ReviewError("review limitations must match the v1 set")
        validate_id(self.plan_id, kind="fdp")
        validate_id(self.bundle_id, kind="rvb")
        if self.queues != tuple(sorted(set(self.queues))):
            raise ReviewError("review queues must be unique and sorted")
        if self.items != tuple(sorted(set(self.items))):
            raise ReviewError("review items must be unique and sorted")
        expected = derive_id(
            "rvb",
            self.model_dump(mode="json", exclude={"bundle_id"}),
        )
        if self.bundle_id != expected:
            raise ReviewError("review bundle identity mismatch")
        return self


def assemble_review_bundle(
    *,
    plan_id: str,
    queues: tuple[str, ...] = (),
    items: tuple[str, ...] = (),
    assignments: tuple[str, ...] = (),
    verdicts: tuple[str, ...] = (),
    waivers: tuple[ReviewWaiver, ...] = (),
    corrections: tuple[ReviewCorrection, ...] = (),
    supersessions: tuple[ReviewSupersession, ...] = (),
) -> ReviewBundle:
    """Bind a non-blocking empty-capable review bundle to a finished-dataset plan."""
    payload = {
        "assignments": assignments,
        "blocks_seal": False,
        "contract_id": REVIEW_CONTRACT_ID,
        "contract_version": REVIEW_CONTRACT_VERSION,
        "corrections": corrections,
        "items": items,
        "limitations": REVIEW_LIMITATIONS,
        "plan_id": plan_id,
        "queues": queues,
        "schema_id": REVIEW_BUNDLE_SCHEMA_ID,
        "supersessions": supersessions,
        "verdicts": verdicts,
        "waivers": waivers,
    }
    return ReviewBundle(bundle_id=derive_id("rvb", payload), **payload)


def empty_review_bundle(*, plan_id: str) -> ReviewBundle:
    """Bound empty bundle. Queues, verdicts, waivers, and corrections stay vacant."""
    return assemble_review_bundle(plan_id=plan_id)
