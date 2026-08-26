"""Tokenizer-bound length simulations. Unbound unless a pin is supplied.

Item 13.6 simulates token length and truncation only when a caller supplies
an exact tokenizer id, revision, max-token policy, and encode function.
Whitespace splitting is not a tokenizer. The report does not block seal.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from veriformis.construction import ConstructionResult, DatasetRecipe, DatasetRecord
from veriformis.datasets.curation import OBJECTIVE_FIELD_ROLES
from veriformis.datasets.models import CurationResult
from veriformis.datasets.splitting import SplitResult
from veriformis.errors import QualityReportError
from veriformis.identity import canonical_digest, lossless_json_bytes
from veriformis.quality.distributions import included_dataset_records
from veriformis.quality.leakage import report_leakage_checks
from veriformis.quality.report import (
    QualityFact,
    QualityPolicyDecision,
    QualityReport,
    assemble_quality_report,
)


TOKENIZER_UNBOUND = "unbound"
TOKENIZER_FACT_NAMES: tuple[str, ...] = (
    "tokenizer-id",
    "tokenizer-max-tokens",
    "tokenizer-revision",
    "tokenizer-status",
    "tokenizer-target-length-distribution",
    "tokenizer-truncation-count",
)


@dataclass(frozen=True)
class BoundTokenizerPin:
    pin_digest: str
    tokenizer_id: str
    tokenizer_revision: str
    max_tokens: int


def bound_tokenizer_pin(
    *,
    tokenizer_id: str,
    tokenizer_revision: str,
    max_tokens: int,
) -> BoundTokenizerPin:
    if not tokenizer_id.strip() or tokenizer_id.strip() != tokenizer_id:
        raise QualityReportError("tokenizer id must be a non-empty exact token")
    if not tokenizer_revision.strip() or tokenizer_revision.strip() != tokenizer_revision:
        raise QualityReportError("tokenizer revision must be a non-empty exact token")
    if type(max_tokens) is not int or max_tokens < 1:
        raise QualityReportError("tokenizer max_tokens must be a positive integer")
    payload = {
        "schema_version": "veriformis.bound-tokenizer-pin/v1",
        "max-tokens": max_tokens,
        "tokenizer-id": tokenizer_id,
        "tokenizer-revision": tokenizer_revision,
    }
    return BoundTokenizerPin(
        pin_digest=canonical_digest(payload),
        tokenizer_id=tokenizer_id,
        tokenizer_revision=tokenizer_revision,
        max_tokens=max_tokens,
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


def _target_text(record: DatasetRecord, target_names: tuple[str, ...]) -> str:
    by_name = {field.name: field.value for field in record.fields}
    missing = [name for name in target_names if name not in by_name]
    if missing:
        raise QualityReportError(
            f"included record {record.record_id} is missing objective field {missing[0]!r}"
        )
    return "".join(by_name[name] for name in target_names)


def _length_histogram(lengths: Sequence[int]) -> list[list[int]]:
    counts: dict[int, int] = {}
    for length in lengths:
        counts[length] = counts.get(length, 0) + 1
    return [[length, counts[length]] for length in sorted(counts)]


def report_tokenizer_simulations(
    *,
    recipe: DatasetRecipe,
    construction: ConstructionResult,
    curation: CurationResult,
    split: SplitResult,
    tokenizer: BoundTokenizerPin | None = None,
    encode: Callable[[str], int] | None = None,
) -> QualityReport:
    """Add tokenizer length facts. Refuse simulation without a bound pin."""
    if tokenizer is None:
        if encode is not None:
            raise QualityReportError("tokenizer encode requires a bound tokenizer pin")
        extra = (
            _text_fact("tokenizer-id", TOKENIZER_UNBOUND),
            _count_fact("tokenizer-max-tokens", 0),
            _text_fact("tokenizer-revision", TOKENIZER_UNBOUND),
            _text_fact("tokenizer-status", TOKENIZER_UNBOUND),
            _text_fact("tokenizer-target-length-distribution", []),
            _count_fact("tokenizer-truncation-count", 0),
        )
    else:
        if encode is None:
            raise QualityReportError("bound tokenizer pin requires an encode function")
        included = included_dataset_records(
            recipe=recipe,
            construction=construction,
            curation=curation,
            split=split,
        )
        _context_names, target_names = OBJECTIVE_FIELD_ROLES[recipe.objective.kind]
        lengths: list[int] = []
        truncated = 0
        for record in included:
            count = encode(_target_text(record, target_names))
            if type(count) is not int or count < 0:
                raise QualityReportError("tokenizer encode must return a non-negative int")
            lengths.append(count)
            if count > tokenizer.max_tokens:
                truncated += 1
        extra = (
            _text_fact("tokenizer-id", tokenizer.tokenizer_id),
            _count_fact("tokenizer-max-tokens", tokenizer.max_tokens),
            _text_fact("tokenizer-revision", tokenizer.tokenizer_revision),
            _text_fact("tokenizer-status", "simulated"),
            _text_fact(
                "tokenizer-target-length-distribution",
                _length_histogram(lengths),
            ),
            _count_fact("tokenizer-truncation-count", truncated),
        )
    if tuple(item.name for item in extra) != TOKENIZER_FACT_NAMES:
        raise QualityReportError("tokenizer facts must match the v1 name set")
    base = report_leakage_checks(
        recipe=recipe,
        construction=construction,
        curation=curation,
        split=split,
    )
    facts = tuple(sorted((*base.facts, *extra), key=lambda item: item.name))
    policy = tuple(
        sorted(
            (
                *base.policy_decisions,
                QualityPolicyDecision(
                    action="record-only",
                    name="tokenizer-record-only",
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
