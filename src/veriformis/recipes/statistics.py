"""Deterministic offline dataset statistics (no tokenizer dependency)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from veriformis.construction.models import ConstructionResult, DatasetRecipe
from veriformis.datasets.models import CurationResult
from veriformis.datasets.splitting import SplitResult
from veriformis.identity import canonical_digest


@dataclass(frozen=True)
class DatasetStatistics:
    """Content-addressed summary of construction or finished-stage counts."""

    schema_version: str
    statistics_id: str
    objective: str
    candidate_count: int
    accepted_record_count: int
    diagnostic_count: int
    included_record_count: int | None
    excluded_record_count: int | None
    quarantined_record_count: int | None
    train_record_count: int | None
    evaluation_record_count: int | None
    mean_target_characters: float | None
    max_target_characters: int | None
    min_target_characters: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "statistics_id": self.statistics_id,
            "objective": self.objective,
            "candidate_count": self.candidate_count,
            "accepted_record_count": self.accepted_record_count,
            "diagnostic_count": self.diagnostic_count,
            "included_record_count": self.included_record_count,
            "excluded_record_count": self.excluded_record_count,
            "quarantined_record_count": self.quarantined_record_count,
            "train_record_count": self.train_record_count,
            "evaluation_record_count": self.evaluation_record_count,
            "mean_target_characters": self.mean_target_characters,
            "max_target_characters": self.max_target_characters,
            "min_target_characters": self.min_target_characters,
        }


def measure_construction_statistics(
    recipe: DatasetRecipe,
    result: ConstructionResult,
) -> DatasetStatistics:
    lengths = _target_lengths(result.records)
    payload = {
        "schema_version": "veriformis.dataset-statistics/v1",
        "objective": recipe.objective.kind,
        "candidate_count": len(result.candidates),
        "accepted_record_count": len(result.records),
        "diagnostic_count": len(result.diagnostics),
        "included_record_count": None,
        "excluded_record_count": None,
        "quarantined_record_count": None,
        "train_record_count": None,
        "evaluation_record_count": None,
        "mean_target_characters": _mean(lengths),
        "max_target_characters": max(lengths) if lengths else None,
        "min_target_characters": min(lengths) if lengths else None,
    }
    return DatasetStatistics(
        statistics_id=canonical_digest(payload),
        **payload,
    )


def measure_finished_statistics(
    recipe: DatasetRecipe,
    result: ConstructionResult,
    curated: CurationResult,
    split_result: SplitResult,
) -> DatasetStatistics:
    lengths = _target_lengths(
        [
            record
            for record in result.records
            if record.record_id in set(curated.included_record_ids)
        ]
    )
    excluded = sum(1 for decision in curated.decisions if decision.status == "excluded")
    quarantined = sum(
        1 for decision in curated.decisions if decision.status == "quarantined"
    )
    payload = {
        "schema_version": "veriformis.dataset-statistics/v1",
        "objective": recipe.objective.kind,
        "candidate_count": len(result.candidates),
        "accepted_record_count": len(result.records),
        "diagnostic_count": len(result.diagnostics),
        "included_record_count": len(curated.included_record_ids),
        "excluded_record_count": excluded,
        "quarantined_record_count": quarantined,
        "train_record_count": split_result.realized_train_record_count,
        "evaluation_record_count": split_result.realized_evaluation_record_count,
        "mean_target_characters": _mean(lengths),
        "max_target_characters": max(lengths) if lengths else None,
        "min_target_characters": min(lengths) if lengths else None,
    }
    return DatasetStatistics(
        statistics_id=canonical_digest(payload),
        **payload,
    )


def _target_lengths(records: Sequence[Any]) -> list[int]:
    lengths: list[int] = []
    for record in records:
        target = None
        for field in record.fields:
            if field.name in {"text", "completion", "output", "fields", "target"}:
                target = field.value
        if target is None and record.fields:
            target = record.fields[-1].value
        if isinstance(target, str):
            lengths.append(len(target))
        elif isinstance(target, Mapping):
            lengths.append(len(str(target)))
    return lengths


def _mean(values: Sequence[int]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
