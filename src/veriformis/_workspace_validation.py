"""Stage-specific semantic replay before workspace publication.

The transaction owns byte access and commit ordering. These validators preserve
its stage-specific refusals without embedding every replay in workspace.py.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from veriformis.workspace import WorkspaceRevision, WorkspaceTransaction

def _load_construction_context(
    self: WorkspaceTransaction, revision: WorkspaceRevision,
    load_json: Callable[[str], Any],
) -> tuple[Any, Any, Any, tuple[str, ...]]:

    from veriformis.errors import (
        WorkspaceCorruptError,
    )

    from veriformis.workspace import (
        _construct_source_scope,
        sha256_digest,
    )

    from veriformis.chunkers.base import chunk_from_dict
    from veriformis.construction import (
        ConstructionInputs,
        IRArtifactInput,
        construction_result_from_json_bytes,
        dataset_recipe_from_json_bytes,
        validate_construction_result,
    )
    from veriformis.rules.engine import transform_record_from_dict
    from veriformis.sources import SourceRef

    construct_state = revision.stages["construct"]
    selected_source_ids = _construct_source_scope(
        construct_state,
        revision.sources,
    )
    recipe = dataset_recipe_from_json_bytes(
        self._candidate_artifact_bytes(
            revision,
            construct_state.outputs["recipe"],
        )
    )
    result = construction_result_from_json_bytes(
        self._candidate_artifact_bytes(
            revision,
            construct_state.outputs["result"],
        )
    )
    if (
        recipe.recipe_id != construct_state.config["recipe_id"]
        or recipe.source_ids != selected_source_ids
        or result.recipe_id != recipe.recipe_id
    ):
        raise WorkspaceCorruptError(
            "construct config, recipe, and result identities disagree"
        )

    sources: list[SourceRef] = []
    for source_id in selected_source_ids:
        descriptor = revision.sources[source_id]
        artifact_id = descriptor.extracted_artifact_id
        if artifact_id is None:
            raise WorkspaceCorruptError(
                f"source {source_id} has no canonical text artifact"
            )
        extracted = self._candidate_artifact_bytes(
            revision,
            artifact_id,
        ).decode("utf-8")
        sources.append(
            SourceRef(
                id=descriptor.id,
                path=descriptor.original_path or descriptor.logical_path,
                sha256=descriptor.sha256,
                size=descriptor.size,
                parser=descriptor.parser_id,
                extracted_text=extracted,
                logical_path=descriptor.logical_path,
                parser_version=descriptor.parser_version,
                canonical_stream_contract_version=(
                    descriptor.canonical_stream_contract_version
                ),
                stream_sha256=sha256_digest(extracted),
                artifact_id=artifact_id,
            )
        )

    selected_set = set(selected_source_ids)
    raw_chunks = load_json(revision.stages["chunk"].outputs["chunks"])
    if not isinstance(raw_chunks, list):
        raise WorkspaceCorruptError("chunk artifact must contain a JSON array")
    chunks = tuple(
        chunk
        for chunk in (chunk_from_dict(item) for item in raw_chunks)
        if chunk.source_id in selected_set
    )

    clean_state = revision.stages["clean"]
    raw_transforms = load_json(clean_state.outputs["transforms"])
    if not isinstance(raw_transforms, list):
        raise WorkspaceCorruptError(
            "transform artifact must contain a JSON array"
        )
    transforms = tuple(
        record
        for record in (
            transform_record_from_dict(item) for item in raw_transforms
        )
        if record.source_id in selected_set
    )
    ir_artifacts: list[IRArtifactInput] = []
    for source_id in selected_source_ids:
        artifact_id = clean_state.outputs[f"source/{source_id}/document"]
        artifact = revision.artifacts[artifact_id]
        ir_artifacts.append(
            IRArtifactInput.create(
                source_id=source_id,
                artifact_id=artifact_id,
                artifact_kind="cleaned-document-ir",
                document_json=self._candidate_artifact_bytes(
                    revision,
                    artifact_id,
                ),
                producer_id=artifact.producer_id,
                producer_version=artifact.producer_version,
                config_digest=artifact.config_digest,
            )
        )
    reviews = tuple(
        decision.review
        for decision in result.decisions
        if decision.review is not None
    )
    inputs = ConstructionInputs.create(
        cleaning_config_digest=clean_state.config_digest,
        sources=sources,
        chunks=chunks,
        transforms=transforms,
        ir_artifacts=ir_artifacts,
        reviews=reviews,
    )
    validate_construction_result(recipe, inputs, result)
    return recipe, result, inputs, selected_source_ids


def validate_finished_rows(
    self: WorkspaceTransaction, revision: WorkspaceRevision,
    load_json: Callable[[str], Any],
    load_construction_context: Callable[[], tuple[Any, Any, Any, tuple[str, ...]]],
) -> None:

    from veriformis.errors import (
        VeriformisError,
        WorkspaceCorruptError,
    )

    from veriformis.datasets import (
        curate_dataset,
        curation_result_from_json_bytes,
        finished_dataset_plan_from_json_bytes,
        row_set_from_json_bytes,
        serialize_dataset,
        split_dataset,
        split_result_from_json_bytes,
    )

    try:
        recipe, construction, inputs, selected_source_ids = (
            load_construction_context()
        )
        plan = finished_dataset_plan_from_json_bytes(
            self._candidate_artifact_bytes(
                revision,
                revision.stages["curate"].outputs["plan"],
            )
        )
        if plan.plan_id != revision.stages[self.stage].config["plan_id"]:
            raise WorkspaceCorruptError(
                f"{self.stage} config and finished dataset plan disagree"
            )
        curation = curation_result_from_json_bytes(
            self._candidate_artifact_bytes(
                revision,
                revision.stages["curate"].outputs["result"],
            )
        )
        replayed_curation = curate_dataset(
            plan,
            recipe,
            inputs,
            construction,
        )
        if curation != replayed_curation:
            raise WorkspaceCorruptError(
                "curation result does not match deterministic replay"
            )
        if self.stage == "curate":
            return

        raw_digests = {
            source_id: revision.sources[source_id].sha256
            for source_id in selected_source_ids
        }
        split_result = split_result_from_json_bytes(
            self._candidate_artifact_bytes(
                revision,
                revision.stages["split"].outputs["result"],
            )
        )
        replayed_split = split_dataset(
            plan,
            construction,
            curation,
            raw_digests,
        )
        if split_result != replayed_split:
            raise WorkspaceCorruptError(
                "split result does not match deterministic replay"
            )
        if self.stage == "split":
            return

        row_set = row_set_from_json_bytes(
            self._candidate_artifact_bytes(
                revision,
                revision.stages["format"].outputs["row-set"],
            )
        )
        serialized = serialize_dataset(
            plan,
            recipe,
            construction,
            curation,
            split_result,
        )
        format_state = revision.stages["format"]
        exact_outputs = {
            "train": serialized.train_jsonl,
            "evaluation": serialized.evaluation_jsonl,
            "provenance": serialized.provenance_jsonl,
        }
        if row_set != serialized.row_set or any(
            self._candidate_artifact_bytes(
                revision,
                format_state.outputs[name],
            )
            != expected
            for name, expected in exact_outputs.items()
        ):
            raise WorkspaceCorruptError(
                "format artifacts do not match exact record lowering"
            )
    except WorkspaceCorruptError:
        raise
    except (
        VeriformisError,
        KeyError,
        UnicodeError,
        ValueError,
        TypeError,
    ) as exc:
        raise WorkspaceCorruptError(
            f"{self.stage} artifacts do not match their declared inputs"
        ) from exc
    return


def validate_finished_validation(
    self: WorkspaceTransaction, revision: WorkspaceRevision,
    load_json: Callable[[str], Any],
    load_construction_context: Callable[[], tuple[Any, Any, Any, tuple[str, ...]]],
) -> None:

    from veriformis.errors import (
        VeriformisError,
        WorkspaceCorruptError,
    )

    from veriformis.datasets import (
        curation_result_from_json_bytes,
        dataset_snapshot_from_json_bytes,
        dataset_validation_report_from_json_bytes,
        finished_dataset_plan_from_json_bytes,
        row_set_from_json_bytes,
        split_result_from_json_bytes,
        validate_finished_dataset,
    )

    try:
        recipe, construction, inputs, _ = load_construction_context()
        plan = finished_dataset_plan_from_json_bytes(
            self._candidate_artifact_bytes(
                revision,
                revision.stages["curate"].outputs["plan"],
            )
        )
        if plan.plan_id != revision.stages["validate"].config["plan_id"]:
            raise WorkspaceCorruptError(
                "validate config and finished dataset plan disagree"
            )
        curation = curation_result_from_json_bytes(
            self._candidate_artifact_bytes(
                revision,
                revision.stages["curate"].outputs["result"],
            )
        )
        split_result = split_result_from_json_bytes(
            self._candidate_artifact_bytes(
                revision,
                revision.stages["split"].outputs["result"],
            )
        )
        row_set = row_set_from_json_bytes(
            self._candidate_artifact_bytes(
                revision,
                revision.stages["format"].outputs["row-set"],
            )
        )
        format_state = revision.stages["format"]
        train_jsonl = self._candidate_artifact_bytes(
            revision,
            format_state.outputs["train"],
        )
        evaluation_jsonl = self._candidate_artifact_bytes(
            revision,
            format_state.outputs["evaluation"],
        )
        provenance_jsonl = self._candidate_artifact_bytes(
            revision,
            format_state.outputs["provenance"],
        )
        expected = validate_finished_dataset(
            plan,
            recipe,
            inputs,
            construction,
            curation,
            split_result,
            row_set,
            train_jsonl=train_jsonl,
            evaluation_jsonl=evaluation_jsonl,
            provenance_jsonl=provenance_jsonl,
        )
        validate_state = revision.stages["validate"]
        snapshot = dataset_snapshot_from_json_bytes(
            self._candidate_artifact_bytes(
                revision,
                validate_state.outputs["snapshot"],
            )
        )
        report = dataset_validation_report_from_json_bytes(
            self._candidate_artifact_bytes(
                revision,
                validate_state.outputs["report"],
            )
        )
        expected_status = (
            "complete" if expected.status == "passed" else "failed"
        )
        if (
            snapshot != expected.snapshot
            or report != expected
            or validate_state.status != expected_status
        ):
            raise WorkspaceCorruptError(
                "validation artifacts do not match exact snapshot replay"
            )
    except WorkspaceCorruptError:
        raise
    except (
        VeriformisError,
        KeyError,
        UnicodeError,
        ValueError,
        TypeError,
    ) as exc:
        raise WorkspaceCorruptError(
            "validate artifacts do not match their declared inputs"
        ) from exc
    return


def validate_finished_seal(
    self: WorkspaceTransaction, revision: WorkspaceRevision,
    load_json: Callable[[str], Any],
    load_construction_context: Callable[[], tuple[Any, Any, Any, tuple[str, ...]]],
) -> None:

    from veriformis.errors import (
        VeriformisError,
        WorkspaceCorruptError,
    )

    from veriformis.bundle import (
        BundleAttestation,
        FinishedBundleManifest,
        build_finished_bundle,
    )
    from veriformis.datasets import (
        curation_result_from_json_bytes,
        dataset_validation_report_from_json_bytes,
        finished_dataset_plan_from_json_bytes,
        row_set_from_json_bytes,
        split_result_from_json_bytes,
        validate_finished_dataset,
    )

    try:
        recipe, construction, inputs, _ = load_construction_context()
        plan = finished_dataset_plan_from_json_bytes(
            self._candidate_artifact_bytes(
                revision,
                revision.stages["curate"].outputs["plan"],
            )
        )
        seal_state = revision.stages["seal"]
        if plan.plan_id != seal_state.config["plan_id"]:
            raise WorkspaceCorruptError(
                "seal config and finished dataset plan disagree"
            )
        curation = curation_result_from_json_bytes(
            self._candidate_artifact_bytes(
                revision,
                revision.stages["curate"].outputs["result"],
            )
        )
        split_result = split_result_from_json_bytes(
            self._candidate_artifact_bytes(
                revision,
                revision.stages["split"].outputs["result"],
            )
        )
        row_set = row_set_from_json_bytes(
            self._candidate_artifact_bytes(
                revision,
                revision.stages["format"].outputs["row-set"],
            )
        )
        format_state = revision.stages["format"]
        train_jsonl = self._candidate_artifact_bytes(
            revision,
            format_state.outputs["train"],
        )
        evaluation_jsonl = self._candidate_artifact_bytes(
            revision,
            format_state.outputs["evaluation"],
        )
        provenance_jsonl = self._candidate_artifact_bytes(
            revision,
            format_state.outputs["provenance"],
        )
        report_bytes = self._candidate_artifact_bytes(
            revision,
            revision.stages["validate"].outputs["report"],
        )
        report = dataset_validation_report_from_json_bytes(report_bytes)
        expected_report = validate_finished_dataset(
            plan,
            recipe,
            inputs,
            construction,
            curation,
            split_result,
            row_set,
            train_jsonl=train_jsonl,
            evaluation_jsonl=evaluation_jsonl,
            provenance_jsonl=provenance_jsonl,
        )
        if report != expected_report or report.status != "passed":
            raise WorkspaceCorruptError(
                "seal requires the exact current passing validation report"
            )
        files = {
            "data/train.jsonl": train_jsonl,
            "data/evaluation.jsonl": evaluation_jsonl,
            "metadata/row-provenance.jsonl": provenance_jsonl,
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
            "data/train.jsonl": row_set.train_row_count,
            "data/evaluation.jsonl": row_set.evaluation_row_count,
            "metadata/row-provenance.jsonl": row_set.total_row_count,
        }
        expected_manifest, expected_attestation = build_finished_bundle(
            files,
            roles=roles,
            media_types=media_types,
            record_counts=record_counts,
            dataset_snapshot_id=report.snapshot_id,
            validation_report_id=report.report_id,
        )
        manifest_bytes = self._candidate_artifact_bytes(
            revision,
            seal_state.outputs["manifest"],
        )
        attestation_bytes = self._candidate_artifact_bytes(
            revision,
            seal_state.outputs["attestation"],
        )
        manifest = FinishedBundleManifest.from_json_bytes(manifest_bytes)
        attestation = BundleAttestation.from_json_bytes(attestation_bytes)
        if (
            manifest != expected_manifest
            or attestation != expected_attestation
            or manifest_bytes != expected_manifest.canonical_bytes()
            or attestation_bytes != expected_attestation.canonical_bytes()
        ):
            raise WorkspaceCorruptError(
                "seal receipts do not match the validated minimal bundle"
            )
    except WorkspaceCorruptError:
        raise
    except (
        VeriformisError,
        KeyError,
        UnicodeError,
        ValueError,
        TypeError,
    ) as exc:
        raise WorkspaceCorruptError(
            "seal receipts do not match their declared inputs"
        ) from exc
    return


def validate_construct(
    self: WorkspaceTransaction, revision: WorkspaceRevision,
    load_json: Callable[[str], Any],
) -> None:

    from veriformis.errors import (
        VeriformisError,
        WorkspaceCorruptError,
    )

    from veriformis.workspace import (
        _construct_source_scope,
        lossless_json_bytes,
        sha256_digest,
    )

    from veriformis.chunkers.base import chunk_from_dict
    from veriformis.construction import (
        ConstructionInputs,
        IRArtifactInput,
        construction_result_from_dict,
        construction_result_to_dict,
        dataset_recipe_from_dict,
        dataset_recipe_to_dict,
        validate_construction_result,
    )
    from veriformis.rules.engine import transform_record_from_dict
    from veriformis.sources import SourceRef

    try:
        construct_state = revision.stages["construct"]
        selected_source_ids = _construct_source_scope(
            construct_state,
            revision.sources,
        )
        recipe_bytes = self._candidate_artifact_bytes(
            revision,
            construct_state.outputs["recipe"],
        )
        result_bytes = self._candidate_artifact_bytes(
            revision,
            construct_state.outputs["result"],
        )
        raw_recipe = load_json(construct_state.outputs["recipe"])
        raw_result = load_json(construct_state.outputs["result"])
        if not isinstance(raw_recipe, dict) or not isinstance(raw_result, dict):
            raise WorkspaceCorruptError(
                "construct artifacts must contain JSON objects"
            )
        recipe = dataset_recipe_from_dict(raw_recipe)
        result = construction_result_from_dict(raw_result)
        if recipe_bytes != lossless_json_bytes(dataset_recipe_to_dict(recipe)):
            raise WorkspaceCorruptError(
                "dataset recipe artifact is not canonical JSON"
            )
        if result_bytes != lossless_json_bytes(
            construction_result_to_dict(result)
        ):
            raise WorkspaceCorruptError(
                "construction result artifact is not canonical JSON"
            )
        if (
            recipe.recipe_id != construct_state.config["recipe_id"]
            or recipe.source_ids != selected_source_ids
            or result.recipe_id != recipe.recipe_id
        ):
            raise WorkspaceCorruptError(
                "construct config, recipe, and result identities disagree"
            )

        clean_state = revision.stages["clean"]
        chunk_state = revision.stages["chunk"]
        if recipe.cleaning_config_digest != clean_state.config_digest:
            raise WorkspaceCorruptError(
                "dataset recipe does not bind the active clean config"
            )
        chunk_config = chunk_state.config
        if set(chunk_config) != {"strategy", "size", "overlap"} or (
            recipe.segmentation.strategy != chunk_config["strategy"]
            or recipe.segmentation.size != chunk_config["size"]
            or recipe.segmentation.overlap != chunk_config["overlap"]
        ):
            raise WorkspaceCorruptError(
                "dataset recipe does not bind the active segmentation"
            )

        sources: list[SourceRef] = []
        for source_id in selected_source_ids:
            descriptor = revision.sources[source_id]
            artifact_id = descriptor.extracted_artifact_id
            if artifact_id is None:
                raise WorkspaceCorruptError(
                    f"source {source_id} has no canonical text artifact"
                )
            extracted = self._candidate_artifact_bytes(
                revision,
                artifact_id,
            ).decode("utf-8")
            sources.append(
                SourceRef(
                    id=descriptor.id,
                    path=(descriptor.original_path or descriptor.logical_path),
                    sha256=descriptor.sha256,
                    size=descriptor.size,
                    parser=descriptor.parser_id,
                    extracted_text=extracted,
                    logical_path=descriptor.logical_path,
                    parser_version=descriptor.parser_version,
                    canonical_stream_contract_version=(
                        descriptor.canonical_stream_contract_version
                    ),
                    stream_sha256=sha256_digest(extracted),
                    artifact_id=artifact_id,
                )
            )

        raw_chunks = load_json(chunk_state.outputs["chunks"])
        if not isinstance(raw_chunks, list):
            raise WorkspaceCorruptError(
                "chunk artifact must contain a JSON array"
            )
        selected_set = set(selected_source_ids)
        chunks = tuple(
            chunk
            for chunk in (chunk_from_dict(item) for item in raw_chunks)
            if chunk.source_id in selected_set
        )

        raw_transforms = load_json(clean_state.outputs["transforms"])
        if not isinstance(raw_transforms, list):
            raise WorkspaceCorruptError(
                "transform artifact must contain a JSON array"
            )
        transforms = tuple(
            record
            for record in (
                transform_record_from_dict(item) for item in raw_transforms
            )
            if record.source_id in selected_set
        )

        ir_artifacts: list[IRArtifactInput] = []
        for source_id in selected_source_ids:
            document_artifact_id = clean_state.outputs[
                f"source/{source_id}/document"
            ]
            artifact = revision.artifacts[document_artifact_id]
            ir_artifacts.append(
                IRArtifactInput.create(
                    source_id=source_id,
                    artifact_id=document_artifact_id,
                    artifact_kind="cleaned-document-ir",
                    document_json=self._candidate_artifact_bytes(
                        revision,
                        document_artifact_id,
                    ),
                    producer_id=artifact.producer_id,
                    producer_version=artifact.producer_version,
                    config_digest=artifact.config_digest,
                )
            )

        reviews = tuple(
            decision.review
            for decision in result.decisions
            if decision.review is not None
        )
        inputs = ConstructionInputs.create(
            cleaning_config_digest=clean_state.config_digest,
            sources=sources,
            chunks=chunks,
            transforms=transforms,
            ir_artifacts=ir_artifacts,
            reviews=reviews,
        )
        validate_construction_result(recipe, inputs, result)
    except WorkspaceCorruptError:
        raise
    except (
        VeriformisError,
        KeyError,
        UnicodeError,
        ValueError,
        TypeError,
    ) as exc:
        raise WorkspaceCorruptError(
            "construct artifacts do not match their declared inputs"
        ) from exc
    return


def validate_chunk(
    self: WorkspaceTransaction, revision: WorkspaceRevision,
    load_json: Callable[[str], Any],
) -> None:

    from veriformis.errors import (
        VeriformisError,
        WorkspaceCorruptError,
    )

    from veriformis.workspace import (
        canonical_digest,
        sha256_digest,
    )

    from veriformis.chunkers.base import chunk_from_dict
    from veriformis.chunkers.pipeline import build_chunks
    from veriformis.errors import EvidenceError
    from veriformis.evidence import derivation_from_dict, replay_derivations
    from veriformis.ir import (
        block_text,
        document_from_dict,
        iter_document_blocks,
        validate_document_against_stream,
    )
    from veriformis.rules.cleaning import (
        cleaning_input_digest,
        cleaning_plan_from_dict,
        plan_cleaning,
    )
    from veriformis.rules.derivations import (
        block_derivations_from_dict,
        build_block_derivations,
    )
    from veriformis.rules.engine import transform_record_from_dict
    from veriformis.rules.library import rules_from_clean_config
    from veriformis.sources import SourceRef

    raw_chunks = load_json(revision.stages["chunk"].outputs["chunks"])
    if not isinstance(raw_chunks, list):
        raise WorkspaceCorruptError("chunk artifact must contain a JSON array")
    try:
        chunks = [chunk_from_dict(item) for item in raw_chunks]
        ids = [chunk.id for chunk in chunks]
        if len(ids) != len(set(ids)):
            raise EvidenceError("chunk artifact contains duplicate identities")
        sources: dict[str, SourceRef] = {}
        documents = {}
        derivations_by_source = {}
        expected_records = []
        clean_state = revision.stages["clean"]
        parse_state = revision.stages["parse"]
        configured_rules = rules_from_clean_config(clean_state.config)
        for source_id, descriptor in sorted(revision.sources.items()):
            artifact_id = descriptor.extracted_artifact_id
            if artifact_id is None:
                raise EvidenceError(
                    f"source {source_id} has no canonical text artifact"
                )
            extracted = self._candidate_artifact_bytes(
                revision, artifact_id
            ).decode("utf-8")
            sources[source_id] = SourceRef(
                id=descriptor.id,
                path=descriptor.original_path or descriptor.logical_path,
                sha256=descriptor.sha256,
                size=descriptor.size,
                parser=descriptor.parser_id,
                extracted_text=extracted,
                logical_path=descriptor.logical_path,
                parser_version=descriptor.parser_version,
                canonical_stream_contract_version=(
                    descriptor.canonical_stream_contract_version
                ),
                stream_sha256=sha256_digest(extracted),
                artifact_id=artifact_id,
            )
            parsed = document_from_dict(
                load_json(parse_state.outputs[f"source/{source_id}/document"])
            )
            validate_document_against_stream(parsed, extracted, exact=True)
            plan = cleaning_plan_from_dict(
                load_json(
                    clean_state.outputs[f"source/{source_id}/cleaning-plan"]
                )
            )
            expected_input = cleaning_input_digest(
                parsed,
                source_id=source_id,
                raw_sha256=descriptor.sha256,
                canonical_artifact_id=artifact_id,
                canonical_stream_sha256=sha256_digest(extracted),
                parser=descriptor.parser_id,
                parser_version=descriptor.parser_version,
                canonical_stream_contract_version=(
                    descriptor.canonical_stream_contract_version
                ),
            )
            if plan.base_input_sha256 != expected_input:
                raise EvidenceError(
                    f"cleaning plan is not bound to source {source_id}"
                )
            expected_preview = plan_cleaning(
                parsed,
                configured_rules,
                max_remove_frac=(
                    clean_state.config["max_remove_ppm"] / 1_000_000
                ),
                base_input_sha256=expected_input,
            )
            if plan != expected_preview.plan:
                raise EvidenceError(
                    "cleaning plan does not match configured replay"
                )
            cleaned = document_from_dict(
                load_json(clean_state.outputs[f"source/{source_id}/document"])
            )
            if cleaned != expected_preview.document:
                raise EvidenceError(
                    f"cleaned document does not replay for source {source_id}"
                )
            validate_document_against_stream(cleaned, extracted, exact=False)
            documents[source_id] = cleaned
            expected_records.extend(expected_preview.records)

            derivation_artifact_id = clean_state.outputs[
                f"source/{source_id}/block-derivations"
            ]
            if revision.artifacts[
                derivation_artifact_id
            ].config_digest != canonical_digest(
                {**clean_state.config, "cleaning_plan_id": plan.id}
            ):
                raise EvidenceError(
                    "block derivation artifact is not configured for its plan"
                )
            raw_derivations = load_json(derivation_artifact_id)
            actual_derivations = block_derivations_from_dict(raw_derivations)
            expected_derivations = build_block_derivations(
                sources[source_id],
                cleaned,
                cleaning_plan_id=plan.id,
            )
            if actual_derivations != expected_derivations:
                raise EvidenceError(
                    "block derivations are not the canonical replay"
                )
            expected_indexes = {
                str(block.block_index)
                for block in iter_document_blocks(cleaned)
            }
            if (
                not isinstance(raw_derivations, dict)
                or set(raw_derivations) != expected_indexes
            ):
                raise EvidenceError(
                    "block derivations do not cover the cleaned document"
                )
            source_derivations = {}
            for block in iter_document_blocks(cleaned):
                raw_steps = raw_derivations[str(block.block_index)]
                if not isinstance(raw_steps, list) or block.span is None:
                    raise EvidenceError("invalid block derivation entry")
                steps = tuple(derivation_from_dict(item) for item in raw_steps)
                original = extracted[block.span.start : block.span.end]
                cleaned_text = block_text(block)
                if original == cleaned_text:
                    if steps:
                        raise EvidenceError(
                            "unchanged block carries cleaning derivations"
                        )
                else:
                    expected_context = canonical_digest(
                        {
                            "cleaning_plan_id": plan.id,
                            "source_id": source_id,
                            "block_index": block.block_index,
                        }
                    )
                    if (
                        len(steps) != 1
                        or steps[0].kind != "edits"
                        or steps[0].context_digest != expected_context
                        or replay_derivations(original, steps) != cleaned_text
                    ):
                        raise EvidenceError(
                            "block derivation is not bound to its plan"
                        )
                source_derivations[block.block_index] = steps
            derivations_by_source[source_id] = source_derivations

        raw_records = load_json(clean_state.outputs["transforms"])
        if not isinstance(raw_records, list):
            raise EvidenceError("transform artifact must be an array")
        records = [transform_record_from_dict(item) for item in raw_records]
        if records != expected_records:
            raise EvidenceError(
                "transform metadata does not match cleaning plan replay"
            )
        config = revision.stages["chunk"].config
        if set(config) != {"strategy", "size", "overlap"}:
            raise EvidenceError(
                "chunk stage config does not match its v1 schema"
            )
        expected_chunks = build_chunks(
            documents,
            sources,
            records,
            derivations_by_source,
            strategy=config["strategy"],
            size=config["size"],
            overlap=config["overlap"],
        )
        if chunks != expected_chunks:
            raise EvidenceError(
                "chunk artifact does not match deterministic replay"
            )
    except WorkspaceCorruptError:
        raise
    except (
        VeriformisError,
        KeyError,
        UnicodeError,
        ValueError,
        TypeError,
    ) as exc:
        raise WorkspaceCorruptError(
            "chunk artifact does not match its registered clean state"
        ) from exc
    return


def validate_clean(
    self: WorkspaceTransaction, revision: WorkspaceRevision,
    load_json: Callable[[str], Any],
) -> None:

    from veriformis.errors import (
        VeriformisError,
        WorkspaceCorruptError,
    )

    from veriformis.workspace import (
        canonical_digest,
        sha256_digest,
    )

    from veriformis.ir import (
        block_text,
        document_from_dict,
        iter_document_blocks,
        validate_document_against_stream,
    )

    parse_state = revision.stages["parse"]
    from veriformis.evidence import (
        derivation_from_dict,
        replay_derivations,
    )
    from veriformis.rules.cleaning import (
        cleaning_input_digest,
        cleaning_plan_from_dict,
        plan_cleaning,
    )
    from veriformis.rules.derivations import (
        block_derivations_from_dict,
        build_block_derivations,
    )
    from veriformis.rules.engine import transform_record_from_dict
    from veriformis.rules.library import rules_from_clean_config
    from veriformis.sources import SourceRef

    clean_state = revision.stages["clean"]
    try:
        configured_rules = rules_from_clean_config(clean_state.config)
    except VeriformisError as exc:
        raise WorkspaceCorruptError("clean stage config is invalid") from exc
    expected_records = []
    for source_id, source in sorted(revision.sources.items()):
        canonical_artifact_id = source.extracted_artifact_id
        if canonical_artifact_id is None:
            raise WorkspaceCorruptError(
                f"source {source_id} lacks canonical input"
            )
        canonical = self._candidate_artifact_bytes(
            revision, canonical_artifact_id
        ).decode("utf-8")
        parsed = document_from_dict(
            load_json(parse_state.outputs[f"source/{source_id}/document"])
        )
        validate_document_against_stream(parsed, canonical, exact=True)
        plan = cleaning_plan_from_dict(
            load_json(clean_state.outputs[f"source/{source_id}/cleaning-plan"])
        )
        expected_input = cleaning_input_digest(
            parsed,
            source_id=source_id,
            raw_sha256=source.sha256,
            canonical_artifact_id=canonical_artifact_id,
            canonical_stream_sha256=sha256_digest(canonical),
            parser=source.parser_id,
            parser_version=source.parser_version,
            canonical_stream_contract_version=(
                source.canonical_stream_contract_version
            ),
        )
        if plan.base_input_sha256 != expected_input:
            raise WorkspaceCorruptError(
                f"cleaning plan is not bound to source {source_id}"
            )
        expected_preview = plan_cleaning(
            parsed,
            configured_rules,
            max_remove_frac=clean_state.config["max_remove_ppm"] / 1_000_000,
            base_input_sha256=expected_input,
        )
        if plan != expected_preview.plan:
            raise WorkspaceCorruptError(
                f"cleaning plan is not the configured replay for source {source_id}"
            )
        expected_records.extend(expected_preview.records)
        cleaned = document_from_dict(
            load_json(clean_state.outputs[f"source/{source_id}/document"])
        )
        expected_cleaned = expected_preview.document
        if cleaned != expected_cleaned:
            raise WorkspaceCorruptError(
                f"cleaned document does not replay for source {source_id}"
            )
        validate_document_against_stream(cleaned, canonical, exact=False)

        raw_derivations = load_json(
            clean_state.outputs[f"source/{source_id}/block-derivations"]
        )
        if not isinstance(raw_derivations, dict):
            raise WorkspaceCorruptError(
                "block derivations must be a JSON object"
            )
        actual_derivations = block_derivations_from_dict(raw_derivations)
        expected_derivations = build_block_derivations(
            SourceRef(
                id=source.id,
                path=source.logical_path,
                sha256=source.sha256,
                size=source.size,
                parser=source.parser_id,
                extracted_text=canonical,
                logical_path=source.logical_path,
                parser_version=source.parser_version,
                canonical_stream_contract_version=(
                    source.canonical_stream_contract_version
                ),
                stream_sha256=sha256_digest(canonical),
                artifact_id=canonical_artifact_id,
            ),
            cleaned,
            cleaning_plan_id=plan.id,
        )
        if actual_derivations != expected_derivations:
            raise WorkspaceCorruptError(
                "block derivations do not match canonical cleaning replay"
            )
        derivation_artifact_id = clean_state.outputs[
            f"source/{source_id}/block-derivations"
        ]
        expected_derivation_config = canonical_digest(
            {**clean_state.config, "cleaning_plan_id": plan.id}
        )
        if (
            revision.artifacts[derivation_artifact_id].config_digest
            != expected_derivation_config
        ):
            raise WorkspaceCorruptError(
                f"block derivations are not configured for plan {plan.id}"
            )
        expected_indexes = {
            str(block.block_index) for block in iter_document_blocks(cleaned)
        }
        if set(raw_derivations) != expected_indexes:
            raise WorkspaceCorruptError(
                f"block derivations do not cover source {source_id}"
            )
        for block in iter_document_blocks(cleaned):
            raw_steps = raw_derivations[str(block.block_index)]
            if not isinstance(raw_steps, list):
                raise WorkspaceCorruptError(
                    "block derivation entry must be an array"
                )
            steps = tuple(derivation_from_dict(item) for item in raw_steps)
            if block.span is None:
                raise WorkspaceCorruptError(
                    "cleaned block lacks immutable source span"
                )
            original = canonical[block.span.start : block.span.end]
            cleaned_text = block_text(block)
            if original == cleaned_text:
                if steps:
                    raise WorkspaceCorruptError(
                        "unchanged block carries cleaning derivations"
                    )
                continue
            expected_context = canonical_digest(
                {
                    "cleaning_plan_id": plan.id,
                    "source_id": source_id,
                    "block_index": block.block_index,
                }
            )
            if (
                len(steps) != 1
                or steps[0].kind != "edits"
                or steps[0].context_digest != expected_context
            ):
                raise WorkspaceCorruptError(
                    "block derivation is not bound to its cleaning plan"
                )
            if replay_derivations(original, steps) != cleaned_text:
                raise WorkspaceCorruptError(
                    f"block derivations do not reconstruct source {source_id}"
                )

    raw_records = load_json(clean_state.outputs["transforms"])
    if not isinstance(raw_records, list):
        raise WorkspaceCorruptError("transform artifact must be a JSON array")
    records = [transform_record_from_dict(item) for item in raw_records]
    if records != expected_records:
        raise WorkspaceCorruptError(
            "transform artifact metadata does not match plan replay"
        )
    return


def validate_parse(
    self: WorkspaceTransaction, revision: WorkspaceRevision,
    load_json: Callable[[str], Any],
) -> None:

    from veriformis.errors import (
        ParseError,
        VeriformisError,
        WorkspaceCorruptError,
    )

    from veriformis.ir import (
        document_from_dict,
        validate_document_against_stream,
    )

    parse_state = revision.stages["parse"]
    from veriformis.diagnostics import (
        parse_report_from_dict,
        validate_parse_report_locations,
    )
    from veriformis.parsers.dispatch import parse_captured_source

    registry = load_json(parse_state.outputs["registry"])
    expected_registry = [
        source.model_dump(mode="json", exclude={"original_path"})
        for source in sorted(revision.sources.values(), key=lambda item: item.id)
    ]
    if registry != expected_registry:
        raise WorkspaceCorruptError(
            "parse registry does not match the candidate source descriptors"
        )

    for source_id, source in sorted(revision.sources.items()):
        if source.raw_artifact_id is None:
            raise WorkspaceCorruptError(
                f"source {source_id} lacks captured raw input"
            )
        raw_bytes = self._candidate_artifact_bytes(
            revision,
            source.raw_artifact_id,
        )
        canonical = self._candidate_artifact_bytes(
            revision,
            parse_state.outputs[f"source/{source_id}/canonical"],
        ).decode("utf-8")
        document = document_from_dict(
            load_json(parse_state.outputs[f"source/{source_id}/document"])
        )
        if document.source_id != source_id:
            raise WorkspaceCorruptError(
                f"parse document source does not match {source_id}"
            )
        validate_document_against_stream(document, canonical, exact=True)
        report = parse_report_from_dict(
            load_json(parse_state.outputs[f"source/{source_id}/diagnostics"])
        )
        if (
            report.source_id != source_id
            or report.parser_name != source.parser_id
            or report.parser_version != source.parser_version
            or report.status == "refused"
        ):
            raise WorkspaceCorruptError(
                f"parse report does not match source {source_id}"
            )
        try:
            validate_parse_report_locations(report, raw_bytes)
        except ParseError as exc:
            raise WorkspaceCorruptError(
                f"parse report locations do not match source {source_id}"
            ) from exc
        try:
            expected = parse_captured_source(
                source.logical_path,
                logical_path=source.logical_path,
                raw_bytes=raw_bytes,
            )
        except (VeriformisError, OSError, UnicodeError, ValueError) as exc:
            raise WorkspaceCorruptError(
                f"captured raw source {source_id} cannot be deterministically parsed"
            ) from exc
        expected_source = expected.source
        descriptor_semantics = (
            source.id,
            source.logical_path,
            source.sha256,
            source.size,
            source.parser_id,
            source.parser_version,
            source.canonical_stream_contract_version,
            source.extracted_artifact_id,
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
            raise WorkspaceCorruptError(
                f"source descriptor does not match raw parser result {source_id}"
            )
        if (
            canonical != expected_source.extracted_text
            or document != expected.document
            or report != expected.diagnostics
        ):
            raise WorkspaceCorruptError(
                f"parse artifacts do not match captured raw source {source_id}"
            )

