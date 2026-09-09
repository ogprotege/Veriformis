"""Preview-only advanced-family quality facts. They do not block seal."""

from __future__ import annotations

from collections import Counter

from veriformis.construction import ConstructionResult, DatasetRecipe
from veriformis.datasets.models import CurationResult
from veriformis.datasets.splitting import SplitResult
from veriformis.errors import QualityReportError
from veriformis.quality.preview import (
    QualityPreviewBinding,
    bind_document_quality_preview,
)
from veriformis.quality.report import QualityFact


FAMILY_HOOK_FACT_NAMES: tuple[str, ...] = (
    "family-missing-label-count",
    "family-ranking-tie-count",
    "family-singleton-label-set-count",
    "family-tool-role-gap-count",
    "family-unpaired-without-policy-count",
)


def _count_fact(name: str, value: int) -> QualityFact:
    return QualityFact(
        bound_to="plan",
        integer_value=value,
        name=name,
        text_value=None,
    )


def _fields(record: object) -> dict[str, str]:
    return {field.name: field.value for field in getattr(record, "fields")}


def family_hook_facts(records: tuple[object, ...]) -> tuple[QualityFact, ...]:
    """Count explicit advanced-family fields. Absent fields stay zero on SFT."""
    missing_label = 0
    unpaired = 0
    tool_gaps = 0
    labels: list[str] = []
    ranks: list[tuple[str, str]] = []
    for record in records:
        fields = _fields(record)
        if "label" in fields:
            if fields["label"] == "":
                missing_label += 1
            else:
                labels.append(fields["label"])
        if "feedback" in fields and "chosen" not in fields and "rejected" not in fields:
            unpaired += 1
        if fields.get("tool-name") and not fields.get("tool-role"):
            tool_gaps += 1
        if fields.get("tools") and "role" not in fields["tools"]:
            tool_gaps += 1
        item = fields.get("entity") or fields.get("shared-prompt") or fields.get("prompt")
        rank = fields.get("rank")
        if item and rank:
            ranks.append((item, rank))
    singleton = 1 if len(set(labels)) == 1 else 0
    rank_counts = Counter(ranks)
    ranking_ties = sum(count - 1 for count in rank_counts.values() if count > 1)
    facts = (
        _count_fact("family-missing-label-count", missing_label),
        _count_fact("family-ranking-tie-count", ranking_ties),
        _count_fact("family-singleton-label-set-count", singleton),
        _count_fact("family-tool-role-gap-count", tool_gaps),
        _count_fact("family-unpaired-without-policy-count", unpaired),
    )
    if tuple(item.name for item in facts) != FAMILY_HOOK_FACT_NAMES:
        raise QualityReportError("family-hook facts must match the v1 name set")
    return facts


def report_family_hooks_from_binding(
    binding: QualityPreviewBinding,
) -> tuple[QualityFact, ...]:
    return family_hook_facts(binding.included)


def report_family_hooks(
    *,
    recipe: DatasetRecipe,
    construction: ConstructionResult,
    curation: CurationResult,
    split: SplitResult,
) -> tuple[QualityFact, ...]:
    return report_family_hooks_from_binding(
        bind_document_quality_preview(
            recipe=recipe,
            construction=construction,
            curation=curation,
            split=split,
        )
    )
