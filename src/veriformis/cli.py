"""Veriformis CLI over immutable, transactional workspace revisions.

The CLI remains the M1 orchestration surface. Every inter-stage artifact is
content-addressed and every successful stage becomes visible through one
atomic workspace ``HEAD`` transition.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import typer

import veriformis
from veriformis.bundle import (
    BundleAttestation,
    BundlePublicationReceipt,
    FinishedBundleManifest,
    build_finished_bundle,
    verify_finished_bundle,
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
    ConstructionPass,
    DatasetRecipe,
    IRArtifactInput,
    SegmentationPolicy,
    TrainingObjective,
    construct_dataset,
    construction_result_from_json_bytes,
    construction_result_to_dict,
    dataset_recipe_from_json_bytes,
    dataset_recipe_to_dict,
    validate_construction_result,
)
from veriformis.contracts import (
    CURATION_STAGE_SCHEMA_ID,
    DETERMINISTIC_V1_OBJECTIVE_KINDS,
    FORMAT_STAGE_SCHEMA_ID,
    SEAL_STAGE_SCHEMA_ID,
    SPLIT_STAGE_SCHEMA_ID,
    VALIDATION_STAGE_SCHEMA_ID,
    V1_ROW_SCHEMA_KINDS,
)
from veriformis.datasets import (
    CurationPolicy,
    DatasetValidationReport,
    FinishedDatasetPlan,
    SerializationOutput,
    SerializationPlan,
    SplitPolicy,
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
    ConstructionError,
    InvalidSourceLocatorError,
    ParseError,
    UnsupportedWorkspaceVersionError,
    VeriformisError,
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
    normalize_logical_path,
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
from veriformis.sources import ParseResult, SourceRef
from veriformis.workspace import (
    CONSTRUCTION_STAGE_CONFIG_SCHEMA_VERSION,
    WORKSPACE_REVISION_SCHEMA_VERSION,
    SourceDescriptor,
    Workspace,
    WorkspaceRevision,
)

app = typer.Typer(help="Veriformis: local-first dataset compiler.")

_CODE_EXTS = CODE_EXTENSIONS
_STRATEGIES = {
    "paragraph": chunk_paragraph,
    "fixed": chunk_fixed,
    "sliding": chunk_sliding,
    "sentence": chunk_sentence,
    "structure": chunk_structure,
}


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


def _logical_paths(
    paths: list[Path],
    *,
    source_root: Path | None,
) -> dict[Path, str]:
    """Derive locators from one explicit root, never from batch composition."""
    root = (source_root or Path.cwd()).resolve()
    if not root.is_dir():
        raise InvalidSourceLocatorError(f"source root is not a directory: {root}")
    logical: dict[Path, str] = {}
    for path in paths:
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(root)
        except ValueError as exc:
            raise InvalidSourceLocatorError(
                f"source {resolved} is outside source root {root}; "
                "pass --source-root explicitly"
            ) from exc
        logical[path] = normalize_logical_path(relative)
    return logical


def _echo_error(exc: Exception, *, status: int = 2) -> None:
    code = getattr(exc, "code", "invalid-data")
    message = getattr(exc, "message", str(exc))
    typer.echo(f"error[{code}]: {message}", err=True)
    raise typer.Exit(code=status) from exc


def _echo_durability_warning(workspace: Workspace) -> None:
    warning = workspace.last_commit_durability_warning
    if warning is not None:
        typer.echo(f"warning[commit-durability]: {warning}", err=True)


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
    inputs = _load_construction_inputs(workspace, revision, recipe.source_ids)
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


@app.command()
def parse(
    paths: list[Path],
    out: Path = typer.Option(..., "-o"),
    source_root: Path | None = typer.Option(None, "--source-root"),
) -> None:
    """Capture raw files and commit one canonical parse revision."""
    try:
        logical_paths = _logical_paths(paths, source_root=source_root)
        captured = [(path, path.read_bytes()) for path in paths]
        results = [
            _parse_one(
                path,
                logical_path=logical_paths[path],
                raw_bytes=raw_bytes,
            )
            for path, raw_bytes in captured
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
    except (VeriformisError, EvidenceError, OSError, UnicodeError, ValueError) as exc:
        _echo_error(exc)
    _echo_durability_warning(workspace)
    typer.echo(f"parsed {len(results)} source(s) into revision {revision.revision_id}")


@app.command()
def clean(
    workspace: Path,
    rules: str = typer.Option("", "--rules"),
    custom: str = typer.Option("", "--custom"),
) -> None:
    """Plan, replay, and atomically commit cleaning for every source."""
    try:
        selected, config = _select_rules(rules, custom)
        store = Workspace.open(workspace)
        current = store.head()
        if (
            current.stages["clean"].status == "complete"
            and current.stages["clean"].config == config
        ):
            _load_documents(store, current, stage="clean")
            _load_transform_records(store, current)
            typer.echo(f"clean unchanged at revision {current.revision_id}")
            return
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
                    typer.echo(f"warning[{source_id}]: {warning}", err=True)
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
    except (
        VeriformisError,
        EvidenceError,
        OSError,
        UnicodeError,
        ValueError,
        re.error,
    ) as exc:
        _echo_error(exc)
    _echo_durability_warning(store)
    typer.echo(
        f"cleaned {len(documents)} document(s); {len(transforms)} transform record(s); "
        f"revision {revision.revision_id}"
    )


@app.command()
def chunk(
    workspace: Path,
    strategy: str = typer.Option("paragraph", "--strategy"),
    size: int = typer.Option(1000, "--size"),
    overlap: int = typer.Option(100, "--overlap"),
) -> None:
    """Chunk cleaned documents with exact reconstructible source evidence."""
    if strategy not in _STRATEGIES:
        typer.echo(
            f"unknown strategy: {strategy} (have: {sorted(_STRATEGIES)})", err=True
        )
        raise typer.Exit(code=2)
    if size < 1 or overlap < 0 or overlap >= size:
        typer.echo(
            "size must be positive and overlap must satisfy 0 <= overlap < size",
            err=True,
        )
        raise typer.Exit(code=2)
    config = {"strategy": strategy, "size": size, "overlap": overlap}
    try:
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
    except (VeriformisError, EvidenceError, OSError, UnicodeError, ValueError) as exc:
        _echo_error(exc)
    _echo_durability_warning(store)
    typer.echo(f"wrote {len(chunks)} chunk(s); revision {revision.revision_id}")


@app.command(name="upgrade-workspace")
def upgrade_workspace(workspace: Path) -> None:
    """Advance a verified workspace through every supported revision migration."""
    try:
        store = Workspace.open(workspace)
        before = store.head()
        revision = store.migrate_to_current(expected_revision_id=before.revision_id)
    except (VeriformisError, OSError, UnicodeError, ValueError) as exc:
        _echo_error(exc)
    _echo_durability_warning(store)
    if revision.revision_id == before.revision_id:
        typer.echo(f"workspace already current at revision {revision.revision_id}")
    else:
        typer.echo(
            f"migrated workspace revision schema {before.schema_version} to "
            f"{revision.schema_version}; revision {revision.revision_id}"
        )


@app.command()
def construct(
    workspace: Path,
    objective: str = typer.Option(..., "--objective"),
    source: list[str] | None = typer.Option(
        None,
        "--source",
        help="Repeat a source ID or logical path to select a subset.",
    ),
    target_row_schema: str | None = typer.Option(
        None,
        "--target-row-schema",
    ),
    split_ratio_ppm: int = typer.Option(500_000, "--split-ratio-ppm"),
    require_review: bool = typer.Option(False, "--require-review"),
) -> None:
    """Construct evidence-bearing candidates and immutable accepted records."""
    try:
        if objective not in DETERMINISTIC_V1_OBJECTIVE_KINDS:
            raise ConstructionError(
                f"unsupported deterministic objective {objective!r}; "
                f"expected one of {sorted(DETERMINISTIC_V1_OBJECTIVE_KINDS)!r}"
            )
        row_schema = target_row_schema or (
            "text" if objective == "full_text" else "prompt_completion"
        )
        if row_schema not in V1_ROW_SCHEMA_KINDS:
            raise ConstructionError(
                f"unsupported target row schema {row_schema!r}; "
                f"expected one of {sorted(V1_ROW_SCHEMA_KINDS)!r}"
            )
        if objective == "full_text" and row_schema != "text":
            raise ConstructionError(
                "full_text recipes require the product 'text' row schema"
            )
        if objective != "full_text" and row_schema == "text":
            raise ConstructionError(
                f"objective {objective!r} requires a supervised row schema"
            )
        if not 1 <= split_ratio_ppm <= 999_999:
            raise ConstructionError("split ratio must be from 1 to 999999 ppm")

        store = Workspace.open(workspace)
        current = store.head()
        if "construct" not in current.stages:
            raise UnsupportedWorkspaceVersionError(
                "construct requires workspace revision schema 2 or later; run "
                "`veriformis upgrade-workspace WORKSPACE` first"
            )
        source_ids = _select_construction_sources(current, source)
        inputs = _load_construction_inputs(store, current, source_ids)
        objective_value = TrainingObjective.create(objective)
        parameters = (
            {"split_ratio_ppm": split_ratio_ppm}
            if objective == "continuation"
            else None
        )
        construction_pass = ConstructionPass.create(
            sequence=1,
            objective_kind=objective,
            parameters=parameters,
        )
        chunk_config = current.stages["chunk"].config
        try:
            recipe = DatasetRecipe.create(
                objective=objective_value,
                source_ids=source_ids,
                cleaning_config_digest=current.stages["clean"].config_digest,
                segmentation=SegmentationPolicy(
                    schema_version="veriformis.segmentation-policy/v1",
                    strategy=chunk_config["strategy"],
                    size=chunk_config["size"],
                    overlap=chunk_config["overlap"],
                ),
                passes=(construction_pass,),
                target_row_schema=row_schema,
                review_policy="required" if require_review else "none",
            )
        except (TypeError, ValueError) as exc:
            raise ConstructionError(f"invalid dataset recipe: {exc}") from exc
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
    except (VeriformisError, OSError, UnicodeError, ValueError, TypeError) as exc:
        _echo_error(exc)
    _echo_durability_warning(store)
    typer.echo(
        f"constructed {len(result.candidates)} candidate(s), "
        f"{len(result.records)} accepted record(s), and "
        f"{len(result.diagnostics)} diagnostic(s); revision "
        f"{revision.revision_id}"
    )


@app.command()
def curate(
    workspace: Path,
    minimum_target_characters: int = typer.Option(
        1,
        "--minimum-target-characters",
    ),
    balance_mode: str = typer.Option("none", "--balance-mode"),
    maximum_records_per_primary_source: int | None = typer.Option(
        None,
        "--maximum-records-per-primary-source",
    ),
    evaluation_ratio_ppm: int = typer.Option(500_000, "--evaluation-ratio-ppm"),
    evaluation_required: bool = typer.Option(
        True,
        "--require-evaluation/--allow-empty-evaluation",
    ),
    split_seed: str = typer.Option("veriformis-v1", "--split-seed"),
    instruction: str | None = typer.Option(None, "--instruction"),
) -> None:
    """Fix the complete dataset plan, then curate constructed records."""
    try:
        if balance_mode not in {"none", "primary-source-cap"}:
            raise ValueError("balance mode must be 'none' or 'primary-source-cap'")
        store = Workspace.open(workspace)
        current = store.head()
        _require_group3_revision(current)
        recipe, result, inputs = _load_constructed_dataset(store, current)
        if recipe.target_row_schema == "instruction_output":
            if instruction is None or not instruction:
                raise ValueError(
                    "--instruction is required for instruction_output rows"
                )
        elif instruction is not None:
            raise ValueError("--instruction is valid only for instruction_output rows")
        curation_policy = CurationPolicy.create(
            minimum_target_characters=minimum_target_characters,
            balance_mode=balance_mode,
            maximum_records_per_primary_source=(maximum_records_per_primary_source),
        )
        split_policy = SplitPolicy.create(
            evaluation_ratio_ppm=evaluation_ratio_ppm,
            evaluation_required=evaluation_required,
            seed=split_seed,
        )
        serialization_plan = SerializationPlan.create(
            row_schema=recipe.target_row_schema,
            instruction_text=instruction,
        )
        plan = FinishedDatasetPlan.create(
            recipe_id=recipe.recipe_id,
            construction_result_id=result.result_id,
            curation_policy=curation_policy,
            split_policy=split_policy,
            serialization_plan=serialization_plan,
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
    except (
        VeriformisError,
        EvidenceError,
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
    ) as exc:
        _echo_error(exc)
    _echo_durability_warning(store)
    excluded = sum(decision.status == "excluded" for decision in curated.decisions)
    quarantined = sum(
        decision.status == "quarantined" for decision in curated.decisions
    )
    blockers = sorted(
        {
            code
            for entry in curated.coverage_ledger.entries
            for code in entry.blocker_codes
        }
    )
    typer.echo(
        f"curated {len(curated.included_record_ids)} included, {excluded} excluded, "
        f"and {quarantined} quarantined record(s); plan {plan.plan_id}; "
        f"revision {revision.revision_id}"
    )
    if blockers:
        typer.echo(f"coverage blockers: {', '.join(blockers)}", err=True)


@app.command()
def split(workspace: Path) -> None:
    """Assign complete transitive leakage groups to fixed partitions."""
    try:
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
    except (
        VeriformisError,
        EvidenceError,
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
    ) as exc:
        _echo_error(exc)
    _echo_durability_warning(store)
    typer.echo(
        f"split {result.realized_train_record_count} train and "
        f"{result.realized_evaluation_record_count} evaluation record(s) across "
        f"{len(result.groups)} leakage group(s); revision {revision.revision_id}"
    )


@app.command(name="format")
def format_cmd(workspace: Path) -> None:
    """Lower curated records into the row schema fixed by their dataset plan."""
    try:
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
    except (
        VeriformisError,
        EvidenceError,
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
    ) as exc:
        _echo_error(exc)
    _echo_durability_warning(store)
    typer.echo(
        f"wrote {len(output.row_set.train_rows)} train and "
        f"{len(output.row_set.evaluation_rows)} evaluation row(s) as "
        f"{output.row_set.row_schema}; revision {revision.revision_id}"
    )


@app.command()
def validate(workspace: Path) -> None:
    """Replay and validate one exact finished-dataset byte snapshot."""
    try:
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
    except (
        VeriformisError,
        EvidenceError,
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
    ) as exc:
        _echo_error(exc, status=1)
    _echo_durability_warning(store)
    for result in report.gate_results:
        typer.echo(f"{result.gate_id}: {result.status.upper()}")
        for finding in result.finding_codes:
            typer.echo(f"  {finding}")
    typer.echo(f"snapshot {report.snapshot_id}")
    typer.echo(f"validation revision {revision.revision_id}")
    if report.status != "passed":
        raise typer.Exit(code=1)


@app.command()
def seal(workspace: Path, out: Path = typer.Option(..., "-o")) -> None:
    """Revalidate, atomically publish, and receipt one finished dataset."""
    publication = None
    try:
        store = Workspace.open(workspace)
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
    except (
        VeriformisError,
        EvidenceError,
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
    ) as exc:
        if publication is not None:
            typer.echo(
                f"published bundle remains visible at {publication.bundle_path}; "
                f"manifest SHA-256 {publication.manifest_sha256}; workspace receipt "
                "did not commit",
                err=True,
            )
        _echo_error(exc, status=1)
    _echo_durability_warning(store)
    if publication.durability_warning is not None:
        typer.echo(
            f"warning[bundle-durability]: {publication.durability_warning}",
            err=True,
        )
    typer.echo(f"sealed bundle: {publication.bundle_path}")
    typer.echo(f"manifest SHA-256: {publication.manifest_sha256}")
    typer.echo(f"verification grade: {publication.trust_grade}")
    typer.echo(f"seal revision {revision.revision_id}")


@app.command(name="verify")
def verify_cmd(
    bundle: Path,
    manifest_sha256: str | None = typer.Option(None, "--manifest-sha256"),
) -> None:
    """Independently verify one closed finished-dataset bundle."""
    from veriformis.bundle import verify_finished_bundle

    try:
        result = verify_finished_bundle(
            bundle,
            expected_manifest_sha256=manifest_sha256,
        )
    except (VeriformisError, OSError, UnicodeError, ValueError, TypeError) as exc:
        _echo_error(exc, status=1)
    typer.echo(f"verification grade: {result.trust_grade}")
    typer.echo(f"bundle: {result.bundle_id}")
    typer.echo(f"snapshot: {result.dataset_snapshot_id}")
    typer.echo(f"validation report: {result.validation_report_id}")
    typer.echo(f"manifest SHA-256: {result.manifest_sha256}")
    typer.echo(f"dataset rows: {result.declared_record_count}")


@app.command()
def preview(
    path: Path,
    rules: str = typer.Option("", "--rules"),
    custom: str = typer.Option("", "--custom"),
    source_root: Path | None = typer.Option(None, "--source-root"),
) -> None:
    """Plan and replay cleaning without writing state.

    Passing a workspace previews the exact durable plan that ``clean`` will
    commit. A raw-file preview uses the same portable parse-input binding;
    ``--source-root`` supplies the locator used by a later parse.
    """
    try:
        selected, config = _select_rules(rules, custom)
        previews: list[tuple[str, str, Any, tuple[TransformRecord, ...]]] = []
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
                previews.append(
                    (
                        sources[source_id].logical_path,
                        sources[source_id].extracted_text,
                        (plan, replayed),
                        records,
                    )
                )
        else:
            raw_bytes = path.read_bytes()
            logical_path = _logical_paths([path], source_root=source_root)[path]
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
            previews.append(
                (
                    logical_path,
                    result.source.extracted_text,
                    (planned.plan, replayed),
                    planned.records,
                )
            )
    except (
        VeriformisError,
        EvidenceError,
        OSError,
        UnicodeError,
        ValueError,
        re.error,
    ) as exc:
        _echo_error(exc)
    for logical_path, before, (plan, replayed), records in previews:
        if len(previews) > 1 or is_workspace:
            typer.echo(f"source: {logical_path}")
        for record in records:
            typer.echo(
                f"{record.rule}: {record.edits} edit(s), "
                f"{record.bytes_removed} byte(s) removed"
            )
        for run in plan.runs:
            for warning in run.warnings:
                typer.echo(f"warning: {warning}")
        typer.echo(f"plan: {plan.id}")
        typer.echo("--- before ---")
        typer.echo(before[:400])
        typer.echo("--- after ---")
        typer.echo(flatten(list(iter_document_blocks(replayed)))[:400])


@app.command()
def version() -> None:
    typer.echo(veriformis.__version__)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
