"""Goal-specific preview v1: exactly what a record is and what receives loss.

The preview is a runtime-only, read-only view over a workspace at or beyond
the ``construct`` stage. It shows, per accepted record, the exact recovered
source spans and their derivation lineage, the context and target fields, the
row exactly as ``format`` would lower it for the selected representation, the
exact supervised span inside that row with its taxonomy loss policy, and the
curation decision when ``curate`` has run. Excluded records carry their
stable reason codes. The preview never mutates a workspace, calls a renderer,
or touches a destination, and it adds no persisted schema.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from veriformis.construction import ConstructionResult, DatasetRecipe, DatasetRecord
from veriformis.construction.pipeline import ConstructionInputs
from veriformis.datasets import CurationResult, SerializationPlan
from veriformis.datasets.curation import OBJECTIVE_FIELD_ROLES
from veriformis.datasets.serialization import render_record_payload
from veriformis.errors import GoalCatalogError
from veriformis.goals.catalog import (
    GoalRepresentation,
    goal_catalog,
    goal_for_objective,
    representation_for_row_schema,
    resolve_goal_instruction,
)
from veriformis.identity import lossless_json_bytes
from veriformis.taxonomy import loss_boundary

GOAL_PREVIEW_SCHEMA_ID = "veriformis.goal-preview/v1"
MAX_RECORD_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 256 * 1024
SAMPLE_POLICY = "first-accepted-record-per-primary-source"
RECORD_LIMIT_OMISSION = "exact-record-exceeds-preview-limit"
RESPONSE_BUDGET_OMISSION = "exact-record-exceeds-response-budget"
INSTRUCTION_REQUIRED_OMISSION = "operator-instruction-required"
CurationStatus = Literal["included", "excluded", "quarantined"]

SUPERVISED_ROW_KEY: dict[str, str] = {
    "text": "text",
    "prompt_completion": "completion",
    "instruction_output": "output",
    "messages": "messages[1].content",
}
CONTEXT_ROW_KEYS: dict[str, tuple[str, ...]] = {
    "text": (),
    "prompt_completion": ("prompt",),
    "instruction_output": ("instruction", "input"),
    "messages": ("messages[0].content",),
}

OmissionReason = Literal[
    "exact-record-exceeds-preview-limit",
    "exact-record-exceeds-response-budget",
    "operator-instruction-required",
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class GoalPreviewEvidence(_StrictModel):
    """One exact piece of recovered evidence behind one record field.

    ``source_text`` evidence names an exact character span of the recovered
    source stream; ``ir_field`` evidence names one strict-IR scalar by JSON
    pointer, whose exact encoded value is the field value itself.
    """

    field: str
    kind: Literal["source_text", "ir_field"]
    source_id: str
    region_id: str
    start: int | None
    end: int | None
    text_sha256: str
    excerpt: str | None
    derivation_kinds: tuple[str, ...]


class GoalPreviewSpan(_StrictModel):
    """The exact span, in Unicode code points, of the rendered row that receives loss."""

    row_key: str
    start: int
    end: int

    @model_validator(mode="after")
    def _ordered(self) -> "GoalPreviewSpan":
        if self.start != 0 or self.end < self.start:
            raise ValueError("supervised span must start at 0 and not end before it starts")
        return self


class GoalPreviewRecord(_StrictModel):
    record_id: str
    source_ids: tuple[str, ...]
    logical_paths: tuple[str, ...]
    chunk_ids: tuple[str, ...]
    pass_id: str
    constructor_id: str
    constructor_version: str
    context: dict[str, str] | None
    target: dict[str, str] | None
    rendered_row: dict[str, Any] | None
    context_row_keys: tuple[str, ...]
    supervised: GoalPreviewSpan
    recovered_source: tuple[GoalPreviewEvidence, ...]
    curation_status: CurationStatus | None
    curation_reason_codes: tuple[str, ...]
    omission_reason: OmissionReason | None
    exact_size_bytes: int


class GoalPreviewExclusion(_StrictModel):
    record_id: str
    source_ids: tuple[str, ...]
    status: CurationStatus
    reason_codes: tuple[str, ...]


class GoalPreviewDiagnostic(_StrictModel):
    code: str
    message: str
    pass_id: str
    source_ids: tuple[str, ...]
    chunk_ids: tuple[str, ...]


class GoalPreview(_StrictModel):
    schema_id: Literal["veriformis.goal-preview/v1"]
    goal_id: str
    title: str
    objective: str
    recipe_id: str
    recipe_library_id: str
    representation_id: str
    row_schema: str
    loss_policy: str
    loss_boundary: str
    supervised_region: str
    supervision_boundary: str
    not_this: tuple[str, ...]
    non_claims: tuple[str, ...]
    sample_policy: Literal["first-accepted-record-per-primary-source"]
    available_stages: tuple[str, ...]
    counts: dict[str, int]
    records: tuple[GoalPreviewRecord, ...]
    exclusions: tuple[GoalPreviewExclusion, ...]
    omitted_exclusion_count: int
    diagnostics: tuple[GoalPreviewDiagnostic, ...]
    omitted_diagnostic_count: int

    def transport_text(self) -> str:
        """The exact ASCII-safe text every surface emits; the bound applies to it."""
        return transport_text(self.model_dump(mode="json"))

    def canonical_bytes(self) -> bytes:
        return lossless_json_bytes(self.model_dump(mode="json"))


def transport_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)


def _transport_size(payload: Any) -> int:
    return len(transport_text(payload).encode("utf-8"))


def resolve_preview_representation(
    recipe: DatasetRecipe, representation_id: str | None
) -> GoalRepresentation:
    """Resolve the goal and representation from the recipe alone (no records)."""
    return _resolve_representation(recipe, representation_id)


def _resolve_representation(
    recipe: DatasetRecipe, representation_id: str | None
) -> GoalRepresentation:
    goal = goal_for_objective(recipe.objective.kind)
    if representation_id is None:
        return representation_for_row_schema(recipe.target_row_schema)
    rep = goal_catalog().representation(representation_id)
    if representation_id not in goal.compatible_representations:
        raise GoalCatalogError(
            f"goal {goal.goal_id!r} does not allow representation "
            f"{representation_id!r}; expected one of "
            f"{list(goal.compatible_representations)!r}"
        )
    return rep


def _recovered_source(
    record: DatasetRecord, sources: dict[str, Any]
) -> tuple[GoalPreviewEvidence, ...]:
    items: list[GoalPreviewEvidence] = []
    for field in record.fields:
        if field.evidence.kind == "ir_field":
            ir_evidence = field.evidence
            items.append(
                GoalPreviewEvidence(
                    field=field.name,
                    kind="ir_field",
                    source_id=ir_evidence.source_id,
                    region_id=f"ir:{ir_evidence.json_pointer}",
                    start=None,
                    end=None,
                    text_sha256=ir_evidence.output_sha256,
                    excerpt=field.value,
                    derivation_kinds=(ir_evidence.encoding,),
                )
            )
            continue
        evidence = field.evidence.evidence
        whole_kinds = tuple(step.kind for step in evidence.derivations)
        if evidence.join_derivation is not None:
            whole_kinds = ("join",) + whole_kinds
        for component in evidence.components:
            span = component.source_range
            source = sources[span.source_id]
            items.append(
                GoalPreviewEvidence(
                    field=field.name,
                    kind="source_text",
                    source_id=span.source_id,
                    region_id=span.region_id,
                    start=span.start,
                    end=span.end,
                    text_sha256=span.text_sha256,
                    excerpt=source.extracted_text[span.start : span.end],
                    derivation_kinds=tuple(step.kind for step in component.derivations)
                    + whole_kinds,
                )
            )
    return tuple(items)


def _redact(record: GoalPreviewRecord, reason: str) -> GoalPreviewRecord:
    return record.model_copy(
        update={
            "context": None,
            "target": None,
            "rendered_row": None,
            "recovered_source": tuple(
                item.model_copy(update={"excerpt": None})
                for item in record.recovered_source
            ),
            "omission_reason": reason,
        }
    )


def build_goal_preview(
    *,
    recipe: DatasetRecipe,
    result: ConstructionResult,
    inputs: ConstructionInputs,
    curation: CurationResult | None,
    representation_id: str | None = None,
    instruction: str | None = None,
    record_ids: tuple[str, ...] = (),
) -> GoalPreview:
    """Build the runtime-only preview from already-loaded, verified stage state."""
    goal = goal_for_objective(recipe.objective.kind)
    rep = _resolve_representation(recipe, representation_id)
    sources = {source.id: source for source in inputs.sources}
    by_id = {record.record_id: record for record in result.records}
    if record_ids:
        if len(set(record_ids)) != len(record_ids):
            raise GoalCatalogError("record ids must not repeat")
        unknown = [record_id for record_id in record_ids if record_id not in by_id]
        if unknown:
            raise GoalCatalogError(f"unknown accepted record id(s) {unknown!r}")
        selected = [by_id[record_id] for record_id in record_ids]
    else:
        seen: set[str] = set()
        selected = []
        for record in result.records:
            primary = record.source_ids[0]
            if primary in seen:
                continue
            seen.add(primary)
            selected.append(record)

    decisions = {} if curation is None else {d.record_id: d for d in curation.decisions}
    context_names, target_names = OBJECTIVE_FIELD_ROLES[recipe.objective.kind]
    resolved_instruction = resolve_goal_instruction(
        objective=recipe.objective.kind,
        row_schema=rep.row_schema,
        instruction=instruction,
    )
    plan = SerializationPlan.create(
        row_schema=rep.row_schema,
        instruction_text=resolved_instruction.instruction_text,
    )
    passes = {construction_pass.pass_id: construction_pass for construction_pass in recipe.passes}

    full_records: list[GoalPreviewRecord] = []
    for record in selected:
        construction_pass = passes[record.pass_id]
        fields = {field.name: field.value for field in record.fields}
        target_value = fields[target_names[0]]
        rendered = render_record_payload(plan, recipe, record)
        decision = decisions.get(record.record_id)
        entry = GoalPreviewRecord(
            record_id=record.record_id,
            source_ids=tuple(record.source_ids),
            logical_paths=tuple(sources[s].logical_path for s in record.source_ids),
            chunk_ids=tuple(record.chunk_ids),
            pass_id=record.pass_id,
            constructor_id=construction_pass.constructor_id,
            constructor_version=construction_pass.constructor_version,
            context={name: fields[name] for name in context_names if name in fields}
            if rep.row_schema != "text"
            else {},
            target={target_names[0]: target_value},
            rendered_row=rendered,
            context_row_keys=CONTEXT_ROW_KEYS[rep.row_schema],
            supervised=GoalPreviewSpan(
                row_key=SUPERVISED_ROW_KEY[rep.row_schema],
                start=0,
                end=len(target_value),
            ),
            recovered_source=_recovered_source(record, sources),
            curation_status=None if decision is None else decision.status,
            curation_reason_codes=() if decision is None else tuple(decision.reason_codes),
            omission_reason=None,
            exact_size_bytes=0,
        )
        full_records.append(
            entry.model_copy(update={"exact_size_bytes": _transport_size(entry.model_dump(mode="json"))})
        )

    all_exclusions: list[GoalPreviewExclusion] = []
    if curation is not None:
        for decision in curation.decisions:
            if decision.status == "included":
                continue
            record = by_id.get(decision.record_id)
            all_exclusions.append(
                GoalPreviewExclusion(
                    record_id=decision.record_id,
                    source_ids=() if record is None else tuple(record.source_ids),
                    status=decision.status,
                    reason_codes=tuple(decision.reason_codes),
                )
            )
    all_diagnostics = [
        GoalPreviewDiagnostic(
            code=diagnostic.code,
            message=diagnostic.message,
            pass_id=diagnostic.pass_id,
            source_ids=tuple(diagnostic.source_ids),
            chunk_ids=tuple(diagnostic.chunk_ids),
        )
        for diagnostic in result.diagnostics
    ]

    counts: dict[str, int] = {
        "accepted": len(result.records),
        "selected": len(selected),
        "omitted": 0,
        "diagnostics": len(result.diagnostics),
    }
    if curation is not None:
        for status in ("included", "excluded", "quarantined"):
            counts[status] = sum(1 for d in curation.decisions if d.status == status)

    def assemble(
        records: list[GoalPreviewRecord],
        exclusions: list[GoalPreviewExclusion],
        diagnostics: list[GoalPreviewDiagnostic],
    ) -> GoalPreview:
        omitted = sum(
            1
            for record in records
            if record.omission_reason in {RECORD_LIMIT_OMISSION, RESPONSE_BUDGET_OMISSION}
        )
        return GoalPreview(
            schema_id=GOAL_PREVIEW_SCHEMA_ID,
            goal_id=goal.goal_id,
            title=goal.title,
            objective=recipe.objective.kind,
            recipe_id=recipe.recipe_id,
            recipe_library_id=goal.recipe_library_id,
            representation_id=rep.representation_id,
            row_schema=rep.row_schema,
            loss_policy=rep.loss_policy,
            loss_boundary=loss_boundary(rep.loss_policy),
            supervised_region=rep.supervised_region,
            supervision_boundary=goal.supervision_boundary,
            not_this=goal.not_this,
            non_claims=goal.non_claims,
            sample_policy=SAMPLE_POLICY,
            available_stages=("construct",) + (() if curation is None else ("curate",)),
            counts={**counts, "omitted": omitted},
            records=tuple(records),
            exclusions=tuple(exclusions),
            omitted_exclusion_count=len(all_exclusions) - len(exclusions),
            diagnostics=tuple(diagnostics),
            omitted_diagnostic_count=len(all_diagnostics) - len(diagnostics),
        )

    def fits(preview: GoalPreview) -> bool:
        return _transport_size(preview.model_dump(mode="json")) <= MAX_RESPONSE_BYTES

    # Skeleton first: every record redacted, no exclusions, no diagnostics.
    # If even that cannot fit, fail closed with an exact reason.
    skeleton = [
        record
        if record.omission_reason == INSTRUCTION_REQUIRED_OMISSION
        and record.exact_size_bytes <= MAX_RECORD_BYTES
        else _redact(record, RESPONSE_BUDGET_OMISSION)
        for record in full_records
    ]
    if not fits(assemble(skeleton, [], [])):
        raise GoalCatalogError(
            f"goal preview of {len(selected)} records cannot fit the "
            f"{MAX_RESPONSE_BYTES}-byte response even when every record is "
            "omitted whole; select fewer records with explicit record ids"
        )
    records = list(skeleton)
    for index, record in enumerate(full_records):
        if record.exact_size_bytes > MAX_RECORD_BYTES:
            records[index] = _redact(record, RECORD_LIMIT_OMISSION)
            continue
        candidate = list(records)
        candidate[index] = record
        if fits(assemble(candidate, [], [])):
            records = candidate
    exclusions: list[GoalPreviewExclusion] = []
    for item in all_exclusions:
        if fits(assemble(records, exclusions + [item], [])):
            exclusions.append(item)
        else:
            break
    diagnostics: list[GoalPreviewDiagnostic] = []
    for item in all_diagnostics:
        if fits(assemble(records, exclusions, diagnostics + [item])):
            diagnostics.append(item)
        else:
            break
    preview = assemble(records, exclusions, diagnostics)
    assert fits(preview)
    return preview


__all__ = [
    "CONTEXT_ROW_KEYS",
    "GOAL_PREVIEW_SCHEMA_ID",
    "INSTRUCTION_REQUIRED_OMISSION",
    "MAX_RECORD_BYTES",
    "MAX_RESPONSE_BYTES",
    "RECORD_LIMIT_OMISSION",
    "RESPONSE_BUDGET_OMISSION",
    "SAMPLE_POLICY",
    "SUPERVISED_ROW_KEY",
    "GoalPreview",
    "GoalPreviewDiagnostic",
    "GoalPreviewEvidence",
    "GoalPreviewExclusion",
    "GoalPreviewRecord",
    "GoalPreviewSpan",
    "build_goal_preview",
    "transport_text",
]
