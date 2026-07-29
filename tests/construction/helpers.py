from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from veriformis.chunkers.base import Chunk
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
)
from veriformis.identity import (
    canonical_digest,
    derive_artifact_id,
    lossless_json_bytes,
    sha256_digest,
)
from veriformis.ir import Block, Document, attach_canonical_provenance
from veriformis.ir.serde import document_to_dict
from veriformis.rules.cleaning import plan_cleaning
from veriformis.rules.derivations import build_block_derivations
from veriformis.rules.engine import RegexRule
from veriformis.rules.engine import TransformRecord
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
    strategy: str = "paragraph",
    size: int = 1_000,
    overlap: int = 100,
    block_derivations=None,
    transformed: set[int] | None = None,
    artifact_kind: str = "cleaned-document-ir",
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
    kwargs = {
        "source": source,
        "transformed": transformed or set(),
        "block_derivations": block_derivations or {},
        "region_id": "body",
    }
    if strategy in {"paragraph", "sentence", "structure"}:
        chunker = {
            "paragraph": chunk_paragraph,
            "sentence": chunk_sentence,
            "structure": chunk_structure,
        }[strategy]
        chunks = chunker(document.children, max_size=size, **kwargs)
    else:
        chunker = {"fixed": chunk_fixed, "sliding": chunk_sliding}[strategy]
        chunks = chunker(document.children, size=size, overlap=overlap, **kwargs)
    document_json = lossless_json_bytes(document_to_dict(document))
    artifact_config_digest = canonical_digest({"fixture": logical_path})
    artifact_id = derive_artifact_id(
        kind=artifact_kind,
        content_sha256=sha256_digest(document_json),
        source_ids=(source.id,),
        producer_id="veriformis.test.fixture",
        producer_version="1",
        config_digest=artifact_config_digest,
    )
    artifact = IRArtifactInput.create(
        source_id=source.id,
        artifact_id=artifact_id,
        artifact_kind=artifact_kind,
        document_json=document_json,
        producer_id="veriformis.test.fixture",
        producer_version="1",
        config_digest=artifact_config_digest,
    )
    return SourceBundle(source, document, tuple(chunks), artifact)


def recipe_for(
    sources: Sequence[SourceRef],
    objective_kind: str,
    *,
    strategy: str = "paragraph",
    size: int = 1_000,
    overlap: int = 100,
    review_policy: str = "none",
    parameters: dict | None = None,
) -> DatasetRecipe:
    objective = TrainingObjective.create(objective_kind)
    construction_pass = ConstructionPass.create(
        sequence=1,
        objective_kind=objective_kind,
        parameters=parameters,
    )
    return DatasetRecipe.create(
        objective=objective,
        source_ids=tuple(source.id for source in sources),
        cleaning_config_digest=canonical_digest({"cleaning": "fixture-v1"}),
        segmentation=SegmentationPolicy(
            schema_version="veriformis.segmentation-policy/v1",
            strategy=strategy,
            size=size,
            overlap=overlap,
        ),
        passes=(construction_pass,),
        target_row_schema=(
            "text" if objective_kind == "full_text" else "prompt_completion"
        ),
        review_policy=review_policy,
    )


def cleaned_source_bundle(
    tmp_path: Path,
    *,
    logical_path: str,
    text: str,
) -> tuple[SourceBundle, tuple[TransformRecord, ...]]:
    from veriformis.ir import Paragraph, Text

    original = Document(children=[Paragraph(children=[Text(text)])])
    stream = attach_canonical_provenance(original)
    source = register_source(
        tmp_path / logical_path,
        "fixture",
        stream,
        logical_path=logical_path,
        raw_bytes=stream.encode("utf-8"),
    )
    original.source_id = source.id
    preview = plan_cleaning(
        original,
        [RegexRule("collapse-space", r" {2,}", " ", flags=0)],
    )
    derivations = build_block_derivations(
        source,
        preview.document,
        cleaning_plan_id=preview.plan.id,
    )
    transformed = {
        record.block_index
        for record in preview.records
        if record.edits and not record.warned
    }
    chunks = chunk_paragraph(
        preview.document.children,
        max_size=1_000,
        source=source,
        transformed=transformed,
        block_derivations=derivations,
        region_id="body",
    )
    document_json = lossless_json_bytes(document_to_dict(preview.document))
    artifact_config_digest = canonical_digest({"cleaning_plan_id": preview.plan.id})
    artifact_id = derive_artifact_id(
        kind="cleaned-document-ir",
        content_sha256=sha256_digest(document_json),
        source_ids=(source.id,),
        producer_id="veriformis.test.cleaning",
        producer_version="1",
        config_digest=artifact_config_digest,
    )
    artifact = IRArtifactInput.create(
        source_id=source.id,
        artifact_id=artifact_id,
        artifact_kind="cleaned-document-ir",
        document_json=document_json,
        producer_id="veriformis.test.cleaning",
        producer_version="1",
        config_digest=artifact_config_digest,
    )
    return (
        SourceBundle(source, preview.document, tuple(chunks), artifact),
        tuple(preview.records),
    )


def inputs_for(
    bundles: Sequence[SourceBundle],
    *,
    transforms: Sequence[TransformRecord] = (),
    include_artifacts: bool = True,
    reviews=(),
    cleaning_config_digest: str | None = None,
) -> ConstructionInputs:
    return ConstructionInputs.create(
        cleaning_config_digest=(
            cleaning_config_digest
            if cleaning_config_digest is not None
            else canonical_digest({"cleaning": "fixture-v1"})
        ),
        sources=tuple(bundle.source for bundle in bundles),
        chunks=tuple(chunk for bundle in bundles for chunk in bundle.chunks),
        transforms=transforms,
        ir_artifacts=(
            tuple(bundle.artifact for bundle in bundles)
            if include_artifacts
            else ()
        ),
        reviews=reviews,
    )
