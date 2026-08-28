"""Executable stepwise-supervision family. User-provided steps only."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from veriformis.errors import ConstructionError, SplitError
from veriformis.families.admission import FamilyAdmission, create_family_admission


STEPWISE_FAMILY_ID = "stepwise-supervision"
STEPWISE_OBJECTIVE = "stepwise"
STEPWISE_ROW_SCHEMA = "stepwise-trace"
STEPWISE_LOSS_POLICY = "final-step-only"
STEPWISE_GOAL_ID = "use-provided-steps"
STEPWISE_REPRESENTATION_ID = "prompt-and-steps"
STEPWISE_CONTRACT_VERSION = 1
STEPWISE_PAYLOAD_KEYS: tuple[str, ...] = ("prompt", "steps")


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


def stepwise_admission() -> FamilyAdmission:
    """Return the admitted pin. Loading it is not a mapping execute."""
    return create_family_admission(
        family_id=STEPWISE_FAMILY_ID,
        lifecycle="admitted",
        row_schema_ids=(STEPWISE_ROW_SCHEMA,),
        loss_policy_id=STEPWISE_LOSS_POLICY,
        evidence_kinds=("mapped_value",),
        leakage_grouping_keys=("shared-prompt", "source"),
        review_hook_ids=("stepwise-gap",),
        quality_hook_ids=(),
        generation_allowed=False,
        profile_eligibility=(),
    )


def refuse_document_source_steps() -> None:
    """Document-source construction cannot invent intermediate steps."""
    raise ConstructionError(
        "stepwise requires dataset-row mapped_value steps; "
        "document-source construction cannot invent stepwise traces"
    )


def normalize_steps(value: object) -> list[str]:
    """Admit one ordered user-provided step list. Empty or unproven steps fail."""
    if not isinstance(value, list) or len(value) < 2:
        raise ValueError(
            "stepwise-trace steps must be a list of at least two nonempty strings"
        )
    normalized: list[str] = []
    for index, step in enumerate(value):
        if type(step) is not str or step == "":
            raise ValueError(
                f"stepwise-trace step {index} must be a non-empty string"
            )
        normalized.append(step)
    return normalized


def imported_stepwise_groups(
    included: Sequence[object],
    raw_digests: Mapping[str, str],
) -> tuple[object, ...]:
    """Union imported stepwise rows by source and shared prompt."""
    from veriformis.mapping.finish import ImportedLeakageGroup, exact_imported_fingerprint

    ordered = tuple(sorted(included, key=lambda item: item.record_id))
    if not ordered:
        raise SplitError("stepwise split requires at least one included record")
    disjoint = _DisjointSet(len(ordered))
    token_owner: dict[tuple[str, str], int] = {}
    fingerprints: dict[str, str] = {}
    for index, record in enumerate(ordered):
        fields = {field.name: field.value for field in record.fields}
        prompt = fields.get("prompt")
        if type(prompt) is not str or prompt == "":
            raise SplitError(
                f"grouping key 'shared-prompt' is missing or empty for {record.record_id}"
            )
        fingerprint = exact_imported_fingerprint(record)
        fingerprints[record.record_id] = fingerprint
        digest = raw_digests.get(record.source_id)
        if type(digest) is not str or digest == "":
            raise SplitError(
                f"raw digest is missing for stepwise source {record.source_id}"
            )
        tokens = (
            ("exact-record-fingerprint", fingerprint),
            ("raw-sha256", digest),
            ("shared-prompt", prompt),
            ("source", record.source_id),
        )
        for token in tokens:
            owner = token_owner.setdefault(token, index)
            disjoint.union(index, owner)
    members_by_root: dict[int, list[object]] = {}
    for index, record in enumerate(ordered):
        members_by_root.setdefault(disjoint.find(index), []).append(record)
    groups = []
    for members in members_by_root.values():
        source_ids = tuple(sorted({item.source_id for item in members}))
        groups.append(
            ImportedLeakageGroup.create(
                record_ids=tuple(item.record_id for item in members),
                source_ids=source_ids,
                raw_sha256_values=tuple(
                    raw_digests[source_id] for source_id in source_ids
                ),
                exact_record_fingerprints=tuple(
                    sorted({fingerprints[item.record_id] for item in members})
                ),
            )
        )
    return tuple(sorted(groups, key=lambda item: item.group_id))
