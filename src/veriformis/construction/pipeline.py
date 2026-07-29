"""Deterministic construction orchestration and exact replay validation."""

from __future__ import annotations

from typing import Any, Literal, Sequence

from pydantic import BaseModel, ConfigDict, model_validator

from veriformis.chunkers.base import Chunk, chunk_to_dict
from veriformis.errors import (
    ConstructionError,
    DuplicateIdentityError,
    VeriformisError,
)
from veriformis.evidence import resolve_evidence
from veriformis.identity import (
    canonical_digest,
    derive_artifact_id,
    derive_source_id,
    lossless_json_bytes,
    sha256_digest,
    validate_id,
    validate_sha256,
)
from veriformis.rules.engine import (
    TransformRecord,
    transform_record_to_dict,
    validate_transform_record,
)
from veriformis.sources import SourceRef

from .constructors import construction_field_context, get_constructor
from .evidence import (
    IRArtifactKind,
    IRFieldEvidence,
    load_ir_document_json,
    resolve_ir_field_evidence,
)
from .models import (
    CandidateRecord,
    ConstructionDiagnostic,
    ConstructionResult,
    DatasetRecipe,
    DatasetRecord,
    OBJECTIVE_FIELD_CONTRACTS,
    PromotionDecision,
    ReviewEvidence,
    SourceTextEvidence,
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        arbitrary_types_allowed=True,
    )


class IRArtifactInput(_StrictModel):
    """One exact parsed or cleaned strict-IR artifact used by construction."""

    schema_version: Literal["veriformis.construction-ir-input/v1"] = (
        "veriformis.construction-ir-input/v1"
    )
    source_id: str
    source_ids: tuple[str, ...]
    artifact_id: str
    artifact_kind: IRArtifactKind
    document_sha256: str
    producer_id: str
    producer_version: str
    config_digest: str
    document_json: bytes

    @model_validator(mode="after")
    def _validate_artifact(self) -> IRArtifactInput:
        validate_id(self.source_id, kind="src")
        if self.source_ids != (self.source_id,):
            raise ValueError("construction IR input requires exact single-source scope")
        validate_id(self.artifact_id, kind="art")
        validate_sha256(self.document_sha256)
        validate_sha256(self.config_digest)
        if not self.producer_id:
            raise ValueError("construction IR producer_id must be non-empty")
        if not self.producer_version:
            raise ValueError("construction IR producer_version must be non-empty")
        if self.document_sha256 != sha256_digest(self.document_json):
            raise ValueError("construction IR input content digest mismatch")
        expected_artifact_id = derive_artifact_id(
            kind=self.artifact_kind,
            content_sha256=self.document_sha256,
            source_ids=self.source_ids,
            producer_id=self.producer_id,
            producer_version=self.producer_version,
            config_digest=self.config_digest,
        )
        if self.artifact_id != expected_artifact_id:
            raise ValueError("construction IR artifact identity mismatch")
        _, document = load_ir_document_json(self.document_json)
        if document.source_id != self.source_id:
            raise ValueError("construction IR input source identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        source_id: str,
        artifact_id: str,
        artifact_kind: IRArtifactKind,
        document_json: bytes,
        producer_id: str,
        producer_version: str,
        config_digest: str,
    ) -> IRArtifactInput:
        return cls(
            source_id=source_id,
            source_ids=(source_id,),
            artifact_id=artifact_id,
            artifact_kind=artifact_kind,
            document_sha256=sha256_digest(document_json),
            producer_id=producer_id,
            producer_version=producer_version,
            config_digest=config_digest,
            document_json=document_json,
        )


