"""Strict immutable contracts for deterministic dataset curation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypeVar, get_origin

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationInfo,
    model_validator,
)

from veriformis.errors import CurationError, DuplicateIdentityError
from veriformis.identity import derive_id, lossless_json_bytes, validate_id

from ._json import canonical_json_object_from_bytes, reject_floats


BalanceMode = Literal["none", "primary_source_cap"]
CurationStatus = Literal["included", "excluded", "quarantined"]
QualityFindingCode = Literal[
    "target-too-short",
    "exact-duplicate",
    "conflicting-target",
    "primary-source-cap",
]
CurationReasonCode = Literal[
    "quality-passed",
    "target-too-short",
    "exact-duplicate",
    "conflicting-target",
    "primary-source-cap",
]
CoverageBlockerCode = Literal[
    "no-constructed-candidates",
    "no-dataset-records",
    "no-included-contribution",
]

V1_QUALITY_FINDING_CODES: tuple[QualityFindingCode, ...] = (
    "conflicting-target",
    "exact-duplicate",
    "primary-source-cap",
    "target-too-short",
)
V1_CURATION_REASON_CODES: tuple[CurationReasonCode, ...] = (
    "conflicting-target",
    "exact-duplicate",
    "primary-source-cap",
    "quality-passed",
    "target-too-short",
)
V1_COVERAGE_BLOCKER_CODES: tuple[CoverageBlockerCode, ...] = (
    "no-constructed-candidates",
    "no-dataset-records",
    "no-included-contribution",
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        arbitrary_types_allowed=True,
    )

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
                f"{cls.__name__} fields do not match its persisted schema; "
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


def _require_canonical_ids(
    values: tuple[str, ...],
    *,
    kind: str,
    field_name: str,
) -> tuple[str, ...]:
    checked = tuple(validate_id(value, kind=kind) for value in values)
    if len(checked) != len(set(checked)):
        raise DuplicateIdentityError(f"{field_name} contains duplicate identities")
    if checked != tuple(sorted(checked)):
        raise ValueError(f"{field_name} must be sorted in canonical order")
    return values


def _require_canonical_codes(
    values: tuple[str, ...],
    *,
    allowed: tuple[str, ...],
    field_name: str,
) -> tuple[str, ...]:
    if any(value not in allowed for value in values):
        raise ValueError(f"{field_name} contains an unsupported code")
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} contains duplicate codes")
    if values != tuple(sorted(values)):
        raise ValueError(f"{field_name} must be sorted in canonical order")
    return values


def _require_nonnegative_integer(value: int, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _revalidate_nested(
    value: _StrictModel,
    model_type: type[_StrictModel],
    *,
    label: str,
) -> None:
    """Reject unchecked model copies at every nested public boundary."""
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


class CurationPolicy(_StrictModel):
    schema_version: Literal["veriformis.curation-policy/v1"] = (
        "veriformis.curation-policy/v1"
    )
    policy_id: str
    minimum_target_characters: int
    exact_duplicate_policy: Literal["keep-lexicographically-smallest-record-id"] = (
        "keep-lexicographically-smallest-record-id"
    )
    conflict_policy: Literal["quarantine-all-distinct-targets"] = (
        "quarantine-all-distinct-targets"
    )
    near_duplicate_policy: Literal["disabled"] = "disabled"
    balance_mode: BalanceMode
    maximum_records_per_primary_source: int | None

    @model_validator(mode="after")
    def _validate_policy(self) -> CurationPolicy:
        validate_id(self.policy_id, kind="cpl")
        _require_nonnegative_integer(
            self.minimum_target_characters,
            "minimum_target_characters",
        )
        if self.balance_mode == "none":
            if self.maximum_records_per_primary_source is not None:
                raise ValueError("no-balancing policy requires a null source cap")
        elif (
            type(self.maximum_records_per_primary_source) is not int
            or self.maximum_records_per_primary_source < 1
        ):
            raise ValueError(
                "primary-source-cap policy requires a positive integer source cap"
            )
        expected_id = derive_id(
            "cpl",
            self.model_dump(mode="json", exclude={"policy_id"}),
        )
        if self.policy_id != expected_id:
            raise ValueError("curation policy identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        minimum_target_characters: int,
        balance_mode: BalanceMode = "none",
        maximum_records_per_primary_source: int | None = None,
    ) -> CurationPolicy:
        payload = {
            "schema_version": "veriformis.curation-policy/v1",
            "minimum_target_characters": minimum_target_characters,
            "exact_duplicate_policy": ("keep-lexicographically-smallest-record-id"),
            "conflict_policy": "quarantine-all-distinct-targets",
            "near_duplicate_policy": "disabled",
            "balance_mode": balance_mode,
            "maximum_records_per_primary_source": (maximum_records_per_primary_source),
        }
        return cls(policy_id=derive_id("cpl", payload), **payload)


class QualityFinding(_StrictModel):
    schema_version: Literal["veriformis.quality-finding/v1"] = (
        "veriformis.quality-finding/v1"
    )
    finding_id: str
    record_id: str
    code: QualityFindingCode
    related_record_ids: tuple[str, ...]
    observed_count: int | None
    required_count: int | None

    @model_validator(mode="after")
    def _validate_finding(self) -> QualityFinding:
        validate_id(self.finding_id, kind="qfn")
        validate_id(self.record_id, kind="rec")
        _require_canonical_ids(
            self.related_record_ids,
            kind="rec",
            field_name="quality finding related_record_ids",
        )
        if self.record_id in self.related_record_ids:
            raise ValueError("quality finding cannot relate a record to itself")
        if self.code not in V1_QUALITY_FINDING_CODES:
            raise ValueError("quality finding contains an unsupported code")

        if self.code == "target-too-short":
            if self.related_record_ids:
                raise ValueError("target-too-short finding cannot name related records")
            if (
                type(self.observed_count) is not int
                or self.observed_count < 0
                or type(self.required_count) is not int
                or self.required_count < 1
                or self.observed_count >= self.required_count
            ):
                raise ValueError("target-too-short finding counts are inconsistent")
        elif self.code == "exact-duplicate":
            if len(self.related_record_ids) != 1:
                raise ValueError("exact-duplicate finding requires one representative")
            if self.observed_count is not None or self.required_count is not None:
                raise ValueError("exact-duplicate finding does not use counts")
        elif self.code == "conflicting-target":
            if not self.related_record_ids:
                raise ValueError("conflicting-target finding requires related records")
            if (
                type(self.observed_count) is not int
                or self.observed_count < 2
                or self.required_count is not None
            ):
                raise ValueError("conflicting-target finding counts are inconsistent")
        else:
            if self.related_record_ids:
                raise ValueError(
                    "primary-source-cap finding cannot name related records"
                )
            if (
                type(self.observed_count) is not int
                or type(self.required_count) is not int
                or self.required_count < 1
                or self.observed_count <= self.required_count
            ):
                raise ValueError("primary-source-cap finding counts are inconsistent")

        expected_id = derive_id(
            "qfn",
            self.model_dump(mode="json", exclude={"finding_id"}),
        )
        if self.finding_id != expected_id:
            raise ValueError("quality finding identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        record_id: str,
        code: QualityFindingCode,
        related_record_ids: tuple[str, ...] | list[str] = (),
        observed_count: int | None = None,
        required_count: int | None = None,
    ) -> QualityFinding:
        payload = {
            "schema_version": "veriformis.quality-finding/v1",
            "record_id": record_id,
            "code": code,
            "related_record_ids": tuple(sorted(related_record_ids)),
            "observed_count": observed_count,
            "required_count": required_count,
        }
        return cls(finding_id=derive_id("qfn", payload), **payload)


class CurationDecision(_StrictModel):
    schema_version: Literal["veriformis.curation-decision/v1"] = (
        "veriformis.curation-decision/v1"
    )
    decision_id: str
    record_id: str
    status: CurationStatus
    reason_codes: tuple[CurationReasonCode, ...]
    finding_ids: tuple[str, ...]

    @model_validator(mode="after")
    def _validate_decision(self) -> CurationDecision:
        validate_id(self.decision_id, kind="cud")
        validate_id(self.record_id, kind="rec")
        _require_canonical_codes(
            self.reason_codes,
            allowed=V1_CURATION_REASON_CODES,
            field_name="curation decision reason_codes",
        )
        _require_canonical_ids(
            self.finding_ids,
            kind="qfn",
            field_name="curation decision finding_ids",
        )
        if len(self.reason_codes) != 1:
            raise ValueError("curation decision requires exactly one reason code")
        reason = self.reason_codes[0]
        if self.status == "included":
            if reason != "quality-passed" or self.finding_ids:
                raise ValueError("included decision must have no quality finding")
        elif self.status == "excluded":
            if (
                reason
                not in {
                    "target-too-short",
                    "exact-duplicate",
                    "primary-source-cap",
                }
                or len(self.finding_ids) != 1
            ):
                raise ValueError("excluded decision requires one exclusion finding")
        elif reason != "conflicting-target" or len(self.finding_ids) != 1:
            raise ValueError("quarantined decision requires one conflict finding")

        expected_id = derive_id(
            "cud",
            self.model_dump(mode="json", exclude={"decision_id"}),
        )
        if self.decision_id != expected_id:
            raise ValueError("curation decision identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        record_id: str,
        status: CurationStatus,
        reason_code: CurationReasonCode,
        finding_ids: tuple[str, ...] | list[str] = (),
    ) -> CurationDecision:
        payload = {
            "schema_version": "veriformis.curation-decision/v1",
            "record_id": record_id,
            "status": status,
            "reason_codes": (reason_code,),
            "finding_ids": tuple(sorted(finding_ids)),
        }
        return cls(decision_id=derive_id("cud", payload), **payload)


class CoverageLedgerEntry(_StrictModel):
    schema_version: Literal["veriformis.coverage-ledger-entry/v1"] = (
        "veriformis.coverage-ledger-entry/v1"
    )
    entry_id: str
    source_id: str
    candidate_count: int
    record_count: int
    included_count: int
    excluded_count: int
    quarantined_count: int
    primary_included_count: int
    blocker_codes: tuple[CoverageBlockerCode, ...]

    @model_validator(mode="after")
    def _validate_entry(self) -> CoverageLedgerEntry:
        validate_id(self.entry_id, kind="cve")
        validate_id(self.source_id, kind="src")
        for field_name in (
            "candidate_count",
            "record_count",
            "included_count",
            "excluded_count",
            "quarantined_count",
            "primary_included_count",
        ):
            _require_nonnegative_integer(getattr(self, field_name), field_name)
        if self.candidate_count < self.record_count:
            raise ValueError("coverage candidate_count cannot be below record_count")
        if self.record_count != (
            self.included_count + self.excluded_count + self.quarantined_count
        ):
            raise ValueError("coverage record status counts do not close")
        if self.primary_included_count > self.included_count:
            raise ValueError("primary included coverage exceeds included coverage")
        _require_canonical_codes(
            self.blocker_codes,
            allowed=V1_COVERAGE_BLOCKER_CODES,
            field_name="coverage blocker_codes",
        )
        expected_blockers: list[CoverageBlockerCode] = []
        if self.candidate_count == 0:
            expected_blockers.append("no-constructed-candidates")
        if self.record_count == 0:
            expected_blockers.append("no-dataset-records")
        if self.included_count == 0:
            expected_blockers.append("no-included-contribution")
        if self.blocker_codes != tuple(sorted(expected_blockers)):
            raise ValueError("coverage blocker codes do not match integer counts")
        expected_id = derive_id(
            "cve",
            self.model_dump(mode="json", exclude={"entry_id"}),
        )
        if self.entry_id != expected_id:
            raise ValueError("coverage ledger entry identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        source_id: str,
        candidate_count: int,
        record_count: int,
        included_count: int,
        excluded_count: int,
        quarantined_count: int,
        primary_included_count: int,
    ) -> CoverageLedgerEntry:
        blockers: list[CoverageBlockerCode] = []
        if candidate_count == 0:
            blockers.append("no-constructed-candidates")
        if record_count == 0:
            blockers.append("no-dataset-records")
        if included_count == 0:
            blockers.append("no-included-contribution")
        payload = {
            "schema_version": "veriformis.coverage-ledger-entry/v1",
            "source_id": source_id,
            "candidate_count": candidate_count,
            "record_count": record_count,
            "included_count": included_count,
            "excluded_count": excluded_count,
            "quarantined_count": quarantined_count,
            "primary_included_count": primary_included_count,
            "blocker_codes": tuple(sorted(blockers)),
        }
        return cls(entry_id=derive_id("cve", payload), **payload)


class CoverageLedger(_StrictModel):
    schema_version: Literal["veriformis.coverage-ledger/v1"] = (
        "veriformis.coverage-ledger/v1"
    )
    ledger_id: str
    selected_source_ids: tuple[str, ...]
    entries: tuple[CoverageLedgerEntry, ...]

    @model_validator(mode="after")
    def _validate_ledger(self) -> CoverageLedger:
        validate_id(self.ledger_id, kind="cvl")
        if not self.selected_source_ids:
            raise ValueError("coverage ledger requires selected sources")
        _require_canonical_ids(
            self.selected_source_ids,
            kind="src",
            field_name="coverage selected_source_ids",
        )
        if tuple(entry.source_id for entry in self.entries) != self.selected_source_ids:
            raise ValueError("coverage ledger requires one ordered entry per source")
        for entry in self.entries:
            _revalidate_nested(
                entry,
                CoverageLedgerEntry,
                label="coverage ledger entry",
            )
        if len({entry.entry_id for entry in self.entries}) != len(self.entries):
            raise DuplicateIdentityError("coverage ledger contains duplicate entries")
        expected_id = derive_id(
            "cvl",
            self.model_dump(mode="json", exclude={"ledger_id"}),
        )
        if self.ledger_id != expected_id:
            raise ValueError("coverage ledger identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        selected_source_ids: tuple[str, ...],
        entries: tuple[CoverageLedgerEntry, ...],
    ) -> CoverageLedger:
        payload = {
            "schema_version": "veriformis.coverage-ledger/v1",
            "selected_source_ids": selected_source_ids,
            "entries": entries,
        }
        return cls(ledger_id=derive_id("cvl", payload), **payload)


class CurationResult(_StrictModel):
    schema_version: Literal["veriformis.curation-result/v1"] = (
        "veriformis.curation-result/v1"
    )
    result_id: str
    plan_id: str
    recipe_id: str
    construction_result_id: str
    policy_id: str
    input_record_ids: tuple[str, ...]
    decisions: tuple[CurationDecision, ...]
    findings: tuple[QualityFinding, ...]
    included_record_ids: tuple[str, ...]
    coverage_ledger: CoverageLedger

    @model_validator(mode="after")
    def _validate_result(self) -> CurationResult:
        validate_id(self.result_id, kind="cur")
        validate_id(self.plan_id, kind="fdp")
        validate_id(self.recipe_id, kind="rcp")
        validate_id(self.construction_result_id, kind="run")
        validate_id(self.policy_id, kind="cpl")
        _require_canonical_ids(
            self.input_record_ids,
            kind="rec",
            field_name="curation input_record_ids",
        )
        for decision in self.decisions:
            _revalidate_nested(
                decision,
                CurationDecision,
                label="curation decision",
            )
        for finding in self.findings:
            _revalidate_nested(
                finding,
                QualityFinding,
                label="quality finding",
            )
        _revalidate_nested(
            self.coverage_ledger,
            CoverageLedger,
            label="coverage ledger",
        )
        decision_record_ids = tuple(decision.record_id for decision in self.decisions)
        if decision_record_ids != self.input_record_ids:
            raise ValueError(
                "curation requires one ordered decision per dataset record"
            )
        if len({decision.decision_id for decision in self.decisions}) != len(
            self.decisions
        ):
            raise DuplicateIdentityError("curation result contains duplicate decisions")

        finding_ids = tuple(finding.finding_id for finding in self.findings)
        _require_canonical_ids(
            finding_ids,
            kind="qfn",
            field_name="curation finding identities",
        )
        findings_by_id = {finding.finding_id: finding for finding in self.findings}
        referenced_findings = tuple(
            finding_id
            for decision in self.decisions
            for finding_id in decision.finding_ids
        )
        if tuple(sorted(referenced_findings)) != finding_ids:
            raise ValueError("curation findings do not exactly match decision evidence")
        for decision in self.decisions:
            if not decision.finding_ids:
                continue
            finding = findings_by_id[decision.finding_ids[0]]
            if (
                finding.record_id != decision.record_id
                or finding.code != decision.reason_codes[0]
            ):
                raise ValueError("curation decision does not match its quality finding")

        expected_included = tuple(
            decision.record_id
            for decision in self.decisions
            if decision.status == "included"
        )
        if self.included_record_ids != expected_included:
            raise ValueError("included record identities do not match decisions")
        expected_id = derive_id(
            "cur",
            self.model_dump(mode="json", exclude={"result_id"}),
        )
        if self.result_id != expected_id:
            raise ValueError("curation result identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        plan_id: str,
        recipe_id: str,
        construction_result_id: str,
        policy_id: str,
        input_record_ids: tuple[str, ...],
        decisions: tuple[CurationDecision, ...],
        findings: tuple[QualityFinding, ...],
        included_record_ids: tuple[str, ...],
        coverage_ledger: CoverageLedger,
    ) -> CurationResult:
        payload = {
            "schema_version": "veriformis.curation-result/v1",
            "plan_id": plan_id,
            "recipe_id": recipe_id,
            "construction_result_id": construction_result_id,
            "policy_id": policy_id,
            "input_record_ids": input_record_ids,
            "decisions": decisions,
            "findings": findings,
            "included_record_ids": included_record_ids,
            "coverage_ledger": coverage_ledger,
        }
        return cls(result_id=derive_id("cur", payload), **payload)


ModelT = TypeVar("ModelT", bound=_StrictModel)


def _model_to_dict(
    value: ModelT, model_type: type[ModelT], *, label: str
) -> dict[str, Any]:
    try:
        payload = value.model_dump(mode="json")
        reject_floats(payload)
        checked = model_type.model_validate_json(lossless_json_bytes(payload))
    except DuplicateIdentityError:
        raise
    except (AttributeError, TypeError, UnicodeError, ValueError) as exc:
        raise CurationError(f"invalid {label}: {exc}") from exc
    if checked != value:
        raise CurationError(f"{label} does not round-trip exactly")
    return payload


def _model_from_json_bytes(
    data: bytes,
    model_type: type[ModelT],
    *,
    label: str,
) -> ModelT:
    try:
        canonical_json_object_from_bytes(data, label=label)
        return model_type.model_validate_json(data)
    except DuplicateIdentityError:
        raise
    except (TypeError, UnicodeError, ValueError) as exc:
        raise CurationError(f"invalid {label}: {exc}") from exc


def _model_from_dict(
    value: dict[str, Any],
    model_type: type[ModelT],
    *,
    label: str,
) -> ModelT:
    try:
        return _model_from_json_bytes(
            lossless_json_bytes(value),
            model_type,
            label=label,
        )
    except DuplicateIdentityError:
        raise
    except CurationError:
        raise
    except (TypeError, UnicodeError, ValueError) as exc:
        raise CurationError(f"invalid {label}: {exc}") from exc


def curation_policy_to_dict(value: CurationPolicy) -> dict[str, Any]:
    return _model_to_dict(value, CurationPolicy, label="curation policy")


def curation_policy_from_json_bytes(data: bytes) -> CurationPolicy:
    return _model_from_json_bytes(data, CurationPolicy, label="curation policy")


def curation_policy_from_dict(value: dict[str, Any]) -> CurationPolicy:
    return _model_from_dict(value, CurationPolicy, label="curation policy")


def coverage_ledger_to_dict(value: CoverageLedger) -> dict[str, Any]:
    return _model_to_dict(value, CoverageLedger, label="coverage ledger")


def coverage_ledger_from_json_bytes(data: bytes) -> CoverageLedger:
    return _model_from_json_bytes(data, CoverageLedger, label="coverage ledger")


def coverage_ledger_from_dict(value: dict[str, Any]) -> CoverageLedger:
    return _model_from_dict(value, CoverageLedger, label="coverage ledger")


def curation_result_to_dict(value: CurationResult) -> dict[str, Any]:
    return _model_to_dict(value, CurationResult, label="curation result")


def curation_result_from_json_bytes(data: bytes) -> CurationResult:
    return _model_from_json_bytes(data, CurationResult, label="curation result")


def curation_result_from_dict(value: dict[str, Any]) -> CurationResult:
    return _model_from_dict(value, CurationResult, label="curation result")


__all__ = [
    "V1_COVERAGE_BLOCKER_CODES",
    "V1_CURATION_REASON_CODES",
    "V1_QUALITY_FINDING_CODES",
    "BalanceMode",
    "CoverageBlockerCode",
    "CoverageLedger",
    "CoverageLedgerEntry",
    "CurationDecision",
    "CurationError",
    "CurationPolicy",
    "CurationReasonCode",
    "CurationResult",
    "CurationStatus",
    "QualityFinding",
    "QualityFindingCode",
    "coverage_ledger_from_dict",
    "coverage_ledger_from_json_bytes",
    "coverage_ledger_to_dict",
    "curation_policy_from_dict",
    "curation_policy_from_json_bytes",
    "curation_policy_to_dict",
    "curation_result_from_dict",
    "curation_result_from_json_bytes",
    "curation_result_to_dict",
]
