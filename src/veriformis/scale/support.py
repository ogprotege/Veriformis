"""Operator-reviewed scale support discovery. Published tiers stay empty."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any, Literal

from pydantic import field_validator, model_validator

from veriformis.errors import ScaleError
from veriformis.scale.models import ScaleInputMode, _StrictModel

SUPPORT_DATA_NAME = "support-v1.json"
SUPPORT_SCHEMA_ID = "veriformis.scale-support-discovery/v1"
SUPPORT_CONTRACT_ID = "veriformis.scale-support"
SUPPORT_CONTRACT_VERSION = 1


class ScaleObservation(_StrictModel):
    observation_id: str
    kind: Literal["named-hardware-baseline", "cli-compile-measured"]
    input_mode: ScaleInputMode
    evidence: str
    source_bytes: int
    peak_rss_bytes: int
    seal_observed: bool
    wall_ns: int | None = None
    wall_s: float | None = None

    @model_validator(mode="after")
    def _closed(self) -> ScaleObservation:
        if not self.observation_id.strip() or not self.evidence.strip():
            raise ScaleError("scale observation fields must be non-empty")
        if self.source_bytes < 1 or self.peak_rss_bytes < 1:
            raise ScaleError("scale observation sizes must be positive")
        if self.kind == "named-hardware-baseline":
            if self.wall_ns is None or self.wall_s is not None:
                raise ScaleError(
                    "named-hardware observations record wall_ns only"
                )
            if self.wall_ns < 1:
                raise ScaleError("named-hardware wall_ns must be positive")
        if self.kind == "cli-compile-measured":
            if self.wall_s is None or self.wall_ns is not None:
                raise ScaleError("CLI compile observations record wall_s only")
            if self.wall_s <= 0:
                raise ScaleError("CLI compile wall_s must be positive")
        return self


class ScaleRefusal(_StrictModel):
    observation_id: str
    kind: Literal["compile-refused", "scale-baseline-refused"]
    evidence: str
    sla_claim: Literal[False]

    @model_validator(mode="after")
    def _closed(self) -> ScaleRefusal:
        if not self.observation_id.strip() or not self.evidence.strip():
            raise ScaleError("scale refusal fields must be non-empty")
        return self


class ScaleSupportCatalog(_StrictModel):
    schema_id: Literal["veriformis.scale-support-discovery/v1"]
    contract_id: Literal["veriformis.scale-support"]
    contract_version: Literal[1]
    sla_claim: Literal[False]
    statistical_meaning: Literal[False]
    operator_review: str
    published_tiers: tuple[()]
    observed: tuple[ScaleObservation, ...]
    refusals: tuple[ScaleRefusal, ...]
    unmeasured: tuple[str, ...]

    @field_validator("published_tiers", mode="before")
    @classmethod
    def _empty_tiers(cls, value: Any) -> Any:
        if value not in ([], ()):
            raise ScaleError(
                "published scale tiers must stay empty; a modest fig-leaf tier "
                "is forbidden"
            )
        return ()

    @field_validator("observed", "refusals", "unmeasured", mode="before")
    @classmethod
    def _tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> ScaleSupportCatalog:
        if self.operator_review.strip() != self.operator_review:
            raise ScaleError("operator_review must be exact")
        if not self.operator_review:
            raise ScaleError("operator_review must be non-empty")
        if not self.observed:
            raise ScaleError("scale support requires at least one observation")
        if not self.refusals:
            raise ScaleError("scale support requires retained refusals")
        if not self.unmeasured:
            raise ScaleError("scale support must name unmeasured work")
        seen: set[str] = set()
        for item in (*self.observed, *self.refusals):
            if item.observation_id in seen:
                raise ScaleError(
                    f"duplicate scale observation id {item.observation_id!r}"
                )
            seen.add(item.observation_id)
        if tuple(sorted(self.unmeasured)) != self.unmeasured:
            raise ScaleError("unmeasured identifiers must be sorted")
        if len(set(self.unmeasured)) != len(self.unmeasured):
            raise ScaleError("unmeasured identifiers must be unique")
        return self


@lru_cache(maxsize=1)
def _load_support() -> tuple[str, ScaleSupportCatalog]:
    raw = (
        resources.files("veriformis.scale")
        .joinpath(SUPPORT_DATA_NAME)
        .read_text(encoding="utf-8")
    )
    payload = json.loads(raw)
    canonical = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if canonical != raw:
        raise ScaleError("scale support catalog is not canonical JSON")
    catalog = ScaleSupportCatalog.model_validate(payload)
    return canonical, catalog


def scale_support_catalog() -> ScaleSupportCatalog:
    return _load_support()[1]


def scale_support_catalog_json() -> str:
    return _load_support()[0]


def scale_support_discovery() -> dict[str, Any]:
    return json.loads(scale_support_catalog_json())
