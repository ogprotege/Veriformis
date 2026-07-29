"""Veriformis CLI over immutable, transactional workspace revisions.

The CLI remains the M1 orchestration surface. Every inter-stage artifact is
content-addressed and every successful stage becomes visible through one
atomic workspace ``HEAD`` transition.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

import typer

import veriformis
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
    construction_result_to_dict,
    dataset_recipe_to_dict,
)
from veriformis.contracts import (
    DETERMINISTIC_V1_OBJECTIVE_KINDS,
    V1_ROW_SCHEMA_KINDS,
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
from veriformis.serializers.chat import serialize_chat
from veriformis.serializers.formats import serialize_completion, serialize_instruction
from veriformis.sources import ParseResult, SourceRef
from veriformis.validate.gates import RECORD_SCHEMAS, GateResult, run_gates
from veriformis.workspace import (
    CONSTRUCTION_STAGE_CONFIG_SCHEMA_VERSION,
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


def _json_load(data: bytes) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number is not allowed: {value}")

    def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise EvidenceError(
                    f"persisted JSON contains duplicate key {key!r}"
                )
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
        raise EvidenceError(f"persisted artifact is not valid UTF-8 JSON: {exc}") from exc


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
        extracted = workspace.read_artifact(artifact_id, revision=revision).decode("utf-8")
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
        canonical_stream_contract_version=(
            source.canonical_stream_contract_version
        ),
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
    parsed_sources = (
        _load_sources(workspace, revision)
        if stage == "clean"
        else None
    )
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
                    revision.stages["clean"].config["max_remove_ppm"]
                    / 1_000_000
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
    derivations_by_source: dict[
        str, dict[int, tuple[DerivationStep, ...]]
    ] = {}
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
                    raise EvidenceError("parser and workspace canonical artifact IDs differ")
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
        if current.stages["clean"].status == "complete" \
                and current.stages["clean"].config == config:
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
    except (VeriformisError, EvidenceError, OSError, UnicodeError, ValueError, re.error) as exc:
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
        typer.echo(f"unknown strategy: {strategy} (have: {sorted(_STRATEGIES)})", err=True)
        raise typer.Exit(code=2)
    if size < 1 or overlap < 0 or overlap >= size:
        typer.echo("size must be positive and overlap must satisfy 0 <= overlap < size", err=True)
        raise typer.Exit(code=2)
    config = {"strategy": strategy, "size": size, "overlap": overlap}
    try:
        store = Workspace.open(workspace)
        with store.begin("chunk") as transaction:
            base = transaction.base
            documents = _load_documents(store, base, stage="clean")
            sources = _load_sources(store, base)
            raw_transforms = _load_transform_records(store, base)
            derivations_by_source: dict[
                str, dict[int, tuple[DerivationStep, ...]]
            ] = {}
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
    """Atomically migrate a verified revision-v1 workspace to revision v2."""
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
            raise ConstructionError(
                "split ratio must be from 1 to 999999 ppm"
            )

        store = Workspace.open(workspace)
        current = store.head()
        if "construct" not in current.stages:
            raise UnsupportedWorkspaceVersionError(
                "construct requires workspace revision schema 2; run "
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


@app.command(name="format")
def format_cmd(
    workspace: Path,
    format: str = typer.Option(..., "--format"),
    template: str = typer.Option("llama3", "--template"),
    instruction: str = typer.Option("", "--instruction"),
    with_heading_path: bool = typer.Option(False, "--with-heading-path"),
) -> None:
    """Serialize current chunks into the selected M1 record projection."""
    if format not in RECORD_SCHEMAS:
        typer.echo(f"unknown format: {format} (have: {sorted(RECORD_SCHEMAS)})", err=True)
        raise typer.Exit(code=2)
    if format == "instruction" and not instruction:
        typer.echo("--instruction is required for instruction format", err=True)
        raise typer.Exit(code=2)
    config = {
        "format": format,
        "template": template if format == "chat" else None,
        "instruction": instruction if format == "instruction" else None,
        "with_heading_path": with_heading_path,
    }
    try:
        store = Workspace.open(workspace)
        with store.begin("format") as transaction:
            base = transaction.base
            chunks = _load_chunks(store, base)
            if format == "completion":
                records = serialize_completion(
                    chunks,
                    include_heading_path=with_heading_path,
                )
            elif format == "instruction":
                records = serialize_instruction(chunks, instruction=instruction)
            else:
                records = serialize_chat(
                    [
                        {
                            "user": "Summarize the following.",
                            "assistant": item.text,
                        }
                        for item in chunks
                    ],
                    template=template,
                )
            record_bytes = "".join(
                json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
                for record in records
            ).encode("utf-8")
            source_ids = tuple(sorted({item.source_id for item in chunks}))
            records_artifact = transaction.put_artifact(
                record_bytes,
                kind="formatted-records",
                media_type="application/x-ndjson",
                source_ids=source_ids,
                producer_id=f"veriformis.serializer.{format}",
                producer_version="1",
                config=config,
            )
            metadata_artifact = transaction.put_artifact(
                lossless_json_bytes({"format": format, "template": config["template"]}),
                kind="records-metadata",
                media_type="application/json",
                source_ids=source_ids,
                producer_id=f"veriformis.serializer.{format}",
                producer_version="1",
                config=config,
            )
            revision = transaction.commit(
                outputs={
                    "records": records_artifact,
                    "records-meta": metadata_artifact,
                },
                config=config,
            )
    except (VeriformisError, EvidenceError, OSError, UnicodeError, ValueError) as exc:
        _echo_error(exc)
    _echo_durability_warning(store)
    typer.echo(f"wrote {len(records)} record(s); revision {revision.revision_id}")


@app.command()
def validate(workspace: Path, format: str = typer.Option(..., "--format")) -> None:
    """Run M1 gates against one immutable workspace revision."""
    if format not in RECORD_SCHEMAS:
        typer.echo(f"unknown format: {format} (have: {sorted(RECORD_SCHEMAS)})", err=True)
        raise typer.Exit(code=2)
    config = {"format": format}
    try:
        store = Workspace.open(workspace)
        with store.begin("validate") as transaction:
            base = transaction.base
            metadata = _json_load(
                _output_bytes(store, base, "format", "records-meta")
            )
            if metadata.get("format") != format:
                raise EvidenceError(
                    f"requested format {format!r} does not match formatted records"
                )
            chunks = _load_chunks(store, base)
            sources = _load_sources(store, base)
            records = [
                json.loads(line)
                for line in _output_bytes(store, base, "format", "records")
                .decode("utf-8")
                .splitlines()
                if line.strip()
            ]
            results = run_gates(records, format, chunks, sources)
            artifact = transaction.put_artifact(
                lossless_json_bytes([asdict(result) for result in results]),
                kind="validation-report",
                media_type="application/json",
                source_ids=tuple(sorted(sources)),
                producer_id="veriformis.validation",
                producer_version="1",
                config=config,
            )
            revision = transaction.commit(
                outputs={"validations": artifact},
                config=config,
                status="complete" if all(result.passed for result in results) else "failed",
            )
    except (VeriformisError, EvidenceError, OSError, UnicodeError, ValueError) as exc:
        _echo_error(exc, status=1)
    _echo_durability_warning(store)
    for result in results:
        typer.echo(f"{result.gate}: {'PASS' if result.passed else 'FAIL'}")
        for message in result.messages:
            typer.echo(f"  {message}")
    if not all(result.passed for result in results):
        raise typer.Exit(code=1)
    typer.echo(f"validation revision {revision.revision_id}")


@app.command()
def seal(workspace: Path, out: Path = typer.Option(..., "-o")) -> None:
    """Write the current validated snapshot using the M1 bundle format."""
    from veriformis.bundle.writer import write_bundle

    try:
        store = Workspace.open(workspace)
        with store.begin("seal") as transaction:
            revision = transaction.base
            sources = _load_sources(store, revision)
            _load_documents(store, revision, stage="clean")
            chunks = _load_chunks(store, revision)
            records = [
                json.loads(line)
                for line in _output_bytes(store, revision, "format", "records")
                .decode("utf-8")
                .splitlines()
                if line.strip()
            ]
            transforms = _load_transform_records(store, revision)
            validations = [
                GateResult(**value)
                for value in _json_load(
                    _output_bytes(store, revision, "validate", "validations")
                )
            ]
            metadata = _json_load(
                _output_bytes(store, revision, "format", "records-meta")
            )
            bundle = write_bundle(
                out,
                records=records,
                chunks=chunks,
                sources=list(sources.values()),
                transforms=transforms,
                validations=validations,
                format=metadata["format"],
                template=metadata.get("template"),
            )
    except (VeriformisError, EvidenceError, OSError, UnicodeError, ValueError) as exc:
        _echo_error(exc, status=1)
    typer.echo(f"sealed bundle: {bundle}")


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
                cleaned_documents = _load_documents(
                    store, revision, stage="clean"
                )
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
    except (VeriformisError, EvidenceError, OSError, UnicodeError, ValueError, re.error) as exc:
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
