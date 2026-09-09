"""Shared review fixtures, separate from collected tests."""

from __future__ import annotations
from dataclasses import dataclass
from collections.abc import Sequence
from pathlib import Path
from veriformis.chunkers.base import Chunk
from veriformis.chunkers.strategies import chunk_paragraph
from veriformis.construction import (
    ConstructionInputs,
    ConstructionPass,
    ConstructionResult,
    DatasetRecipe,
    IRArtifactInput,
    SegmentationPolicy,
    TrainingObjective,
    construct_dataset,
)
from veriformis.identity import (
    canonical_digest,
    derive_artifact_id,
    lossless_json_bytes,
    sha256_digest,
)
from veriformis.ir import Block, Document, Paragraph, Text, attach_canonical_provenance
from veriformis.ir.serde import document_to_dict
from veriformis.sources import SourceRef, register_source

@dataclass(frozen=True)
class SourceBundle:
    source: SourceRef
    document: Document
    chunks: tuple[Chunk, ...]
    artifact: IRArtifactInput

def source_bundle(
    tmp_path: Path,
    *,
    logical_path: str,
    blocks: Sequence[Block],
) -> SourceBundle:
    document = Document(children=list(blocks))
    stream = attach_canonical_provenance(document)
    source = register_source(
        tmp_path / logical_path,
        "fixture",
        stream,
        logical_path=logical_path,
        raw_bytes=stream.encode("utf-8"),
    )
    document.source_id = source.id
    chunks = chunk_paragraph(
        document.children,
        max_size=1_000,
        source=source,
        transformed=set(),
        block_derivations={},
        region_id="body",
    )
    document_json = lossless_json_bytes(document_to_dict(document))
    artifact_config_digest = canonical_digest({"fixture": logical_path})
    artifact_id = derive_artifact_id(
        kind="cleaned-document-ir",
        content_sha256=sha256_digest(document_json),
        source_ids=(source.id,),
        producer_id="veriformis.test.review-queues",
        producer_version="1",
        config_digest=artifact_config_digest,
    )
    artifact = IRArtifactInput.create(
        source_id=source.id,
        artifact_id=artifact_id,
        artifact_kind="cleaned-document-ir",
        document_json=document_json,
        producer_id="veriformis.test.review-queues",
        producer_version="1",
        config_digest=artifact_config_digest,
    )
    return SourceBundle(source, document, tuple(chunks), artifact)

def _construct(
    tmp_path: Path,
    texts: tuple[tuple[str, str], ...],
    *,
    review_policy: str = "none",
) -> ConstructionResult:
    bundles = tuple(
        source_bundle(
            tmp_path,
            logical_path=logical_path,
            blocks=[Paragraph(children=[Text(text)])],
        )
        for logical_path, text in texts
    )
    recipe = DatasetRecipe.create(
        objective=TrainingObjective.create("full_text"),
        source_ids=tuple(item.source.id for item in bundles),
        cleaning_config_digest=canonical_digest({"cleaning": "fixture-v1"}),
        segmentation=SegmentationPolicy(
            schema_version="veriformis.segmentation-policy/v1",
            strategy="paragraph",
            size=1_000,
            overlap=100,
        ),
        passes=(ConstructionPass.create(sequence=1, objective_kind="full_text"),),
        target_row_schema="text",
        review_policy=review_policy,  # type: ignore[arg-type]
    )
    inputs = ConstructionInputs.create(
        cleaning_config_digest=canonical_digest({"cleaning": "fixture-v1"}),
        sources=tuple(bundle.source for bundle in bundles),
        chunks=tuple(chunk for bundle in bundles for chunk in bundle.chunks),
        transforms=(),
        ir_artifacts=tuple(bundle.artifact for bundle in bundles),
    )
    return construct_dataset(recipe, inputs)