class ConstructionInputs(_StrictModel):
    """Complete declared in-memory inputs for one pure construct-stage run."""

    schema_version: Literal["veriformis.construction-inputs/v1"] = (
        "veriformis.construction-inputs/v1"
    )
    cleaning_config_digest: str
    sources: tuple[SourceRef, ...]
    chunks: tuple[Chunk, ...]
    transforms: tuple[TransformRecord, ...] = ()
    ir_artifacts: tuple[IRArtifactInput, ...] = ()
    reviews: tuple[ReviewEvidence, ...] = ()

    @model_validator(mode="after")
    def _validate_inputs(self) -> ConstructionInputs:
        validate_sha256(self.cleaning_config_digest)
        source_ids: list[str] = []
        sources_by_id: dict[str, SourceRef] = {}
        for source in self.sources:
            _validate_source(source)
            source_ids.append(source.id)
            sources_by_id[source.id] = source
        _require_unique(source_ids, "construction source")

        chunk_ids: list[str] = []
        for chunk in self.chunks:
            chunk_to_dict(chunk)
            if chunk.source_id not in sources_by_id:
                raise ValueError("construction chunk names an undeclared source")
            assert chunk.evidence is not None
            resolved = resolve_evidence(chunk.evidence, sources_by_id)
            if resolved != chunk.text:
                raise ValueError("construction chunk does not resolve exactly")
            chunk_ids.append(chunk.id)
        _require_unique(chunk_ids, "construction chunk")

        transform_ids: list[str] = []
        for record in self.transforms:
            validate_transform_record(record)
            if record.source_id not in sources_by_id:
                raise ValueError("construction transform names an undeclared source")
            transform_ids.append(record.id)
        _require_unique(transform_ids, "construction transform")

        artifact_ids: list[str] = []
        artifact_keys: list[tuple[str, str]] = []
        for artifact in self.ir_artifacts:
            if artifact.source_id not in sources_by_id:
                raise ValueError("construction IR artifact names an undeclared source")
            artifact_ids.append(artifact.artifact_id)
            artifact_keys.append((artifact.source_id, artifact.artifact_kind))
        _require_unique(artifact_ids, "construction IR artifact")
        _require_unique(artifact_keys, "construction IR artifact source/kind")

        review_ids: list[str] = []
        for review in self.reviews:
            # A fresh strict round-trip catches objects created by unchecked copy.
            ReviewEvidence.model_validate_json(
                lossless_json_bytes(review.model_dump(mode="json"))
            )
            review_ids.append(review.review_id)
        _require_unique(review_ids, "construction review")
        return self

    @classmethod
    def create(
        cls,
        *,
        sources: Sequence[SourceRef],
        chunks: Sequence[Chunk],
        cleaning_config_digest: str,
        transforms: Sequence[TransformRecord] = (),
        ir_artifacts: Sequence[IRArtifactInput] = (),
        reviews: Sequence[ReviewEvidence] = (),
    ) -> ConstructionInputs:
        """Create inputs without making caller order semantically significant."""
        return cls(
            cleaning_config_digest=cleaning_config_digest,
            sources=tuple(sources),
            chunks=tuple(chunks),
            transforms=tuple(transforms),
            ir_artifacts=tuple(ir_artifacts),
            reviews=tuple(reviews),
        )

    def input_digest(self) -> str:
        """Digest the complete semantic input set in canonical identity order."""
        return canonical_digest(
            {
                "schema_version": self.schema_version,
                "cleaning_config_digest": self.cleaning_config_digest,
                "sources": sorted(
                    (_source_payload(source) for source in self.sources),
                    key=lambda value: value["id"],
                ),
                "chunks": sorted(
                    (chunk_to_dict(chunk) for chunk in self.chunks),
                    key=lambda value: value["id"],
                ),
                "transforms": sorted(
                    (transform_record_to_dict(record) for record in self.transforms),
                    key=lambda value: value["id"],
                ),
                "ir_artifacts": sorted(
                    (
                        {
                            "schema_version": artifact.schema_version,
                            "source_id": artifact.source_id,
                            "source_ids": artifact.source_ids,
                            "artifact_id": artifact.artifact_id,
                            "artifact_kind": artifact.artifact_kind,
                            "document_sha256": artifact.document_sha256,
                            "producer_id": artifact.producer_id,
                            "producer_version": artifact.producer_version,
                            "config_digest": artifact.config_digest,
                        }
                        for artifact in self.ir_artifacts
                    ),
                    key=lambda value: value["artifact_id"],
                ),
                "reviews": sorted(
                    (review.model_dump(mode="json") for review in self.reviews),
                    key=lambda value: value["review_id"],
                ),
            }
        )


