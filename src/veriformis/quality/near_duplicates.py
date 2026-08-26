"""Named near-duplicate clusters. Not semantic identity. No silent deletes.

Algorithm ``veriformis.near-duplicate-ws-shingle-jaccard/v1``:
normalize by strip, whitespace collapse, and casefold; take overlapping
character 5-grams; score Jaccard similarity in parts-per-million integers;
cluster pairs at a recorded threshold. Curation ``near_duplicate_policy``
stays ``disabled``. The report does not delete rows or block seal.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from veriformis.construction import ConstructionResult, DatasetRecipe, DatasetRecord
from veriformis.datasets.curation import OBJECTIVE_FIELD_ROLES
from veriformis.datasets.models import CurationResult
from veriformis.datasets.splitting import SplitResult
from veriformis.errors import QualityReportError
from veriformis.identity import canonical_digest, lossless_json_bytes
from veriformis.quality.distributions import (
    included_dataset_records,
    report_dataset_distributions,
)
from veriformis.quality.report import (
    QualityFact,
    QualityPolicyDecision,
    QualityReport,
    assemble_quality_report,
)


NEAR_DUPLICATE_ALGORITHM_ID = "veriformis.near-duplicate-ws-shingle-jaccard/v1"
NEAR_DUPLICATE_SHINGLE_SIZE = 5
NEAR_DUPLICATE_CLUSTER_THRESHOLD_PPM = 800_000
NEAR_DUPLICATE_PREVIEW_THRESHOLDS_PPM: tuple[int, ...] = (
    500_000,
    800_000,
    900_000,
    990_000,
)
_WHITESPACE = re.compile(r"\s+")

NEAR_DUPLICATE_FACT_NAMES: tuple[str, ...] = (
    "near-duplicate-algorithm",
    "near-duplicate-cluster-count",
    "near-duplicate-cluster-threshold-ppm",
    "near-duplicate-clusters",
    "near-duplicate-member-count",
    "near-duplicate-shingle-size",
    "near-duplicate-threshold-preview",
)


def _count_fact(name: str, value: int) -> QualityFact:
    return QualityFact(
        bound_to="plan",
        integer_value=value,
        name=name,
        text_value=None,
    )


def _text_fact(name: str, value: object) -> QualityFact:
    return QualityFact(
        bound_to="plan",
        integer_value=None,
        name=name,
        text_value=lossless_json_bytes(value).decode("utf-8"),
    )


def _normalize(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip().casefold()


def _shingles(text: str) -> frozenset[str]:
    if not text:
        return frozenset()
    size = NEAR_DUPLICATE_SHINGLE_SIZE
    if len(text) <= size:
        return frozenset((text,))
    return frozenset(text[index : index + size] for index in range(len(text) - size + 1))


def _jaccard_ppm(left: frozenset[str], right: frozenset[str]) -> int:
    if not left and not right:
        return 1_000_000
    union = left | right
    if not union:
        return 0
    return (len(left & right) * 1_000_000) // len(union)


def _target_text(record: DatasetRecord, target_names: tuple[str, ...]) -> str:
    by_name = {field.name: field.value for field in record.fields}
    missing = [name for name in target_names if name not in by_name]
    if missing:
        raise QualityReportError(
            f"included record {record.record_id} is missing objective field {missing[0]!r}"
        )
    return "".join(by_name[name] for name in target_names)


def _union_find(record_ids: Sequence[str]):
    parent = {record_id: record_id for record_id in record_ids}

    def find(record_id: str) -> str:
        root = record_id
        while parent[root] != root:
            root = parent[root]
        current = record_id
        while parent[current] != root:
            nxt = parent[current]
            parent[current] = root
            current = nxt
        return root

    def union(left: str, right: str) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left == root_right:
            return
        if root_left < root_right:
            parent[root_right] = root_left
        else:
            parent[root_left] = root_right

    return find, union


def _clusters_at_threshold(
    *,
    record_ids: Sequence[str],
    similarities: Mapping[tuple[str, str], int],
    threshold_ppm: int,
) -> tuple[tuple[str, ...], ...]:
    find, union = _union_find(record_ids)
    for (left, right), ppm in similarities.items():
        if ppm >= threshold_ppm:
            union(left, right)
    grouped: dict[str, list[str]] = {}
    for record_id in record_ids:
        grouped.setdefault(find(record_id), []).append(record_id)
    clusters = []
    for members in grouped.values():
        if len(members) < 2:
            continue
        clusters.append(tuple(sorted(members)))
    return tuple(sorted(clusters))


def _pair_key(left: str, right: str) -> tuple[str, str]:
    return (left, right) if left < right else (right, left)


def report_near_duplicates(
    *,
    recipe: DatasetRecipe,
    construction: ConstructionResult,
    curation: CurationResult,
    split: SplitResult,
) -> QualityReport:
    """Add inspectable near-duplicate clusters to the distribution report."""
    base = report_dataset_distributions(
        recipe=recipe,
        construction=construction,
        curation=curation,
        split=split,
    )
    included = included_dataset_records(
        recipe=recipe,
        construction=construction,
        curation=curation,
        split=split,
    )
    _context_names, target_names = OBJECTIVE_FIELD_ROLES[recipe.objective.kind]
    record_ids = tuple(record.record_id for record in included)
    shingles = {
        record.record_id: _shingles(_normalize(_target_text(record, target_names)))
        for record in included
    }
    similarities: dict[tuple[str, str], int] = {}
    for index, left in enumerate(record_ids):
        for right in record_ids[index + 1 :]:
            similarities[_pair_key(left, right)] = _jaccard_ppm(
                shingles[left],
                shingles[right],
            )
    clusters = _clusters_at_threshold(
        record_ids=record_ids,
        similarities=similarities,
        threshold_ppm=NEAR_DUPLICATE_CLUSTER_THRESHOLD_PPM,
    )
    cluster_payload = []
    members: list[str] = []
    for cluster in clusters:
        members.extend(cluster)
        pairs = [
            [left, right, similarities[_pair_key(left, right)]]
            for left_index, left in enumerate(cluster)
            for right in cluster[left_index + 1 :]
        ]
        cluster_payload.append(
            {
                "cluster-id": canonical_digest(
                    {
                        "algorithm": NEAR_DUPLICATE_ALGORITHM_ID,
                        "record-ids": list(cluster),
                    }
                ),
                "pair-similarities-ppm": pairs,
                "record-ids": list(cluster),
            }
        )
    cluster_payload.sort(key=lambda item: item["cluster-id"])
    preview = {}
    for threshold in NEAR_DUPLICATE_PREVIEW_THRESHOLDS_PPM:
        preview_clusters = _clusters_at_threshold(
            record_ids=record_ids,
            similarities=similarities,
            threshold_ppm=threshold,
        )
        preview[str(threshold)] = {
            "cluster-count": len(preview_clusters),
            "member-count": sum(len(cluster) for cluster in preview_clusters),
        }
    extra = (
        _text_fact("near-duplicate-algorithm", NEAR_DUPLICATE_ALGORITHM_ID),
        _count_fact("near-duplicate-cluster-count", len(clusters)),
        _count_fact(
            "near-duplicate-cluster-threshold-ppm",
            NEAR_DUPLICATE_CLUSTER_THRESHOLD_PPM,
        ),
        _text_fact("near-duplicate-clusters", cluster_payload),
        _count_fact("near-duplicate-member-count", len(members)),
        _count_fact("near-duplicate-shingle-size", NEAR_DUPLICATE_SHINGLE_SIZE),
        _text_fact("near-duplicate-threshold-preview", preview),
    )
    names = tuple(item.name for item in extra)
    if names != NEAR_DUPLICATE_FACT_NAMES:
        raise QualityReportError("near-duplicate facts must match the v1 name set")
    facts = tuple(sorted((*base.facts, *extra), key=lambda item: item.name))
    policy = (
        QualityPolicyDecision(
            action="record-only",
            name="near-duplicate-disabled",
            threshold_id=None,
        ),
    )
    return assemble_quality_report(
        plan_id=base.plan_id,
        facts=facts,
        policy_decisions=policy,
    )
