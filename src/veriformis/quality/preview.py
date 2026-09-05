"""Private quality preview view. Never a DatasetRecord or construction result."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from veriformis.construction import (
    ConstructionResult,
    DatasetRecipe,
    DatasetRecord,
    IRFieldEvidence,
    RecordField,
)
from veriformis.datasets.curation import OBJECTIVE_FIELD_ROLES
from veriformis.datasets.models import CoverageLedger, CurationResult
from veriformis.datasets.splitting import SplitResult
from veriformis.errors import QualityReportError
from veriformis.mapping.finish import (
    FinishedImportPlan,
    ImportedCurationResult,
    ImportedSplitResult,
)
from veriformis.mapping.models import ImportedRecord
from veriformis.mapping.result import MappingRecipe, MappingResult


@dataclass(frozen=True)
class QualityPreviewField:
    name: str
    value: str
    language_token: str | None


@dataclass(frozen=True)
class QualityPreviewRecord:
    record_id: str
    source_ids: tuple[str, ...]
    objective_id: str
    fields: tuple[QualityPreviewField, ...]

    def field_map(self) -> dict[str, str]:
        return {field.name: field.value for field in self.fields}

    def require_values(self, names: tuple[str, ...]) -> tuple[str, ...]:
        by_name = self.field_map()
        missing = [name for name in names if name not in by_name]
        if missing:
            raise QualityReportError(
                f"included record {self.record_id} is missing objective field "
                f"{missing[0]!r}"
            )
        return tuple(by_name[name] for name in names)

    def joined_values(self, names: tuple[str, ...]) -> str:
        return "".join(self.require_values(names))


@dataclass(frozen=True)
class QualityPreviewDecision:
    status: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class QualityPreviewAssignment:
    record_id: str
    partition: str


@dataclass(frozen=True)
class QualityPreviewBinding:
    plan_id: str
    objective_kind: str
    row_schema: str
    included: tuple[QualityPreviewRecord, ...]
    decisions: tuple[QualityPreviewDecision, ...]
    coverage_ledger: CoverageLedger
    assignments: tuple[QualityPreviewAssignment, ...]
    realized_train_record_count: int
    realized_evaluation_record_count: int
    imported_partition_hints: Mapping[str, str]


def language_token_for_dataset_field(field: RecordField) -> str | None:
    if field.name == "language":
        return field.value
    evidence = field.evidence
    if not isinstance(evidence, IRFieldEvidence):
        return None
    tokens = [part for part in evidence.json_pointer.split("/") if part]
    if tokens and tokens[-1] == "language":
        return field.value
    return None


def preview_record_from_dataset(record: DatasetRecord) -> QualityPreviewRecord:
    return QualityPreviewRecord(
        record_id=record.record_id,
        source_ids=record.source_ids,
        objective_id=record.objective_id,
        fields=tuple(
            QualityPreviewField(
                name=field.name,
                value=field.value,
                language_token=language_token_for_dataset_field(field),
            )
            for field in record.fields
        ),
    )


def preview_record_from_imported(record: ImportedRecord) -> QualityPreviewRecord:
    return QualityPreviewRecord(
        record_id=record.record_id,
        source_ids=(record.source_id,),
        objective_id=record.objective_id,
        fields=tuple(
            QualityPreviewField(
                name=field.name,
                value=field.value,
                language_token=field.value if field.name == "language" else None,
            )
            for field in record.fields
        ),
    )


def _require_objective_kind(kind: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    try:
        return OBJECTIVE_FIELD_ROLES[kind]
    except KeyError as exc:
        raise QualityReportError(
            f"quality preview has no field roles for objective {kind!r}"
        ) from exc


def bind_document_quality_preview(
    *,
    recipe: DatasetRecipe,
    construction: ConstructionResult,
    curation: CurationResult,
    split: SplitResult,
    imported_partition_hints: Mapping[str, str] | None = None,
) -> QualityPreviewBinding:
    if recipe.recipe_id != construction.recipe_id:
        raise QualityReportError("distribution recipe does not match construction")
    if recipe.recipe_id != curation.recipe_id:
        raise QualityReportError("distribution recipe does not match curation")
    if construction.result_id != curation.construction_result_id:
        raise QualityReportError("distribution construction does not match curation")
    if construction.result_id != split.construction_result_id:
        raise QualityReportError("distribution construction does not match split")
    if curation.result_id != split.curation_result_id:
        raise QualityReportError("distribution curation does not match split")
    if curation.plan_id != split.plan_id:
        raise QualityReportError("distribution plan identities do not match")
    if tuple(sorted(curation.included_record_ids)) != split.input_record_ids:
        raise QualityReportError("split input does not match included records")
    _require_objective_kind(recipe.objective.kind)
    records_by_id: Mapping[str, DatasetRecord] = {
        record.record_id: record for record in construction.records
    }
    missing = [
        record_id
        for record_id in curation.included_record_ids
        if record_id not in records_by_id
    ]
    if missing:
        raise QualityReportError("included record is missing from construction")
    included = tuple(
        preview_record_from_dataset(records_by_id[record_id])
        for record_id in curation.included_record_ids
    )
    hints = dict(imported_partition_hints or {})
    return QualityPreviewBinding(
        plan_id=curation.plan_id,
        objective_kind=recipe.objective.kind,
        row_schema=recipe.target_row_schema,
        included=included,
        decisions=tuple(
            QualityPreviewDecision(
                status=decision.status,
                reason_codes=decision.reason_codes,
            )
            for decision in curation.decisions
        ),
        coverage_ledger=curation.coverage_ledger,
        assignments=tuple(
            QualityPreviewAssignment(
                record_id=item.record_id,
                partition=item.partition,
            )
            for item in split.assignments
        ),
        realized_train_record_count=split.realized_train_record_count,
        realized_evaluation_record_count=split.realized_evaluation_record_count,
        imported_partition_hints=MappingProxyType(hints),
    )


def bind_import_quality_preview(
    *,
    plan: FinishedImportPlan,
    recipe: MappingRecipe,
    mapping_result: MappingResult,
    curation: ImportedCurationResult,
    split: ImportedSplitResult,
) -> QualityPreviewBinding:
    if recipe.recipe_id != mapping_result.recipe_id:
        raise QualityReportError("quality recipe does not match mapping result")
    if recipe.recipe_id != curation.recipe_id:
        raise QualityReportError("quality recipe does not match imported curation")
    if plan.recipe_id != recipe.recipe_id:
        raise QualityReportError("quality import plan does not match mapping recipe")
    if mapping_result.result_id != curation.mapping_result_id:
        raise QualityReportError("quality mapping result does not match curation")
    if mapping_result.result_id != split.mapping_result_id:
        raise QualityReportError("quality mapping result does not match split")
    if mapping_result.result_id != plan.mapping_result_id:
        raise QualityReportError("quality mapping result does not match import plan")
    if curation.result_id != split.curation_result_id:
        raise QualityReportError("quality imported curation does not match split")
    if curation.plan_id != split.plan_id or plan.plan_id != curation.plan_id:
        raise QualityReportError("quality import plan identities do not match")
    if tuple(sorted(curation.included_record_ids)) != split.input_record_ids:
        raise QualityReportError("imported split input does not match included records")
    _require_objective_kind(recipe.objective_kind)
    records_by_id: Mapping[str, ImportedRecord] = {
        record.record_id: record for record in mapping_result.records
    }
    missing = [
        record_id
        for record_id in curation.included_record_ids
        if record_id not in records_by_id
    ]
    if missing:
        raise QualityReportError("included record is missing from mapping result")
    included = tuple(
        preview_record_from_imported(records_by_id[record_id])
        for record_id in curation.included_record_ids
    )
    assigned = {item.record_id for item in split.assignments}
    hints = {
        record.record_id: record.partition_hint
        for record in mapping_result.records
        if record.partition_hint is not None and record.record_id in assigned
    }
    return QualityPreviewBinding(
        plan_id=plan.plan_id,
        objective_kind=recipe.objective_kind,
        row_schema=recipe.row_schema,
        included=included,
        decisions=tuple(
            QualityPreviewDecision(
                status=decision.status,
                reason_codes=decision.reason_codes,
            )
            for decision in curation.decisions
        ),
        coverage_ledger=curation.coverage_ledger,
        assignments=tuple(
            QualityPreviewAssignment(
                record_id=item.record_id,
                partition=item.partition,
            )
            for item in split.assignments
        ),
        realized_train_record_count=split.realized_train_record_count,
        realized_evaluation_record_count=split.realized_evaluation_record_count,
        imported_partition_hints=MappingProxyType(hints),
    )


def context_and_target_names(
    binding: QualityPreviewBinding,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return _require_objective_kind(binding.objective_kind)


def with_imported_partition_hints(
    binding: QualityPreviewBinding,
    hints: Mapping[str, str] | None,
) -> QualityPreviewBinding:
    if hints is None:
        return binding
    return QualityPreviewBinding(
        plan_id=binding.plan_id,
        objective_kind=binding.objective_kind,
        row_schema=binding.row_schema,
        included=binding.included,
        decisions=binding.decisions,
        coverage_ledger=binding.coverage_ledger,
        assignments=binding.assignments,
        realized_train_record_count=binding.realized_train_record_count,
        realized_evaluation_record_count=binding.realized_evaluation_record_count,
        imported_partition_hints=MappingProxyType(dict(hints)),
    )
