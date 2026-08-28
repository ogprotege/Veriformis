"""Versioned review contracts.

Queues list existing facts. Corrections bind a new transform or mapping
revision. Waivers cannot change bytes. Default review policy stays none.
Required unresolved reviews block seal. Default recipes stay none.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from veriformis.contracts import (
    REVIEW_BUNDLE_SCHEMA_ID,
    REVIEW_CONTRACT_ID,
    REVIEW_CONTRACT_VERSION,
    REVIEW_PACKET_SCHEMA_ID,
)
from veriformis.errors import ReviewError
from veriformis.identity import derive_id, validate_id, validate_sha256


CORE_QUEUE_KINDS: tuple[str, ...] = (
    "conflict",
    "construction-pending",
    "mapping",
    "ocr-review",
    "parser-degradation",
)
OPT_IN_QUEUE_KINDS: tuple[str, ...] = (
    "detector-finding",
    "label-conflict",
    "near-duplicate",
    "preference-inconsistency",
    "stepwise-gap",
    "tool-trace-incomplete",
)
SAMPLING_QUEUE_KIND = "sample-acceptance"
SAMPLE_ALGORITHM_ID = "veriformis.review-sample-hmac-sha256/v1"
QUEUE_KINDS: tuple[str, ...] = tuple(
    sorted((*CORE_QUEUE_KINDS, *OPT_IN_QUEUE_KINDS, SAMPLING_QUEUE_KIND))
)

REVIEW_LIMITATIONS: tuple[str, ...] = (
    "default-review-none",
    "no-default-heuristic-required-review",
    "no-mac-review",
    "required-review-blocks-seal",
    "unsigned-reviewer",
    "waiver-does-not-change-bytes",
)

QueueKind = Literal[
    "conflict",
    "construction-pending",
    "detector-finding",
    "label-conflict",
    "mapping",
    "near-duplicate",
    "ocr-review",
    "parser-degradation",
    "preference-inconsistency",
    "sample-acceptance",
    "stepwise-gap",
    "tool-trace-incomplete",
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


_TOKEN = re.compile(r"^[a-z][a-z0-9-]*$")


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


class ReviewItem(_StrictModel):
    item_id: str
    queue_kind: QueueKind
    required: bool
    schema_version: Literal["veriformis.review-item/v1"] = "veriformis.review-item/v1"
    subject_id: str

    @model_validator(mode="after")
    def _closed(self) -> ReviewItem:
        if self.queue_kind not in QUEUE_KINDS:
            raise ReviewError("review item queue_kind is not in the v1 set")
        _require_token(self.subject_id, "subject_id")
        validate_id(self.item_id, kind="rit")
        expected = derive_id(
            "rit",
            self.model_dump(mode="json", exclude={"item_id"}),
        )
        if self.item_id != expected:
            raise ReviewError("review item identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        queue_kind: QueueKind,
        subject_id: str,
        required: bool,
    ) -> ReviewItem:
        payload = {
            "queue_kind": queue_kind,
            "required": required,
            "schema_version": "veriformis.review-item/v1",
            "subject_id": subject_id,
        }
        return cls(item_id=derive_id("rit", payload), **payload)


def rank_sample_subjects(
    *,
    seed: str,
    population: tuple[str, ...],
    size: int,
) -> tuple[str, ...]:
    """Rank population by HMAC-SHA256(seed, subject) and take ``size`` members."""
    ranked = sorted(
        population,
        key=lambda subject: (
            hmac.new(
                seed.encode("utf-8"),
                subject.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest(),
            subject,
        ),
    )
    return tuple(sorted(ranked[:size]))


class ReviewSample(_StrictModel):
    algorithm_id: Literal["veriformis.review-sample-hmac-sha256/v1"]
    population: tuple[str, ...]
    sample_id: str
    schema_version: Literal["veriformis.review-sample/v1"] = (
        "veriformis.review-sample/v1"
    )
    seed: str
    selected: tuple[str, ...]
    size: int
    statistical_meaning: Literal[False]

    @field_validator("population", "selected", mode="before")
    @classmethod
    def _tuples(cls, value: Any) -> Any:
        return _tuple_str(value)

    @model_validator(mode="after")
    def _closed(self) -> ReviewSample:
        if self.algorithm_id != SAMPLE_ALGORITHM_ID:
            raise ReviewError("sample algorithm_id is invalid")
        if _TOKEN.fullmatch(self.seed) is None:
            raise ReviewError("sample seed must be a lowercase token")
        if not self.population:
            raise ReviewError("sample population must be non-empty")
        if self.population != tuple(sorted(set(self.population))):
            raise ReviewError("sample population must be unique and sorted")
        for subject in self.population:
            _require_token(subject, "sample population member")
        if type(self.size) is not int or self.size < 1:
            raise ReviewError("sample size must be a positive int")
        if self.size > len(self.population):
            raise ReviewError("sample size cannot exceed the population")
        expected_selected = rank_sample_subjects(
            seed=self.seed,
            population=self.population,
            size=self.size,
        )
        if self.selected != expected_selected:
            raise ReviewError("sample selection does not match the named seed")
        if self.statistical_meaning:
            raise ReviewError("review sampling claims no statistical meaning")
        validate_id(self.sample_id, kind="rsm")
        expected = derive_id(
            "rsm",
            self.model_dump(mode="json", exclude={"sample_id"}),
        )
        if self.sample_id != expected:
            raise ReviewError("review sample identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        seed: str,
        population: tuple[str, ...],
        size: int,
    ) -> ReviewSample:
        canonical = tuple(sorted(population))
        selected = rank_sample_subjects(
            seed=seed,
            population=canonical,
            size=size,
        )
        payload = {
            "algorithm_id": SAMPLE_ALGORITHM_ID,
            "population": canonical,
            "schema_version": "veriformis.review-sample/v1",
            "seed": seed,
            "selected": selected,
            "size": size,
            "statistical_meaning": False,
        }
        return cls(sample_id=derive_id("rsm", payload), **payload)


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


class ReviewTransform(_StrictModel):
    input_sha256: str
    operation: str
    output_sha256: str
    schema_version: Literal["veriformis.review-transform/v1"] = (
        "veriformis.review-transform/v1"
    )
    source_id: str
    transform_id: str

    @model_validator(mode="after")
    def _closed(self) -> ReviewTransform:
        if _TOKEN.fullmatch(self.operation) is None:
            raise ReviewError("transform operation must be a lowercase token")
        try:
            validate_id(self.source_id, kind="src")
            validate_sha256(self.input_sha256)
            validate_sha256(self.output_sha256)
        except ValueError as exc:
            raise ReviewError("review transform source or digest is invalid") from exc
        if self.input_sha256 == self.output_sha256:
            raise ReviewError(
                "transform correction must change bytes; record a waiver instead"
            )
        validate_id(self.transform_id, kind="trn")
        expected = derive_id(
            "trn",
            self.model_dump(mode="json", exclude={"transform_id"}),
        )
        if self.transform_id != expected:
            raise ReviewError("review transform identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        source_id: str,
        input_sha256: str,
        output_sha256: str,
        operation: str,
    ) -> ReviewTransform:
        payload = {
            "input_sha256": input_sha256,
            "operation": operation,
            "output_sha256": output_sha256,
            "schema_version": "veriformis.review-transform/v1",
            "source_id": source_id,
        }
        return cls(transform_id=derive_id("trn", payload), **payload)


class ReviewCorrection(_StrictModel):
    correction_id: str
    item_id: str
    kind: CorrectionKind
    result_id: str
    schema_version: Literal["veriformis.review-correction/v1"] = (
        "veriformis.review-correction/v1"
    )

    @model_validator(mode="after")
    def _closed(self) -> ReviewCorrection:
        if self.kind not in {"mapping-revision", "transform"}:
            raise ReviewError("correction must be a transform or mapping revision")
        validate_id(self.item_id, kind="rit")
        expected_kind = "trn" if self.kind == "transform" else "mpl"
        try:
            validate_id(self.result_id, kind=expected_kind)
        except ValueError as exc:
            raise ReviewError(
                "correction result_id must be a new transform or mapping-plan identity"
            ) from exc
        if self.result_id == self.item_id:
            raise ReviewError("correction cannot reuse the review-item identity")
        validate_id(self.correction_id, kind="rcr")
        expected = derive_id(
            "rcr",
            self.model_dump(mode="json", exclude={"correction_id"}),
        )
        if self.correction_id != expected:
            raise ReviewError("correction identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        item_id: str,
        kind: CorrectionKind,
        result_id: str,
    ) -> ReviewCorrection:
        payload = {
            "item_id": item_id,
            "kind": kind,
            "result_id": result_id,
            "schema_version": "veriformis.review-correction/v1",
        }
        return cls(correction_id=derive_id("rcr", payload), **payload)


class ReviewDecision(_StrictModel):
    decision_id: str
    item_id: str
    rationale: str
    reviewer_id: str
    schema_version: Literal["veriformis.review-decision/v1"] = (
        "veriformis.review-decision/v1"
    )
    verdict: ReviewVerdict

    @model_validator(mode="after")
    def _closed(self) -> ReviewDecision:
        _require_token(self.reviewer_id, "reviewer_id")
        _require_token(self.rationale, "review decision rationale")
        if self.verdict not in {"accepted", "rejected"}:
            raise ReviewError("review decision verdict is invalid")
        validate_id(self.item_id, kind="rit")
        validate_id(self.decision_id, kind="rvd")
        expected = derive_id(
            "rvd",
            self.model_dump(mode="json", exclude={"decision_id"}),
        )
        if self.decision_id != expected:
            raise ReviewError("review decision identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        item_id: str,
        reviewer_id: str,
        verdict: ReviewVerdict,
        rationale: str,
    ) -> ReviewDecision:
        payload = {
            "item_id": item_id,
            "rationale": rationale,
            "reviewer_id": reviewer_id,
            "schema_version": "veriformis.review-decision/v1",
            "verdict": verdict,
        }
        return cls(decision_id=derive_id("rvd", payload), **payload)


class ReviewPacket(_StrictModel):
    corrections: tuple[ReviewCorrection, ...]
    decisions: tuple[ReviewDecision, ...]
    items: tuple[ReviewItem, ...]
    packet_id: str
    plan_id: str
    schema_id: str
    waivers: tuple[ReviewWaiver, ...]

    @field_validator(
        "corrections",
        "decisions",
        "items",
        "waivers",
        mode="before",
    )
    @classmethod
    def _tuples(cls, value: Any) -> Any:
        return _tuple_str(value)

    @model_validator(mode="after")
    def _closed(self) -> ReviewPacket:
        if self.schema_id != REVIEW_PACKET_SCHEMA_ID:
            raise ReviewError("review packet schema_id is invalid")
        validate_id(self.plan_id, kind="fdp")
        item_ids = tuple(item.item_id for item in self.items)
        if item_ids != tuple(sorted(set(item_ids))):
            raise ReviewError("review packet items must be unique and sorted")
        decision_items = tuple(item.item_id for item in self.decisions)
        if decision_items != tuple(sorted(set(decision_items))):
            raise ReviewError("review packet decisions must be unique by item")
        if any(item.item_id not in item_ids for item in self.decisions):
            raise ReviewError("review decision names an unknown item")
        if any(item.item_id not in item_ids for item in self.waivers):
            raise ReviewError("review waiver names an unknown item")
        if any(item.item_id not in item_ids for item in self.corrections):
            raise ReviewError("review correction names an unknown item")
        validate_id(self.packet_id, kind="rpk")
        expected = derive_id(
            "rpk",
            self.model_dump(mode="json", exclude={"packet_id"}),
        )
        if self.packet_id != expected:
            raise ReviewError("review packet identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        plan_id: str,
        items: tuple[ReviewItem, ...] = (),
        decisions: tuple[ReviewDecision, ...] = (),
        waivers: tuple[ReviewWaiver, ...] = (),
        corrections: tuple[ReviewCorrection, ...] = (),
    ) -> ReviewPacket:
        ordered_items = tuple(sorted(items, key=lambda item: item.item_id))
        ordered_decisions = tuple(
            sorted(decisions, key=lambda item: item.item_id)
        )
        ordered_waivers = tuple(sorted(waivers, key=lambda item: item.waiver_id))
        ordered_corrections = tuple(
            sorted(corrections, key=lambda item: item.correction_id)
        )
        payload = {
            "corrections": [
                item.model_dump(mode="json") for item in ordered_corrections
            ],
            "decisions": [
                item.model_dump(mode="json") for item in ordered_decisions
            ],
            "items": [item.model_dump(mode="json") for item in ordered_items],
            "plan_id": plan_id,
            "schema_id": REVIEW_PACKET_SCHEMA_ID,
            "waivers": [item.model_dump(mode="json") for item in ordered_waivers],
        }
        return cls(packet_id=derive_id("rpk", payload), **payload)


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

    @classmethod
    def create(
        cls,
        *,
        prior_review_id: str,
        successor_review_id: str,
    ) -> ReviewSupersession:
        payload = {
            "prior_review_id": prior_review_id,
            "schema_version": "veriformis.review-supersession/v1",
            "successor_review_id": successor_review_id,
        }
        return cls(supersession_id=derive_id("rsp", payload), **payload)


class ReviewBundle(_StrictModel):
    assignments: tuple[str, ...]
    blocks_seal: bool
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
        if type(self.blocks_seal) is not bool:
            raise ReviewError("review blocks_seal must be a bool")
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
    blocks_seal: bool = False,
) -> ReviewBundle:
    """Bind a review bundle to a finished-dataset plan."""
    payload = {
        "assignments": assignments,
        "blocks_seal": blocks_seal,
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