def construct_dataset(
    recipe: DatasetRecipe,
    inputs: ConstructionInputs,
) -> ConstructionResult:
    """Execute every declared pass and return the immutable lifecycle result."""
    checked_recipe, checked_inputs = _validate_recipe_inputs(recipe, inputs)
    return _construct_dataset_validated(checked_recipe, checked_inputs)


def _construct_dataset_validated(
    recipe: DatasetRecipe,
    inputs: ConstructionInputs,
) -> ConstructionResult:
    """Execute construction from values freshly checked at a public boundary."""
    candidates: list[CandidateRecord] = []
    diagnostics = []
    ordinal = 1
    chunk_source_ids = {chunk.source_id for chunk in inputs.chunks}
    for construction_pass in recipe.passes:
        constructor = get_constructor(
            construction_pass.constructor_id,
            construction_pass.constructor_version,
        )
        output = constructor(
            recipe,
            construction_pass,
            inputs.sources,
            inputs.chunks,
            inputs.transforms,
            inputs.ir_artifacts,
        )
        for draft in sorted(output.drafts, key=lambda item: item.order_key):
            candidate = CandidateRecord.create(
                ordinal=ordinal,
                recipe_id=recipe.recipe_id,
                objective_id=recipe.objective.objective_id,
                pass_id=construction_pass.pass_id,
                source_ids=draft.source_ids,
                chunk_ids=draft.chunk_ids,
                transform_ids=draft.transform_ids,
                fields=draft.fields,
            )
            _validate_candidate(recipe, inputs, candidate)
            candidates.append(candidate)
            ordinal += 1
        missing_source_diagnostics = tuple(
            ConstructionDiagnostic.create(
                code="source-chunks-unavailable",
                message="selected source has no constructed input chunks",
                pass_id=construction_pass.pass_id,
                source_ids=(source_id,),
            )
            for source_id in recipe.source_ids
            if source_id not in chunk_source_ids
        )
        diagnostics.extend(
            sorted(
                (*missing_source_diagnostics, *output.diagnostics),
                key=lambda item: (
                    item.source_ids,
                    item.chunk_ids,
                    item.input_key,
                    item.code,
                    item.diagnostic_id,
                ),
            )
        )

    decisions, records = _decide(recipe, inputs.reviews, tuple(candidates))
    return ConstructionResult.create(
        recipe_id=recipe.recipe_id,
        input_digest=inputs.input_digest(),
        executed_pass_ids=tuple(item.pass_id for item in recipe.passes),
        candidates=tuple(candidates),
        decisions=decisions,
        records=records,
        diagnostics=tuple(diagnostics),
    )


def validate_construction_result(
    recipe: DatasetRecipe,
    inputs: ConstructionInputs,
    result: ConstructionResult,
) -> ConstructionResult:
    """Replay construction and require byte-semantic equality with a result."""
    checked_recipe, checked_inputs = _validate_recipe_inputs(recipe, inputs)
    # Revalidate nested IDs before comparing against the replay result.
    try:
        checked = ConstructionResult.model_validate_json(
            lossless_json_bytes(result.model_dump(mode="json"))
        )
    except (TypeError, ValueError) as exc:
        raise ConstructionError(f"invalid construction result: {exc}") from exc
    expected = _construct_dataset_validated(checked_recipe, checked_inputs)
    if checked != expected:
        raise ConstructionError("construction result does not match exact replay")
    return checked


