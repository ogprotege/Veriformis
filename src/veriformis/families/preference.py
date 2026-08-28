"""Executable preference-and-ranking family. User-provided chosen/rejected pairs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from veriformis.errors import ConstructionError, FamilyAdmissionError, SplitError
from veriformis.families.admission import FamilyAdmission, create_family_admission
from veriformis.identity import derive_id


PREFERENCE_FAMILY_ID = "preference-and-ranking"
PREFERENCE_OBJECTIVE = "preference_pair"
PREFERENCE_ROW_SCHEMA = "preference-pair"
PREFERENCE_LOSS_POLICY = "pair-supervision"
PREFERENCE_GOAL_ID = "prefer-chosen-over-rejected"
PREFERENCE_REPRESENTATION_ID = "prompt-chosen-rejected"
PREFERENCE_CONTRACT_VERSION = 1
PREFERENCE_PAYLOAD_KEYS: tuple[str, ...] = ("prompt", "chosen", "rejected")


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


def preference_admission() -> FamilyAdmission:
    """Return the admitted pin. Loading it is not a mapping execute."""
    return create_family_admission(
        family_id=PREFERENCE_FAMILY_ID,
        lifecycle="admitted",
        row_schema_ids=(PREFERENCE_ROW_SCHEMA,),
        loss_policy_id=PREFERENCE_LOSS_POLICY,
        evidence_kinds=("mapped_value",),
        leakage_grouping_keys=("shared-prompt", "source"),
        review_hook_ids=("preference-inconsistency",),
        quality_hook_ids=("ranking-tie", "unpaired-without-policy"),
        generation_allowed=False,
        profile_eligibility=(),
    )


def pair_set_id(pairs: Sequence[tuple[str, str, str]]) -> str:
    """Content-addressed identity over unique prompt/chosen/rejected triples."""
    unique = tuple(sorted(set(pairs)))
    if not unique or any(
        any(type(item) is not str or item == "" for item in triple) for triple in unique
    ):
        raise FamilyAdmissionError(
            "preference pair set requires non-empty unique prompt, chosen, and rejected strings"
        )
    return derive_id(
        "pset",
        {
            "pairs": [
                {"chosen": chosen, "prompt": prompt, "rejected": rejected}
                for prompt, chosen, rejected in unique
            ]
        },
    )


def refuse_document_source_preference() -> None:
    """Document-source construction cannot invent chosen or rejected completions."""
    raise ConstructionError(
        "preference_pair requires dataset-row mapped_value chosen and rejected "
        "strings; document-source construction cannot invent preference pairs"
    )


def imported_preference_groups(
    included: Sequence[object],
    raw_digests: Mapping[str, str],
) -> tuple[object, ...]:
    """Union imported preference rows by source and shared prompt."""
    from veriformis.mapping.finish import ImportedLeakageGroup, exact_imported_fingerprint

    ordered = tuple(sorted(included, key=lambda item: item.record_id))
    if not ordered:
        raise SplitError("preference split requires at least one included record")
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
                f"raw digest is missing for preference source {record.source_id}"
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
