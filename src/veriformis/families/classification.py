"""Executable explicit-label-classification family. User-provided labels only."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from veriformis.errors import ConstructionError, FamilyAdmissionError, SplitError
from veriformis.families.admission import FamilyAdmission, create_family_admission
from veriformis.identity import derive_id


CLASSIFICATION_FAMILY_ID = "explicit-label-classification"
CLASSIFICATION_OBJECTIVE = "explicit_label"
CLASSIFICATION_ROW_SCHEMA = "label-classification"
CLASSIFICATION_LOSS_POLICY = "label-only"
CLASSIFICATION_GOAL_ID = "classify-with-provided-labels"
CLASSIFICATION_REPRESENTATION_ID = "context-and-label"
CLASSIFICATION_CONTRACT_VERSION = 1
CLASSIFICATION_PAYLOAD_KEYS: tuple[str, ...] = ("context", "label", "annotator")


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


def classification_admission() -> FamilyAdmission:
    """Return the admitted pin. Loading it is not a mapping execute."""
    return create_family_admission(
        family_id=CLASSIFICATION_FAMILY_ID,
        lifecycle="admitted",
        row_schema_ids=(CLASSIFICATION_ROW_SCHEMA,),
        loss_policy_id=CLASSIFICATION_LOSS_POLICY,
        evidence_kinds=("mapped_value",),
        leakage_grouping_keys=("annotator", "source"),
        review_hook_ids=("label-conflict",),
        quality_hook_ids=("missing-label", "singleton-label-set"),
        generation_allowed=False,
        profile_eligibility=(),
    )


def label_set_id(labels: Sequence[str]) -> str:
    """Content-addressed identity over the unique provided labels."""
    unique = tuple(sorted(set(labels)))
    if not unique or any(type(item) is not str or item == "" for item in unique):
        raise FamilyAdmissionError("label set requires non-empty unique label strings")
    return derive_id("lset", {"labels": list(unique)})


def refuse_document_source_labels() -> None:
    """Document-source construction cannot invent classification labels."""
    raise ConstructionError(
        "explicit_label requires dataset-row mapped_value labels; "
        "document-source construction cannot invent labels"
    )


def imported_classification_groups(
    included: Sequence[object],
    raw_digests: Mapping[str, str],
) -> tuple[object, ...]:
    """Union imported classification rows by source and annotator."""
    from veriformis.mapping.finish import ImportedLeakageGroup, exact_imported_fingerprint
    ordered = tuple(sorted(included, key=lambda item: item.record_id))
    if not ordered:
        raise SplitError("classification split requires at least one included record")
    disjoint = _DisjointSet(len(ordered))
    token_owner: dict[tuple[str, str], int] = {}
    fingerprints: dict[str, str] = {}
    for index, record in enumerate(ordered):
        fields = {field.name: field.value for field in record.fields}
        annotator = fields.get("annotator")
        if type(annotator) is not str or annotator == "":
            raise SplitError(
                f"grouping key 'annotator' is missing or empty for {record.record_id}"
            )
        fingerprint = exact_imported_fingerprint(record)
        fingerprints[record.record_id] = fingerprint
        digest = raw_digests.get(record.source_id)
        if type(digest) is not str or digest == "":
            raise SplitError(
                f"raw digest is missing for classification source {record.source_id}"
            )
        tokens = (
            ("annotator", annotator),
            ("exact-record-fingerprint", fingerprint),
            ("raw-sha256", digest),
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