def _validate_recipe_inputs(
    recipe: DatasetRecipe,
    inputs: ConstructionInputs,
) -> tuple[DatasetRecipe, ConstructionInputs]:
    # Revalidate identities in case an unchecked model copy reached the boundary.
    try:
        checked_recipe = DatasetRecipe.model_validate_json(
            lossless_json_bytes(recipe.model_dump(mode="json"))
        )
    except VeriformisError:
        raise
    except (AttributeError, TypeError, UnicodeError, ValueError) as exc:
        raise ConstructionError(f"invalid dataset recipe: {exc}") from exc
    try:
        checked_inputs = ConstructionInputs.model_validate_json(
            lossless_json_bytes(inputs.model_dump(mode="json"))
        )
    except VeriformisError:
        raise
    except (AttributeError, TypeError, UnicodeError, ValueError) as exc:
        raise ConstructionError(f"invalid construction inputs: {exc}") from exc

    source_ids = {source.id for source in checked_inputs.sources}
    if checked_inputs.cleaning_config_digest != checked_recipe.cleaning_config_digest:
        raise ConstructionError(
            "construction input cleaning config does not match dataset recipe"
        )
    if source_ids != set(checked_recipe.source_ids):
        raise ConstructionError(
            "construction inputs must cover exactly the recipe source selection"
        )
    if {chunk.source_id for chunk in checked_inputs.chunks} - source_ids:
        raise ConstructionError("construction chunk scope exceeds the recipe")
    for chunk in checked_inputs.chunks:
        context = chunk.identity_context
        if context.get("strategy") != checked_recipe.segmentation.strategy:
            raise ConstructionError("chunk strategy does not match dataset recipe")
        if checked_recipe.segmentation.strategy in {
            "paragraph",
            "sentence",
            "structure",
        }:
            if context.get("max_size") != checked_recipe.segmentation.size:
                raise ConstructionError("chunk size does not match dataset recipe")
        else:
            if (
                context.get("size") != checked_recipe.segmentation.size
                or context.get("overlap") != checked_recipe.segmentation.overlap
            ):
                raise ConstructionError(
                    "chunk size or overlap does not match dataset recipe"
                )
    return checked_recipe, checked_inputs


def _validate_candidate(
    recipe: DatasetRecipe,
    inputs: ConstructionInputs,
    candidate: CandidateRecord,
) -> None:
    expected_names = OBJECTIVE_FIELD_CONTRACTS[recipe.objective.kind]
    if tuple(field.name for field in candidate.fields) != expected_names:
        raise ConstructionError("candidate fields do not match objective semantics")
    source_map = {source.id: source for source in inputs.sources}
    chunks_by_id = {chunk.id: chunk for chunk in inputs.chunks}
    transforms_by_id = {record.id: record for record in inputs.transforms}
    artifacts_by_id = {
        artifact.artifact_id: artifact for artifact in inputs.ir_artifacts
    }
    if any(chunk_id not in chunks_by_id for chunk_id in candidate.chunk_ids):
        raise ConstructionError("candidate names an undeclared chunk")
    if any(transform_id not in transforms_by_id for transform_id in candidate.transform_ids):
        raise ConstructionError("candidate names an undeclared transform")
    chunk_sources = {
        chunks_by_id[chunk_id].source_id for chunk_id in candidate.chunk_ids
    }
    if chunk_sources != set(candidate.source_ids):
        raise ConstructionError("candidate source binding is not exact")
    for field in candidate.fields:
        evidence = field.evidence
        if isinstance(evidence, SourceTextEvidence):
            if evidence.evidence.source_id not in candidate.source_ids:
                raise ConstructionError("field evidence names another candidate source")
            resolved = resolve_evidence(evidence.evidence, source_map)
        elif isinstance(evidence, IRFieldEvidence):
            if evidence.source_id not in candidate.source_ids:
                raise ConstructionError("IR evidence names another candidate source")
            artifact = artifacts_by_id.get(evidence.artifact_id)
            if artifact is None:
                raise ConstructionError("IR evidence names an undeclared artifact")
            resolved = resolve_ir_field_evidence(
                evidence,
                source_id=artifact.source_id,
                artifact_id=artifact.artifact_id,
                artifact_kind=artifact.artifact_kind,
                document_json=artifact.document_json,
                context=construction_field_context(
                    recipe,
                    next(
                        item
                        for item in recipe.passes
                        if item.pass_id == candidate.pass_id
                    ),
                    field.name,
                    candidate.chunk_ids,
                    json_pointer=evidence.json_pointer,
                ),
            )
        else:  # pragma: no cover - discriminated model excludes this branch.
            raise ConstructionError("candidate field has unsupported evidence")
        if resolved != field.value:
            raise ConstructionError("candidate field value does not resolve exactly")


