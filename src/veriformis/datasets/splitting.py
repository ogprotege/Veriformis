"""Deterministic, leakage-safe train and evaluation splitting.

Splitting consumes already replay-validated Group 2 construction and Group 3
curation artifacts. It does not mutate either artifact. Version 1 joins every
included record into transitive leakage components using source identities,
raw-source byte digests, and exact-record fingerprint families. A multi-source
record therefore bridges every source that contributed to it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal, TypeVar, get_origin

from pydantic import BaseModel, ConfigDict, ValidationInfo, model_validator

from veriformis.construction import (
    ConstructionResult,
    DatasetRecord,
    construction_result_from_dict,
)
from veriformis.errors import (
    ConstructionError,
    CurationError,
    DuplicateIdentityError,
    SplitError,
)
from veriformis.identity import (
    canonical_digest,
    derive_id,
    lossless_json_bytes,
    sha256_digest,
    validate_id,
    validate_sha256,
)

from ._json import canonical_json_object_from_bytes, reject_floats
from .curation import exact_record_fingerprint
from .models import CurationResult, curation_result_from_dict

if TYPE_CHECKING:
    from .plan import FinishedDatasetPlan


Partition = Literal["train", "evaluation"]
SplitAlgorithm = Literal["transitive-leakage-prefix-v1"]

V1_PARTITIONS: tuple[Partition, ...] = ("train", "evaluation")
V1_SPLIT_ALGORITHM: SplitAlgorithm = "transitive-leakage-prefix-v1"
_RATIO_SCALE = 1_000_000


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        arbitrary_types_allowed=True,
        revalidate_instances="always",
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


def _require_nonempty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _require_canonical_ids(
    values: tuple[str, ...],
    *,
    kind: str,
    field_name: str,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if not values and not allow_empty:
        raise ValueError(f"{field_name} cannot be empty")
    checked = tuple(validate_id(value, kind=kind) for value in values)
    if len(checked) != len(set(checked)):
        raise DuplicateIdentityError(f"{field_name} contains duplicate identities")
    if checked != tuple(sorted(checked)):
        raise ValueError(f"{field_name} must be sorted in canonical order")
    return values


def _require_canonical_sha256_values(
    values: tuple[str, ...],
    *,
    field_name: str,
) -> tuple[str, ...]:
    if not values:
        raise ValueError(f"{field_name} cannot be empty")
    checked = tuple(validate_sha256(value) for value in values)
    if len(checked) != len(set(checked)):
        raise ValueError(f"{field_name} contains duplicate values")
    if checked != tuple(sorted(checked)):
        raise ValueError(f"{field_name} must be sorted in canonical order")
    return values


class SplitPolicy(_StrictModel):
    """Exact integer split policy with an explicit evaluation fallback."""

    schema_version: Literal["veriformis.split-policy/v1"] = "veriformis.split-policy/v1"
    policy_id: str
    algorithm: SplitAlgorithm = V1_SPLIT_ALGORITHM
    evaluation_ratio_ppm: int
    evaluation_required: bool
    seed: str

    @model_validator(mode="after")
    def _validate_policy(self) -> SplitPolicy:
        validate_id(self.policy_id, kind="spp")
        if (
            type(self.evaluation_ratio_ppm) is not int
            or not 1 <= self.evaluation_ratio_ppm < _RATIO_SCALE
        ):
            raise ValueError("evaluation_ratio_ppm must be an integer in 1..999999")
        if type(self.evaluation_required) is not bool:
            raise ValueError("evaluation_required must be a boolean")
        _require_nonempty(self.seed, "split seed")
        expected_id = derive_id(
            "spp",
            self.model_dump(mode="json", exclude={"policy_id"}),
        )
        if self.policy_id != expected_id:
            raise ValueError("split policy identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        evaluation_ratio_ppm: int,
        evaluation_required: bool = True,
        seed: str,
    ) -> SplitPolicy:
        payload = {
            "schema_version": "veriformis.split-policy/v1",
            "algorithm": V1_SPLIT_ALGORITHM,
            "evaluation_ratio_ppm": evaluation_ratio_ppm,
            "evaluation_required": evaluation_required,
            "seed": seed,
        }
        return cls(policy_id=derive_id("spp", payload), **payload)


class LeakageGroup(_StrictModel):
    """One complete transitive leakage component."""

    schema_version: Literal["veriformis.leakage-group/v1"] = (
        "veriformis.leakage-group/v1"
    )
    group_id: str
    record_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    raw_sha256_values: tuple[str, ...]
    exact_record_fingerprints: tuple[str, ...]

    @model_validator(mode="after")
    def _validate_group(self) -> LeakageGroup:
        validate_id(self.group_id, kind="lkg")
        _require_canonical_ids(
            self.record_ids,
            kind="rec",
            field_name="leakage group record_ids",
        )
        _require_canonical_ids(
            self.source_ids,
            kind="src",
            field_name="leakage group source_ids",
        )
        _require_canonical_sha256_values(
            self.raw_sha256_values,
            field_name="leakage group raw_sha256_values",
        )
        _require_canonical_sha256_values(
            self.exact_record_fingerprints,
            field_name="leakage group exact_record_fingerprints",
        )
        expected_id = derive_id(
            "lkg",
            self.model_dump(mode="json", exclude={"group_id"}),
        )
        if self.group_id != expected_id:
            raise ValueError("leakage group identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        record_ids: Sequence[str],
        source_ids: Sequence[str],
        raw_sha256_values: Sequence[str],
        exact_record_fingerprints: Sequence[str],
    ) -> LeakageGroup:
        payload = {
            "schema_version": "veriformis.leakage-group/v1",
            "record_ids": tuple(sorted(record_ids)),
            "source_ids": tuple(sorted(source_ids)),
            "raw_sha256_values": tuple(sorted(raw_sha256_values)),
            "exact_record_fingerprints": tuple(sorted(exact_record_fingerprints)),
        }
        return cls(group_id=derive_id("lkg", payload), **payload)


class RecordAssignment(_StrictModel):
    """The authoritative partition for one included record."""

    schema_version: Literal["veriformis.record-assignment/v1"] = (
        "veriformis.record-assignment/v1"
    )
    assignment_id: str
    policy_id: str
    record_id: str
    group_id: str
    partition: Partition

    @model_validator(mode="after")
    def _validate_assignment(self) -> RecordAssignment:
        validate_id(self.assignment_id, kind="asg")
        validate_id(self.policy_id, kind="spp")
        validate_id(self.record_id, kind="rec")
        validate_id(self.group_id, kind="lkg")
        if self.partition not in V1_PARTITIONS:
            raise ValueError("record assignment contains an unsupported partition")
        expected_id = derive_id(
            "asg",
            self.model_dump(mode="json", exclude={"assignment_id"}),
        )
        if self.assignment_id != expected_id:
            raise ValueError("record assignment identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        policy_id: str,
        record_id: str,
        group_id: str,
        partition: Partition,
    ) -> RecordAssignment:
        payload = {
            "schema_version": "veriformis.record-assignment/v1",
            "policy_id": policy_id,
            "record_id": record_id,
            "group_id": group_id,
            "partition": partition,
        }
        return cls(assignment_id=derive_id("asg", payload), **payload)


class SplitResult(_StrictModel):
    """Complete, immutable leakage grouping and partition assignment."""

    schema_version: Literal["veriformis.split-result/v1"] = "veriformis.split-result/v1"
    result_id: str
    policy_id: str
    plan_id: str
    construction_result_id: str
    curation_result_id: str
    input_record_ids: tuple[str, ...]
    groups: tuple[LeakageGroup, ...]
    assignments: tuple[RecordAssignment, ...]
    requested_evaluation_record_count: int
    realized_train_record_count: int
    realized_evaluation_record_count: int
    assignment_digest: str

    @model_validator(mode="after")
    def _validate_result(self) -> SplitResult:
        validate_id(self.result_id, kind="spt")
        validate_id(self.policy_id, kind="spp")
        validate_id(self.plan_id, kind="fdp")
        validate_id(self.construction_result_id, kind="run")
        validate_id(self.curation_result_id, kind="cur")
        _require_canonical_ids(
            self.input_record_ids,
            kind="rec",
            field_name="split input_record_ids",
        )

        group_ids = tuple(group.group_id for group in self.groups)
        _require_canonical_ids(
            group_ids,
            kind="lkg",
            field_name="split group identities",
        )
        grouped_record_ids = tuple(
            sorted(record_id for group in self.groups for record_id in group.record_ids)
        )
        if grouped_record_ids != self.input_record_ids:
            raise ValueError(
                "leakage groups do not cover included records exactly once"
            )

        assignment_ids = tuple(
            assignment.assignment_id for assignment in self.assignments
        )
        if len(assignment_ids) != len(set(assignment_ids)):
            raise DuplicateIdentityError(
                "split result contains duplicate record assignments"
            )
        assignment_record_ids = tuple(
            assignment.record_id for assignment in self.assignments
        )
        if assignment_record_ids != self.input_record_ids:
            raise ValueError(
                "split result requires one ordered assignment per included record"
            )

        group_by_record = {
            record_id: group.group_id
            for group in self.groups
            for record_id in group.record_ids
        }
        partitions_by_group: dict[str, set[Partition]] = {
            group_id: set() for group_id in group_ids
        }
        for assignment in self.assignments:
            if assignment.policy_id != self.policy_id:
                raise ValueError("record assignment names another split policy")
            if assignment.group_id != group_by_record[assignment.record_id]:
                raise ValueError("record assignment names another leakage group")
            partitions_by_group[assignment.group_id].add(assignment.partition)
        if any(len(partitions) != 1 for partitions in partitions_by_group.values()):
            raise ValueError("a leakage group cannot cross partitions")

        for field_name in (
            "requested_evaluation_record_count",
            "realized_train_record_count",
            "realized_evaluation_record_count",
        ):
            value = getattr(self, field_name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        total = len(self.input_record_ids)
        if self.requested_evaluation_record_count > total:
            raise ValueError("requested evaluation count exceeds input records")
        train_count = sum(
            assignment.partition == "train" for assignment in self.assignments
        )
        evaluation_count = sum(
            assignment.partition == "evaluation" for assignment in self.assignments
        )
        if (
            self.realized_train_record_count != train_count
            or self.realized_evaluation_record_count != evaluation_count
            or train_count + evaluation_count != total
        ):
            raise ValueError("split result partition counts do not close")
        if train_count < 1:
            raise ValueError("split result requires a non-empty train partition")

        validate_sha256(self.assignment_digest)
        expected_assignment_digest = canonical_digest(
            {
                "schema_version": "veriformis.assignment-set/v1",
                "assignments": self.assignments,
            }
        )
        if self.assignment_digest != expected_assignment_digest:
            raise ValueError("split assignment digest mismatch")
        expected_id = derive_id(
            "spt",
            self.model_dump(mode="json", exclude={"result_id"}),
        )
        if self.result_id != expected_id:
            raise ValueError("split result identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        policy_id: str,
        plan_id: str,
        construction_result_id: str,
        curation_result_id: str,
        input_record_ids: Sequence[str],
        groups: Sequence[LeakageGroup],
        assignments: Sequence[RecordAssignment],
        requested_evaluation_record_count: int,
    ) -> SplitResult:
        normalized_record_ids = tuple(sorted(input_record_ids))
        normalized_groups = tuple(sorted(groups, key=lambda item: item.group_id))
        normalized_assignments = tuple(
            sorted(assignments, key=lambda item: item.record_id)
        )
        train_count = sum(
            assignment.partition == "train" for assignment in normalized_assignments
        )
        evaluation_count = sum(
            assignment.partition == "evaluation"
            for assignment in normalized_assignments
        )
        assignment_digest = canonical_digest(
            {
                "schema_version": "veriformis.assignment-set/v1",
                "assignments": normalized_assignments,
            }
        )
        payload = {
            "schema_version": "veriformis.split-result/v1",
            "policy_id": policy_id,
            "plan_id": plan_id,
            "construction_result_id": construction_result_id,
            "curation_result_id": curation_result_id,
            "input_record_ids": normalized_record_ids,
            "groups": normalized_groups,
            "assignments": normalized_assignments,
            "requested_evaluation_record_count": (requested_evaluation_record_count),
            "realized_train_record_count": train_count,
            "realized_evaluation_record_count": evaluation_count,
            "assignment_digest": assignment_digest,
        }
        return cls(result_id=derive_id("spt", payload), **payload)


ModelT = TypeVar("ModelT", bound=_StrictModel)


def _model_to_dict(
    value: ModelT,
    model_type: type[ModelT],
    *,
    label: str,
) -> dict[str, Any]:
    try:
        payload = value.model_dump(mode="json")
        reject_floats(payload)
        checked = model_type.model_validate_json(lossless_json_bytes(payload))
    except DuplicateIdentityError:
        raise
    except (AttributeError, TypeError, UnicodeError, ValueError) as exc:
        raise SplitError(f"invalid {label}: {exc}") from exc
    if checked != value:
        raise SplitError(f"{label} does not round-trip exactly")
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
        raise SplitError(f"invalid {label}: {exc}") from exc


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
    except (DuplicateIdentityError, SplitError):
        raise
    except (TypeError, UnicodeError, ValueError) as exc:
        raise SplitError(f"invalid {label}: {exc}") from exc


def split_policy_to_dict(value: SplitPolicy) -> dict[str, Any]:
    return _model_to_dict(value, SplitPolicy, label="split policy")


def split_policy_from_json_bytes(data: bytes) -> SplitPolicy:
    return _model_from_json_bytes(data, SplitPolicy, label="split policy")


def split_policy_from_dict(value: dict[str, Any]) -> SplitPolicy:
    return _model_from_dict(value, SplitPolicy, label="split policy")


def leakage_group_to_dict(value: LeakageGroup) -> dict[str, Any]:
    return _model_to_dict(value, LeakageGroup, label="leakage group")


def leakage_group_from_json_bytes(data: bytes) -> LeakageGroup:
    return _model_from_json_bytes(data, LeakageGroup, label="leakage group")


def leakage_group_from_dict(value: dict[str, Any]) -> LeakageGroup:
    return _model_from_dict(value, LeakageGroup, label="leakage group")


def record_assignment_to_dict(value: RecordAssignment) -> dict[str, Any]:
    return _model_to_dict(value, RecordAssignment, label="record assignment")


def record_assignment_from_json_bytes(data: bytes) -> RecordAssignment:
    return _model_from_json_bytes(
        data,
        RecordAssignment,
        label="record assignment",
    )


def record_assignment_from_dict(value: dict[str, Any]) -> RecordAssignment:
    return _model_from_dict(
        value,
        RecordAssignment,
        label="record assignment",
    )


def split_result_to_dict(value: SplitResult) -> dict[str, Any]:
    return _model_to_dict(value, SplitResult, label="split result")


def split_result_from_json_bytes(data: bytes) -> SplitResult:
    return _model_from_json_bytes(data, SplitResult, label="split result")


def split_result_from_dict(value: dict[str, Any]) -> SplitResult:
    return _model_from_dict(value, SplitResult, label="split result")


def split_dataset(
    plan: FinishedDatasetPlan,
    construction_result: ConstructionResult,
    curation_result: CurationResult,
    source_raw_sha256_by_id: Mapping[str, str],
) -> SplitResult:
    """Build deterministic leakage components and whole-component partitions.

    The caller remains responsible for replaying raw-source construction and
    curation before this boundary. This function revalidates both persisted
    artifact schemas and every relationship needed for splitting.
    """
    from .plan import finished_dataset_plan_from_dict

    try:
        checked_plan = finished_dataset_plan_from_dict(plan.model_dump(mode="json"))
    except (AttributeError, CurationError, DuplicateIdentityError) as exc:
        raise SplitError(f"invalid finished dataset plan: {exc}") from exc
    checked_policy = _checked_policy(checked_plan.split_policy)
    checked_construction = _checked_construction_result(construction_result)
    checked_curation = _checked_curation_result(curation_result)
    _validate_construction_curation_relationship(
        checked_construction,
        checked_curation,
    )
    if (
        checked_plan.recipe_id != checked_construction.recipe_id
        or checked_plan.construction_result_id != checked_construction.result_id
        or checked_curation.plan_id != checked_plan.plan_id
        or checked_curation.policy_id != checked_plan.curation_policy.policy_id
    ):
        raise SplitError(
            "finished dataset plan, construction, and curation identities disagree"
        )
    raw_digests = _checked_source_raw_digests(
        source_raw_sha256_by_id,
        checked_curation.coverage_ledger.selected_source_ids,
    )

    records_by_id = {
        record.record_id: record for record in checked_construction.records
    }
    included_records = tuple(
        records_by_id[record_id] for record_id in checked_curation.included_record_ids
    )
    if not included_records:
        raise SplitError("splitting requires at least one curation-included record")

    source_bases = _included_record_source_bases(
        checked_construction,
        checked_curation,
    )
    groups = build_leakage_groups(
        included_records,
        raw_digests,
        source_bases,
    )
    assignments, requested_evaluation_record_count = assign_leakage_partitions(
        checked_policy,
        groups,
        checked_curation.included_record_ids,
    )
    return SplitResult.create(
        policy_id=checked_policy.policy_id,
        plan_id=checked_curation.plan_id,
        construction_result_id=checked_construction.result_id,
        curation_result_id=checked_curation.result_id,
        input_record_ids=checked_curation.included_record_ids,
        groups=groups,
        assignments=assignments,
        requested_evaluation_record_count=requested_evaluation_record_count,
    )


def validate_split_result(
    plan: FinishedDatasetPlan,
    construction_result: ConstructionResult,
    curation_result: CurationResult,
    source_raw_sha256_by_id: Mapping[str, str],
    result: SplitResult,
) -> SplitResult:
    """Replay an exact split and reject any altered persisted result."""
    try:
        result_payload = result.model_dump(mode="json")
    except (AttributeError, TypeError, UnicodeError, ValueError) as exc:
        raise SplitError(f"invalid split result: {exc}") from exc
    checked_result = split_result_from_dict(result_payload)
    replayed = split_dataset(
        plan,
        construction_result,
        curation_result,
        source_raw_sha256_by_id,
    )
    if checked_result != replayed:
        raise SplitError("split result does not match deterministic replay")
    return checked_result


def _checked_policy(value: SplitPolicy) -> SplitPolicy:
    try:
        return split_policy_from_dict(value.model_dump(mode="json"))
    except (
        AttributeError,
        DuplicateIdentityError,
        SplitError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as exc:
        if isinstance(exc, SplitError):
            raise
        raise SplitError(f"invalid split policy: {exc}") from exc


def _checked_construction_result(value: ConstructionResult) -> ConstructionResult:
    try:
        return construction_result_from_dict(value.model_dump(mode="json"))
    except (
        AttributeError,
        ConstructionError,
        DuplicateIdentityError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as exc:
        raise SplitError(f"invalid construction result: {exc}") from exc


def _checked_curation_result(value: CurationResult) -> CurationResult:
    try:
        return curation_result_from_dict(value.model_dump(mode="json"))
    except (
        AttributeError,
        CurationError,
        DuplicateIdentityError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as exc:
        raise SplitError(f"invalid curation result: {exc}") from exc


def _validate_construction_curation_relationship(
    construction: ConstructionResult,
    curation: CurationResult,
) -> None:
    if curation.construction_result_id != construction.result_id:
        raise SplitError("curation result names another construction result")
    if curation.recipe_id != construction.recipe_id:
        raise SplitError("curation result names another construction recipe")
    record_ids = tuple(sorted(record.record_id for record in construction.records))
    if curation.input_record_ids != record_ids:
        raise SplitError(
            "curation input records do not exactly match construction records"
        )

    decisions = {decision.record_id: decision for decision in curation.decisions}
    entries = {entry.source_id: entry for entry in curation.coverage_ledger.entries}
    selected_source_ids = set(curation.coverage_ledger.selected_source_ids)
    referenced_source_ids = {
        source_id
        for candidate in construction.candidates
        for source_id in candidate.source_ids
    } | {
        source_id
        for diagnostic in construction.diagnostics
        for source_id in diagnostic.source_ids
    }
    if not referenced_source_ids.issubset(selected_source_ids):
        raise SplitError("construction names sources outside the coverage ledger")

    for source_id, entry in entries.items():
        candidates = tuple(
            candidate
            for candidate in construction.candidates
            if source_id in candidate.source_ids
        )
        records = tuple(
            record for record in construction.records if source_id in record.source_ids
        )
        expected_status_counts = {
            "included": 0,
            "excluded": 0,
            "quarantined": 0,
        }
        primary_included_count = 0
        for record in records:
            decision = decisions[record.record_id]
            expected_status_counts[decision.status] += 1
            if decision.status == "included" and record.source_ids[0] == source_id:
                primary_included_count += 1
        actual = (
            entry.candidate_count,
            entry.record_count,
            entry.included_count,
            entry.excluded_count,
            entry.quarantined_count,
            entry.primary_included_count,
        )
        expected = (
            len(candidates),
            len(records),
            expected_status_counts["included"],
            expected_status_counts["excluded"],
            expected_status_counts["quarantined"],
            primary_included_count,
        )
        if actual != expected:
            raise SplitError(
                f"coverage ledger does not match construction and curation for "
                f"source {source_id}"
            )


def _checked_source_raw_digests(
    value: Mapping[str, str],
    selected_source_ids: tuple[str, ...],
) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise SplitError("source raw digest input must be a mapping")
    try:
        actual_source_ids = tuple(sorted(value))
    except TypeError as exc:
        raise SplitError("source raw digest mapping keys must be strings") from exc
    if actual_source_ids != selected_source_ids:
        raise SplitError(
            "source raw digest mapping must exactly cover selected source identities"
        )
    result: dict[str, str] = {}
    try:
        for source_id in selected_source_ids:
            validate_id(source_id, kind="src")
            result[source_id] = validate_sha256(value[source_id])
    except (TypeError, ValueError) as exc:
        raise SplitError(f"invalid source raw digest mapping: {exc}") from exc
    return result


def _included_record_source_bases(
    construction: ConstructionResult,
    curation: CurationResult,
) -> dict[str, tuple[str, ...]]:
    """Retain excluded exact-duplicate origins on their included representative."""
    records = {record.record_id: record for record in construction.records}
    bases: dict[str, set[str]] = {
        record_id: set(records[record_id].source_ids)
        for record_id in curation.included_record_ids
    }
    findings = {finding.finding_id: finding for finding in curation.findings}
    for decision in curation.decisions:
        if decision.reason_codes != ("exact-duplicate",):
            continue
        finding = findings[decision.finding_ids[0]]
        representative_id = finding.related_record_ids[0]
        if representative_id not in bases:
            continue
        duplicate = records[decision.record_id]
        representative = records[representative_id]
        if exact_record_fingerprint(duplicate) != exact_record_fingerprint(
            representative
        ):
            raise SplitError(
                "exact-duplicate curation finding joins distinct fingerprints"
            )
        bases[representative_id].update(duplicate.source_ids)
    return {
        record_id: tuple(sorted(source_ids)) for record_id, source_ids in bases.items()
    }


class _DisjointSet:
    def __init__(self, size: int):
        self._parents = list(range(size))

    def find(self, item: int) -> int:
        root = item
        while self._parents[root] != root:
            root = self._parents[root]
        while self._parents[item] != root:
            self._parents[item], item = root, self._parents[item]
        return root

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        low, high = sorted((left_root, right_root))
        self._parents[high] = low


def assign_leakage_partitions(
    policy: SplitPolicy,
    groups: Sequence[LeakageGroup],
    ordered_record_ids: Sequence[str],
) -> tuple[tuple[RecordAssignment, ...], int]:
    """Assign whole leakage groups to train or evaluation.

    The default SFT algorithm name remains ``transitive-leakage-prefix-v1``.
    Extra grouping keys affect only how groups are formed, not this prefix
    assignment.
    """
    checked_policy = _checked_policy(policy)
    if not groups:
        raise SplitError("splitting requires at least one leakage group")
    group_by_record = {
        record_id: group.group_id for group in groups for record_id in group.record_ids
    }
    missing = [record_id for record_id in ordered_record_ids if record_id not in group_by_record]
    extra = [
        record_id
        for record_id in group_by_record
        if record_id not in set(ordered_record_ids)
    ]
    if missing or extra:
        raise SplitError("leakage groups do not cover included records exactly once")
    if len(groups) < 2:
        if checked_policy.evaluation_required:
            raise SplitError(
                "evaluation is required but fewer than two leakage groups exist"
            )
        assignments = tuple(
            RecordAssignment.create(
                policy_id=checked_policy.policy_id,
                record_id=record_id,
                group_id=groups[0].group_id,
                partition="train",
            )
            for record_id in ordered_record_ids
        )
        return assignments, 0

    target = _rounded_clamped_evaluation_target(
        len(ordered_record_ids),
        checked_policy.evaluation_ratio_ppm,
    )
    priority_order = tuple(
        sorted(
            groups,
            key=lambda group: (
                sha256_digest(
                    checked_policy.policy_id + checked_policy.seed + group.group_id
                ),
                group.group_id,
            ),
        )
    )
    best_prefix_length = _nearest_proper_prefix(priority_order, target)
    evaluation_group_ids = {
        group.group_id for group in priority_order[:best_prefix_length]
    }
    assignments = tuple(
        RecordAssignment.create(
            policy_id=checked_policy.policy_id,
            record_id=record_id,
            group_id=group_by_record[record_id],
            partition=(
                "evaluation"
                if group_by_record[record_id] in evaluation_group_ids
                else "train"
            ),
        )
        for record_id in ordered_record_ids
    )
    return assignments, target


def build_leakage_groups(
    records: Sequence[DatasetRecord],
    raw_digests: Mapping[str, str],
    source_bases: Mapping[str, tuple[str, ...]],
    extra_tokens_by_record: Mapping[str, Sequence[tuple[str, str]]] | None = None,
) -> tuple[LeakageGroup, ...]:
    """Build transitive leakage components.

    Default SFT grouping uses source identities, raw-source digests, and
    exact-record fingerprints. Extra tokens are optional and unused by the
    default compile path.
    """
    return _build_leakage_groups(
        records,
        raw_digests,
        source_bases,
        extra_tokens_by_record,
    )


def _build_leakage_groups(
    records: Sequence[DatasetRecord],
    raw_digests: Mapping[str, str],
    source_bases: Mapping[str, tuple[str, ...]],
    extra_tokens_by_record: Mapping[str, Sequence[tuple[str, str]]] | None = None,
) -> tuple[LeakageGroup, ...]:
    ordered = tuple(sorted(records, key=lambda item: item.record_id))
    disjoint = _DisjointSet(len(ordered))
    token_owner: dict[tuple[str, str], int] = {}
    fingerprints: dict[str, str] = {}
    extras = extra_tokens_by_record or {}

    for index, record in enumerate(ordered):
        fingerprint = exact_record_fingerprint(record)
        fingerprints[record.record_id] = fingerprint
        source_ids = source_bases[record.record_id]
        tokens = {
            *(("source", source_id) for source_id in source_ids),
            *(("raw-sha256", raw_digests[source_id]) for source_id in source_ids),
            ("exact-record-fingerprint", fingerprint),
            *tuple(extras.get(record.record_id, ())),
        }
        for token in sorted(tokens):
            owner = token_owner.setdefault(token, index)
            disjoint.union(index, owner)

    members_by_root: dict[int, list[DatasetRecord]] = {}
    for index, record in enumerate(ordered):
        members_by_root.setdefault(disjoint.find(index), []).append(record)

    groups = []
    for members in members_by_root.values():
        source_ids = tuple(
            sorted(
                {
                    source_id
                    for record in members
                    for source_id in source_bases[record.record_id]
                }
            )
        )
        groups.append(
            LeakageGroup.create(
                record_ids=tuple(record.record_id for record in members),
                source_ids=source_ids,
                raw_sha256_values=tuple(
                    sorted({raw_digests[source_id] for source_id in source_ids})
                ),
                exact_record_fingerprints=tuple(
                    sorted({fingerprints[record.record_id] for record in members})
                ),
            )
        )
    return tuple(sorted(groups, key=lambda item: item.group_id))


def _rounded_clamped_evaluation_target(
    total_records: int,
    evaluation_ratio_ppm: int,
) -> int:
    rounded = (
        total_records * evaluation_ratio_ppm + (_RATIO_SCALE // 2)
    ) // _RATIO_SCALE
    return max(1, min(total_records - 1, rounded))


def _nearest_proper_prefix(
    ordered_groups: Sequence[LeakageGroup],
    target: int,
) -> int:
    cumulative = 0
    options: list[tuple[int, int]] = []
    for prefix_length, group in enumerate(ordered_groups[:-1], start=1):
        cumulative += len(group.record_ids)
        options.append((abs(cumulative - target), prefix_length))
    if not options:
        raise SplitError("no non-empty proper evaluation prefix exists")
    return min(options)[1]


__all__ = [
    "V1_PARTITIONS",
    "V1_SPLIT_ALGORITHM",
    "LeakageGroup",
    "Partition",
    "RecordAssignment",
    "SplitAlgorithm",
    "SplitPolicy",
    "SplitResult",
    "assign_leakage_partitions",
    "build_leakage_groups",
    "leakage_group_from_dict",
    "leakage_group_from_json_bytes",
    "leakage_group_to_dict",
    "record_assignment_from_dict",
    "record_assignment_from_json_bytes",
    "record_assignment_to_dict",
    "split_dataset",
    "split_policy_from_dict",
    "split_policy_from_json_bytes",
    "split_policy_to_dict",
    "split_result_from_dict",
    "split_result_from_json_bytes",
    "split_result_to_dict",
    "validate_split_result",
]
