"""Leakage facts against imported partition hints and digest-bound corpora.

Item 13.5 records exact-target overlap across split partitions, mismatches
between imported partition hints and realized assignments, and hits against
an optional digest-bound reference corpus. The report does not certify
absence of contamination and does not block seal.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from veriformis.construction import ConstructionResult, DatasetRecipe
from veriformis.datasets.models import CurationResult
from veriformis.datasets.splitting import Partition, SplitResult
from veriformis.errors import QualityReportError
from veriformis.identity import (
    canonical_digest,
    lossless_json_bytes,
    sha256_digest,
    validate_sha256,
)
from veriformis.quality.near_duplicates import report_near_duplicates_from_binding
from veriformis.quality.preview import (
    QualityPreviewBinding,
    bind_document_quality_preview,
    context_and_target_names,
    with_imported_partition_hints,
)
from veriformis.quality.report import (
    QualityFact,
    QualityPolicyDecision,
    QualityReport,
    assemble_quality_report,
)


LEAKAGE_FACT_NAMES: tuple[str, ...] = (
    "leakage-cross-partition-exact-target-count",
    "leakage-imported-partition-mismatch-count",
    "leakage-imported-partition-mismatches",
    "leakage-reference-corpus-digest",
    "leakage-reference-corpus-hit-count",
    "leakage-reference-corpus-hits",
)

UNBOUND_REFERENCE_CORPUS = "unbound"


@dataclass(frozen=True)
class BoundReferenceCorpus:
    """Exact target SHA-256 values bound by a canonical corpus digest."""

    corpus_digest: str
    target_sha256_values: tuple[str, ...]


def bound_reference_corpus(values: Sequence[str]) -> BoundReferenceCorpus:
    checked = tuple(sorted(set(values)))
    if not checked:
        raise QualityReportError("reference corpus cannot be empty")
    for value in checked:
        validate_sha256(value)
    return BoundReferenceCorpus(
        corpus_digest=canonical_digest(
            {
                "schema_version": "veriformis.bound-reference-corpus/v1",
                "target-sha256-values": checked,
            }
        ),
        target_sha256_values=checked,
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


def report_leakage_checks_from_binding(
    binding: QualityPreviewBinding,
    *,
    reference_corpus: BoundReferenceCorpus | None = None,
) -> QualityReport:
    """Add leakage facts to the near-duplicate quality report."""
    base = report_near_duplicates_from_binding(binding)
    included = binding.included
    _context_names, target_names = context_and_target_names(binding)
    assignment = {item.record_id: item.partition for item in binding.assignments}
    partitions_by_digest: dict[str, set[str]] = {}
    digest_by_record: dict[str, str] = {}
    for record in included:
        digest = sha256_digest(record.joined_values(target_names))
        digest_by_record[record.record_id] = digest
        partitions_by_digest.setdefault(digest, set()).add(assignment[record.record_id])
    cross = sum(len(parts) > 1 for parts in partitions_by_digest.values())
    hints = binding.imported_partition_hints
    mismatches: list[dict[str, str]] = []
    for record_id, hinted in sorted(hints.items()):
        if record_id not in assignment:
            raise QualityReportError(
                f"imported partition hint names unknown record {record_id}"
            )
        if hinted not in {"train", "evaluation"}:
            raise QualityReportError("imported partition hint is not a v1 partition")
        assigned = assignment[record_id]
        if hinted != assigned:
            mismatches.append(
                {
                    "assigned": assigned,
                    "hinted": hinted,
                    "record-id": record_id,
                }
            )
    if reference_corpus is None:
        corpus_digest: str | dict[str, str] = UNBOUND_REFERENCE_CORPUS
        hits: list[str] = []
    else:
        corpus_digest = reference_corpus.corpus_digest
        admitted = set(reference_corpus.target_sha256_values)
        hits = sorted(
            record_id
            for record_id, digest in digest_by_record.items()
            if digest in admitted
        )
    extra = (
        _count_fact("leakage-cross-partition-exact-target-count", cross),
        _count_fact("leakage-imported-partition-mismatch-count", len(mismatches)),
        _text_fact("leakage-imported-partition-mismatches", mismatches),
        _text_fact("leakage-reference-corpus-digest", corpus_digest),
        _count_fact("leakage-reference-corpus-hit-count", len(hits)),
        _text_fact("leakage-reference-corpus-hits", hits),
    )
    if tuple(item.name for item in extra) != LEAKAGE_FACT_NAMES:
        raise QualityReportError("leakage facts must match the v1 name set")
    facts = tuple(sorted((*base.facts, *extra), key=lambda item: item.name))
    policy = tuple(
        sorted(
            (
                *base.policy_decisions,
                QualityPolicyDecision(
                    action="record-only",
                    name="leakage-record-only",
                    threshold_id=None,
                ),
            ),
            key=lambda item: item.name,
        )
    )
    return assemble_quality_report(
        plan_id=base.plan_id,
        facts=facts,
        policy_decisions=policy,
        recommendations=base.recommendations,
    )


def report_leakage_checks(
    *,
    recipe: DatasetRecipe,
    construction: ConstructionResult,
    curation: CurationResult,
    split: SplitResult,
    imported_partition_hints: Mapping[str, Partition] | None = None,
    reference_corpus: BoundReferenceCorpus | None = None,
) -> QualityReport:
    """Add leakage facts to the near-duplicate quality report."""
    binding = with_imported_partition_hints(
        bind_document_quality_preview(
            recipe=recipe,
            construction=construction,
            curation=curation,
            split=split,
        ),
        imported_partition_hints,
    )
    return report_leakage_checks_from_binding(
        binding, reference_corpus=reference_corpus
    )