def _decide(
    recipe: DatasetRecipe,
    reviews: tuple[ReviewEvidence, ...],
    candidates: tuple[CandidateRecord, ...],
) -> tuple[tuple[PromotionDecision, ...], tuple[DatasetRecord, ...]]:
    candidate_ids = {candidate.candidate_id for candidate in candidates}
    reviews_by_candidate: dict[str, ReviewEvidence] = {}
    for review in reviews:
        if review.candidate_id not in candidate_ids:
            raise ConstructionError("review evidence names an unknown candidate")
        if review.candidate_id in reviews_by_candidate:
            raise ConstructionError("candidate has more than one review evidence value")
        reviews_by_candidate[review.candidate_id] = review
    if recipe.review_policy == "none" and reviews_by_candidate:
        raise ConstructionError("no-review recipe received undeclared review evidence")

    decisions: list[PromotionDecision] = []
    records: list[DatasetRecord] = []
    for candidate in candidates:
        review = reviews_by_candidate.get(candidate.candidate_id)
        if recipe.review_policy == "none":
            decision = PromotionDecision.create(
                candidate_id=candidate.candidate_id,
                status="accepted",
                reason_codes=("construction-integrity-v1",),
            )
        elif review is None:
            decision = PromotionDecision.create(
                candidate_id=candidate.candidate_id,
                status="pending_review",
                reason_codes=("review-required",),
            )
        else:
            decision = PromotionDecision.create(
                candidate_id=candidate.candidate_id,
                status=review.verdict,
                reason_codes=(
                    "review-approved"
                    if review.verdict == "accepted"
                    else "review-rejected",
                ),
                review=review,
            )
        decisions.append(decision)
        if decision.status == "accepted":
            records.append(DatasetRecord.promote(candidate, decision))
    return tuple(decisions), tuple(records)


def _validate_source(source: SourceRef) -> None:
    if not isinstance(source, SourceRef):
        raise ValueError("construction source must use SourceRef")
    validate_id(source.id, kind="src")
    validate_id(source.artifact_id, kind="art")
    validate_sha256(source.sha256)
    validate_sha256(source.stream_sha256)
    if type(source.size) is not int or source.size < 0:
        raise ValueError("construction source size must be non-negative")
    if not isinstance(source.parser, str) or not source.parser:
        raise ValueError("construction source parser must be non-empty")
    if not isinstance(source.parser_version, str) or not source.parser_version:
        raise ValueError("construction source parser version must be non-empty")
    if sha256_digest(source.extracted_text) != source.stream_sha256:
        raise ValueError("construction source stream digest mismatch")
    if derive_source_id(source.logical_path, source.sha256) != source.id:
        raise ValueError("construction source identity mismatch")
    config_digest = canonical_digest(
        {
            "parser": source.parser,
            "parser_version": source.parser_version,
            "canonical_stream_contract_version": (
                source.canonical_stream_contract_version
            ),
        }
    )
    expected_artifact_id = derive_artifact_id(
        kind="canonical-source-text",
        content_sha256=source.stream_sha256,
        source_ids=(source.id,),
        producer_id=f"veriformis.parser.{source.parser}",
        producer_version=source.parser_version,
        config_digest=config_digest,
    )
    if source.artifact_id != expected_artifact_id:
        raise ValueError("construction source artifact identity mismatch")


def _source_payload(source: SourceRef) -> dict[str, Any]:
    return {
        "id": source.id,
        "logical_path": source.logical_path,
        "raw_sha256": source.sha256,
        "size": source.size,
        "parser": source.parser,
        "parser_version": source.parser_version,
        "canonical_stream_contract_version": (
            source.canonical_stream_contract_version
        ),
        "stream_sha256": source.stream_sha256,
        "artifact_id": source.artifact_id,
    }


def _require_unique(values: Sequence[Any], label: str) -> None:
    if len(values) != len(set(values)):
        raise DuplicateIdentityError(f"{label} identities contain duplicates")


__all__ = [
    "ConstructionInputs",
    "IRArtifactInput",
    "construct_dataset",
    "validate_construction_result",
]
