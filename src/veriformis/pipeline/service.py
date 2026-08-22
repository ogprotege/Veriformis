"""Surface-neutral pipeline orchestration for Veriformis.

``PipelineService`` owns stage policy and workspace transactions. Interface
adapters (CLI, future MCP or application shells) translate arguments and
results only; they must not reimplement stage rules.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import veriformis
from pydantic import ValidationError

from veriformis.bundle import (
    BundleArchiveReceipt,
    BundleAttestation,
    BundlePublicationReceipt,
    FinishedBundleManifest,
    VerificationResult,
    build_finished_bundle,
    verify_finished_bundle,
    verify_bundle_archive,
    write_bundle_archive,
    write_finished_bundle,
)
from veriformis.bundle.finished import FinishedBundleError
from veriformis.chunkers.base import Chunk, chunk_from_dict, chunk_to_dict, flatten
from veriformis.chunkers.pipeline import build_chunks
from veriformis.chunkers.strategies import (
    chunk_fixed,
    chunk_paragraph,
    chunk_sentence,
    chunk_sliding,
    chunk_structure,
)
from veriformis.construction import (
    ConstructionInputs,
    DatasetRecipe,
    IRArtifactInput,
    ReviewEvidence,
    construct_dataset,
    construction_result_from_json_bytes,
    construction_result_to_dict,
    dataset_recipe_from_json_bytes,
    dataset_recipe_to_dict,
    validate_construction_result,
)
from veriformis.contracts import (
    CURATION_STAGE_SCHEMA_ID,
    FORMAT_STAGE_SCHEMA_ID,
    SEAL_STAGE_SCHEMA_ID,
    SPLIT_STAGE_SCHEMA_ID,
    VALIDATION_STAGE_SCHEMA_ID,
)
from veriformis.datasets import (
    DatasetValidationReport,
    FinishedDatasetPlan,
    SerializationOutput,
    curate_dataset,
    curation_result_from_json_bytes,
    curation_result_to_dict,
    dataset_snapshot_json_bytes,
    dataset_validation_report_from_json_bytes,
    dataset_validation_report_json_bytes,
    finished_dataset_plan_from_json_bytes,
    finished_dataset_plan_to_dict,
    row_set_from_json_bytes,
    row_set_to_dict,
    serialize_dataset,
    split_dataset,
    split_result_from_json_bytes,
    split_result_to_dict,
    validate_finished_dataset,
)
from veriformis.errors import (
    GoalCatalogError,
    MissingStageInputError,
    ConstructionError,
    ParseError,
    TaxonomyError,
    UnsupportedWorkspaceVersionError,
)
from veriformis.exports import (
    CancellationCheck,
    DEFAULT_EXPORT_SERVICE,
    ExportDiscovery,
    ExportDryRunPreview,
    ExportDryRunRequest,
    ExportDryRunRequestV2,
    ExportExecuteRequest,
    ExportExecuteRequestV2,
    ExportInspectRequest,
    ExportInspection,
    ExportPackArchiveReceipt,
    ExportPublicationOutcome,
    ExportPlan,
    ExportService,
    ExportVerifiedOutcome,
    ExportVerifyRequest,
    ExportVerifyRequestV2,
    verify_export_pack_archive,
    write_export_pack_archive,
)
from veriformis.diagnostics import (
    parse_report_from_dict,
    parse_report_to_dict,
    validate_parse_report_locations,
)
from veriformis.evidence import (
    DerivationStep,
    EvidenceError,
    resolve_evidence,
)
from veriformis.identity import (
    canonical_digest,
    lossless_json_bytes,
    sha256_digest,
)
from veriformis.ir import (
    document_from_dict,
    document_to_dict,
    iter_document_blocks,
    validate_document_against_stream,
)
from veriformis.parsers.dispatch import CODE_EXTENSIONS, parse_captured_source
from veriformis.rules.cleaning import (
    cleaning_plan_from_dict,
    cleaning_plan_to_dict,
    cleaning_input_digest,
    expected_transform_records,
    plan_cleaning,
    replay_cleaning_plan,
)
from veriformis.rules.engine import (
    Rule,
    TransformRecord,
    transform_record_from_dict,
    transform_record_to_dict,
)
from veriformis.rules.derivations import (
    block_derivations_from_dict,
    block_derivations_to_dict,
    build_block_derivations,
    load_exact_block_derivations,
)
from veriformis.rules.library import rules_from_clean_config, select_rules
from veriformis.sources import (
    ParseResult,
    SourceRef,
    capture_source_batch,
)
from veriformis.taxonomy import (
    implemented_discovery,
    require_identifier,
)
from veriformis.workspace import (
    CONSTRUCTION_STAGE_CONFIG_SCHEMA_VERSION,
    WORKSPACE_REVISION_SCHEMA_VERSION,
    SourceDescriptor,
    Workspace,
    WorkspaceRevision,
)

if TYPE_CHECKING:
    from veriformis.goals.preflight import CompilePreflight
    from veriformis.goals.preview import GoalPreview

_CODE_EXTS = CODE_EXTENSIONS
_STRATEGIES = {
    "paragraph": chunk_paragraph,
    "fixed": chunk_fixed,
    "sliding": chunk_sliding,
    "sentence": chunk_sentence,
    "structure": chunk_structure,
}


@dataclass(frozen=True)
class ServiceMessage:
    """Adapter-facing status line produced by a stage."""

    text: str
    stream: Literal["stdout", "stderr"] = "stdout"
    kind: str = "info"


@dataclass(frozen=True)
class StageOutcome:
    """Common envelope for stage results returned to adapters."""

    messages: tuple[ServiceMessage, ...] = ()
    exit_status: int = 0
    durability_warning: str | None = None
    revision_id: str | None = None


@dataclass(frozen=True)
class ParseOutcome(StageOutcome):
    source_count: int = 0


@dataclass(frozen=True)
class CleanOutcome(StageOutcome):
    document_count: int = 0
    transform_count: int = 0
    unchanged: bool = False


@dataclass(frozen=True)
class ChunkOutcome(StageOutcome):
    chunk_count: int = 0


@dataclass(frozen=True)
class UpgradeOutcome(StageOutcome):
    previous_schema_version: str | None = None
    schema_version: str | None = None
    already_current: bool = False


@dataclass(frozen=True)
class ConstructOutcome(StageOutcome):
    candidate_count: int = 0
    record_count: int = 0
    diagnostic_count: int = 0
    recipe_id: str | None = None
    result_id: str | None = None


@dataclass(frozen=True)
class CurateOutcome(StageOutcome):
    included_count: int = 0
    excluded_count: int = 0
    quarantined_count: int = 0
    plan_id: str | None = None
    coverage_blockers: tuple[str, ...] = ()


@dataclass(frozen=True)
class SplitOutcome(StageOutcome):
    train_record_count: int = 0
    evaluation_record_count: int = 0
    group_count: int = 0
    assignment_digest: str | None = None


@dataclass(frozen=True)
class FormatOutcome(StageOutcome):
    train_row_count: int = 0
    evaluation_row_count: int = 0
    row_schema: str | None = None


@dataclass(frozen=True)
class ValidateOutcome(StageOutcome):
    report: DatasetValidationReport | None = None
    snapshot_id: str | None = None


@dataclass(frozen=True)
class SealOutcome(StageOutcome):
    publication: BundlePublicationReceipt | None = None
    bundle_visible_without_receipt: bool = False


@dataclass(frozen=True)
class VerifyOutcome(StageOutcome):
    verification: VerificationResult | None = None


@dataclass(frozen=True)
class PackageOutcome(StageOutcome):
    receipt: BundleArchiveReceipt | ExportPackArchiveReceipt | None = None


class SealPartialPublicationError(Exception):
    """Bundle bytes became visible but the workspace seal receipt did not commit."""

    def __init__(
        self,
        publication: BundlePublicationReceipt,
        cause: BaseException,
    ) -> None:
        self.publication = publication
        self.cause = cause
        super().__init__(str(cause))


@dataclass(frozen=True)
class PreviewSourceView:
    logical_path: str
    before_text: str
    after_text: str
    plan_id: str
    records: tuple[TransformRecord, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class PreviewOutcome(StageOutcome):
    is_workspace: bool = False
    sources: tuple[PreviewSourceView, ...] = ()


@dataclass(frozen=True)
class VersionOutcome(StageOutcome):
    version: str = ""


@dataclass(frozen=True)
class GoalPreviewOutcome(StageOutcome):
    preview: GoalPreview | None = None


@dataclass(frozen=True)
class CompilePreflightOutcome(StageOutcome):
    preflight: CompilePreflight | None = None


@dataclass(frozen=True)
class ExportDiscoveryOutcome(StageOutcome):
    discovery: ExportDiscovery | None = None


@dataclass(frozen=True)
class ExportPlanOutcome(StageOutcome):
    plan: ExportPlan | None = None
    preview: ExportDryRunPreview | None = None


@dataclass(frozen=True)
class ExportInspectionOutcome(StageOutcome):
    inspection: ExportInspection | None = None


@dataclass(frozen=True)
class ExportExecutionOutcome(StageOutcome):
    publication: ExportPublicationOutcome | None = None


@dataclass(frozen=True)
class ExportVerifyOutcome(StageOutcome):
    verified: ExportVerifiedOutcome | None = None



def _parse_one(path: Path, *, logical_path: str, raw_bytes: bytes) -> ParseResult:
    return parse_captured_source(
        path,
        logical_path=logical_path,
        raw_bytes=raw_bytes,
    )


def _require_accepted_parse(result: ParseResult, *, logical_path: str) -> None:
    if result.diagnostics.status != "refused":
        return
    codes = sorted(
        diagnostic.code
        for diagnostic in result.diagnostics.diagnostics
        if diagnostic.severity == "error"
    )
    detail = ", ".join(codes) if codes else "unspecified-parser-error"
    raise ParseError(f"parser refused {logical_path}: {detail}")


def _recover_exact_finished_bundle(
    target: Path,
    *,
    files: dict[str, bytes],
    manifest: FinishedBundleManifest,
    attestation: BundleAttestation,
    manifest_bytes: bytes,
    attestation_bytes: bytes,
    expected_report: DatasetValidationReport,
) -> BundlePublicationReceipt:
    """Adopt only an independently verified, byte-identical prior publication."""
    expected_manifest_sha256 = sha256_digest(manifest_bytes)
    verification = verify_finished_bundle(
        target,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    if (
        verification.bundle_id != manifest.bundle_id
        or verification.dataset_snapshot_id != manifest.dataset_snapshot_id
        or verification.validation_report_id != manifest.validation_report_id
        or verification.content_root_sha256 != manifest.content_root_sha256
        or verification.trust_grade != "external_digest"
    ):
        raise FinishedBundleError(
            "existing finished bundle does not match the current dataset binding"
        )

    expected_files = {
        "manifest.json": manifest_bytes,
        "attestation.json": attestation_bytes,
        **files,
    }
    try:
        observed_files = {
            relative_path: (target / relative_path).read_bytes()
            for relative_path in expected_files
        }
    except OSError as exc:
        raise FinishedBundleError(
            f"existing finished bundle changed during recovery: {exc}"
        ) from exc
    mismatched = sorted(
        path
        for path, expected in expected_files.items()
        if observed_files[path] != expected
    )
    if mismatched:
        raise FinishedBundleError(
            "existing finished bundle differs from the current exact payload: "
            f"{mismatched}"
        )
    recovered_report = dataset_validation_report_from_json_bytes(
        observed_files["validation.json"]
    )
    if recovered_report != expected_report:
        raise FinishedBundleError(
            "existing finished bundle report or snapshot differs from the current "
            "validated dataset"
        )

    final_verification = verify_finished_bundle(
        target,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    if final_verification != verification:
        raise FinishedBundleError(
            "existing finished bundle changed during exact recovery"
        )
    return BundlePublicationReceipt(
        bundle_path=target,
        manifest=manifest,
        attestation=attestation,
        manifest_bytes=manifest_bytes,
        attestation_bytes=attestation_bytes,
        manifest_sha256=expected_manifest_sha256,
        verification=final_verification,
        durability_warning=None,
    )


def _json_load(data: bytes) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number is not allowed: {value}")

    def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise EvidenceError(f"persisted JSON contains duplicate key {key!r}")
            value[key] = item
        return value

    try:
        return json.loads(
            data.decode("utf-8"),
            object_pairs_hook=strict_object,
            parse_constant=reject_constant,
        )
    except EvidenceError:
        raise
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise EvidenceError(
            f"persisted artifact is not valid UTF-8 JSON: {exc}"
        ) from exc


def _output_bytes(
    workspace: Workspace,
    revision: WorkspaceRevision,
    stage: str,
    key: str,
) -> bytes:
    try:
        artifact_id = revision.stages[stage].outputs[key]
    except KeyError as exc:
        raise EvidenceError(f"workspace stage {stage!r} lacks output {key!r}") from exc
    return workspace.read_artifact(artifact_id, revision=revision)


def _load_sources(
    workspace: Workspace,
    revision: WorkspaceRevision,
) -> dict[str, SourceRef]:
    expected_registry = [
        descriptor.model_dump(mode="json", exclude={"original_path"})
        for descriptor in sorted(revision.sources.values(), key=lambda item: item.id)
    ]
    registry = _json_load(_output_bytes(workspace, revision, "parse", "registry"))
    if registry != expected_registry:
        raise EvidenceError(
            "parse registry does not match the active source descriptors"
        )
    sources: dict[str, SourceRef] = {}
    for source_id, descriptor in sorted(revision.sources.items()):
        artifact_id = descriptor.extracted_artifact_id
        if artifact_id is None:
            raise EvidenceError(f"source {source_id} has no canonical text artifact")
        extracted = workspace.read_artifact(artifact_id, revision=revision).decode(
            "utf-8"
        )
        report = parse_report_from_dict(
            _json_load(
                _output_bytes(
                    workspace,
                    revision,
                    "parse",
                    f"source/{source_id}/diagnostics",
                )
            )
        )
        if descriptor.raw_artifact_id is None:
            raise EvidenceError(f"source {source_id} has no captured raw artifact")
        raw_bytes = workspace.read_artifact(
            descriptor.raw_artifact_id,
            revision=revision,
        )
        try:
            validate_parse_report_locations(report, raw_bytes)
        except ParseError as exc:
            raise EvidenceError(
                f"parse report locations for {source_id} exceed the captured source"
            ) from exc
        if (
            report.source_id != source_id
            or report.parser_name != descriptor.parser_id
            or report.parser_version != descriptor.parser_version
            or report.status == "refused"
        ):
            raise EvidenceError(
                f"parse report for {source_id} does not match its source descriptor"
            )
        expected = parse_captured_source(
            descriptor.logical_path,
            logical_path=descriptor.logical_path,
            raw_bytes=raw_bytes,
        )
        document = document_from_dict(
            _json_load(
                _output_bytes(
                    workspace,
                    revision,
                    "parse",
                    f"source/{source_id}/document",
                )
            )
        )
        expected_source = expected.source
        descriptor_semantics = (
            descriptor.id,
            descriptor.logical_path,
            descriptor.sha256,
            descriptor.size,
            descriptor.parser_id,
            descriptor.parser_version,
            descriptor.canonical_stream_contract_version,
            descriptor.extracted_artifact_id,
        )
        expected_semantics = (
            expected_source.id,
            expected_source.logical_path,
            expected_source.sha256,
            expected_source.size,
            expected_source.parser,
            expected_source.parser_version,
            expected_source.canonical_stream_contract_version,
            expected_source.artifact_id,
        )
        if descriptor_semantics != expected_semantics:
            raise EvidenceError(
                f"source descriptor {source_id} does not match captured raw bytes"
            )
        if (
            extracted != expected_source.extracted_text
            or document != expected.document
            or report != expected.diagnostics
        ):
            raise EvidenceError(
                f"parse artifacts for {source_id} do not match captured raw bytes"
            )
        sources[source_id] = expected_source
    return sources


def _cleaning_input_digest(source: SourceRef, document: Any) -> str:
    """Identify the exact, portable parse snapshot consumed by cleaning."""
    return cleaning_input_digest(
        document,
        source_id=source.id,
        raw_sha256=source.sha256,
        canonical_artifact_id=source.artifact_id,
        canonical_stream_sha256=source.stream_sha256,
        parser=source.parser,
        parser_version=source.parser_version,
        canonical_stream_contract_version=(source.canonical_stream_contract_version),
    )


def _load_documents(
    workspace: Workspace,
    revision: WorkspaceRevision,
    *,
    stage: str,
) -> dict[str, Any]:
    configured_rules = (
        rules_from_clean_config(revision.stages["clean"].config)
        if stage == "clean"
        else None
    )
    parsed_documents = (
        _load_documents(workspace, revision, stage="parse")
        if stage == "clean"
        else None
    )
    parsed_sources = _load_sources(workspace, revision) if stage == "clean" else None
    documents = {}
    for source_id in sorted(revision.sources):
        value = _json_load(
            _output_bytes(
                workspace,
                revision,
                stage,
                f"source/{source_id}/document",
            )
        )
        document = document_from_dict(value)
        if document.source_id != source_id:
            raise EvidenceError(
                f"document source {document.source_id!r} does not match {source_id!r}"
            )
        descriptor = revision.sources[source_id]
        if descriptor.extracted_artifact_id is None:
            raise EvidenceError(f"source {source_id} has no canonical text artifact")
        canonical_stream = workspace.read_artifact(
            descriptor.extracted_artifact_id,
            revision=revision,
        ).decode("utf-8")
        validate_document_against_stream(
            document,
            canonical_stream,
            exact=stage == "parse",
        )
        if stage == "clean":
            plan = cleaning_plan_from_dict(
                _json_load(
                    _output_bytes(
                        workspace,
                        revision,
                        "clean",
                        f"source/{source_id}/cleaning-plan",
                    )
                )
            )
            expected_input = _cleaning_input_digest(
                parsed_sources[source_id], parsed_documents[source_id]
            )
            if plan.base_input_sha256 != expected_input:
                raise EvidenceError(
                    f"cleaning plan for {source_id} is not bound to its parse input"
                )
            expected_preview = plan_cleaning(
                parsed_documents[source_id],
                configured_rules,
                max_remove_frac=(
                    revision.stages["clean"].config["max_remove_ppm"] / 1_000_000
                ),
                base_input_sha256=expected_input,
            )
            if plan != expected_preview.plan:
                raise EvidenceError(
                    f"cleaning plan for {source_id} is not the configured replay"
                )
            if document != expected_preview.document:
                raise EvidenceError(
                    f"cleaned document for {source_id} does not match its replayable plan"
                )
        documents[source_id] = document
    return documents


def _load_transform_records(
    workspace: Workspace,
    revision: WorkspaceRevision,
) -> list[TransformRecord]:
    _load_documents(workspace, revision, stage="clean")
    raw = _json_load(_output_bytes(workspace, revision, "clean", "transforms"))
    if not isinstance(raw, list):
        raise EvidenceError("transform artifact must contain a JSON array")
    records = [transform_record_from_dict(value) for value in raw]
    record_ids = [record.id for record in records]
    if len(record_ids) != len(set(record_ids)):
        raise EvidenceError("transform artifact contains duplicate identities")
    expected_records: list[TransformRecord] = []
    parsed_documents = _load_documents(workspace, revision, stage="parse")
    for source_id in sorted(revision.sources):
        plan = cleaning_plan_from_dict(
            _json_load(
                _output_bytes(
                    workspace,
                    revision,
                    "clean",
                    f"source/{source_id}/cleaning-plan",
                )
            )
        )
        expected_records.extend(
            expected_transform_records(parsed_documents[source_id], plan)
        )
    if records != expected_records:
        raise EvidenceError(
            "transform artifact metadata does not match cleaning plan replay"
        )
    return records


def _load_chunks(workspace: Workspace, revision: WorkspaceRevision) -> list[Chunk]:
    raw = _json_load(_output_bytes(workspace, revision, "chunk", "chunks"))
    if not isinstance(raw, list):
        raise EvidenceError("chunk artifact must contain a JSON array")
    chunks = [chunk_from_dict(value) for value in raw]
    ids = [chunk.id for chunk in chunks]
    if len(ids) != len(set(ids)):
        raise EvidenceError("chunk artifact contains duplicate identities")
    sources = _load_sources(workspace, revision)
    for chunk in chunks:
        resolved = resolve_evidence(chunk.evidence, sources)
        if resolved != chunk.text:
            raise EvidenceError(
                f"chunk {chunk.id} text does not match its resolved source evidence"
            )
    documents = _load_documents(workspace, revision, stage="clean")
    transforms = _load_transform_records(workspace, revision)
    derivations_by_source: dict[str, dict[int, tuple[DerivationStep, ...]]] = {}
    for source_id, document in sorted(documents.items()):
        plan = cleaning_plan_from_dict(
            _json_load(
                _output_bytes(
                    workspace,
                    revision,
                    "clean",
                    f"source/{source_id}/cleaning-plan",
                )
            )
        )
        artifact_id = revision.stages["clean"].outputs[
            f"source/{source_id}/block-derivations"
        ]
        if revision.artifacts[artifact_id].config_digest != canonical_digest(
            {**revision.stages["clean"].config, "cleaning_plan_id": plan.id}
        ):
            raise EvidenceError(
                "block derivation artifact is not configured for its cleaning plan"
            )
        derivations_by_source[source_id] = _validated_block_derivations(
            _json_load(workspace.read_artifact(artifact_id, revision=revision)),
            source=sources[source_id],
            document=document,
            cleaning_plan_id=plan.id,
        )
    config = revision.stages["chunk"].config
    if set(config) != {"strategy", "size", "overlap"}:
        raise EvidenceError("chunk stage config does not match its v1 schema")
    expected = build_chunks(
        documents,
        sources,
        transforms,
        derivations_by_source,
        strategy=config["strategy"],
        size=config["size"],
        overlap=config["overlap"],
    )
    if chunks != expected:
        raise EvidenceError(
            "chunk artifact does not match deterministic clean-state replay"
        )
    return chunks


def _select_construction_sources(
    revision: WorkspaceRevision,
    selectors: list[str] | None,
) -> tuple[str, ...]:
    """Resolve optional source IDs or logical locators to one exact source set."""
    if not selectors:
        return tuple(sorted(revision.sources))
    by_path = {
        descriptor.logical_path: source_id
        for source_id, descriptor in revision.sources.items()
    }
    selected: list[str] = []
    for selector in selectors:
        source_id = selector if selector in revision.sources else by_path.get(selector)
        if source_id is None:
            raise EvidenceError(f"unknown construction source: {selector!r}")
        selected.append(source_id)
    if len(selected) != len(set(selected)):
        raise EvidenceError("construction source selection contains duplicates")
    return tuple(sorted(selected))


def _load_construction_inputs(
    workspace: Workspace,
    revision: WorkspaceRevision,
    source_ids: tuple[str, ...],
    *,
    reviews: tuple[ReviewEvidence, ...] = (),
) -> ConstructionInputs:
    """Load the exact verified upstream state consumed by construction."""
    selected = set(source_ids)
    all_sources = _load_sources(workspace, revision)
    sources = tuple(all_sources[source_id] for source_id in source_ids)
    chunks = tuple(
        chunk
        for chunk in _load_chunks(workspace, revision)
        if chunk.source_id in selected
    )
    transforms = tuple(
        record
        for record in _load_transform_records(workspace, revision)
        if record.source_id in selected
    )
    clean_state = revision.stages["clean"]
    ir_artifacts: list[IRArtifactInput] = []
    for source_id in source_ids:
        artifact_id = clean_state.outputs[f"source/{source_id}/document"]
        artifact = revision.artifacts[artifact_id]
        ir_artifacts.append(
            IRArtifactInput.create(
                source_id=source_id,
                artifact_id=artifact_id,
                artifact_kind="cleaned-document-ir",
                document_json=workspace.read_artifact(
                    artifact_id,
                    revision=revision,
                ),
                producer_id=artifact.producer_id,
                producer_version=artifact.producer_version,
                config_digest=artifact.config_digest,
            )
        )
    return ConstructionInputs.create(
        cleaning_config_digest=clean_state.config_digest,
        sources=sources,
        chunks=chunks,
        transforms=transforms,
        ir_artifacts=ir_artifacts,
        reviews=reviews,
    )


def _require_group3_revision(revision: WorkspaceRevision) -> None:
    if revision.schema_version != WORKSPACE_REVISION_SCHEMA_VERSION:
        raise UnsupportedWorkspaceVersionError(
            "finished-dataset stages require workspace revision schema 3; run "
            "`veriformis upgrade-workspace WORKSPACE` first"
        )


def _finished_stage_config(schema_version: str, plan_id: str) -> dict[str, str]:
    return {"schema_version": schema_version, "plan_id": plan_id}


def _load_constructed_dataset(
    workspace: Workspace,
    revision: WorkspaceRevision,
) -> tuple[DatasetRecipe, Any, ConstructionInputs]:
    _require_group3_revision(revision)
    recipe = dataset_recipe_from_json_bytes(
        _output_bytes(workspace, revision, "construct", "recipe")
    )
    result = construction_result_from_json_bytes(
        _output_bytes(workspace, revision, "construct", "result")
    )
    # Replay with the review evidence carried on the persisted decisions,
    # exactly as the workspace construct commit gate reconstructs it.
    reviews = tuple(
        decision.review
        for decision in result.decisions
        if decision.review is not None
    )
    inputs = _load_construction_inputs(
        workspace,
        revision,
        recipe.source_ids,
        reviews=reviews,
    )
    validate_construction_result(recipe, inputs, result)
    return recipe, result, inputs


def _load_finished_plan(
    workspace: Workspace,
    revision: WorkspaceRevision,
) -> FinishedDatasetPlan:
    return finished_dataset_plan_from_json_bytes(
        _output_bytes(workspace, revision, "curate", "plan")
    )


def _load_curation_result(workspace: Workspace, revision: WorkspaceRevision):
    return curation_result_from_json_bytes(
        _output_bytes(workspace, revision, "curate", "result")
    )


def _load_split_result(workspace: Workspace, revision: WorkspaceRevision):
    return split_result_from_json_bytes(
        _output_bytes(workspace, revision, "split", "result")
    )


def _load_serialization_output(
    workspace: Workspace,
    revision: WorkspaceRevision,
) -> SerializationOutput:
    row_set = row_set_from_json_bytes(
        _output_bytes(workspace, revision, "format", "row-set")
    )
    output = SerializationOutput(
        row_set=row_set,
        train_jsonl=_output_bytes(workspace, revision, "format", "train"),
        evaluation_jsonl=_output_bytes(
            workspace,
            revision,
            "format",
            "evaluation",
        ),
        provenance_jsonl=_output_bytes(
            workspace,
            revision,
            "format",
            "provenance",
        ),
    )
    if (
        row_set.train_jsonl_sha256 != sha256_digest(output.train_jsonl)
        or row_set.evaluation_jsonl_sha256 != sha256_digest(output.evaluation_jsonl)
        or row_set.provenance_jsonl_sha256 != sha256_digest(output.provenance_jsonl)
    ):
        raise EvidenceError("formatted bytes do not match their row-set digests")
    return output


def _select_rules(rules: str, custom: str) -> tuple[list[Rule], dict[str, Any]]:
    return select_rules(rules, custom)


def _build_block_derivations(
    source: SourceRef,
    document: Any,
    *,
    cleaning_plan_id: str,
) -> dict[int, tuple[DerivationStep, ...]]:
    return build_block_derivations(
        source,
        document,
        cleaning_plan_id=cleaning_plan_id,
    )


def _derivations_to_dict(
    derivations: dict[int, tuple[DerivationStep, ...]],
) -> dict[str, list[dict]]:
    return block_derivations_to_dict(derivations)


def _derivations_from_dict(value: Any) -> dict[int, tuple[DerivationStep, ...]]:
    return block_derivations_from_dict(value)


def _validated_block_derivations(
    value: Any,
    *,
    source: SourceRef,
    document: Any,
    cleaning_plan_id: str,
) -> dict[int, tuple[DerivationStep, ...]]:
    return load_exact_block_derivations(
        value,
        source=source,
        document=document,
        cleaning_plan_id=cleaning_plan_id,
    )


class PipelineService:
    """Typed, surface-neutral orchestration over workspace stages."""

    def __init__(self, *, export_service: ExportService | None = None) -> None:
        self._export_service = (
            DEFAULT_EXPORT_SERVICE if export_service is None else export_service
        )

    @property
    def export_service(self) -> ExportService:
        """Return the sole service authorized to derive exports from bundles."""
        return getattr(self, "_export_service", DEFAULT_EXPORT_SERVICE)

    def discover_taxonomy(self) -> dict[str, tuple[str, ...]]:
        """Return a fresh, adapter-safe copy of implemented taxonomy discovery."""
        return dict(implemented_discovery())

    def discover_goals(self) -> dict[str, Any]:
        """Return a fresh, adapter-safe copy of the versioned goal catalog."""
        from veriformis.goals import discover_goals

        return discover_goals()

    def discover_presets(self) -> dict[str, Any]:
        """Return a fresh, adapter-safe copy of the versioned recipe presets."""
        from veriformis.goals import discover_presets

        return discover_presets()

    def preflight(
        self,
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
    ) -> CompilePreflightOutcome:
        """Evaluate one immutable source capture without opening a workspace."""
        from veriformis.goals import build_compile_preflight

        preflight = build_compile_preflight(
            paths,
            source_root=source_root,
            goal=goal,
            preset=preset,
            representation=representation,
            instruction=instruction,
            rules=rules,
            custom=custom,
            strategy=strategy,
            size=size,
            overlap=overlap,
            split_ratio_ppm=split_ratio_ppm,
            require_review=require_review,
            consumer_profile=consumer_profile,
            minimum_target_characters=minimum_target_characters,
            balance_mode=balance_mode,
            maximum_records_per_primary_source=maximum_records_per_primary_source,
            evaluation_ratio_ppm=evaluation_ratio_ppm,
            evaluation_required=evaluation_required,
            split_seed=split_seed,
            review_policy=review_policy,
        )
        return CompilePreflightOutcome(
            preflight=preflight,
            exit_status=0 if preflight.admitted else 2,
        )

    def preview_goal(
        self,
        workspace: Path,
        *,
        representation: str | None = None,
        instruction: str | None = None,
        record_ids: tuple[str, ...] = (),
    ) -> GoalPreviewOutcome:
        """Preview exactly what a goal's records are and what receives loss.

        Read-only over a workspace at or beyond ``construct``; uses the
        curation decisions and persisted instruction when ``curate`` has run.
        Never opens a transaction, calls a renderer, or touches a destination.
        """
        from veriformis.goals import build_goal_preview
        from veriformis.goals.preview import resolve_preview_representation

        store = Workspace.open(workspace)
        revision = store.head()
        _require_group3_revision(revision)
        if revision.stages["construct"].status != "complete":
            raise MissingStageInputError(
                "goal preview requires a completed construct stage; run "
                "`veriformis construct WORKSPACE --objective OBJECTIVE` first"
            )
        # Resolve the goal and representation from the recipe alone so an
        # incompatible selection fails before any record is read.
        recipe = dataset_recipe_from_json_bytes(
            _output_bytes(store, revision, "construct", "recipe")
        )
        resolve_preview_representation(recipe, representation)
        recipe, result, inputs = _load_constructed_dataset(store, revision)
        curation = None
        persisted_instruction = None
        if revision.stages["curate"].status == "complete":
            curation = _load_curation_result(store, revision)
            plan = _load_finished_plan(store, revision)
            # Non-None only when the persisted row schema is instruction_output.
            persisted_instruction = plan.serialization_plan.instruction_text
        preview = build_goal_preview(
            recipe=recipe,
            result=result,
            inputs=inputs,
            curation=curation,
            representation_id=representation,
            instruction=instruction if instruction is not None else persisted_instruction,
            record_ids=tuple(record_ids),
        )
        return GoalPreviewOutcome(preview=preview)

    def discover_exports(self) -> ExportDiscoveryOutcome:
        """Discover only executable export implementations in the service."""
        return ExportDiscoveryOutcome(
            discovery=self.export_service.discover_exports()
        )

    def dry_run_export(
        self,
        request: ExportDryRunRequest | ExportDryRunRequestV2,
    ) -> ExportPlanOutcome:
        """Derive a source-anchored plan and exact destination-free preview."""
        preview = self.export_service.dry_run_export_preview(request)
        return ExportPlanOutcome(plan=preview.plan, preview=preview)

    def inspect_export(
        self,
        request: ExportInspectRequest,
        *,
        cancellation_check: CancellationCheck | None = None,
    ) -> ExportInspectionOutcome:
        """Inspect self-described physical output without asserting source trust."""
        return ExportInspectionOutcome(
            inspection=self.export_service.inspect_export(
                request,
                cancellation_check=cancellation_check,
            )
        )

    def execute_export(
        self,
        request: ExportExecuteRequest | ExportExecuteRequestV2,
        *,
        cancellation_check: CancellationCheck | None = None,
    ) -> ExportExecutionOutcome:
        """Re-derive and publish an operator-confirmed export plan."""
        return ExportExecutionOutcome(
            publication=self.export_service.execute_export(
                request,
                cancellation_check=cancellation_check,
            )
        )

    def verify_export(
        self,
        request: ExportVerifyRequest | ExportVerifyRequestV2,
        *,
        cancellation_check: CancellationCheck | None = None,
    ) -> ExportVerifyOutcome:
        """Verify destination bytes against re-derived source authority."""
        return ExportVerifyOutcome(
            verified=self.export_service.verify_export(
                request,
                cancellation_check=cancellation_check,
            )
        )

    def parse(
        self,
        paths: list[Path],
        out: Path,
        *,
        source_root: Path | None = None,
    ) -> ParseOutcome:
        """Capture raw files and commit one canonical parse revision."""
        source_captures = capture_source_batch(paths, source_root=source_root)
        captured: list[tuple[Path, bytes]] = []
        for source_capture in source_captures:
            if source_capture.error is not None:
                raise source_capture.error
            assert source_capture.raw_bytes is not None
            captured.append((source_capture.path, source_capture.raw_bytes))
        results = [
            _parse_one(
                path,
                logical_path=source_capture.logical_path,
                raw_bytes=raw_bytes,
            )
            for source_capture, (path, raw_bytes) in zip(
                source_captures,
                captured,
                strict=True,
            )
        ]
        for result in results:
            _require_accepted_parse(
                result,
                logical_path=result.source.logical_path,
            )
        workspace = Workspace.create(out)
        with workspace.begin("parse") as transaction:
            descriptors: list[SourceDescriptor] = []
            outputs: dict[str, Any] = {}
            for (path, raw_bytes), result in sorted(
                zip(captured, results, strict=True),
                key=lambda item: item[1].source.id,
            ):
                source = result.source
                parser_config = {
                    "parser": source.parser,
                    "parser_version": source.parser_version,
                    "canonical_stream_contract_version": (
                        source.canonical_stream_contract_version
                    ),
                }
                raw_artifact = transaction.put_artifact(
                    raw_bytes,
                    kind="raw-source",
                    media_type="application/octet-stream",
                    source_ids=(source.id,),
                    producer_id="veriformis.source-capture",
                    producer_version="1",
                    config={"logical_path": source.logical_path},
                )
                canonical_artifact = transaction.put_artifact(
                    source.extracted_text,
                    kind="canonical-source-text",
                    media_type="text/plain; charset=utf-8",
                    source_ids=(source.id,),
                    producer_id=f"veriformis.parser.{source.parser}",
                    producer_version=source.parser_version,
                    config=parser_config,
                )
                if canonical_artifact.id != source.artifact_id:
                    raise EvidenceError(
                        "parser and workspace canonical artifact IDs differ"
                    )
                document_artifact = transaction.put_artifact(
                    lossless_json_bytes(document_to_dict(result.document)),
                    kind="document-ir",
                    media_type="application/json",
                    source_ids=(source.id,),
                    producer_id=f"veriformis.parser.{source.parser}",
                    producer_version=source.parser_version,
                    config=parser_config,
                )
                diagnostics_artifact = transaction.put_artifact(
                    lossless_json_bytes(parse_report_to_dict(result.diagnostics)),
                    kind="parse-report",
                    media_type="application/json",
                    source_ids=(source.id,),
                    producer_id=f"veriformis.parser.{source.parser}",
                    producer_version=source.parser_version,
                    config=parser_config,
                )
                descriptor = SourceDescriptor.create(
                    logical_path=source.logical_path,
                    original_path=str(path.resolve()),
                    sha256=source.sha256,
                    size=source.size,
                    parser_id=source.parser,
                    parser_version=source.parser_version,
                    canonical_stream_contract_version=(
                        source.canonical_stream_contract_version
                    ),
                    raw_artifact_id=raw_artifact.id,
                    extracted_artifact_id=canonical_artifact.id,
                    document_artifact_id=document_artifact.id,
                )
                descriptors.append(descriptor)
                outputs.update(
                    {
                        f"source/{source.id}/raw": raw_artifact,
                        f"source/{source.id}/canonical": canonical_artifact,
                        f"source/{source.id}/document": document_artifact,
                        f"source/{source.id}/diagnostics": diagnostics_artifact,
                    }
                )
            transaction.set_sources(descriptors)
            registry_artifact = transaction.put_artifact(
                lossless_json_bytes(
                    [
                        descriptor.model_dump(
                            mode="json",
                            exclude={"original_path"},
                        )
                        for descriptor in sorted(descriptors, key=lambda item: item.id)
                    ]
                ),
                kind="source-registry",
                media_type="application/json",
                source_ids=tuple(descriptor.id for descriptor in descriptors),
                producer_id="veriformis.parse-stage",
                producer_version="1",
                config={"source_count": len(descriptors)},
            )
            outputs["registry"] = registry_artifact
            revision = transaction.commit(
                outputs=outputs,
                config={
                    "sources": [
                        descriptor.logical_path
                        for descriptor in sorted(descriptors, key=lambda item: item.id)
                    ]
                },
            )
        return ParseOutcome(
            source_count=len(results),
            revision_id=revision.revision_id,
            durability_warning=workspace.last_commit_durability_warning,
            messages=(
                ServiceMessage(
                    f"parsed {len(results)} source(s) into revision {revision.revision_id}"
                ),
            ),
        )

    def clean(
        self,
        workspace: Path,
        *,
        rules: str = "",
        custom: str = "",
    ) -> CleanOutcome:
        """Plan, replay, and atomically commit cleaning for every source."""
        selected, config = _select_rules(rules, custom)
        store = Workspace.open(workspace)
        current = store.head()
        messages: list[ServiceMessage] = []
        if (
            current.stages["clean"].status == "complete"
            and current.stages["clean"].config == config
        ):
            _load_documents(store, current, stage="clean")
            _load_transform_records(store, current)
            return CleanOutcome(
                unchanged=True,
                revision_id=current.revision_id,
                durability_warning=store.last_commit_durability_warning,
                messages=(
                    ServiceMessage(
                        f"clean unchanged at revision {current.revision_id}"
                    ),
                ),
            )
        with store.begin("clean") as transaction:
            base = transaction.base
            documents = _load_documents(store, base, stage="parse")
            sources = _load_sources(store, base)
            outputs: dict[str, Any] = {}
            transforms: list[dict] = []
            for source_id, document in sorted(documents.items()):
                preview = plan_cleaning(
                    document,
                    selected,
                    base_input_sha256=_cleaning_input_digest(
                        sources[source_id], document
                    ),
                )
                cleaned = replay_cleaning_plan(document, preview.plan)
                for warning in preview.warnings:
                    messages.append(
                        ServiceMessage(
                            f"warning[{source_id}]: {warning}",
                            stream="stderr",
                            kind="warning",
                        )
                    )
                derivations = _build_block_derivations(
                    sources[source_id],
                    cleaned,
                    cleaning_plan_id=preview.plan.id,
                )
                document_artifact = transaction.put_artifact(
                    lossless_json_bytes(document_to_dict(cleaned)),
                    kind="cleaned-document-ir",
                    media_type="application/json",
                    source_ids=(source_id,),
                    producer_id="veriformis.cleaning",
                    producer_version="1",
                    config=config,
                )
                plan_artifact = transaction.put_artifact(
                    lossless_json_bytes(cleaning_plan_to_dict(preview.plan)),
                    kind="cleaning-plan",
                    media_type="application/json",
                    source_ids=(source_id,),
                    producer_id="veriformis.cleaning",
                    producer_version="1",
                    config=config,
                )
                derivation_artifact = transaction.put_artifact(
                    lossless_json_bytes(_derivations_to_dict(derivations)),
                    kind="block-derivations",
                    media_type="application/json",
                    source_ids=(source_id,),
                    producer_id="veriformis.cleaning",
                    producer_version="1",
                    config={**config, "cleaning_plan_id": preview.plan.id},
                )
                outputs.update(
                    {
                        f"source/{source_id}/document": document_artifact,
                        f"source/{source_id}/cleaning-plan": plan_artifact,
                        f"source/{source_id}/block-derivations": derivation_artifact,
                    }
                )
                transforms.extend(
                    transform_record_to_dict(record) for record in preview.records
                )
            transform_artifact = transaction.put_artifact(
                lossless_json_bytes(transforms),
                kind="transform-records",
                media_type="application/json",
                source_ids=tuple(sorted(sources)),
                producer_id="veriformis.cleaning",
                producer_version="1",
                config=config,
            )
            outputs["transforms"] = transform_artifact
            revision = transaction.commit(outputs=outputs, config=config)
        messages.append(
            ServiceMessage(
                f"cleaned {len(documents)} document(s); {len(transforms)} transform "
                f"record(s); revision {revision.revision_id}"
            )
        )
        return CleanOutcome(
            document_count=len(documents),
            transform_count=len(transforms),
            revision_id=revision.revision_id,
            durability_warning=store.last_commit_durability_warning,
            messages=tuple(messages),
        )

    def chunk(
        self,
        workspace: Path,
        *,
        strategy: str | None = None,
        size: int | None = None,
        overlap: int | None = None,
        goal: str | None = None,
        preset: str | None = None,
    ) -> ChunkOutcome:
        """Chunk cleaned documents with exact reconstructible source evidence.

        Omitted settings come from the selected goal's preset, or from the
        recipe-wide preset defaults when no goal or preset is selected.
        """
        from veriformis.goals.presets import (
            SegmentationSettings,
            recipe_defaults,
            resolve_recipe_settings,
        )

        if strategy is not None and strategy not in _STRATEGIES:
            raise ValueError(
                f"unknown strategy: {strategy} (have: {sorted(_STRATEGIES)})"
            )
        try:
            if goal is not None or preset is not None:
                segmentation = resolve_recipe_settings(
                    goal=goal, preset=preset, strategy=strategy, size=size, overlap=overlap
                ).segmentation
            else:
                base = recipe_defaults().segmentation
                segmentation = SegmentationSettings(
                    strategy=base.strategy if strategy is None else strategy,
                    size=base.size if size is None else size,
                    overlap=base.overlap if overlap is None else overlap,
                )
        except GoalCatalogError as exc:
            raise ValueError(exc.message) from exc
        except ValidationError as exc:
            raise ValueError(f"invalid chunk settings: {exc}") from exc
        strategy = segmentation.strategy
        size = segmentation.size
        overlap = segmentation.overlap
        if strategy not in _STRATEGIES:
            raise ValueError(
                f"unknown strategy: {strategy} (have: {sorted(_STRATEGIES)})"
            )
        if size < 1 or overlap < 0 or overlap >= size:
            raise ValueError(
                "size must be positive and overlap must satisfy 0 <= overlap < size"
            )
        config = {"strategy": strategy, "size": size, "overlap": overlap}
        store = Workspace.open(workspace)
        with store.begin("chunk") as transaction:
            base = transaction.base
            documents = _load_documents(store, base, stage="clean")
            sources = _load_sources(store, base)
            raw_transforms = _load_transform_records(store, base)
            derivations_by_source: dict[str, dict[int, tuple[DerivationStep, ...]]] = {}
            for source_id, document in sorted(documents.items()):
                plan = cleaning_plan_from_dict(
                    _json_load(
                        _output_bytes(
                            store,
                            base,
                            "clean",
                            f"source/{source_id}/cleaning-plan",
                        )
                    )
                )
                derivation_artifact_id = base.stages["clean"].outputs[
                    f"source/{source_id}/block-derivations"
                ]
                expected_derivation_config = canonical_digest(
                    {**base.stages["clean"].config, "cleaning_plan_id": plan.id}
                )
                if (
                    base.artifacts[derivation_artifact_id].config_digest
                    != expected_derivation_config
                ):
                    raise EvidenceError(
                        "block derivation artifact is not configured for its cleaning plan"
                    )
                derivations_by_source[source_id] = _validated_block_derivations(
                    _json_load(
                        store.read_artifact(
                            derivation_artifact_id,
                            revision=base,
                        )
                    ),
                    source=sources[source_id],
                    document=document,
                    cleaning_plan_id=plan.id,
                )
            chunks = build_chunks(
                documents,
                sources,
                raw_transforms,
                derivations_by_source,
                strategy=strategy,
                size=size,
                overlap=overlap,
            )
            artifact = transaction.put_artifact(
                lossless_json_bytes([chunk_to_dict(item) for item in chunks]),
                kind="chunks",
                media_type="application/json",
                source_ids=tuple(sorted(sources)),
                producer_id=f"veriformis.chunker.{strategy}",
                producer_version="1",
                config=config,
            )
            revision = transaction.commit(outputs={"chunks": artifact}, config=config)
        return ChunkOutcome(
            chunk_count=len(chunks),
            revision_id=revision.revision_id,
            durability_warning=store.last_commit_durability_warning,
            messages=(
                ServiceMessage(
                    f"wrote {len(chunks)} chunk(s); revision {revision.revision_id}"
                ),
            ),
        )

    def upgrade_workspace(self, workspace: Path) -> UpgradeOutcome:
        """Advance a verified workspace through every supported revision migration."""
        store = Workspace.open(workspace)
        before = store.head()
        revision = store.migrate_to_current(expected_revision_id=before.revision_id)
        already = revision.revision_id == before.revision_id
        if already:
            message = f"workspace already current at revision {revision.revision_id}"
        else:
            message = (
                f"migrated workspace revision schema {before.schema_version} to "
                f"{revision.schema_version}; revision {revision.revision_id}"
            )
        return UpgradeOutcome(
            previous_schema_version=before.schema_version,
            schema_version=revision.schema_version,
            already_current=already,
            revision_id=revision.revision_id,
            durability_warning=store.last_commit_durability_warning,
            messages=(ServiceMessage(message),),
        )

    def construct(
        self,
        workspace: Path,
        *,
        objective: str | None = None,
        goal: str | None = None,
        preset: str | None = None,
        representation: str | None = None,
        source: list[str] | None = None,
        target_row_schema: str | None = None,
        split_ratio_ppm: int | None = None,
        require_review: bool | None = None,
        consumer_profile: str | None = None,
    ) -> ConstructOutcome:
        """Construct evidence-bearing candidates and immutable accepted records.

        Select the goal by plain-language ``goal``, by ``preset``, or by the
        persisted ``objective`` kind; omitted settings come from the preset
        data. The recipe is always built through the named recipe library, so
        every selection path yields the same ``recipe_id`` for the same
        effective settings.
        """
        from veriformis.goals.presets import resolve_recipe_settings
        from veriformis.recipes.library import build_named_recipe

        try:
            if objective is not None:
                require_identifier("objective", objective)
            if target_row_schema is not None:
                require_identifier("semantic_row", target_row_schema)
        except TaxonomyError as exc:
            raise ConstructionError(exc.message) from exc
        try:
            settings = resolve_recipe_settings(
                goal=goal,
                preset=preset,
                representation=representation,
                objective=objective,
                target_row_schema=target_row_schema,
                split_ratio_ppm=split_ratio_ppm,
                require_review=require_review,
                consumer_profile=consumer_profile,
            )
        except GoalCatalogError as exc:
            raise ConstructionError(exc.message) from exc
        objective = settings.objective
        row_schema = settings.row_schema
        store = Workspace.open(workspace)
        current = store.head()
        if "construct" not in current.stages:
            raise UnsupportedWorkspaceVersionError(
                "construct requires workspace revision schema 2 or later; run "
                "`veriformis upgrade-workspace WORKSPACE` first"
            )
        source_ids = _select_construction_sources(current, source)
        inputs = _load_construction_inputs(store, current, source_ids)
        from veriformis.goals import require_goal_input_family

        family_errors: list[str] = []
        for selected_source in sorted(inputs.sources, key=lambda item: item.logical_path):
            try:
                require_goal_input_family(
                    settings.goal_id,
                    logical_path=selected_source.logical_path,
                    parser_id=selected_source.parser,
                )
            except GoalCatalogError as exc:
                family_errors.append(exc.message)
        if family_errors:
            raise ConstructionError(
                "goal input-family admission failed: " + "; ".join(family_errors)
            )
        chunk_config = current.stages["chunk"].config
        if preset is not None:
            expected = settings.segmentation.model_dump()
            observed = {
                "strategy": chunk_config["strategy"],
                "size": chunk_config["size"],
                "overlap": chunk_config["overlap"],
            }
            if observed != expected:
                raise ConstructionError(
                    f"workspace chunks were produced with {observed!r}, but preset "
                    f"{preset!r} expects {expected!r}; re-run `veriformis chunk "
                    f"WORKSPACE --preset {preset}` first"
                )
        recipe = build_named_recipe(
            settings.recipe_library_id,
            source_ids=source_ids,
            cleaning_config_digest=current.stages["clean"].config_digest,
            segmentation={
                "strategy": chunk_config["strategy"],
                "size": chunk_config["size"],
                "overlap": chunk_config["overlap"],
            },
            split_ratio_ppm=settings.construction.split_ratio_ppm,
            require_review=settings.construction.require_review,
            target_row_schema=row_schema,
            consumer_profile=settings.construction.consumer_profile,
        )
        result = construct_dataset(recipe, inputs)
        config = {
            "schema_version": CONSTRUCTION_STAGE_CONFIG_SCHEMA_VERSION,
            "recipe_id": recipe.recipe_id,
            "selected_source_ids": list(source_ids),
        }
        with store.begin(
            "construct",
            expected_revision_id=current.revision_id,
        ) as transaction:
            recipe_artifact = transaction.put_artifact(
                lossless_json_bytes(dataset_recipe_to_dict(recipe)),
                kind="dataset-recipe",
                media_type="application/json",
                source_ids=source_ids,
                producer_id="veriformis.construction.recipe",
                producer_version="1",
                config=config,
            )
            result_artifact = transaction.put_artifact(
                lossless_json_bytes(construction_result_to_dict(result)),
                kind="construction-result",
                media_type="application/json",
                source_ids=source_ids,
                producer_id="veriformis.construction.result",
                producer_version="1",
                config=config,
            )
            revision = transaction.commit(
                outputs={
                    "recipe": recipe_artifact,
                    "result": result_artifact,
                },
                config=config,
            )
        return ConstructOutcome(
            candidate_count=len(result.candidates),
            record_count=len(result.records),
            diagnostic_count=len(result.diagnostics),
            recipe_id=recipe.recipe_id,
            result_id=result.result_id,
            revision_id=revision.revision_id,
            durability_warning=store.last_commit_durability_warning,
            messages=(
                ServiceMessage(
                    f"constructed {len(result.candidates)} candidate(s), "
                    f"{len(result.records)} accepted record(s), and "
                    f"{len(result.diagnostics)} diagnostic(s); revision "
                    f"{revision.revision_id}"
                ),
            ),
        )

    def curate(
        self,
        workspace: Path,
        *,
        goal: str | None = None,
        preset: str | None = None,
        minimum_target_characters: int | None = None,
        balance_mode: str | None = None,
        maximum_records_per_primary_source: int | None = None,
        evaluation_ratio_ppm: int | None = None,
        evaluation_required: bool | None = None,
        split_seed: str | None = None,
        instruction: str | None = None,
    ) -> CurateOutcome:
        """Fix the complete dataset plan, then curate constructed records.

        Omitted settings come from the selected preset or, by default, from
        the constructed goal's safe preset; the plan is built through the
        recipe library so every surface fixes the same plan.
        """
        from veriformis.goals.catalog import resolve_operator_instruction
        from veriformis.goals.presets import resolve_recipe_settings
        from veriformis.recipes.library import build_default_finished_plan

        store = Workspace.open(workspace)
        current = store.head()
        _require_group3_revision(current)
        recipe, result, inputs = _load_constructed_dataset(store, current)
        try:
            instruction = resolve_operator_instruction(
                objective=recipe.objective.kind,
                row_schema=recipe.target_row_schema,
                instruction=instruction,
            )
        except GoalCatalogError as exc:
            raise ValueError(exc.message) from exc
        try:
            settings = resolve_recipe_settings(
                goal=goal,
                preset=preset,
                objective=recipe.objective.kind,
                target_row_schema=recipe.target_row_schema,
                minimum_target_characters=minimum_target_characters,
                balance_mode=balance_mode,
                maximum_records_per_primary_source=maximum_records_per_primary_source,
                evaluation_ratio_ppm=evaluation_ratio_ppm,
                evaluation_required=evaluation_required,
                split_seed=split_seed,
            )
        except GoalCatalogError as exc:
            raise ValueError(exc.message) from exc
        curation = settings.curation
        plan = build_default_finished_plan(
            recipe_id=recipe.recipe_id,
            construction_result_id=result.result_id,
            target_row_schema=recipe.target_row_schema,
            minimum_target_characters=curation.minimum_target_characters,
            balance_mode=curation.balance_mode,
            maximum_records_per_primary_source=curation.maximum_records_per_primary_source,
            evaluation_ratio_ppm=curation.evaluation_ratio_ppm,
            evaluation_required=curation.evaluation_required,
            split_seed=curation.split_seed,
            instruction=instruction,
        )
        curated = curate_dataset(plan, recipe, inputs, result)
        config = _finished_stage_config(CURATION_STAGE_SCHEMA_ID, plan.plan_id)
        with store.begin(
            "curate",
            expected_revision_id=current.revision_id,
        ) as transaction:
            plan_artifact = transaction.put_artifact(
                lossless_json_bytes(finished_dataset_plan_to_dict(plan)),
                kind="finished-dataset-plan",
                media_type="application/json",
                source_ids=recipe.source_ids,
                producer_id="veriformis.curation.plan",
                producer_version="1",
                config=config,
            )
            result_artifact = transaction.put_artifact(
                lossless_json_bytes(curation_result_to_dict(curated)),
                kind="curation-result",
                media_type="application/json",
                source_ids=recipe.source_ids,
                producer_id="veriformis.curation.result",
                producer_version="1",
                config=config,
            )
            revision = transaction.commit(
                outputs={"plan": plan_artifact, "result": result_artifact},
                config=config,
            )
        excluded = sum(decision.status == "excluded" for decision in curated.decisions)
        quarantined = sum(
            decision.status == "quarantined" for decision in curated.decisions
        )
        blockers = tuple(
            sorted(
                {
                    code
                    for entry in curated.coverage_ledger.entries
                    for code in entry.blocker_codes
                }
            )
        )
        messages: list[ServiceMessage] = [
            ServiceMessage(
                f"curated {len(curated.included_record_ids)} included, {excluded} excluded, "
                f"and {quarantined} quarantined record(s); plan {plan.plan_id}; "
                f"revision {revision.revision_id}"
            )
        ]
        if blockers:
            messages.append(
                ServiceMessage(
                    f"coverage blockers: {', '.join(blockers)}",
                    stream="stderr",
                    kind="warning",
                )
            )
        return CurateOutcome(
            included_count=len(curated.included_record_ids),
            excluded_count=excluded,
            quarantined_count=quarantined,
            plan_id=plan.plan_id,
            coverage_blockers=blockers,
            revision_id=revision.revision_id,
            durability_warning=store.last_commit_durability_warning,
            messages=tuple(messages),
        )

    def split(self, workspace: Path) -> SplitOutcome:
        """Assign complete transitive leakage groups to fixed partitions."""
        store = Workspace.open(workspace)
        current = store.head()
        recipe, construction, _ = _load_constructed_dataset(store, current)
        plan = _load_finished_plan(store, current)
        curated = _load_curation_result(store, current)
        raw_digests = {
            source_id: current.sources[source_id].sha256
            for source_id in recipe.source_ids
        }
        result = split_dataset(
            plan,
            construction,
            curated,
            raw_digests,
        )
        config = _finished_stage_config(SPLIT_STAGE_SCHEMA_ID, plan.plan_id)
        with store.begin(
            "split",
            expected_revision_id=current.revision_id,
        ) as transaction:
            artifact = transaction.put_artifact(
                lossless_json_bytes(split_result_to_dict(result)),
                kind="split-result",
                media_type="application/json",
                source_ids=recipe.source_ids,
                producer_id="veriformis.splitting.result",
                producer_version="1",
                config=config,
            )
            revision = transaction.commit(outputs={"result": artifact}, config=config)
        return SplitOutcome(
            train_record_count=result.realized_train_record_count,
            evaluation_record_count=result.realized_evaluation_record_count,
            group_count=len(result.groups),
            assignment_digest=result.assignment_digest,
            revision_id=revision.revision_id,
            durability_warning=store.last_commit_durability_warning,
            messages=(
                ServiceMessage(
                    f"split {result.realized_train_record_count} train and "
                    f"{result.realized_evaluation_record_count} evaluation record(s) across "
                    f"{len(result.groups)} leakage group(s); revision {revision.revision_id}"
                ),
            ),
        )

    def format(self, workspace: Path) -> FormatOutcome:
        """Lower curated records into the row schema fixed by their dataset plan."""
        store = Workspace.open(workspace)
        current = store.head()
        recipe, construction, _ = _load_constructed_dataset(store, current)
        plan = _load_finished_plan(store, current)
        curated = _load_curation_result(store, current)
        split_result = _load_split_result(store, current)
        output = serialize_dataset(
            plan,
            recipe,
            construction,
            curated,
            split_result,
        )
        config = _finished_stage_config(FORMAT_STAGE_SCHEMA_ID, plan.plan_id)
        with store.begin(
            "format",
            expected_revision_id=current.revision_id,
        ) as transaction:
            row_set_artifact = transaction.put_artifact(
                lossless_json_bytes(row_set_to_dict(output.row_set)),
                kind="formatted-row-set",
                media_type="application/json",
                source_ids=recipe.source_ids,
                producer_id="veriformis.dataset-serializer.row-set",
                producer_version="1",
                config=config,
            )
            train_artifact = transaction.put_artifact(
                output.train_jsonl,
                kind="training-partition",
                media_type="application/jsonl",
                source_ids=recipe.source_ids,
                producer_id="veriformis.dataset-serializer.train",
                producer_version="1",
                config=config,
            )
            evaluation_artifact = transaction.put_artifact(
                output.evaluation_jsonl,
                kind="evaluation-partition",
                media_type="application/jsonl",
                source_ids=recipe.source_ids,
                producer_id="veriformis.dataset-serializer.evaluation",
                producer_version="1",
                config=config,
            )
            provenance_artifact = transaction.put_artifact(
                output.provenance_jsonl,
                kind="row-provenance",
                media_type="application/jsonl",
                source_ids=recipe.source_ids,
                producer_id="veriformis.dataset-serializer.provenance",
                producer_version="1",
                config=config,
            )
            revision = transaction.commit(
                outputs={
                    "row-set": row_set_artifact,
                    "train": train_artifact,
                    "evaluation": evaluation_artifact,
                    "provenance": provenance_artifact,
                },
                config=config,
            )
        return FormatOutcome(
            train_row_count=len(output.row_set.train_rows),
            evaluation_row_count=len(output.row_set.evaluation_rows),
            row_schema=output.row_set.row_schema,
            revision_id=revision.revision_id,
            durability_warning=store.last_commit_durability_warning,
            messages=(
                ServiceMessage(
                    f"wrote {len(output.row_set.train_rows)} train and "
                    f"{len(output.row_set.evaluation_rows)} evaluation row(s) as "
                    f"{output.row_set.row_schema}; revision {revision.revision_id}"
                ),
            ),
        )

    def validate(self, workspace: Path) -> ValidateOutcome:
        """Replay and validate one exact finished-dataset byte snapshot."""
        store = Workspace.open(workspace)
        current = store.head()
        recipe, construction, inputs = _load_constructed_dataset(store, current)
        plan = _load_finished_plan(store, current)
        curated = _load_curation_result(store, current)
        split_result = _load_split_result(store, current)
        output = _load_serialization_output(store, current)
        report = validate_finished_dataset(
            plan,
            recipe,
            inputs,
            construction,
            curated,
            split_result,
            output.row_set,
            train_jsonl=output.train_jsonl,
            evaluation_jsonl=output.evaluation_jsonl,
            provenance_jsonl=output.provenance_jsonl,
        )
        config = _finished_stage_config(VALIDATION_STAGE_SCHEMA_ID, plan.plan_id)
        with store.begin(
            "validate",
            expected_revision_id=current.revision_id,
        ) as transaction:
            snapshot_artifact = transaction.put_artifact(
                dataset_snapshot_json_bytes(report.snapshot),
                kind="dataset-snapshot",
                media_type="application/json",
                source_ids=recipe.source_ids,
                producer_id="veriformis.dataset-validation.snapshot",
                producer_version="1",
                config=config,
            )
            report_artifact = transaction.put_artifact(
                dataset_validation_report_json_bytes(report),
                kind="dataset-validation-report",
                media_type="application/json",
                source_ids=recipe.source_ids,
                producer_id="veriformis.dataset-validation.report",
                producer_version="1",
                config=config,
            )
            revision = transaction.commit(
                outputs={"snapshot": snapshot_artifact, "report": report_artifact},
                config=config,
                status="complete" if report.status == "passed" else "failed",
            )
        messages: list[ServiceMessage] = []
        for result in report.gate_results:
            messages.append(ServiceMessage(f"{result.gate_id}: {result.status.upper()}"))
            for finding in result.finding_codes:
                messages.append(ServiceMessage(f"  {finding}"))
        messages.append(ServiceMessage(f"snapshot {report.snapshot_id}"))
        messages.append(
            ServiceMessage(f"validation revision {revision.revision_id}")
        )
        exit_status = 0 if report.status == "passed" else 1
        return ValidateOutcome(
            report=report,
            snapshot_id=report.snapshot_id,
            revision_id=revision.revision_id,
            exit_status=exit_status,
            durability_warning=store.last_commit_durability_warning,
            messages=tuple(messages),
        )

    def seal(self, workspace: Path, out: Path) -> SealOutcome:
        """Revalidate, atomically publish, and receipt one finished dataset."""
        publication = None
        store = Workspace.open(workspace)
        try:
            current = store.head()
            expected_revision_id = current.revision_id
            with store.begin(
                "seal",
                expected_revision_id=expected_revision_id,
            ) as transaction:
                base = transaction.base
                recipe, construction, inputs = _load_constructed_dataset(store, base)
                plan = _load_finished_plan(store, base)
                curated = _load_curation_result(store, base)
                split_result = _load_split_result(store, base)
                output = _load_serialization_output(store, base)
                expected_report = validate_finished_dataset(
                    plan,
                    recipe,
                    inputs,
                    construction,
                    curated,
                    split_result,
                    output.row_set,
                    train_jsonl=output.train_jsonl,
                    evaluation_jsonl=output.evaluation_jsonl,
                    provenance_jsonl=output.provenance_jsonl,
                )
                report_bytes = _output_bytes(store, base, "validate", "report")
                saved_report = dataset_validation_report_from_json_bytes(report_bytes)
                if saved_report != expected_report or saved_report.status != "passed":
                    raise ValueError(
                        "seal requires the exact current passing validation report"
                    )
                files = {
                    "data/train.jsonl": output.train_jsonl,
                    "data/evaluation.jsonl": output.evaluation_jsonl,
                    "metadata/row-provenance.jsonl": output.provenance_jsonl,
                    "validation.json": report_bytes,
                }
                roles = {
                    "data/train.jsonl": "training-partition",
                    "data/evaluation.jsonl": "evaluation-partition",
                    "metadata/row-provenance.jsonl": "row-provenance",
                    "validation.json": "dataset-validation-report",
                }
                media_types = {
                    "data/train.jsonl": "application/jsonl",
                    "data/evaluation.jsonl": "application/jsonl",
                    "metadata/row-provenance.jsonl": "application/jsonl",
                    "validation.json": "application/json",
                }
                record_counts = {
                    "data/train.jsonl": output.row_set.train_row_count,
                    "data/evaluation.jsonl": output.row_set.evaluation_row_count,
                    "metadata/row-provenance.jsonl": output.row_set.total_row_count,
                }
                manifest, attestation = build_finished_bundle(
                    files,
                    roles=roles,
                    media_types=media_types,
                    record_counts=record_counts,
                    dataset_snapshot_id=saved_report.snapshot_id,
                    validation_report_id=saved_report.report_id,
                )
                manifest_bytes = manifest.canonical_bytes()
                attestation_bytes = attestation.canonical_bytes()
                config = _finished_stage_config(SEAL_STAGE_SCHEMA_ID, plan.plan_id)
                manifest_artifact = transaction.put_artifact(
                    manifest_bytes,
                    kind="finished-bundle-manifest",
                    media_type="application/json",
                    source_ids=recipe.source_ids,
                    producer_id="veriformis.bundle.manifest",
                    producer_version="1",
                    config=config,
                )
                attestation_artifact = transaction.put_artifact(
                    attestation_bytes,
                    kind="finished-bundle-attestation",
                    media_type="application/json",
                    source_ids=recipe.source_ids,
                    producer_id="veriformis.bundle.attestation",
                    producer_version="1",
                    config=config,
                )

                def publish_or_recover() -> None:
                    nonlocal publication
                    target = Path(os.path.abspath(os.fspath(out)))
                    if os.path.lexists(target):
                        publication = _recover_exact_finished_bundle(
                            target,
                            files=files,
                            manifest=manifest,
                            attestation=attestation,
                            manifest_bytes=manifest_bytes,
                            attestation_bytes=attestation_bytes,
                            expected_report=saved_report,
                        )
                        return
                    try:
                        publication = write_finished_bundle(
                            target,
                            files,
                            roles=roles,
                            media_types=media_types,
                            record_counts=record_counts,
                            dataset_snapshot_id=saved_report.snapshot_id,
                            validation_report_id=saved_report.report_id,
                        )
                    except FinishedBundleError:
                        if not os.path.lexists(target):
                            raise
                        publication = _recover_exact_finished_bundle(
                            target,
                            files=files,
                            manifest=manifest,
                            attestation=attestation,
                            manifest_bytes=manifest_bytes,
                            attestation_bytes=attestation_bytes,
                            expected_report=saved_report,
                        )
                        return
                    if (
                        publication.manifest_bytes != manifest_bytes
                        or publication.attestation_bytes != attestation_bytes
                        or publication.manifest != manifest
                        or publication.attestation != attestation
                    ):
                        raise FinishedBundleError(
                            "visible finished bundle receipt differs from the staged "
                            "workspace receipt"
                        )

                transaction._set_seal_publication_action(publish_or_recover)
                revision = transaction.commit(
                    outputs={
                        "manifest": manifest_artifact,
                        "attestation": attestation_artifact,
                    },
                    config=config,
                )
        except Exception as exc:
            if publication is not None:
                raise SealPartialPublicationError(publication, exc) from exc
            raise
        assert publication is not None
        messages: list[ServiceMessage] = []
        if publication.durability_warning is not None:
            messages.append(
                ServiceMessage(
                    f"warning[bundle-durability]: {publication.durability_warning}",
                    stream="stderr",
                    kind="warning",
                )
            )
        messages.extend(
            [
                ServiceMessage(f"sealed bundle: {publication.bundle_path}"),
                ServiceMessage(f"manifest SHA-256: {publication.manifest_sha256}"),
                ServiceMessage(f"verification grade: {publication.trust_grade}"),
                ServiceMessage(f"seal revision {revision.revision_id}"),
            ]
        )
        return SealOutcome(
            publication=publication,
            revision_id=revision.revision_id,
            durability_warning=store.last_commit_durability_warning,
            messages=tuple(messages),
        )

    def verify(
        self,
        bundle: Path,
        *,
        manifest_sha256: str | None = None,
    ) -> VerifyOutcome:
        """Independently verify one closed finished-dataset bundle."""
        result = verify_finished_bundle(
            bundle,
            expected_manifest_sha256=manifest_sha256,
        )
        return VerifyOutcome(
            verification=result,
            messages=(
                ServiceMessage(f"verification grade: {result.trust_grade}"),
                ServiceMessage(f"bundle: {result.bundle_id}"),
                ServiceMessage(f"snapshot: {result.dataset_snapshot_id}"),
                ServiceMessage(f"validation report: {result.validation_report_id}"),
                ServiceMessage(f"manifest SHA-256: {result.manifest_sha256}"),
                ServiceMessage(f"dataset rows: {result.declared_record_count}"),
            ),
        )

    def package(
        self,
        bundle: Path,
        out: Path,
        *,
        manifest_sha256: str | None = None,
        export_receipt_sha256: str | None = None,
    ) -> PackageOutcome:
        """Publish one explicitly anchored deterministic transport archive."""
        if (manifest_sha256 is None) == (export_receipt_sha256 is None):
            raise ValueError(
                "package requires exactly one of manifest_sha256 or "
                "export_receipt_sha256"
            )
        if manifest_sha256 is not None:
            receipt = write_bundle_archive(
                bundle,
                out,
                expected_manifest_sha256=manifest_sha256,
            )
            messages = (
                ServiceMessage(f"transport archive: {receipt.archive_path}"),
                ServiceMessage(f"archive SHA-256: {receipt.archive_sha256}"),
                ServiceMessage(f"manifest SHA-256: {receipt.manifest_sha256}"),
                ServiceMessage(
                    f"verification grade: {receipt.verification.trust_grade}"
                ),
                ServiceMessage(f"archive members: {receipt.member_count}"),
            )
        else:
            assert export_receipt_sha256 is not None
            receipt = write_export_pack_archive(
                bundle,
                out,
                expected_export_receipt_sha256=export_receipt_sha256,
            )
            messages = (
                ServiceMessage(f"transport archive: {receipt.archive_path}"),
                ServiceMessage(f"archive SHA-256: {receipt.archive_sha256}"),
                ServiceMessage(
                    f"export receipt SHA-256: {receipt.export_receipt_sha256}"
                ),
                ServiceMessage(f"export receipt: {receipt.export_receipt_id}"),
                ServiceMessage(f"export plan: {receipt.export_plan_id}"),
                ServiceMessage(
                    "output content root SHA-256: "
                    f"{receipt.output_content_root_sha256}"
                ),
                ServiceMessage(f"source trust grade: {receipt.source_trust_grade}"),
                ServiceMessage(f"archive members: {receipt.member_count}"),
            )
        return PackageOutcome(
            receipt=receipt,
            durability_warning=receipt.durability_warning,
            messages=messages,
        )

    def package_verify(
        self,
        archive: Path,
        *,
        manifest_sha256: str | None = None,
        export_receipt_sha256: str | None = None,
    ) -> PackageOutcome:
        """Independently verify one explicitly anchored transport archive."""
        if (manifest_sha256 is None) == (export_receipt_sha256 is None):
            raise ValueError(
                "package-verify requires exactly one of manifest_sha256 or "
                "export_receipt_sha256"
            )
        if manifest_sha256 is not None:
            receipt = verify_bundle_archive(
                archive,
                expected_manifest_sha256=manifest_sha256,
            )
            messages = (
                ServiceMessage("transport archive status: accepted"),
                ServiceMessage(f"archive SHA-256: {receipt.archive_sha256}"),
                ServiceMessage(f"manifest SHA-256: {receipt.manifest_sha256}"),
                ServiceMessage(
                    f"verification grade: {receipt.verification.trust_grade}"
                ),
                ServiceMessage(f"archive members: {receipt.member_count}"),
            )
        else:
            assert export_receipt_sha256 is not None
            receipt = verify_export_pack_archive(
                archive,
                expected_export_receipt_sha256=export_receipt_sha256,
            )
            messages = (
                ServiceMessage("transport archive status: accepted"),
                ServiceMessage(f"archive SHA-256: {receipt.archive_sha256}"),
                ServiceMessage(
                    f"export receipt SHA-256: {receipt.export_receipt_sha256}"
                ),
                ServiceMessage(f"export receipt: {receipt.export_receipt_id}"),
                ServiceMessage(f"export plan: {receipt.export_plan_id}"),
                ServiceMessage(
                    "output content root SHA-256: "
                    f"{receipt.output_content_root_sha256}"
                ),
                ServiceMessage(f"source trust grade: {receipt.source_trust_grade}"),
                ServiceMessage(f"archive members: {receipt.member_count}"),
            )
        return PackageOutcome(
            receipt=receipt,
            messages=messages,
        )

    def preview(
        self,
        path: Path,
        *,
        rules: str = "",
        custom: str = "",
        source_root: Path | None = None,
    ) -> PreviewOutcome:
        """Plan and replay cleaning without writing state."""
        selected, config = _select_rules(rules, custom)
        views: list[PreviewSourceView] = []
        is_workspace = path.is_dir() and (path / "workspace.json").is_file()
        if is_workspace:
            store = Workspace.open(path)
            revision = store.head()
            documents = _load_documents(store, revision, stage="parse")
            sources = _load_sources(store, revision)
            reuse_persisted = (
                revision.stages["clean"].status == "complete"
                and revision.stages["clean"].config == config
            )
            persisted_records: list[TransformRecord] = []
            if reuse_persisted:
                cleaned_documents = _load_documents(store, revision, stage="clean")
                persisted_records = _load_transform_records(store, revision)
            for source_id, document in sorted(documents.items()):
                if reuse_persisted:
                    plan = cleaning_plan_from_dict(
                        _json_load(
                            _output_bytes(
                                store,
                                revision,
                                "clean",
                                f"source/{source_id}/cleaning-plan",
                            )
                        )
                    )
                    replayed = cleaned_documents[source_id]
                    records = tuple(
                        record
                        for record in persisted_records
                        if record.source_id == source_id
                    )
                    warnings: tuple[str, ...] = ()
                else:
                    planned = plan_cleaning(
                        document,
                        selected,
                        base_input_sha256=_cleaning_input_digest(
                            sources[source_id], document
                        ),
                    )
                    plan = planned.plan
                    replayed = replay_cleaning_plan(document, plan)
                    records = planned.records
                    warnings = tuple(
                        warning
                        for run in plan.runs
                        for warning in run.warnings
                    )
                views.append(
                    PreviewSourceView(
                        logical_path=sources[source_id].logical_path,
                        before_text=sources[source_id].extracted_text,
                        after_text=flatten(list(iter_document_blocks(replayed))),
                        plan_id=plan.id,
                        records=records,
                        warnings=warnings
                        if not reuse_persisted
                        else tuple(
                            warning
                            for run in plan.runs
                            for warning in run.warnings
                        ),
                    )
                )
        else:
            source_capture = capture_source_batch(
                [path],
                source_root=source_root,
            )[0]
            if source_capture.error is not None:
                raise source_capture.error
            assert source_capture.raw_bytes is not None
            raw_bytes = source_capture.raw_bytes
            logical_path = source_capture.logical_path
            result = _parse_one(
                path,
                logical_path=logical_path,
                raw_bytes=raw_bytes,
            )
            _require_accepted_parse(result, logical_path=logical_path)
            planned = plan_cleaning(
                result.document,
                selected,
                base_input_sha256=_cleaning_input_digest(
                    result.source, result.document
                ),
            )
            replayed = replay_cleaning_plan(result.document, planned.plan)
            views.append(
                PreviewSourceView(
                    logical_path=logical_path,
                    before_text=result.source.extracted_text,
                    after_text=flatten(list(iter_document_blocks(replayed))),
                    plan_id=planned.plan.id,
                    records=planned.records,
                    warnings=tuple(
                        warning
                        for run in planned.plan.runs
                        for warning in run.warnings
                    ),
                )
            )
        messages: list[ServiceMessage] = []
        for view in views:
            if len(views) > 1 or is_workspace:
                messages.append(ServiceMessage(f"source: {view.logical_path}"))
            for record in view.records:
                messages.append(
                    ServiceMessage(
                        f"{record.rule}: {record.edits} edit(s), "
                        f"{record.bytes_removed} byte(s) removed"
                    )
                )
            for warning in view.warnings:
                messages.append(ServiceMessage(f"warning: {warning}"))
            messages.append(ServiceMessage(f"plan: {view.plan_id}"))
            messages.append(ServiceMessage("--- before ---"))
            messages.append(ServiceMessage(view.before_text[:400]))
            messages.append(ServiceMessage("--- after ---"))
            messages.append(ServiceMessage(view.after_text[:400]))
        return PreviewOutcome(
            is_workspace=is_workspace,
            sources=tuple(views),
            messages=tuple(messages),
        )

    def version(self) -> VersionOutcome:
        return VersionOutcome(
            version=veriformis.__version__,
            messages=(ServiceMessage(veriformis.__version__),),
        )


# Module-level singleton for adapters that do not need injection.
DEFAULT_PIPELINE_SERVICE = PipelineService()
