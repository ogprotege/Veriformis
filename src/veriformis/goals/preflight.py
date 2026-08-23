"""Read-only compile preflight over one immutable capture of raw sources.

The response is runtime-only.  Preflight composes the same pure recovery,
cleaning, chunking, construction, curation, and split functions as the real
stages, but never creates a workspace or writes a destination.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from veriformis.chunkers import build_chunks
from veriformis.construction import (
    ConstructionInputs,
    IRArtifactInput,
    construct_dataset,
)
from veriformis.datasets import curate_dataset, split_dataset
from veriformis.diagnostics import validate_parse_report_locations
from veriformis.errors import (
    CompilePreflightError,
    GoalCatalogError,
    GoalInstructionError,
    InvalidSourceLocatorError,
    ParseError,
    SplitError,
    TaxonomyError,
    UnsupportedInputError,
    VeriformisError,
)
from veriformis.identity import (
    canonical_digest,
    derive_artifact_id,
    derive_source_id,
    lossless_json_bytes,
    sha256_digest,
)
from veriformis.ir import document_to_dict
from veriformis.parsers.dispatch import parse_captured_source
from veriformis.recipes.library import build_default_finished_plan, build_named_recipe
from veriformis.rules.cleaning import (
    cleaning_input_digest,
    plan_cleaning,
    replay_cleaning_plan,
)
from veriformis.rules.derivations import build_block_derivations
from veriformis.rules.library import select_rules
from veriformis.sources import capture_source_batch, safe_logical_locators
from veriformis.taxonomy import (
    INPUT_FAMILY_PARSERS,
    assert_compile_combination,
    input_family_for_suffix,
)

from .catalog import (
    CurationDefaults,
    goal_catalog,
    goal_catalog_json,
    require_goal_input_family,
    resolve_goal_instruction,
)
from .presets import (
    ConstructionSettings,
    ResolvedRecipeSettings,
    SegmentationSettings,
    preset_catalog,
    resolve_recipe_settings,
)

COMPILE_PREFLIGHT_SCHEMA_ID = "veriformis.compile-preflight/v1"
MAX_SOURCE_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 256 * 1024

EvaluatedThrough = Literal[
    "selection", "capture", "parse", "family", "construct", "curate", "split"
]
ParserStatus = Literal["not-evaluated", "complete", "degraded", "refused", "error"]
EvidenceStatus = Literal["not-evaluated", "available", "missing"]
SourceOmissionReason = Literal[
    "exact-source-exceeds-preflight-limit",
    "exact-source-exceeds-response-budget",
]
RefusalCode = Literal[
    "source-read-failed",
    "unsupported-input",
    "parser-refused",
    "goal-input-family-ineligible",
    "goal-evidence-unavailable",
    "curation-coverage-blocked",
    "evaluation-partition-unavailable",
]
IncompatibilityCode = Literal[
    "selection-required",
    "goal-invalid",
    "preset-incompatible",
    "representation-incompatible",
    "consumer-profile-incompatible",
    "override-invalid",
    "instruction-required",
    "instruction-not-applicable",
    "instruction-untruthful",
    "review-evidence-unavailable",
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class PreflightCodeCount(_StrictModel):
    code: str
    count: int


class PreflightParserDiagnostic(_StrictModel):
    diagnostic_id: str
    code: str
    severity: Literal["info", "warning", "error"]
    disposition: Literal["preserved", "normalized", "omitted", "refused"]
    loss_kind: Literal[
        "none", "presentation", "metadata", "structure", "text", "unknown"
    ]
    message: str


class PreflightRefusal(_StrictModel):
    code: RefusalCode
    detail_codes: tuple[str, ...]
    message: str


class PreflightSource(_StrictModel):
    logical_path: str
    source_id: str | None
    sha256: str | None
    size: int | None
    input_family: str | None
    parser_id: str | None
    parser_status: ParserStatus
    parser_eligible: bool
    goal_family_eligible: bool | None
    evidence_status: EvidenceStatus
    admitted: bool
    refusal_reasons: tuple[PreflightRefusal, ...]
    diagnostic_counts: tuple[PreflightCodeCount, ...]
    diagnostics: tuple[PreflightParserDiagnostic, ...]
    omitted_diagnostic_count: int
    omission_reason: SourceOmissionReason | None
    exact_size_bytes: int


class PreflightResolvedSelection(_StrictModel):
    goal_id: str
    preset_id: str
    representation_id: str
    objective: str
    row_schema: str
    recipe_library_id: str
    consumer_profile: str
    settings_digest: str
    cleaning_config_digest: str
    segmentation: SegmentationSettings
    construction: ConstructionSettings
    curation: CurationDefaults
    review_policy: Literal["none", "required"]


class PreflightSelection(_StrictModel):
    requested_goal: str | None
    requested_preset: str | None
    requested_representation: str | None
    instruction_supplied: bool
    resolved: PreflightResolvedSelection | None


class PreflightIncompatibility(_StrictModel):
    code: IncompatibilityCode
    fields: tuple[str, ...]
    message: str


class PreflightConstructionDiagnostic(_StrictModel):
    diagnostic_id: str
    code: str
    message: str
    pass_id: str
    source_ids: tuple[str, ...]
    chunk_ids: tuple[str, ...]


class PreflightExpectedExclusion(_StrictModel):
    stage: Literal["construct", "curate"]
    subject_id: str
    source_ids: tuple[str, ...]
    status: Literal["pending_review", "rejected", "excluded", "quarantined"]
    reason_codes: tuple[str, ...]


class PreflightReasonCount(_StrictModel):
    stage: Literal["construct", "curate"]
    status: Literal["pending_review", "rejected", "excluded", "quarantined"]
    reason_code: str
    count: int


class PreflightCoverageBlocker(_StrictModel):
    source_id: str
    blocker_codes: tuple[str, ...]


class PreflightLimitation(_StrictModel):
    code: str
    message: str
    source_ids: tuple[str, ...]


class PreflightCounts(_StrictModel):
    source_count: int
    parser_eligible_source_count: int
    family_eligible_source_count: int
    evidence_eligible_source_count: int
    admitted_source_count: int
    candidate_count: int
    record_count: int
    pending_review_count: int
    included_count: int
    excluded_count: int
    quarantined_count: int


class CompilePreflight(_StrictModel):
    schema_id: Literal["veriformis.compile-preflight/v1"]
    request_digest: str
    captured_source_digest: str | None
    evaluated_through: EvaluatedThrough
    admitted: bool
    selection: PreflightSelection
    counts: PreflightCounts
    sources: tuple[PreflightSource, ...]
    incompatibilities: tuple[PreflightIncompatibility, ...]
    missing_evidence: tuple[PreflightConstructionDiagnostic, ...]
    expected_exclusion_counts: tuple[PreflightReasonCount, ...]
    expected_exclusions: tuple[PreflightExpectedExclusion, ...]
    omitted_expected_exclusion_count: int
    coverage_blockers: tuple[PreflightCoverageBlocker, ...]
    known_limitations: tuple[PreflightLimitation, ...]
    omitted_diagnostic_count: int

    @model_validator(mode="after")
    def _truthful_admission(self) -> "CompilePreflight":
        blockers = (
            bool(self.incompatibilities)
            or bool(self.coverage_blockers)
            or any(not source.admitted for source in self.sources)
        )
        if self.admitted == blockers:
            raise ValueError("preflight admitted flag does not match its blockers")
        if self.counts.source_count != len(self.sources):
            raise ValueError("preflight source_count does not match sources")
        return self

    def transport_text(self) -> str:
        return _transport_text(self.model_dump(mode="json"))

    def canonical_bytes(self) -> bytes:
        return lossless_json_bytes(self.model_dump(mode="json"))


def _transport_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True)


def _transport_size(value: Any) -> int:
    return len(_transport_text(value).encode("utf-8"))


def _request_digest(logical_paths: tuple[str, ...], values: dict[str, Any]) -> str:
    return canonical_digest(
        {
            "schema_id": COMPILE_PREFLIGHT_SCHEMA_ID,
            "goal_catalog_sha256": sha256_digest(goal_catalog_json()),
            "logical_paths": list(logical_paths),
            "selection": values,
        }
    )


def _parser_id_for_suffix(*, logical_path: str, input_family: str) -> str:
    parsers = INPUT_FAMILY_PARSERS[input_family]
    suffix_parser = Path(logical_path).suffix.lower().lstrip(".")
    return suffix_parser if suffix_parser in parsers else parsers[0]


def _limitations() -> tuple[PreflightLimitation, ...]:
    items = [
        PreflightLimitation(
            code="point-in-time-source-capture",
            message=(
                "Preflight binds one captured byte snapshot; compile recaptures sources "
                "and may observe later changes."
            ),
            source_ids=(),
        ),
        PreflightLimitation(
            code="not-a-publication-guarantee",
            message=(
                "Admission does not replace compile replay, validation, sealing, or "
                "independent verification."
            ),
            source_ids=(),
        ),
        PreflightLimitation(
            code="no-fine-tuning-suitability-judgment",
            message="Preflight does not decide whether fine-tuning is appropriate.",
            source_ids=(),
        ),
        PreflightLimitation(
            code="no-trainer-compatibility",
            message="A compatible compile profile is not a trainer compatibility claim.",
            source_ids=(),
        ),
        PreflightLimitation(
            code="no-generated-text",
            message="Preflight and compile do not generate source or target text.",
            source_ids=(),
        ),
        PreflightLimitation(
            code="no-invented-target",
            message="Preflight and compile do not invent a target absent from the source.",
            source_ids=(),
        ),
        PreflightLimitation(
            code="no-quality-intelligence",
            message=(
                "Preflight does not perform Phase 13 distribution, near-duplicate, "
                "PII, secret, contamination, or tokenizer analysis."
            ),
            source_ids=(),
        ),
    ]
    return tuple(items)


def _empty_counts(source_count: int = 0) -> PreflightCounts:
    return PreflightCounts(
        source_count=source_count,
        parser_eligible_source_count=0,
        family_eligible_source_count=0,
        evidence_eligible_source_count=0,
        admitted_source_count=0,
        candidate_count=0,
        record_count=0,
        pending_review_count=0,
        included_count=0,
        excluded_count=0,
        quarantined_count=0,
    )


def _selection_precheck(
    *,
    goal: str | None,
    preset: str | None,
    representation: str | None,
    consumer_profile: str | None,
) -> PreflightIncompatibility | None:
    """Classify selection fields from their typed role, never error prose."""
    if goal is None and preset is None:
        return PreflightIncompatibility(
            code="selection-required",
            fields=("goal", "preset"),
            message="select a goal or preset",
        )

    selected_preset = None
    if preset is not None:
        try:
            selected_preset = preset_catalog().preset(preset)
        except GoalCatalogError as exc:
            return PreflightIncompatibility(
                code="preset-incompatible",
                fields=("preset",),
                message=exc.message,
            )
        if goal is not None and goal != selected_preset.goal_id:
            return PreflightIncompatibility(
                code="preset-incompatible",
                fields=("goal", "preset"),
                message=(
                    f"preset {preset!r} belongs to goal "
                    f"{selected_preset.goal_id!r}, not {goal!r}"
                ),
            )
        goal = selected_preset.goal_id

    assert goal is not None
    catalog = goal_catalog()
    try:
        goal_entry = catalog.goal(goal)
    except GoalCatalogError as exc:
        return PreflightIncompatibility(
            code="goal-invalid",
            fields=("goal",),
            message=exc.message,
        )

    if representation is None:
        if selected_preset is None:
            selected_preset = preset_catalog().safe_preset(goal)
        representation = selected_preset.representation_id
    try:
        representation_entry = catalog.representation(representation)
    except GoalCatalogError as exc:
        return PreflightIncompatibility(
            code="representation-incompatible",
            fields=("representation",),
            message=exc.message,
        )
    if representation not in goal_entry.compatible_representations:
        return PreflightIncompatibility(
            code="representation-incompatible",
            fields=("representation",),
            message=(
                f"goal {goal!r} does not allow representation {representation!r}; "
                f"expected one of {list(goal_entry.compatible_representations)!r}"
            ),
        )

    if consumer_profile is not None:
        try:
            assert_compile_combination(
                goal_entry.objective,
                representation_entry.row_schema,
                profile=consumer_profile,
            )
        except TaxonomyError as exc:
            return PreflightIncompatibility(
                code="consumer-profile-incompatible",
                fields=("consumer_profile",),
                message=exc.message,
            )
    return None


def _initial_source(logical_path: str) -> PreflightSource:
    return PreflightSource(
        logical_path=logical_path,
        source_id=None,
        sha256=None,
        size=None,
        input_family=None,
        parser_id=None,
        parser_status="not-evaluated",
        parser_eligible=False,
        goal_family_eligible=None,
        evidence_status="not-evaluated",
        admitted=False,
        refusal_reasons=(),
        diagnostic_counts=(),
        diagnostics=(),
        omitted_diagnostic_count=0,
        omission_reason=None,
        exact_size_bytes=0,
    )


def _set_exact_size(source: PreflightSource) -> PreflightSource:
    """Set the transport size to a stable fixed point including that field."""
    sized = source
    for _ in range(8):
        observed = _transport_size(sized.model_dump(mode="json"))
        if observed == sized.exact_size_bytes:
            return sized
        sized = sized.model_copy(update={"exact_size_bytes": observed})
    raise CompilePreflightError(
        f"source detail size did not stabilize for {source.logical_path!r}"
    )


def _source_with_size(source: PreflightSource) -> PreflightSource:
    if source.exact_size_bytes != 0:
        raise CompilePreflightError(
            f"source detail for {source.logical_path!r} was bounded more than once"
        )
    source = _set_exact_size(source)
    if source.exact_size_bytes <= MAX_SOURCE_BYTES:
        return source
    redacted = source.model_copy(
        update={
            "diagnostics": (),
            "omitted_diagnostic_count": (
                source.omitted_diagnostic_count + len(source.diagnostics)
            ),
            "omission_reason": "exact-source-exceeds-preflight-limit",
        }
    )
    if _transport_size(redacted.model_dump(mode="json")) > MAX_SOURCE_BYTES:
        raise CompilePreflightError(
            f"mandatory source verdict for {source.logical_path!r} exceeds the "
            f"{MAX_SOURCE_BYTES}-byte source limit"
        )
    return redacted


def _sources_with_sizes(
    sources: list[PreflightSource] | tuple[PreflightSource, ...],
) -> tuple[PreflightSource, ...]:
    """Finalize each source verdict exactly once after its evidence is complete."""
    return tuple(_source_with_size(source) for source in sources)


def _assemble_bounded(preflight: CompilePreflight) -> CompilePreflight:
    if _transport_size(preflight.model_dump(mode="json")) <= MAX_RESPONSE_BYTES:
        return preflight
    omitted_diagnostics = preflight.omitted_diagnostic_count + len(
        preflight.missing_evidence
    )
    reduced_sources = tuple(
        source.model_copy(
            update={
                "diagnostics": (),
                "omitted_diagnostic_count": (
                    source.omitted_diagnostic_count + len(source.diagnostics)
                ),
                "omission_reason": (
                    source.omission_reason or "exact-source-exceeds-response-budget"
                ),
            }
        )
        if source.diagnostics
        else source
        for source in preflight.sources
    )
    reduced = preflight.model_copy(
        update={
            "sources": reduced_sources,
            "missing_evidence": (),
            "expected_exclusions": (),
            "omitted_expected_exclusion_count": (
                preflight.omitted_expected_exclusion_count
                + len(preflight.expected_exclusions)
            ),
            "omitted_diagnostic_count": omitted_diagnostics,
        }
    )
    if _transport_size(reduced.model_dump(mode="json")) > MAX_RESPONSE_BYTES:
        raise CompilePreflightError(
            f"mandatory compile preflight skeleton exceeds the "
            f"{MAX_RESPONSE_BYTES}-byte response limit; select fewer sources"
        )
    return reduced


def build_compile_preflight(
    paths: list[Path],
    *,
    source_root: Path | None = None,
    goal: str | None = None,
    preset: str | None = None,
    representation: str | None = None,
    instruction: str | None = None,
    rules: str = "",
    custom: str = "",
    strategy: str | None = None,
    size: int | None = None,
    overlap: int | None = None,
    split_ratio_ppm: int | None = None,
    require_review: bool | None = None,
    consumer_profile: str | None = None,
    minimum_target_characters: int | None = None,
    balance_mode: str | None = None,
    maximum_records_per_primary_source: int | None = None,
    evaluation_ratio_ppm: int | None = None,
    evaluation_required: bool | None = None,
    split_seed: str | None = None,
    review_policy: str | None = None,
) -> CompilePreflight:
    """Build one complete, bounded preflight report without any filesystem write."""
    requested_logical_paths = safe_logical_locators(
        paths,
        source_root=source_root,
    )
    request_values = {
        "goal": goal,
        "preset": preset,
        "representation": representation,
        "instruction_sha256": None
        if instruction is None
        else sha256_digest(instruction),
        "effective_instruction_sha256": None,
        "rules": rules,
        "custom": custom,
        "strategy": strategy,
        "size": size,
        "overlap": overlap,
        "split_ratio_ppm": split_ratio_ppm,
        "require_review": require_review,
        "consumer_profile": consumer_profile,
        "minimum_target_characters": minimum_target_characters,
        "balance_mode": balance_mode,
        "maximum_records_per_primary_source": maximum_records_per_primary_source,
        "evaluation_ratio_ppm": evaluation_ratio_ppm,
        "evaluation_required": evaluation_required,
        "split_seed": split_seed,
        "review_policy": review_policy,
    }
    request_digest = _request_digest(requested_logical_paths, request_values)
    selection = PreflightSelection(
        requested_goal=goal,
        requested_preset=preset,
        requested_representation=representation,
        instruction_supplied=instruction is not None,
        resolved=None,
    )
    incompatibilities: list[PreflightIncompatibility] = []
    resolved_instruction: str | None = None
    clean_config: dict[str, Any] | None = None
    settings: ResolvedRecipeSettings | None = None
    selection_problem = _selection_precheck(
        goal=goal,
        preset=preset,
        representation=representation,
        consumer_profile=consumer_profile,
    )
    if selection_problem is not None:
        incompatibilities.append(selection_problem)
    else:
        try:
            _, clean_config = select_rules(rules, custom)
        except (VeriformisError, ValueError, TypeError) as exc:
            incompatibilities.append(
                PreflightIncompatibility(
                    code="override-invalid",
                    fields=("rules", "custom"),
                    message=getattr(exc, "message", str(exc)),
                )
            )
        if clean_config is not None:
            try:
                settings = resolve_recipe_settings(
                    goal=goal,
                    preset=preset,
                    representation=representation,
                    strategy=strategy,
                    size=size,
                    overlap=overlap,
                    split_ratio_ppm=split_ratio_ppm,
                    require_review=require_review,
                    consumer_profile=consumer_profile,
                    minimum_target_characters=minimum_target_characters,
                    balance_mode=balance_mode,
                    maximum_records_per_primary_source=(
                        maximum_records_per_primary_source
                    ),
                    evaluation_ratio_ppm=evaluation_ratio_ppm,
                    evaluation_required=evaluation_required,
                    split_seed=split_seed,
                    review_policy=review_policy,
                )
            except (GoalCatalogError, VeriformisError, ValueError, TypeError) as exc:
                incompatibilities.append(
                    PreflightIncompatibility(
                        code="override-invalid",
                        fields=("overrides",),
                        message=getattr(exc, "message", str(exc)),
                    )
                )
    if settings is not None and clean_config is not None:
        chosen_preset = (
            preset or preset_catalog().safe_preset(settings.goal_id).preset_id
        )
        selection = selection.model_copy(
            update={
                "resolved": PreflightResolvedSelection(
                    goal_id=settings.goal_id,
                    preset_id=chosen_preset,
                    representation_id=settings.representation_id,
                    objective=settings.objective,
                    row_schema=settings.row_schema,
                    recipe_library_id=settings.recipe_library_id,
                    consumer_profile=settings.construction.consumer_profile,
                    settings_digest=settings.settings_digest,
                    cleaning_config_digest=canonical_digest(clean_config),
                    segmentation=settings.segmentation,
                    construction=settings.construction,
                    curation=settings.curation,
                    review_policy=settings.review_policy,
                )
            }
        )
        try:
            resolved_instruction = resolve_goal_instruction(
                objective=settings.objective,
                row_schema=settings.row_schema,
                instruction=instruction,
            ).instruction_text
            request_values["effective_instruction_sha256"] = (
                None
                if resolved_instruction is None
                else sha256_digest(resolved_instruction)
            )
            request_digest = _request_digest(requested_logical_paths, request_values)
        except GoalInstructionError as exc:
            incompatibility_code: IncompatibilityCode = (
                "instruction-not-applicable"
                if exc.reason_codes == ("instruction-not-applicable",)
                else "instruction-untruthful"
            )
            incompatibilities.append(
                PreflightIncompatibility(
                    code=incompatibility_code,
                    fields=("instruction", "representation"),
                    message=exc.message,
                )
            )
        if settings.construction.require_review:
            incompatibilities.append(
                PreflightIncompatibility(
                    code="review-evidence-unavailable",
                    fields=("require_review", "review_policy"),
                    message=(
                        "the current compile surfaces supply no review evidence; "
                        "a review-required recipe cannot produce dataset records"
                    ),
                )
            )

    limitations = _limitations()
    if incompatibilities:
        return _assemble_bounded(
            CompilePreflight(
                schema_id=COMPILE_PREFLIGHT_SCHEMA_ID,
                request_digest=request_digest,
                captured_source_digest=None,
                evaluated_through="selection",
                admitted=False,
                selection=selection,
                counts=_empty_counts(),
                sources=(),
                incompatibilities=tuple(incompatibilities),
                missing_evidence=(),
                expected_exclusion_counts=(),
                expected_exclusions=(),
                omitted_expected_exclusion_count=0,
                coverage_blockers=(),
                known_limitations=limitations,
                omitted_diagnostic_count=0,
            )
        )
    assert settings is not None and clean_config is not None

    if not paths:
        incompatibility = PreflightIncompatibility(
            code="override-invalid",
            fields=("paths",),
            message="compile preflight requires at least one raw source path",
        )
        return _assemble_bounded(
            CompilePreflight(
                schema_id=COMPILE_PREFLIGHT_SCHEMA_ID,
                request_digest=request_digest,
                captured_source_digest=None,
                evaluated_through="capture",
                admitted=False,
                selection=selection,
                counts=_empty_counts(),
                sources=(),
                incompatibilities=(incompatibility,),
                missing_evidence=(),
                expected_exclusion_counts=(),
                expected_exclusions=(),
                omitted_expected_exclusion_count=0,
                coverage_blockers=(),
                known_limitations=limitations,
                omitted_diagnostic_count=0,
            )
        )

    try:
        source_captures = capture_source_batch(paths, source_root=source_root)
    except InvalidSourceLocatorError as exc:
        entries = _sources_with_sizes(
            [
                _initial_source(logical_path).model_copy(
                    update={
                        "parser_status": "error",
                        "refusal_reasons": (
                            PreflightRefusal(
                                code="source-read-failed",
                                detail_codes=(exc.code,),
                                message=exc.message,
                            ),
                        ),
                    }
                )
                for logical_path in safe_logical_locators(
                    paths,
                    source_root=source_root,
                )
            ]
        )
        return _assemble_bounded(
            CompilePreflight(
                schema_id=COMPILE_PREFLIGHT_SCHEMA_ID,
                request_digest=request_digest,
                captured_source_digest=None,
                evaluated_through="capture",
                admitted=False,
                selection=selection,
                counts=_empty_counts(len(entries)),
                sources=entries,
                incompatibilities=(),
                missing_evidence=(),
                expected_exclusion_counts=(),
                expected_exclusions=(),
                omitted_expected_exclusion_count=0,
                coverage_blockers=(),
                known_limitations=limitations,
                omitted_diagnostic_count=0,
            )
        )

    captured: list[tuple[Path, str, bytes]] = []
    source_entries: list[PreflightSource] = []
    for source_capture in source_captures:
        path = source_capture.path
        logical = source_capture.logical_path
        if source_capture.error is not None:
            exc = source_capture.error
            detail_code = getattr(exc, "code", type(exc).__name__)
            source_entries.append(
                _initial_source(logical).model_copy(
                    update={
                        "parser_status": "error",
                        "refusal_reasons": (
                            PreflightRefusal(
                                code="source-read-failed",
                                detail_codes=(detail_code,),
                                message=getattr(exc, "message", str(exc)),
                            ),
                        ),
                    }
                )
            )
        else:
            assert source_capture.raw_bytes is not None
            raw = source_capture.raw_bytes
            captured.append((path, logical, raw))
    if source_entries:
        for _, logical, raw in captured:
            raw_sha256 = sha256_digest(raw)
            source_entries.append(
                _initial_source(logical).model_copy(
                    update={
                        "source_id": derive_source_id(logical, raw_sha256),
                        "sha256": raw_sha256,
                        "size": len(raw),
                    }
                )
            )
        source_entries.sort(key=lambda item: item.logical_path)
        bounded_sources = _sources_with_sizes(source_entries)
        return _assemble_bounded(
            CompilePreflight(
                schema_id=COMPILE_PREFLIGHT_SCHEMA_ID,
                request_digest=request_digest,
                captured_source_digest=None,
                evaluated_through="capture",
                admitted=False,
                selection=selection,
                counts=_empty_counts(len(source_entries)),
                sources=bounded_sources,
                incompatibilities=(),
                missing_evidence=(),
                expected_exclusion_counts=(),
                expected_exclusions=(),
                omitted_expected_exclusion_count=0,
                coverage_blockers=(),
                known_limitations=limitations,
                omitted_diagnostic_count=0,
            )
        )

    capture_digest = canonical_digest(
        [
            {"logical_path": logical, "sha256": sha256_digest(raw), "size": len(raw)}
            for _, logical, raw in sorted(captured, key=lambda item: item[1])
        ]
    )
    parse_results = []
    parse_blocked = False
    family_rejected = False
    for path, logical, raw in captured:
        base = _initial_source(logical)
        try:
            family = input_family_for_suffix(Path(logical).suffix)
        except TaxonomyError as exc:
            source_entries.append(
                base.model_copy(
                    update={
                        "sha256": sha256_digest(raw),
                        "size": len(raw),
                        "parser_status": "refused",
                        "refusal_reasons": (
                            PreflightRefusal(
                                code="unsupported-input",
                                detail_codes=(exc.code,),
                                message=exc.message,
                            ),
                        ),
                    }
                )
            )
            parse_blocked = True
            continue
        expected_parser_id = _parser_id_for_suffix(
            logical_path=logical,
            input_family=family,
        )
        try:
            result = parse_captured_source(path, logical_path=logical, raw_bytes=raw)
        except (UnsupportedInputError, ParseError, ValueError, TypeError) as exc:
            code = getattr(exc, "code", "parse-error")
            source_entries.append(
                base.model_copy(
                    update={
                        "sha256": sha256_digest(raw),
                        "size": len(raw),
                        "input_family": family,
                        "parser_id": expected_parser_id,
                        "parser_status": "error",
                        "refusal_reasons": (
                            PreflightRefusal(
                                code=(
                                    "unsupported-input"
                                    if isinstance(exc, UnsupportedInputError)
                                    else "parser-refused"
                                ),
                                detail_codes=(code,),
                                message=getattr(exc, "message", str(exc)),
                            ),
                        ),
                    }
                )
            )
            parse_blocked = True
            continue
        try:
            validate_parse_report_locations(result.diagnostics, raw)
        except (ParseError, ValueError, TypeError) as exc:
            source_entries.append(
                base.model_copy(
                    update={
                        "source_id": result.source.id,
                        "sha256": result.source.sha256,
                        "size": result.source.size,
                        "input_family": family,
                        "parser_id": result.source.parser,
                        "parser_status": "error",
                        "refusal_reasons": (
                            PreflightRefusal(
                                code="parser-refused",
                                detail_codes=("parse-diagnostic-invalid",),
                                message=str(exc),
                            ),
                        ),
                    }
                )
            )
            parse_blocked = True
            continue
        diagnostics = tuple(
            PreflightParserDiagnostic(
                diagnostic_id=item.diagnostic_id,
                code=item.code,
                severity=item.severity,
                disposition=item.disposition,
                loss_kind=item.loss_kind,
                message=item.message,
            )
            for item in result.diagnostics.diagnostics
        )
        counts = Counter(item.code for item in diagnostics)
        code_counts = tuple(
            PreflightCodeCount(code=code, count=count)
            for code, count in sorted(counts.items())
        )
        if result.diagnostics.status == "refused":
            error_items = tuple(
                item for item in diagnostics if item.severity == "error"
            )
            refusal_codes = tuple(sorted({item.code for item in error_items}))
            source_entries.append(
                base.model_copy(
                    update={
                        "source_id": result.source.id,
                        "sha256": result.source.sha256,
                        "size": result.source.size,
                        "input_family": family,
                        "parser_id": result.source.parser,
                        "parser_status": "refused",
                        "refusal_reasons": (
                            PreflightRefusal(
                                code="parser-refused",
                                detail_codes=refusal_codes,
                                message=(
                                    "parser refused the source with "
                                    f"{len(error_items)} error diagnostic(s)"
                                ),
                            ),
                        ),
                        "diagnostic_counts": code_counts,
                        "diagnostics": diagnostics,
                    }
                )
            )
            parse_blocked = True
            continue
        try:
            require_goal_input_family(
                settings.goal_id,
                logical_path=logical,
                parser_id=result.source.parser,
            )
        except GoalCatalogError as exc:
            source_entries.append(
                base.model_copy(
                    update={
                        "source_id": result.source.id,
                        "sha256": result.source.sha256,
                        "size": result.source.size,
                        "input_family": family,
                        "parser_id": result.source.parser,
                        "parser_status": result.diagnostics.status,
                        "parser_eligible": True,
                        "goal_family_eligible": False,
                        "refusal_reasons": (
                            PreflightRefusal(
                                code="goal-input-family-ineligible",
                                detail_codes=(family,),
                                message=exc.message,
                            ),
                        ),
                        "diagnostic_counts": code_counts,
                        "diagnostics": diagnostics,
                    }
                )
            )
            family_rejected = True
            continue
        parse_results.append(result)
        source_entries.append(
            base.model_copy(
                update={
                    "source_id": result.source.id,
                    "sha256": result.source.sha256,
                    "size": result.source.size,
                    "input_family": family,
                    "parser_id": result.source.parser,
                    "parser_status": result.diagnostics.status,
                    "parser_eligible": True,
                    "goal_family_eligible": True,
                    "diagnostic_counts": code_counts,
                    "diagnostics": diagnostics,
                }
            )
        )
    source_entries.sort(key=lambda item: item.logical_path)
    if parse_blocked or family_rejected:
        counts = _empty_counts(len(source_entries)).model_copy(
            update={
                "parser_eligible_source_count": sum(
                    s.parser_eligible for s in source_entries
                ),
                "family_eligible_source_count": sum(
                    s.goal_family_eligible is True for s in source_entries
                ),
            }
        )
        bounded_sources = _sources_with_sizes(source_entries)
        return _assemble_bounded(
            CompilePreflight(
                schema_id=COMPILE_PREFLIGHT_SCHEMA_ID,
                request_digest=request_digest,
                captured_source_digest=capture_digest,
                evaluated_through="parse" if parse_blocked else "family",
                admitted=False,
                selection=selection,
                counts=counts,
                sources=bounded_sources,
                incompatibilities=(),
                missing_evidence=(),
                expected_exclusion_counts=(),
                expected_exclusions=(),
                omitted_expected_exclusion_count=0,
                coverage_blockers=(),
                known_limitations=limitations,
                omitted_diagnostic_count=0,
            )
        )

    selected_rules, _ = select_rules(rules, custom)
    clean_config_digest = canonical_digest(clean_config)
    documents = {}
    sources = {result.source.id: result.source for result in parse_results}
    transforms = []
    derivations = {}
    ir_artifacts = []
    for result in sorted(parse_results, key=lambda item: item.source.id):
        source = result.source
        preview = plan_cleaning(
            result.document,
            selected_rules,
            base_input_sha256=cleaning_input_digest(
                result.document,
                source_id=source.id,
                raw_sha256=source.sha256,
                canonical_artifact_id=source.artifact_id,
                canonical_stream_sha256=source.stream_sha256,
                parser=source.parser,
                parser_version=source.parser_version,
                canonical_stream_contract_version=(
                    source.canonical_stream_contract_version
                ),
            ),
        )
        cleaned = replay_cleaning_plan(result.document, preview.plan)
        documents[source.id] = cleaned
        transforms.extend(preview.records)
        derivations[source.id] = build_block_derivations(
            source,
            cleaned,
            cleaning_plan_id=preview.plan.id,
        )
        document_json = lossless_json_bytes(document_to_dict(cleaned))
        content_sha256 = sha256_digest(document_json)
        artifact_id = derive_artifact_id(
            kind="cleaned-document-ir",
            content_sha256=content_sha256,
            source_ids=(source.id,),
            producer_id="veriformis.cleaning",
            producer_version="1",
            config_digest=clean_config_digest,
        )
        ir_artifacts.append(
            IRArtifactInput.create(
                source_id=source.id,
                artifact_id=artifact_id,
                artifact_kind="cleaned-document-ir",
                document_json=document_json,
                producer_id="veriformis.cleaning",
                producer_version="1",
                config_digest=clean_config_digest,
            )
        )
    chunks = build_chunks(
        documents,
        sources,
        transforms,
        derivations,
        strategy=settings.segmentation.strategy,
        size=settings.segmentation.size,
        overlap=settings.segmentation.overlap,
    )
    source_ids = tuple(sorted(sources))
    inputs = ConstructionInputs.create(
        cleaning_config_digest=clean_config_digest,
        sources=tuple(sources[source_id] for source_id in source_ids),
        chunks=tuple(chunks),
        transforms=tuple(transforms),
        ir_artifacts=tuple(ir_artifacts),
    )
    recipe = build_named_recipe(
        settings.recipe_library_id,
        source_ids=source_ids,
        cleaning_config_digest=clean_config_digest,
        segmentation=settings.segmentation.model_dump(mode="json"),
        split_ratio_ppm=settings.construction.split_ratio_ppm,
        require_review=settings.construction.require_review,
        target_row_schema=settings.row_schema,
        consumer_profile=settings.construction.consumer_profile,
    )
    result = construct_dataset(recipe, inputs)
    missing_evidence = tuple(
        PreflightConstructionDiagnostic(
            diagnostic_id=item.diagnostic_id,
            code=item.code,
            message=item.message,
            pass_id=item.pass_id,
            source_ids=tuple(item.source_ids),
            chunk_ids=tuple(item.chunk_ids),
        )
        for item in result.diagnostics
    )
    pending = tuple(
        decision
        for decision in result.decisions
        if decision.status in {"pending_review", "rejected"}
    )
    candidates = {candidate.candidate_id: candidate for candidate in result.candidates}
    expected_exclusions: list[PreflightExpectedExclusion] = [
        PreflightExpectedExclusion(
            stage="construct",
            subject_id=decision.candidate_id,
            source_ids=tuple(candidates[decision.candidate_id].source_ids),
            status=decision.status,
            reason_codes=tuple(decision.reason_codes),
        )
        for decision in pending
    ]
    plan = build_default_finished_plan(
        recipe_id=recipe.recipe_id,
        construction_result_id=result.result_id,
        target_row_schema=settings.row_schema,
        minimum_target_characters=settings.curation.minimum_target_characters,
        balance_mode=settings.curation.balance_mode,
        maximum_records_per_primary_source=(
            settings.curation.maximum_records_per_primary_source
        ),
        evaluation_ratio_ppm=settings.curation.evaluation_ratio_ppm,
        evaluation_required=settings.curation.evaluation_required,
        split_seed=settings.curation.split_seed,
        instruction=resolved_instruction,
    )
    curated = curate_dataset(plan, recipe, inputs, result)
    records = {record.record_id: record for record in result.records}
    for decision in curated.decisions:
        if decision.status == "included":
            continue
        expected_exclusions.append(
            PreflightExpectedExclusion(
                stage="curate",
                subject_id=decision.record_id,
                source_ids=tuple(records[decision.record_id].source_ids),
                status=decision.status,
                reason_codes=tuple(decision.reason_codes),
            )
        )
    coverage = tuple(
        PreflightCoverageBlocker(
            source_id=entry.source_id,
            blocker_codes=tuple(entry.blocker_codes),
        )
        for entry in curated.coverage_ledger.entries
        if entry.blocker_codes
    )
    split_refusal: PreflightRefusal | None = None
    split_error: SplitError | None = None
    try:
        split_dataset(
            plan,
            result,
            curated,
            {source_id: sources[source_id].sha256 for source_id in source_ids},
        )
    except SplitError as exc:
        split_error = exc
        if not coverage:
            split_refusal = PreflightRefusal(
                code="evaluation-partition-unavailable",
                detail_codes=(exc.code,),
                message=exc.message,
            )

    diagnostics_by_source: dict[str, Counter[str]] = {
        source_id: Counter() for source_id in source_ids
    }
    for diagnostic in result.diagnostics:
        for source_id in diagnostic.source_ids:
            diagnostics_by_source[source_id][diagnostic.code] += 1
    coverage_by_source = {entry.source_id: entry for entry in coverage}
    candidate_sources = {
        source_id
        for candidate in result.candidates
        for source_id in candidate.source_ids
    }
    included_sources = {
        source_id
        for record_id in curated.included_record_ids
        for source_id in records[record_id].source_ids
    }
    updated_sources = []
    for source in source_entries:
        assert source.source_id is not None
        source_id = source.source_id
        evidence_available = source_id in candidate_sources
        blockers: list[PreflightRefusal] = []
        if not evidence_available:
            codes = tuple(sorted(diagnostics_by_source[source_id]))
            blockers.append(
                PreflightRefusal(
                    code="goal-evidence-unavailable",
                    detail_codes=codes,
                    message=(
                        "the selected goal produced no source-grounded candidate for "
                        f"{source.logical_path!r}"
                    ),
                )
            )
        coverage_entry = coverage_by_source.get(source_id)
        if coverage_entry is not None:
            blockers.append(
                PreflightRefusal(
                    code="curation-coverage-blocked",
                    detail_codes=coverage_entry.blocker_codes,
                    message=(
                        "curation found no complete included contribution for "
                        f"{source.logical_path!r}"
                    ),
                )
            )
        if split_refusal is not None:
            blockers.append(split_refusal)
        combined_counts = Counter(
            {item.code: item.count for item in source.diagnostic_counts}
        )
        combined_counts.update(diagnostics_by_source[source_id])
        updated_sources.append(
            _source_with_size(
                source.model_copy(
                    update={
                        "evidence_status": (
                            "available" if evidence_available else "missing"
                        ),
                        "admitted": not blockers and source_id in included_sources,
                        "refusal_reasons": tuple(blockers),
                        "diagnostic_counts": tuple(
                            PreflightCodeCount(code=code, count=count)
                            for code, count in sorted(combined_counts.items())
                        ),
                    }
                )
            )
        )
    reason_counter = Counter(
        (item.stage, item.status, code)
        for item in expected_exclusions
        for code in item.reason_codes
    )
    reason_counts = tuple(
        PreflightReasonCount(
            stage=stage,
            status=status,
            reason_code=reason,
            count=count,
        )
        for (stage, status, reason), count in sorted(reason_counter.items())
    )
    included_count = len(curated.included_record_ids)
    excluded_count = sum(item.status == "excluded" for item in curated.decisions)
    quarantined_count = sum(item.status == "quarantined" for item in curated.decisions)
    admitted = (
        split_error is None
        and not coverage
        and all(source.admitted for source in updated_sources)
    )
    counts = PreflightCounts(
        source_count=len(updated_sources),
        parser_eligible_source_count=sum(s.parser_eligible for s in updated_sources),
        family_eligible_source_count=sum(
            s.goal_family_eligible is True for s in updated_sources
        ),
        evidence_eligible_source_count=sum(
            s.evidence_status == "available" for s in updated_sources
        ),
        admitted_source_count=sum(s.admitted for s in updated_sources),
        candidate_count=len(result.candidates),
        record_count=len(result.records),
        pending_review_count=sum(
            item.status == "pending_review" for item in result.decisions
        ),
        included_count=included_count,
        excluded_count=excluded_count,
        quarantined_count=quarantined_count,
    )
    return _assemble_bounded(
        CompilePreflight(
            schema_id=COMPILE_PREFLIGHT_SCHEMA_ID,
            request_digest=request_digest,
            captured_source_digest=capture_digest,
            evaluated_through="split" if split_error is None else "curate",
            admitted=admitted,
            selection=selection,
            counts=counts,
            sources=tuple(updated_sources),
            incompatibilities=(),
            missing_evidence=missing_evidence,
            expected_exclusion_counts=reason_counts,
            expected_exclusions=tuple(expected_exclusions),
            omitted_expected_exclusion_count=0,
            coverage_blockers=coverage,
            known_limitations=limitations,
            omitted_diagnostic_count=0,
        )
    )


__all__ = [
    "COMPILE_PREFLIGHT_SCHEMA_ID",
    "MAX_RESPONSE_BYTES",
    "MAX_SOURCE_BYTES",
    "CompilePreflight",
    "PreflightCodeCount",
    "PreflightConstructionDiagnostic",
    "PreflightCounts",
    "PreflightCoverageBlocker",
    "PreflightExpectedExclusion",
    "PreflightIncompatibility",
    "PreflightLimitation",
    "PreflightParserDiagnostic",
    "PreflightReasonCount",
    "PreflightRefusal",
    "PreflightResolvedSelection",
    "PreflightSelection",
    "PreflightSource",
    "build_compile_preflight",
]
