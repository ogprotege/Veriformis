"""Strict, immutable contracts for deterministic dataset construction.

These models describe Group 2 construction state only.  They deliberately do
not model curation, split assignment, formatted rows, validation snapshots, or
bundle sealing, which belong to later roadmap groups.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from types import MappingProxyType
from typing import Annotated, Any, Literal, get_origin

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from veriformis.contracts import (
    PRODUCT_OBJECTIVE_KINDS,
    V1_CONSTRUCTION_DIAGNOSTIC_CODES,
    V1_PROMOTION_REASON_CODES,
)
from veriformis.evidence import (
    SourceEvidence,
    source_evidence_from_dict,
    source_evidence_to_dict,
)
from veriformis.errors import ConstructionError, DuplicateIdentityError, TaxonomyError
from veriformis.identity import (
    canonical_digest,
    derive_id,
    lossless_json_bytes,
    sha256_digest,
    validate_id,
    validate_sha256,
)
from veriformis.taxonomy import assert_objective_row_compatible

from .evidence import IRFieldEvidence
from ._json import reject_floats


ObjectiveKind = Literal[
    "full_text",
    "continuation",
    "section_reconstruction",
    "before_after_transformation",
    "structured_field",
    "explicit_label",
    "preference_pair",
]
ProductRowSchema = Literal[
    "text",
    "prompt_completion",
    "instruction_output",
    "messages",
    "label-classification",
    "preference-pair",
]
ReviewPolicy = Literal["none", "required"]
DecisionStatus = Literal["accepted", "rejected", "pending_review"]
ReviewVerdict = Literal["accepted", "rejected"]
ChunkStrategy = Literal["paragraph", "fixed", "sliding", "sentence", "structure"]
ParameterValue = str | bool | int | None
DiagnosticCode = Literal[
    "continuation-boundary-unavailable",
    "section-structure-unavailable",
    "source-chunks-unavailable",
    "structured-field-chunk-unavailable",
    "structured-field-empty-value",
    "structured-field-unavailable",
    "structured-ir-artifact-unavailable",
    "transformation-pair-empty-or-unchanged",
    "transformation-pair-unavailable",
    "mapped-label-unavailable",
    "mapped-preference-unavailable",
]
PromotionReasonCode = Literal[
    "construction-integrity-v1",
    "review-approved",
    "review-rejected",
    "review-required",
]


OBJECTIVE_FIELD_CONTRACTS: Mapping[str, tuple[str, ...]] = MappingProxyType({
    "full_text": ("text",),
    "continuation": ("prompt", "completion"),
    "section_reconstruction": ("heading", "section"),
    "before_after_transformation": ("before", "after"),
    "structured_field": ("input", "fields"),
    "explicit_label": ("context", "label"),
    "preference_pair": ("prompt", "chosen", "rejected"),
})

BUILTIN_CONSTRUCTOR_IDS: Mapping[str, str] = MappingProxyType({
    "full_text": "veriformis.constructor.full-text",
    "continuation": "veriformis.constructor.continuation",
    "section_reconstruction": "veriformis.constructor.section-reconstruction",
    "before_after_transformation": (
        "veriformis.constructor.before-after-transformation"
    ),
    "structured_field": "veriformis.constructor.structured-field",
    "explicit_label": "veriformis.constructor.explicit-label",
    "preference_pair": "veriformis.constructor.preference-pair",
})

CONSTRUCTION_GATES = ("field-evidence", "objective-shape")
class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        arbitrary_types_allowed=True,
    )

    @model_validator(mode="before")
    @classmethod
    def _require_exact_fields(cls, value: Any, info: ValidationInfo) -> Any:
        if isinstance(value, cls) or not isinstance(value, Mapping):
            return value
        expected = set(cls.model_fields)
        actual = set(value)
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            raise ValueError(
                f"{cls.__name__} fields do not match its persisted schema; "
                f"missing={missing!r}, extra={extra!r}"
            )
        if info.mode != "json":
            return value
        normalized = dict(value)
        for name, field in cls.model_fields.items():
            if get_origin(field.annotation) is tuple and isinstance(
                normalized[name], list
            ):
                normalized[name] = tuple(normalized[name])
        return normalized


def _require_nonempty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _require_canonical_ids(
    values: tuple[str, ...],
    *,
    kind: str,
    field_name: str,
) -> tuple[str, ...]:
    normalized = tuple(sorted(validate_id(value, kind=kind) for value in values))
    if len(values) != len(set(values)):
        raise DuplicateIdentityError(f"{field_name} contains duplicate identities")
    if values != normalized:
        raise ValueError(f"{field_name} must be sorted in canonical order")
    return values


class SourceTextEvidence(_StrictModel):
    """One record field reconstructed through existing SourceEvidence v1."""

    schema_version: Literal["veriformis.field-evidence/v1"] = (
        "veriformis.field-evidence/v1"
    )
    kind: Literal["source_text"] = "source_text"
    evidence: SourceEvidence

    @field_validator("evidence", mode="before")
    @classmethod
    def _load_source_evidence(cls, value: Any) -> SourceEvidence:
        if isinstance(value, dict):
            return source_evidence_from_dict(value)
        if not isinstance(value, SourceEvidence):
            raise ValueError("source-text field evidence must contain SourceEvidence v1")
        source_evidence_to_dict(value)
        return value


FieldEvidence = Annotated[
    SourceTextEvidence | IRFieldEvidence,
    Field(discriminator="kind"),
]


class TrainingObjective(_StrictModel):
    schema_version: Literal["veriformis.training-objective/v1"] = (
        "veriformis.training-objective/v1"
    )
    objective_id: str
    objective_version: Literal[1] = 1
    kind: ObjectiveKind
    field_names: tuple[str, ...]

    @model_validator(mode="after")
    def _validate_contract(self) -> TrainingObjective:
        validate_id(self.objective_id, kind="obj")
        if self.kind not in PRODUCT_OBJECTIVE_KINDS:
            raise ValueError(f"unsupported deterministic objective {self.kind!r}")
        expected_fields = OBJECTIVE_FIELD_CONTRACTS[self.kind]
        if self.field_names != expected_fields:
            raise ValueError(
                f"objective {self.kind!r} fields must be {expected_fields!r}"
            )
        expected_id = derive_id(
            "obj",
            self.model_dump(mode="json", exclude={"objective_id"}),
        )
        if self.objective_id != expected_id:
            raise ValueError("training objective identity mismatch")
        return self

    @classmethod
    def create(cls, kind: ObjectiveKind) -> TrainingObjective:
        if kind not in OBJECTIVE_FIELD_CONTRACTS:
            raise ConstructionError(
                f"unsupported deterministic objective {kind!r}"
            )
        payload = {
            "schema_version": "veriformis.training-objective/v1",
            "objective_version": 1,
            "kind": kind,
            "field_names": OBJECTIVE_FIELD_CONTRACTS[kind],
        }
        return cls(objective_id=derive_id("obj", payload), **payload)


class SegmentationPolicy(_StrictModel):
    schema_version: Literal["veriformis.segmentation-policy/v1"] = (
        "veriformis.segmentation-policy/v1"
    )
    strategy: ChunkStrategy
    size: int
    overlap: int

    @model_validator(mode="after")
    def _validate_sizes(self) -> SegmentationPolicy:
        if type(self.size) is not int or self.size < 1:
            raise ValueError("segmentation size must be a positive integer")
        if (
            type(self.overlap) is not int
            or self.overlap < 0
            or self.overlap >= self.size
        ):
            raise ValueError("segmentation overlap must satisfy 0 <= overlap < size")
        return self


class PassParameter(_StrictModel):
    name: str
    value: ParameterValue

    @field_validator("name")
    @classmethod
    def _valid_name(cls, value: str) -> str:
        return _require_nonempty(value, "construction-pass parameter name")


class ConstructionPass(_StrictModel):
    schema_version: Literal["veriformis.construction-pass/v1"] = (
        "veriformis.construction-pass/v1"
    )
    pass_id: str
    sequence: int
    objective_kind: ObjectiveKind
    constructor_id: str
    constructor_version: str
    parameters: tuple[PassParameter, ...] = ()

    @model_validator(mode="after")
    def _validate_pass(self) -> ConstructionPass:
        validate_id(self.pass_id, kind="pas")
        if type(self.sequence) is not int or self.sequence < 1:
            raise ValueError("construction pass sequence must be positive")
        _require_nonempty(self.constructor_id, "constructor_id")
        _require_nonempty(self.constructor_version, "constructor_version")
        expected_constructor = BUILTIN_CONSTRUCTOR_IDS[self.objective_kind]
        if self.constructor_id != expected_constructor:
            raise ValueError(
                f"objective {self.objective_kind!r} requires constructor "
                f"{expected_constructor!r}"
            )
        names = tuple(parameter.name for parameter in self.parameters)
        if names != tuple(sorted(names)) or len(names) != len(set(names)):
            raise ValueError(
                "construction-pass parameters must have unique names in canonical order"
            )
        expected_id = derive_id(
            "pas",
            self.model_dump(mode="json", exclude={"pass_id"}),
        )
        if self.pass_id != expected_id:
            raise ValueError("construction pass identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        sequence: int,
        objective_kind: ObjectiveKind,
        constructor_version: str = "1",
        parameters: Mapping[str, ParameterValue] | None = None,
    ) -> ConstructionPass:
        if objective_kind not in BUILTIN_CONSTRUCTOR_IDS:
            raise ConstructionError(
                f"unsupported deterministic objective {objective_kind!r}"
            )
        normalized_parameters = tuple(
            PassParameter(name=name, value=value)
            for name, value in sorted((parameters or {}).items())
        )
        payload = {
            "schema_version": "veriformis.construction-pass/v1",
            "sequence": sequence,
            "objective_kind": objective_kind,
            "constructor_id": BUILTIN_CONSTRUCTOR_IDS[objective_kind],
            "constructor_version": constructor_version,
            "parameters": normalized_parameters,
        }
        return cls(pass_id=derive_id("pas", payload), **payload)

    def parameter_map(self) -> dict[str, ParameterValue]:
        return {parameter.name: parameter.value for parameter in self.parameters}


class DatasetRecipe(_StrictModel):
    schema_version: Literal["veriformis.dataset-recipe/v1"] = (
        "veriformis.dataset-recipe/v1"
    )
    recipe_id: str
    objective: TrainingObjective
    source_ids: tuple[str, ...]
    cleaning_config_digest: str
    segmentation: SegmentationPolicy
    passes: tuple[ConstructionPass, ...]
    curation_policy: Literal["deferred"] = "deferred"
    split_policy: Literal["deferred"] = "deferred"
    target_row_schema: ProductRowSchema
    review_policy: ReviewPolicy = "none"
    required_gates: tuple[str, ...] = CONSTRUCTION_GATES

    @field_validator("source_ids")
    @classmethod
    def _valid_sources(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("dataset recipe requires at least one source")
        return _require_canonical_ids(
            value,
            kind="src",
            field_name="dataset recipe source_ids",
        )

    @model_validator(mode="after")
    def _validate_recipe(self) -> DatasetRecipe:
        validate_id(self.recipe_id, kind="rcp")
        validate_sha256(self.cleaning_config_digest)
        try:
            assert_objective_row_compatible(
                self.objective.kind,
                self.target_row_schema,
            )
        except TaxonomyError as exc:
            raise ValueError(exc.message) from exc
        if (
            self.objective.kind == "section_reconstruction"
            and self.segmentation.strategy != "structure"
        ):
            raise ValueError(
                "section_reconstruction recipes require structure segmentation"
            )
        if not self.passes:
            raise ValueError("dataset recipe requires at least one construction pass")
        pass_ids = tuple(item.pass_id for item in self.passes)
        if len(pass_ids) != len(set(pass_ids)):
            raise DuplicateIdentityError(
                "dataset recipe contains duplicate construction passes"
            )
        sequences = tuple(item.sequence for item in self.passes)
        if sequences != tuple(range(1, len(self.passes) + 1)):
            raise ValueError("construction passes must be ordered contiguously from one")
        if any(item.objective_kind != self.objective.kind for item in self.passes):
            raise ValueError("construction pass objective does not match its recipe")
        if self.required_gates != CONSTRUCTION_GATES:
            raise ValueError(
                "Group 2 recipes require field-evidence and objective-shape gates"
            )
        expected_id = derive_id(
            "rcp",
            self.model_dump(mode="json", exclude={"recipe_id"}),
        )
        if self.recipe_id != expected_id:
            raise ValueError("dataset recipe identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        objective: TrainingObjective,
        source_ids: tuple[str, ...] | list[str],
        cleaning_config_digest: str,
        segmentation: SegmentationPolicy,
        target_row_schema: ProductRowSchema,
        passes: tuple[ConstructionPass, ...] | list[ConstructionPass] | None = None,
        review_policy: ReviewPolicy = "none",
    ) -> DatasetRecipe:
        normalized_sources = tuple(sorted(source_ids))
        normalized_passes = tuple(passes) if passes is not None else (
            ConstructionPass.create(
                sequence=1,
                objective_kind=objective.kind,
            ),
        )
        payload = {
            "schema_version": "veriformis.dataset-recipe/v1",
            "objective": objective,
            "source_ids": normalized_sources,
            "cleaning_config_digest": cleaning_config_digest,
            "segmentation": segmentation,
            "passes": normalized_passes,
            "curation_policy": "deferred",
            "split_policy": "deferred",
            "target_row_schema": target_row_schema,
            "review_policy": review_policy,
            "required_gates": CONSTRUCTION_GATES,
        }
        return cls(recipe_id=derive_id("rcp", payload), **payload)


class RecordField(_StrictModel):
    name: str
    value: str
    evidence: FieldEvidence

    @field_validator("name")
    @classmethod
    def _valid_name(cls, value: str) -> str:
        return _require_nonempty(value, "record field name")

    @field_validator("value")
    @classmethod
    def _valid_value(cls, value: str) -> str:
        return _require_nonempty(value, "record field value")

    @model_validator(mode="after")
    def _evidence_matches_value(self) -> RecordField:
        expected = sha256_digest(self.value)
        if isinstance(self.evidence, SourceTextEvidence):
            actual = self.evidence.evidence.output_sha256
        else:
            actual = self.evidence.output_sha256
        if actual != expected:
            raise ValueError(f"field {self.name!r} value does not match its evidence")
        return self


class CandidateRecord(_StrictModel):
    schema_version: Literal["veriformis.candidate-record/v1"] = (
        "veriformis.candidate-record/v1"
    )
    candidate_id: str
    ordinal: int
    recipe_id: str
    objective_id: str
    pass_id: str
    source_ids: tuple[str, ...]
    chunk_ids: tuple[str, ...]
    transform_ids: tuple[str, ...]
    fields: tuple[RecordField, ...]

    @model_validator(mode="after")
    def _validate_candidate(self) -> CandidateRecord:
        validate_id(self.candidate_id, kind="cand")
        validate_id(self.recipe_id, kind="rcp")
        validate_id(self.objective_id, kind="obj")
        validate_id(self.pass_id, kind="pas")
        if type(self.ordinal) is not int or self.ordinal < 1:
            raise ValueError("candidate ordinal must be positive")
        if not self.source_ids:
            raise ValueError("candidate record requires at least one source")
        _require_canonical_ids(
            self.source_ids,
            kind="src",
            field_name="candidate source_ids",
        )
        if not self.chunk_ids:
            raise ValueError("candidate record requires at least one input chunk")
        _require_canonical_ids(
            self.chunk_ids,
            kind="chk",
            field_name="candidate chunk_ids",
        )
        _require_canonical_ids(
            self.transform_ids,
            kind="trn",
            field_name="candidate transform_ids",
        )
        if not self.fields:
            raise ValueError("candidate record requires at least one field")
        field_names = tuple(item.name for item in self.fields)
        if len(field_names) != len(set(field_names)):
            raise ValueError("candidate record contains duplicate field names")
        for field in self.fields:
            evidence_source_id = (
                field.evidence.evidence.source_id
                if isinstance(field.evidence, SourceTextEvidence)
                else field.evidence.source_id
            )
            if evidence_source_id not in self.source_ids:
                raise ValueError("candidate field evidence names another source")
        expected_id = derive_id(
            "cand",
            self.model_dump(mode="json", exclude={"candidate_id"}),
        )
        if self.candidate_id != expected_id:
            raise ValueError("candidate record identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        ordinal: int,
        recipe_id: str,
        objective_id: str,
        pass_id: str,
        source_ids: tuple[str, ...] | list[str],
        chunk_ids: tuple[str, ...] | list[str],
        transform_ids: tuple[str, ...] | list[str],
        fields: tuple[RecordField, ...] | list[RecordField],
    ) -> CandidateRecord:
        payload = {
            "schema_version": "veriformis.candidate-record/v1",
            "ordinal": ordinal,
            "recipe_id": recipe_id,
            "objective_id": objective_id,
            "pass_id": pass_id,
            "source_ids": tuple(sorted(source_ids)),
            "chunk_ids": tuple(sorted(chunk_ids)),
            "transform_ids": tuple(sorted(transform_ids)),
            "fields": tuple(fields),
        }
        return cls(candidate_id=derive_id("cand", payload), **payload)


class ReviewEvidence(_StrictModel):
    schema_version: Literal["veriformis.review-evidence/v1"] = (
        "veriformis.review-evidence/v1"
    )
    review_id: str
    candidate_id: str
    reviewer_id: str
    verdict: ReviewVerdict
    rationale: str

    @field_validator("reviewer_id", "rationale")
    @classmethod
    def _valid_text(cls, value: str, info) -> str:
        return _require_nonempty(value, info.field_name)

    @model_validator(mode="after")
    def _validate_review(self) -> ReviewEvidence:
        validate_id(self.review_id, kind="rvw")
        validate_id(self.candidate_id, kind="cand")
        expected_id = derive_id(
            "rvw",
            self.model_dump(mode="json", exclude={"review_id"}),
        )
        if self.review_id != expected_id:
            raise ValueError("review evidence identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        candidate_id: str,
        reviewer_id: str,
        verdict: ReviewVerdict,
        rationale: str,
    ) -> ReviewEvidence:
        payload = {
            "schema_version": "veriformis.review-evidence/v1",
            "candidate_id": candidate_id,
            "reviewer_id": reviewer_id,
            "verdict": verdict,
            "rationale": rationale,
        }
        return cls(review_id=derive_id("rvw", payload), **payload)


class PromotionDecision(_StrictModel):
    schema_version: Literal["veriformis.promotion-decision/v1"] = (
        "veriformis.promotion-decision/v1"
    )
    decision_id: str
    candidate_id: str
    status: DecisionStatus
    reason_codes: tuple[PromotionReasonCode, ...]
    review: ReviewEvidence | None = None

    @model_validator(mode="after")
    def _validate_decision(self) -> PromotionDecision:
        validate_id(self.decision_id, kind="dec")
        validate_id(self.candidate_id, kind="cand")
        if not self.reason_codes:
            raise ValueError("promotion decision requires at least one reason code")
        if self.reason_codes != tuple(sorted(self.reason_codes)) \
                or len(self.reason_codes) != len(set(self.reason_codes)):
            raise ValueError("promotion reason codes must be unique and canonical")
        if any(code not in V1_PROMOTION_REASON_CODES for code in self.reason_codes):
            raise ValueError("promotion decision contains an unsupported reason code")
        if self.status == "pending_review":
            if self.review is not None:
                raise ValueError("pending review decision cannot carry completed review")
            expected_reasons = ("review-required",)
        elif self.review is not None:
            if self.review.candidate_id != self.candidate_id:
                raise ValueError("review evidence names a different candidate")
            if self.review.verdict != self.status:
                raise ValueError("review verdict does not match promotion status")
            expected_reasons = (
                "review-approved" if self.status == "accepted" else "review-rejected",
            )
        elif self.status == "accepted":
            expected_reasons = ("construction-integrity-v1",)
        else:
            raise ValueError("a rejected decision requires matching review evidence")
        if self.reason_codes != expected_reasons:
            raise ValueError("promotion reason codes do not match decision semantics")
        expected_id = derive_id(
            "dec",
            self.model_dump(mode="json", exclude={"decision_id"}),
        )
        if self.decision_id != expected_id:
            raise ValueError("promotion decision identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        candidate_id: str,
        status: DecisionStatus,
        reason_codes: tuple[PromotionReasonCode, ...] | list[PromotionReasonCode],
        review: ReviewEvidence | None = None,
    ) -> PromotionDecision:
        payload = {
            "schema_version": "veriformis.promotion-decision/v1",
            "candidate_id": candidate_id,
            "status": status,
            "reason_codes": tuple(sorted(reason_codes)),
            "review": review,
        }
        return cls(decision_id=derive_id("dec", payload), **payload)


class DatasetRecord(_StrictModel):
    schema_version: Literal["veriformis.dataset-record/v1"] = (
        "veriformis.dataset-record/v1"
    )
    record_id: str
    candidate_id: str
    decision_id: str
    recipe_id: str
    objective_id: str
    pass_id: str
    source_ids: tuple[str, ...]
    chunk_ids: tuple[str, ...]
    transform_ids: tuple[str, ...]
    fields: tuple[RecordField, ...]

    @model_validator(mode="after")
    def _validate_record(self) -> DatasetRecord:
        validate_id(self.record_id, kind="rec")
        validate_id(self.candidate_id, kind="cand")
        validate_id(self.decision_id, kind="dec")
        validate_id(self.recipe_id, kind="rcp")
        validate_id(self.objective_id, kind="obj")
        validate_id(self.pass_id, kind="pas")
        if not self.source_ids:
            raise ValueError("dataset record requires at least one source")
        _require_canonical_ids(
            self.source_ids,
            kind="src",
            field_name="dataset record source_ids",
        )
        if not self.chunk_ids:
            raise ValueError("dataset record requires at least one input chunk")
        _require_canonical_ids(
            self.chunk_ids,
            kind="chk",
            field_name="dataset record chunk_ids",
        )
        _require_canonical_ids(
            self.transform_ids,
            kind="trn",
            field_name="dataset record transform_ids",
        )
        if not self.fields:
            raise ValueError("dataset record requires at least one field")
        field_names = tuple(field.name for field in self.fields)
        if len(field_names) != len(set(field_names)):
            raise ValueError("dataset record contains duplicate field names")
        for field in self.fields:
            evidence_source_id = (
                field.evidence.evidence.source_id
                if isinstance(field.evidence, SourceTextEvidence)
                else field.evidence.source_id
            )
            if evidence_source_id not in self.source_ids:
                raise ValueError("dataset record field evidence names another source")
        expected_id = derive_id(
            "rec",
            self.model_dump(mode="json", exclude={"record_id"}),
        )
        if self.record_id != expected_id:
            raise ValueError("dataset record identity mismatch")
        return self

    @classmethod
    def promote(
        cls,
        candidate: CandidateRecord,
        decision: PromotionDecision,
    ) -> DatasetRecord:
        try:
            checked_candidate = CandidateRecord.model_validate_json(
                lossless_json_bytes(candidate.model_dump(mode="json"))
            )
            checked_decision = PromotionDecision.model_validate_json(
                lossless_json_bytes(decision.model_dump(mode="json"))
            )
        except (ConstructionError, DuplicateIdentityError):
            raise
        except (TypeError, ValueError) as exc:
            raise ConstructionError(
                f"invalid candidate or promotion decision: {exc}"
            ) from exc
        if (
            checked_decision.status != "accepted"
            or checked_decision.candidate_id != checked_candidate.candidate_id
        ):
            raise ConstructionError("only an accepted candidate can become a dataset record")
        payload = {
            "schema_version": "veriformis.dataset-record/v1",
            "candidate_id": checked_candidate.candidate_id,
            "decision_id": checked_decision.decision_id,
            "recipe_id": checked_candidate.recipe_id,
            "objective_id": checked_candidate.objective_id,
            "pass_id": checked_candidate.pass_id,
            "source_ids": checked_candidate.source_ids,
            "chunk_ids": checked_candidate.chunk_ids,
            "transform_ids": checked_candidate.transform_ids,
            "fields": checked_candidate.fields,
        }
        return cls(record_id=derive_id("rec", payload), **payload)


def _construction_diagnostic_input_key(
    *,
    source_ids: tuple[str, ...],
    chunk_ids: tuple[str, ...],
) -> str:
    return canonical_digest(
        {
            "schema_version": "veriformis.construction-diagnostic-input/v1",
            "source_ids": source_ids,
            "chunk_ids": chunk_ids,
        }
    )


class ConstructionDiagnostic(_StrictModel):
    schema_version: Literal["veriformis.construction-diagnostic/v1"] = (
        "veriformis.construction-diagnostic/v1"
    )
    diagnostic_id: str
    code: DiagnosticCode
    message: str
    pass_id: str
    input_key: str
    source_ids: tuple[str, ...] = ()
    chunk_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _validate_diagnostic(self) -> ConstructionDiagnostic:
        validate_id(self.diagnostic_id, kind="dia")
        _require_nonempty(self.code, "construction diagnostic code")
        if self.code not in V1_CONSTRUCTION_DIAGNOSTIC_CODES:
            raise ValueError("unsupported construction diagnostic code")
        _require_nonempty(self.message, "construction diagnostic message")
        validate_id(self.pass_id, kind="pas")
        validate_sha256(self.input_key)
        if not self.source_ids and not self.chunk_ids:
            raise ValueError("construction diagnostic requires a stable input scope")
        _require_canonical_ids(
            self.source_ids,
            kind="src",
            field_name="diagnostic source_ids",
        )
        _require_canonical_ids(
            self.chunk_ids,
            kind="chk",
            field_name="diagnostic chunk_ids",
        )
        expected_input_key = _construction_diagnostic_input_key(
            source_ids=self.source_ids,
            chunk_ids=self.chunk_ids,
        )
        if self.input_key != expected_input_key:
            raise ValueError("construction diagnostic input key mismatch")
        expected_id = derive_id(
            "dia",
            self.model_dump(mode="json", exclude={"diagnostic_id"}),
        )
        if self.diagnostic_id != expected_id:
            raise ValueError("construction diagnostic identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        code: DiagnosticCode,
        message: str,
        pass_id: str,
        source_ids: tuple[str, ...] | list[str] = (),
        chunk_ids: tuple[str, ...] | list[str] = (),
    ) -> ConstructionDiagnostic:
        normalized_sources = tuple(sorted(source_ids))
        normalized_chunks = tuple(sorted(chunk_ids))
        payload = {
            "schema_version": "veriformis.construction-diagnostic/v1",
            "code": code,
            "message": message,
            "pass_id": pass_id,
            "input_key": _construction_diagnostic_input_key(
                source_ids=normalized_sources,
                chunk_ids=normalized_chunks,
            ),
            "source_ids": normalized_sources,
            "chunk_ids": normalized_chunks,
        }
        return cls(diagnostic_id=derive_id("dia", payload), **payload)


class ConstructionResult(_StrictModel):
    schema_version: Literal["veriformis.construction-result/v1"] = (
        "veriformis.construction-result/v1"
    )
    result_id: str
    recipe_id: str
    input_digest: str
    executed_pass_ids: tuple[str, ...]
    candidates: tuple[CandidateRecord, ...]
    decisions: tuple[PromotionDecision, ...]
    records: tuple[DatasetRecord, ...]
    diagnostics: tuple[ConstructionDiagnostic, ...] = ()

    @model_validator(mode="after")
    def _validate_result(self) -> ConstructionResult:
        validate_id(self.result_id, kind="run")
        validate_id(self.recipe_id, kind="rcp")
        validate_sha256(self.input_digest)
        if not self.executed_pass_ids:
            raise ValueError("construction result requires at least one executed pass")
        if len(self.executed_pass_ids) != len(set(self.executed_pass_ids)):
            raise DuplicateIdentityError(
                "construction result contains duplicate executed passes"
            )
        for pass_id in self.executed_pass_ids:
            validate_id(pass_id, kind="pas")

        candidate_ids = tuple(candidate.candidate_id for candidate in self.candidates)
        if len(candidate_ids) != len(set(candidate_ids)):
            raise DuplicateIdentityError(
                "construction result contains duplicate candidates"
            )
        candidate_ordinals = tuple(candidate.ordinal for candidate in self.candidates)
        if candidate_ordinals != tuple(range(1, len(self.candidates) + 1)):
            raise ValueError(
                "construction candidate ordinals must be contiguous and ordered from one"
            )
        if any(candidate.recipe_id != self.recipe_id for candidate in self.candidates):
            raise ValueError("construction candidate belongs to another recipe")
        if any(
            candidate.pass_id not in self.executed_pass_ids
            for candidate in self.candidates
        ):
            raise ValueError("construction candidate names an unexecuted pass")

        decision_candidates = tuple(decision.candidate_id for decision in self.decisions)
        if decision_candidates != candidate_ids:
            raise ValueError("construction result requires one ordered decision per candidate")
        decision_ids = tuple(decision.decision_id for decision in self.decisions)
        if len(decision_ids) != len(set(decision_ids)):
            raise DuplicateIdentityError(
                "construction result contains duplicate decisions"
            )

        accepted = tuple(
            decision.candidate_id
            for decision in self.decisions
            if decision.status == "accepted"
        )
        record_candidates = tuple(record.candidate_id for record in self.records)
        if record_candidates != accepted:
            raise ValueError("dataset records do not exactly match accepted candidates")
        if len({record.record_id for record in self.records}) != len(self.records):
            raise DuplicateIdentityError(
                "construction result contains duplicate dataset records"
            )
        diagnostic_ids = tuple(item.diagnostic_id for item in self.diagnostics)
        if len(diagnostic_ids) != len(set(diagnostic_ids)):
            raise DuplicateIdentityError(
                "construction result contains duplicate diagnostics"
            )
        if any(
            diagnostic.pass_id not in self.executed_pass_ids
            for diagnostic in self.diagnostics
        ):
            raise ValueError("construction diagnostic names an unexecuted pass")
        covered_pass_ids = {
            candidate.pass_id for candidate in self.candidates
        } | {diagnostic.pass_id for diagnostic in self.diagnostics}
        if covered_pass_ids != set(self.executed_pass_ids):
            raise ValueError(
                "every executed construction pass requires a candidate or diagnostic"
            )

        candidates_by_id = {
            candidate.candidate_id: candidate for candidate in self.candidates
        }
        decisions_by_candidate = {
            decision.candidate_id: decision for decision in self.decisions
        }
        for record in self.records:
            candidate = candidates_by_id[record.candidate_id]
            decision = decisions_by_candidate[record.candidate_id]
            if (
                record.decision_id != decision.decision_id
                or record.recipe_id != candidate.recipe_id
                or record.objective_id != candidate.objective_id
                or record.pass_id != candidate.pass_id
                or record.source_ids != candidate.source_ids
                or record.chunk_ids != candidate.chunk_ids
                or record.transform_ids != candidate.transform_ids
                or record.fields != candidate.fields
            ):
                raise ValueError("dataset record does not preserve its accepted candidate")

        expected_id = derive_id(
            "run",
            self.model_dump(mode="json", exclude={"result_id"}),
        )
        if self.result_id != expected_id:
            raise ValueError("construction result identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        recipe_id: str,
        input_digest: str,
        executed_pass_ids: tuple[str, ...],
        candidates: tuple[CandidateRecord, ...],
        decisions: tuple[PromotionDecision, ...],
        records: tuple[DatasetRecord, ...],
        diagnostics: tuple[ConstructionDiagnostic, ...] = (),
    ) -> ConstructionResult:
        payload = {
            "schema_version": "veriformis.construction-result/v1",
            "recipe_id": recipe_id,
            "input_digest": input_digest,
            "executed_pass_ids": executed_pass_ids,
            "candidates": candidates,
            "decisions": decisions,
            "records": records,
            "diagnostics": diagnostics,
        }
        return cls(result_id=derive_id("run", payload), **payload)


def dataset_recipe_to_dict(recipe: DatasetRecipe) -> dict[str, Any]:
    """Serialize and revalidate one exact recipe schema."""
    value = recipe.model_dump(mode="json")
    if DatasetRecipe.model_validate_json(lossless_json_bytes(value)) != recipe:
        raise ConstructionError("dataset recipe does not round-trip exactly")
    return value


def _canonical_json_object_from_bytes(data: bytes, *, label: str) -> dict[str, Any]:
    if not isinstance(data, bytes):
        raise ConstructionError(f"{label} must be loaded from exact bytes")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise DuplicateIdentityError(
                    f"{label} JSON contains duplicate key {key!r}"
                )
            value[key] = item
        return value

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number {value!r}")

    def reject_float(value: str) -> None:
        raise ValueError(f"floating-point JSON number {value!r}")

    try:
        decoded = data.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
            parse_float=reject_float,
        )
    except DuplicateIdentityError:
        raise
    except (UnicodeError, ValueError) as exc:
        raise ConstructionError(f"invalid {label} JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ConstructionError(f"{label} JSON root must be an object")
    if lossless_json_bytes(value) != data:
        raise ConstructionError(f"{label} JSON bytes are not canonical")
    return value


def dataset_recipe_from_json_bytes(data: bytes) -> DatasetRecipe:
    """Load one exact canonical recipe artifact and recompute every identity."""
    _canonical_json_object_from_bytes(data, label="dataset recipe")
    try:
        return DatasetRecipe.model_validate_json(data)
    except DuplicateIdentityError:
        raise
    except (TypeError, ValueError) as exc:
        raise ConstructionError(f"invalid dataset recipe: {exc}") from exc


def dataset_recipe_from_dict(value: dict[str, Any]) -> DatasetRecipe:
    """Load a recipe through strict JSON semantics and recompute every ID."""
    return dataset_recipe_from_json_bytes(lossless_json_bytes(value))


def construction_result_to_dict(result: ConstructionResult) -> dict[str, Any]:
    """Serialize and revalidate one exact construction-result schema."""
    value = result.model_dump(mode="json")
    if ConstructionResult.model_validate_json(lossless_json_bytes(value)) != result:
        raise ConstructionError("construction result does not round-trip exactly")
    return value


def construction_result_from_json_bytes(data: bytes) -> ConstructionResult:
    """Load one exact canonical result artifact and recompute every identity."""
    _canonical_json_object_from_bytes(data, label="construction result")
    try:
        return ConstructionResult.model_validate_json(data)
    except DuplicateIdentityError:
        raise
    except (TypeError, ValueError) as exc:
        raise ConstructionError(f"invalid construction result: {exc}") from exc


def construction_result_from_dict(value: dict[str, Any]) -> ConstructionResult:
    """Load a construction result and recompute all nested identities."""
    return construction_result_from_json_bytes(lossless_json_bytes(value))


def construction_payload_digest(value: BaseModel | Mapping[str, Any]) -> str:
    """Return the exact-string digest used by construction snapshots."""
    try:
        reject_floats(value)
        return canonical_digest(value)
    except (TypeError, ValueError) as exc:
        raise ConstructionError(f"invalid construction digest payload: {exc}") from exc


__all__ = [
    "BUILTIN_CONSTRUCTOR_IDS",
    "CONSTRUCTION_GATES",
    "OBJECTIVE_FIELD_CONTRACTS",
    "V1_CONSTRUCTION_DIAGNOSTIC_CODES",
    "V1_PROMOTION_REASON_CODES",
    "CandidateRecord",
    "ChunkStrategy",
    "ConstructionDiagnostic",
    "ConstructionError",
    "ConstructionPass",
    "ConstructionResult",
    "DatasetRecipe",
    "DatasetRecord",
    "DecisionStatus",
    "DiagnosticCode",
    "FieldEvidence",
    "ObjectiveKind",
    "PassParameter",
    "ProductRowSchema",
    "PromotionReasonCode",
    "PromotionDecision",
    "RecordField",
    "ReviewEvidence",
    "ReviewPolicy",
    "SegmentationPolicy",
    "SourceTextEvidence",
    "TrainingObjective",
    "construction_payload_digest",
    "construction_result_from_dict",
    "construction_result_from_json_bytes",
    "construction_result_to_dict",
    "dataset_recipe_from_dict",
    "dataset_recipe_from_json_bytes",
    "dataset_recipe_to_dict",
]
