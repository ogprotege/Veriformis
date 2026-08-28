"""Pure deterministic constructors for SFT objectives plus refused labels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol, Sequence

from veriformis.chunkers.base import Chunk
from veriformis.errors import ConstructionError
from veriformis.evidence import (
    EvidenceComponent,
    SourceEvidence,
    join_derivation,
    make_evidence,
    replay_derivations,
    resolve_evidence,
    slice_derivation,
)
from veriformis.identity import canonical_digest
from veriformis.ir import Block, Document, Heading, block_text, iter_document_regions
from veriformis.rules.engine import TransformRecord
from veriformis.sources import SourceRef

from ._json import reject_floats
from .evidence import (
    IRArtifactKind,
    load_ir_document_json,
    make_ir_field_evidence,
)
from .models import (
    ConstructionDiagnostic,
    ConstructionPass,
    DatasetRecipe,
    DiagnosticCode,
    RecordField,
    SourceTextEvidence,
)


class IRArtifactLike(Protocol):
    source_id: str
    artifact_id: str
    artifact_kind: IRArtifactKind
    document_json: bytes


@dataclass(frozen=True)
class CandidateDraft:
    """Constructor output before the pipeline assigns a stable ordinal and ID."""

    source_ids: tuple[str, ...]
    chunk_ids: tuple[str, ...]
    transform_ids: tuple[str, ...]
    fields: tuple[RecordField, ...]
    order_key: tuple[str, ...]


@dataclass(frozen=True)
class ConstructorOutput:
    drafts: tuple[CandidateDraft, ...]
    diagnostics: tuple[ConstructionDiagnostic, ...]


Constructor = Callable[
    [
        DatasetRecipe,
        ConstructionPass,
        tuple[SourceRef, ...],
        tuple[Chunk, ...],
        tuple[TransformRecord, ...],
        tuple[IRArtifactLike, ...],
    ],
    ConstructorOutput,
]


def construction_field_context(
    recipe: DatasetRecipe,
    construction_pass: ConstructionPass,
    field_name: str,
    chunk_ids: Sequence[str],
    **extra: Any,
) -> dict[str, Any]:
    context = {
        "contract": "veriformis.construction-field/v1",
        "recipe_id": recipe.recipe_id,
        "pass_id": construction_pass.pass_id,
        "objective_kind": recipe.objective.kind,
        "field_name": field_name,
        "chunk_ids": tuple(sorted(chunk_ids)),
        **extra,
    }
    try:
        reject_floats(context)
    except (TypeError, ValueError) as exc:
        raise ConstructionError(f"invalid construction field context: {exc}") from exc
    return context


_context = construction_field_context


def _source_maps(
    sources: tuple[SourceRef, ...],
) -> tuple[dict[str, SourceRef], dict[str, str]]:
    by_id = {source.id: source for source in sources}
    locators = {source.id: source.logical_path for source in sources}
    return by_id, locators


def _ordered_chunks(
    recipe: DatasetRecipe,
    sources: tuple[SourceRef, ...],
    chunks: tuple[Chunk, ...],
) -> tuple[Chunk, ...]:
    selected = set(recipe.source_ids)
    locators = {source.id: source.logical_path for source in sources}
    return tuple(
        sorted(
            (chunk for chunk in chunks if chunk.source_id in selected),
            key=lambda chunk: (
                locators[chunk.source_id],
                chunk.source_id,
                chunk.sequence,
                chunk.id,
            ),
        )
    )


def _relevant_transforms(
    chunks: Sequence[Chunk],
    transforms: tuple[TransformRecord, ...],
) -> tuple[TransformRecord, ...]:
    block_keys = {
        (chunk.source_id, block_index)
        for chunk in chunks
        for block_index in chunk.block_indexes
    }
    source_ids = {chunk.source_id for chunk in chunks}
    return tuple(
        sorted(
            (
                record
                for record in transforms
                if record.source_id in source_ids
                and record.edits > 0
                and not record.warned
                and (
                    record.block_index == -1
                    or (record.source_id, record.block_index) in block_keys
                )
            ),
            key=lambda item: (
                item.source_id,
                item.block_index,
                item.rule_index,
                item.id,
            ),
        )
    )


def _source_field(
    *,
    name: str,
    value: str,
    evidence: SourceEvidence,
) -> RecordField:
    return RecordField(
        name=name,
        value=value,
        evidence=SourceTextEvidence(
            schema_version="veriformis.field-evidence/v1",
            kind="source_text",
            evidence=evidence,
        ),
    )


def _clone_evidence(
    evidence: SourceEvidence,
    *,
    value: str,
    context: dict[str, Any],
) -> SourceEvidence:
    return make_evidence(
        source_id=evidence.source_id,
        components=evidence.components,
        output_text=value,
        join=evidence.join_derivation,
        derivations=evidence.derivations,
        context=context,
    )


def _slice_evidence(
    chunk: Chunk,
    *,
    start: int,
    end: int,
    context: dict[str, Any],
) -> SourceEvidence:
    if chunk.evidence is None:
        raise ConstructionError("construction chunk lacks source evidence")
    step = slice_derivation(
        chunk.text,
        start,
        end,
        context={**context, "operation": "objective-slice"},
    )
    return make_evidence(
        source_id=chunk.source_id,
        components=chunk.evidence.components,
        output_text=chunk.text[start:end],
        join=chunk.evidence.join_derivation,
        derivations=chunk.evidence.derivations + (step,),
        context=context,
    )


def _draft(
    *,
    chunks: Sequence[Chunk],
    transforms: tuple[TransformRecord, ...],
    fields: Sequence[RecordField],
    locators: Mapping[str, str],
    suffix: str = "",
) -> CandidateDraft:
    source_ids = tuple(sorted({chunk.source_id for chunk in chunks}))
    chunk_ids = tuple(sorted(chunk.id for chunk in chunks))
    relevant = _relevant_transforms(chunks, transforms)
    transform_ids = tuple(sorted(record.id for record in relevant))
    semantic_digest = canonical_digest(
        {
            "source_ids": source_ids,
            "chunk_ids": chunk_ids,
            "transform_ids": transform_ids,
            "fields": tuple(fields),
        }
    )
    first = min(
        chunks,
        key=lambda chunk: (
            locators[chunk.source_id],
            chunk.source_id,
            chunk.sequence,
            chunk.id,
        ),
    )
    return CandidateDraft(
        source_ids=source_ids,
        chunk_ids=chunk_ids,
        transform_ids=transform_ids,
        fields=tuple(fields),
        order_key=(
            locators[first.source_id],
            first.source_id,
            f"{first.sequence:020d}",
            first.id,
            suffix,
            semantic_digest,
        ),
    )


def _diagnostic(
    *,
    code: DiagnosticCode,
    message: str,
    construction_pass: ConstructionPass,
    chunks: Sequence[Chunk] = (),
    source_ids: Sequence[str] = (),
) -> ConstructionDiagnostic:
    return ConstructionDiagnostic.create(
        code=code,
        message=message,
        pass_id=construction_pass.pass_id,
        source_ids=tuple(sorted({*source_ids, *(chunk.source_id for chunk in chunks)})),
        chunk_ids=tuple(sorted(chunk.id for chunk in chunks)),
    )


def _parameters(
    construction_pass: ConstructionPass,
    *,
    allowed: set[str],
) -> dict[str, str | bool | int | None]:
    values = construction_pass.parameter_map()
    unsupported = sorted(set(values) - allowed)
    if unsupported:
        raise ConstructionError(
            f"unsupported {construction_pass.objective_kind} constructor "
            f"parameters: {unsupported!r}"
        )
    return values


def _selected_ir_artifacts(
    recipe: DatasetRecipe,
    ir_artifacts: tuple[IRArtifactLike, ...],
) -> dict[str, IRArtifactLike]:
    """Choose one deterministic strict-IR artifact for each selected source."""
    selected: dict[str, IRArtifactLike] = {}
    for artifact in sorted(
        ir_artifacts,
        key=lambda item: (
            item.source_id,
            0 if item.artifact_kind == "cleaned-document-ir" else 1,
            item.artifact_id,
        ),
    ):
        if artifact.source_id in recipe.source_ids:
            selected.setdefault(artifact.source_id, artifact)
    return selected


def construct_full_text(
    recipe: DatasetRecipe,
    construction_pass: ConstructionPass,
    sources: tuple[SourceRef, ...],
    chunks: tuple[Chunk, ...],
    transforms: tuple[TransformRecord, ...],
    ir_artifacts: tuple[IRArtifactLike, ...],
) -> ConstructorOutput:
    del ir_artifacts
    _parameters(construction_pass, allowed=set())
    source_map, locators = _source_maps(sources)
    drafts: list[CandidateDraft] = []
    for chunk in _ordered_chunks(recipe, sources, chunks):
        if chunk.evidence is None:
            raise ConstructionError("construction chunk lacks source evidence")
        resolve_evidence(chunk.evidence, source_map)
        context = _context(recipe, construction_pass, "text", (chunk.id,))
        evidence = _clone_evidence(
            chunk.evidence,
            value=chunk.text,
            context=context,
        )
        drafts.append(
            _draft(
                chunks=(chunk,),
                transforms=transforms,
                fields=(_source_field(name="text", value=chunk.text, evidence=evidence),),
                locators=locators,
            )
        )
    return ConstructorOutput(tuple(drafts), ())


def construct_continuation(
    recipe: DatasetRecipe,
    construction_pass: ConstructionPass,
    sources: tuple[SourceRef, ...],
    chunks: tuple[Chunk, ...],
    transforms: tuple[TransformRecord, ...],
    ir_artifacts: tuple[IRArtifactLike, ...],
) -> ConstructorOutput:
    del ir_artifacts
    params = _parameters(construction_pass, allowed={"split_ratio_ppm"})
    ratio = params.get("split_ratio_ppm", 500_000)
    if type(ratio) is not int or not 1 <= ratio <= 999_999:
        raise ConstructionError("split_ratio_ppm must be an integer from 1 to 999999")
    source_map, locators = _source_maps(sources)
    drafts: list[CandidateDraft] = []
    diagnostics: list[ConstructionDiagnostic] = []
    for chunk in _ordered_chunks(recipe, sources, chunks):
        if chunk.evidence is None:
            raise ConstructionError("construction chunk lacks source evidence")
        resolve_evidence(chunk.evidence, source_map)
        if len(chunk.text) < 2:
            diagnostics.append(
                _diagnostic(
                    code="continuation-boundary-unavailable",
                    message="chunk cannot produce non-empty prompt and completion fields",
                    construction_pass=construction_pass,
                    chunks=(chunk,),
                )
            )
            continue
        boundary = max(1, min(len(chunk.text) - 1, len(chunk.text) * ratio // 1_000_000))
        prompt = chunk.text[:boundary]
        completion = chunk.text[boundary:]
        prompt_context = _context(
            recipe,
            construction_pass,
            "prompt",
            (chunk.id,),
            boundary=boundary,
        )
        completion_context = _context(
            recipe,
            construction_pass,
            "completion",
            (chunk.id,),
            boundary=boundary,
        )
        fields = (
            _source_field(
                name="prompt",
                value=prompt,
                evidence=_slice_evidence(
                    chunk,
                    start=0,
                    end=boundary,
                    context=prompt_context,
                ),
            ),
            _source_field(
                name="completion",
                value=completion,
                evidence=_slice_evidence(
                    chunk,
                    start=boundary,
                    end=len(chunk.text),
                    context=completion_context,
                ),
            ),
        )
        drafts.append(
            _draft(
                chunks=(chunk,),
                transforms=transforms,
                fields=fields,
                locators=locators,
            )
        )
    return ConstructorOutput(tuple(drafts), tuple(diagnostics))


@dataclass(frozen=True)
class _SectionUnit:
    region_id: str
    blocks: tuple[Block, ...]

    @property
    def heading(self) -> Heading:
        first = self.blocks[0]
        if not isinstance(first, Heading):  # pragma: no cover - internal invariant.
            raise ConstructionError("section unit does not begin with a heading")
        return first


def _document_section_units(
    document: Document,
) -> tuple[
    tuple[tuple[str, tuple[Block, ...]], ...],
    tuple[_SectionUnit, ...],
]:
    """Return unheaded preambles and exact heading-delimited IR sections."""
    preambles: list[tuple[str, tuple[Block, ...]]] = []
    sections: list[_SectionUnit] = []
    for region_id, blocks in iter_document_regions(document):
        preamble: list[Block] = []
        section: list[Block] = []
        for block in blocks:
            if isinstance(block, Heading):
                if section:
                    sections.append(_SectionUnit(region_id, tuple(section)))
                section = [block]
            elif section:
                section.append(block)
            else:
                preamble.append(block)
        if preamble:
            preambles.append((region_id, tuple(preamble)))
        if section:
            sections.append(_SectionUnit(region_id, tuple(section)))
    return tuple(preambles), tuple(sections)


def _section_chunks(
    source_chunks: Sequence[Chunk],
    blocks: Sequence[Block],
) -> tuple[Chunk, ...]:
    block_indexes = {block.block_index for block in blocks}
    return tuple(
        chunk
        for chunk in source_chunks
        if block_indexes.intersection(chunk.block_indexes)
    )


def _prove_section_components(
    *,
    source: SourceRef,
    region_id: str,
    blocks: tuple[Block, ...],
    chunks: tuple[Chunk, ...],
) -> tuple[EvidenceComponent, ...] | None:
    """Recover each exact IR block component from complete structure chunks."""
    expected_indexes = tuple(block.block_index for block in blocks)
    expected_set = set(expected_indexes)
    blocks_by_index = {block.block_index: block for block in blocks}
    components_by_index: dict[int, EvidenceComponent] = {}

    if not chunks:
        return None
    for chunk in chunks:
        evidence = chunk.evidence
        if evidence is None or evidence.derivations:
            return None
        if not set(chunk.block_indexes) <= expected_set:
            return None
        if len(chunk.block_indexes) != len(evidence.components):
            return None
        chunk_values: list[str] = []
        for block_index, component in zip(
            chunk.block_indexes,
            evidence.components,
            strict=True,
        ):
            if block_index in components_by_index:
                return None
            block = blocks_by_index.get(block_index)
            if block is None or block.span is None:
                return None
            item = component.source_range
            if (
                item.source_id != source.id
                or item.artifact_id != source.artifact_id
                or item.region_id != region_id
                or (item.start, item.end) != (block.span.start, block.span.end)
            ):
                return None
            value = replay_derivations(
                source.extracted_text[item.start:item.end],
                component.derivations,
            )
            if value != block_text(block):
                return None
            components_by_index[block_index] = component
            chunk_values.append(value)
        if chunk.text != "\n\n".join(chunk_values):
            return None

    if set(components_by_index) != expected_set:
        return None
    return tuple(components_by_index[index] for index in expected_indexes)


def _section_evidence(
    *,
    source_id: str,
    components: tuple[EvidenceComponent, ...],
    values: tuple[str, ...],
    value: str,
    context: dict[str, Any],
) -> SourceEvidence:
    join = None
    if len(components) > 1:
        join = join_derivation(
            list(values),
            "\n\n",
            context={**context, "operation": "section-block-join"},
        )
    return make_evidence(
        source_id=source_id,
        components=components,
        output_text=value,
        join=join,
        context=context,
    )


def construct_section_reconstruction(
    recipe: DatasetRecipe,
    construction_pass: ConstructionPass,
    sources: tuple[SourceRef, ...],
    chunks: tuple[Chunk, ...],
    transforms: tuple[TransformRecord, ...],
    ir_artifacts: tuple[IRArtifactLike, ...],
) -> ConstructorOutput:
    _parameters(construction_pass, allowed=set())
    source_map, locators = _source_maps(sources)
    ordered = _ordered_chunks(recipe, sources, chunks)
    chunks_by_source: dict[str, tuple[Chunk, ...]] = {
        source_id: tuple(chunk for chunk in ordered if chunk.source_id == source_id)
        for source_id in recipe.source_ids
    }
    artifacts = _selected_ir_artifacts(recipe, ir_artifacts)
    drafts: list[CandidateDraft] = []
    diagnostics: list[ConstructionDiagnostic] = []

    for source_id in recipe.source_ids:
        source = source_map[source_id]
        source_chunks = chunks_by_source[source_id]
        artifact = artifacts.get(source_id)
        if artifact is None or artifact.artifact_kind != "cleaned-document-ir":
            diagnostics.append(
                _diagnostic(
                    code="section-structure-unavailable",
                    message=(
                        "selected source has no cleaned strict IR section artifact"
                    ),
                    construction_pass=construction_pass,
                    chunks=source_chunks,
                    source_ids=(source_id,),
                )
            )
            continue
        _, document = load_ir_document_json(artifact.document_json)
        if document.source_id != source_id:
            raise ConstructionError("section IR artifact names another source")

        preambles, section_units = _document_section_units(document)
        accounted_chunk_ids: set[str] = set()
        for region_id, preamble in preambles:
            preamble_chunks = _section_chunks(source_chunks, preamble)
            accounted_chunk_ids.update(chunk.id for chunk in preamble_chunks)
            if preamble_chunks:
                diagnostics.append(
                    _diagnostic(
                        code="section-structure-unavailable",
                        message=(
                            "unheaded source unit cannot prove a section in "
                            f"{region_id} before block {preamble[-1].block_index + 1}"
                        ),
                        construction_pass=construction_pass,
                        chunks=preamble_chunks,
                    )
                )

        for unit in section_units:
            unit_chunks = _section_chunks(source_chunks, unit.blocks)
            accounted_chunk_ids.update(chunk.id for chunk in unit_chunks)
            heading = unit.heading
            heading_value = block_text(heading)
            body_blocks = unit.blocks[1:]
            body_values = tuple(block_text(block) for block in body_blocks)
            section_value = "\n\n".join(body_values)
            components = _prove_section_components(
                source=source,
                region_id=unit.region_id,
                blocks=unit.blocks,
                chunks=unit_chunks,
            )
            if not heading_value or not body_blocks or not section_value or components is None:
                diagnostics.append(
                    _diagnostic(
                        code="section-structure-unavailable",
                        message=(
                            "cannot prove a complete non-empty section at "
                            f"{unit.region_id} block {heading.block_index}"
                        ),
                        construction_pass=construction_pass,
                        chunks=unit_chunks,
                        source_ids=(source_id,),
                    )
                )
                continue

            chunk_ids = tuple(chunk.id for chunk in unit_chunks)
            block_indexes = tuple(block.block_index for block in unit.blocks)
            heading_context = _context(
                recipe,
                construction_pass,
                "heading",
                chunk_ids,
                region_id=unit.region_id,
                heading_block_index=heading.block_index,
                section_block_indexes=block_indexes,
            )
            section_context = _context(
                recipe,
                construction_pass,
                "section",
                chunk_ids,
                region_id=unit.region_id,
                heading_block_index=heading.block_index,
                section_block_indexes=block_indexes,
            )
            fields = (
                _source_field(
                    name="heading",
                    value=heading_value,
                    evidence=_section_evidence(
                        source_id=source_id,
                        components=(components[0],),
                        values=(heading_value,),
                        value=heading_value,
                        context=heading_context,
                    ),
                ),
                _source_field(
                    name="section",
                    value=section_value,
                    evidence=_section_evidence(
                        source_id=source_id,
                        components=components[1:],
                        values=body_values,
                        value=section_value,
                        context=section_context,
                    ),
                ),
            )
            drafts.append(
                _draft(
                    chunks=unit_chunks,
                    transforms=transforms,
                    fields=fields,
                    locators=locators,
                    suffix=f"{unit.region_id}:{heading.block_index:020d}",
                )
            )

        for chunk in source_chunks:
            if chunk.id not in accounted_chunk_ids:
                diagnostics.append(
                    _diagnostic(
                        code="section-structure-unavailable",
                        message="structure chunk does not map to a strict IR section unit",
                        construction_pass=construction_pass,
                        chunks=(chunk,),
                    )
                )
    return ConstructorOutput(tuple(drafts), tuple(diagnostics))


def _before_after_transform_ids(
    chunk: Chunk,
    transforms: tuple[TransformRecord, ...],
) -> tuple[str, ...] | None:
    if chunk.evidence is None or len(chunk.evidence.components) != 1:
        return None
    if chunk.evidence.join_derivation is not None or chunk.evidence.derivations:
        return None
    steps = chunk.evidence.components[0].derivations
    if len(steps) != 1 or steps[0].kind != "edits":
        return None
    step = steps[0]
    records = sorted(
        (
            record
            for record in transforms
            if record.source_id == chunk.source_id
            and record.block_index in chunk.block_indexes
            and record.edits > 0
            and not record.warned
        ),
        key=lambda item: (item.rule_index, item.id),
    )
    if not records:
        return None
    if records[0].input_sha256 != step.input_sha256:
        return None
    if records[-1].output_sha256 != step.output_sha256:
        return None
    if any(
        left.output_sha256 != right.input_sha256
        for left, right in zip(records, records[1:])
    ):
        return None
    return tuple(sorted(record.id for record in records))


def construct_before_after_transformation(
    recipe: DatasetRecipe,
    construction_pass: ConstructionPass,
    sources: tuple[SourceRef, ...],
    chunks: tuple[Chunk, ...],
    transforms: tuple[TransformRecord, ...],
    ir_artifacts: tuple[IRArtifactLike, ...],
) -> ConstructorOutput:
    del ir_artifacts
    _parameters(construction_pass, allowed=set())
    source_map, locators = _source_maps(sources)
    drafts: list[CandidateDraft] = []
    diagnostics: list[ConstructionDiagnostic] = []
    for chunk in _ordered_chunks(recipe, sources, chunks):
        transform_ids = _before_after_transform_ids(chunk, transforms)
        if not chunk.transformed or transform_ids is None:
            diagnostics.append(
                _diagnostic(
                    code="transformation-pair-unavailable",
                    message=(
                        "chunk lacks one replayable cleaned transformation with "
                        "matching transform records"
                    ),
                    construction_pass=construction_pass,
                    chunks=(chunk,),
                )
            )
            continue
        assert chunk.evidence is not None
        resolve_evidence(chunk.evidence, source_map)
        component = chunk.evidence.components[0]
        source = source_map[chunk.source_id]
        item = component.source_range
        before = source.extracted_text[item.start:item.end]
        after = chunk.text
        if not before or not after or before == after:
            diagnostics.append(
                _diagnostic(
                    code="transformation-pair-empty-or-unchanged",
                    message="before/after objective requires two non-empty changed values",
                    construction_pass=construction_pass,
                    chunks=(chunk,),
                )
            )
            continue
        before_evidence = make_evidence(
            source_id=chunk.source_id,
            components=(EvidenceComponent(source_range=item, derivations=()),),
            output_text=before,
            context=_context(
                recipe,
                construction_pass,
                "before",
                (chunk.id,),
                transform_ids=transform_ids,
            ),
        )
        after_evidence = _clone_evidence(
            chunk.evidence,
            value=after,
            context=_context(
                recipe,
                construction_pass,
                "after",
                (chunk.id,),
                transform_ids=transform_ids,
            ),
        )
        fields = (
            _source_field(name="before", value=before, evidence=before_evidence),
            _source_field(name="after", value=after, evidence=after_evidence),
        )
        draft = _draft(
            chunks=(chunk,),
            transforms=transforms,
            fields=fields,
            locators=locators,
        )
        if draft.transform_ids != transform_ids:
            raise ConstructionError("candidate transform binding is not exact")
        drafts.append(draft)
    return ConstructorOutput(tuple(drafts), tuple(diagnostics))


@dataclass(frozen=True)
class _StructuredLeaf:
    node_type: str
    field_name: str
    json_pointer: str
    block_index: int
    value: str | int | bool | None


_STRUCTURED_FIELDS: dict[str, tuple[str, ...]] = {
    "Heading": ("level",),
    "CodeBlock": ("language",),
    "Link": ("href", "title"),
    "Image": ("src", "title"),
    "Math": ("display",),
    "Citation": ("key", "locator"),
    "ListBlock": ("ordered",),
    "ListItem": ("checked",),
    "Table": ("alignments",),
}


def _pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _structured_leaves(value: dict[str, Any]) -> tuple[_StructuredLeaf, ...]:
    leaves: list[_StructuredLeaf] = []

    def walk(node: Any, tokens: tuple[str, ...], block_index: int | None) -> None:
        if isinstance(node, dict):
            node_type = node.get("type")
            local_block = block_index
            node_block = node.get("block_index")
            if type(node_block) is int and node_block >= 0:
                local_block = node_block
            if isinstance(node_type, str) and local_block is not None:
                for field_name in _STRUCTURED_FIELDS.get(node_type, ()):
                    raw = node.get(field_name)
                    field_tokens = tokens + (field_name,)
                    if isinstance(raw, list):
                        for index, item in enumerate(raw):
                            if item is None or type(item) in (str, int, bool):
                                leaves.append(
                                    _StructuredLeaf(
                                        node_type=node_type,
                                        field_name=f"{field_name}[{index}]",
                                        json_pointer="/" + "/".join(
                                            _pointer_token(part)
                                            for part in field_tokens + (str(index),)
                                        ),
                                        block_index=local_block,
                                        value=item,
                                    )
                                )
                    elif raw is not None and type(raw) in (str, int, bool):
                        leaves.append(
                            _StructuredLeaf(
                                node_type=node_type,
                                field_name=field_name,
                                json_pointer="/" + "/".join(
                                    _pointer_token(part) for part in field_tokens
                                ),
                                block_index=local_block,
                                value=raw,
                            )
                        )
            for key, item in node.items():
                walk(item, tokens + (key,), local_block)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, tokens + (str(index),), block_index)

    walk(value, (), None)
    return tuple(
        sorted(
            leaves,
            key=lambda item: (
                item.block_index,
                item.json_pointer,
                item.node_type,
                item.field_name,
            ),
        )
    )


def construct_structured_field(
    recipe: DatasetRecipe,
    construction_pass: ConstructionPass,
    sources: tuple[SourceRef, ...],
    chunks: tuple[Chunk, ...],
    transforms: tuple[TransformRecord, ...],
    ir_artifacts: tuple[IRArtifactLike, ...],
) -> ConstructorOutput:
    _parameters(construction_pass, allowed=set())
    source_map, locators = _source_maps(sources)
    ordered = _ordered_chunks(recipe, sources, chunks)
    chunks_by_source: dict[str, list[Chunk]] = {}
    for chunk in ordered:
        chunks_by_source.setdefault(chunk.source_id, []).append(chunk)

    selected_artifacts = _selected_ir_artifacts(recipe, ir_artifacts)

    drafts: list[CandidateDraft] = []
    diagnostics: list[ConstructionDiagnostic] = []
    for source_id in recipe.source_ids:
        artifact = selected_artifacts.get(source_id)
        if artifact is None:
            diagnostics.append(
                _diagnostic(
                    code="structured-ir-artifact-unavailable",
                    message="selected source has no declared strict IR artifact",
                    construction_pass=construction_pass,
                    source_ids=(source_id,),
                )
            )
            continue
        document_value, document = load_ir_document_json(artifact.document_json)
        if document.source_id != source_id:
            raise ConstructionError("structured IR artifact names another source")
        leaves = _structured_leaves(document_value)
        if not leaves:
            diagnostics.append(
                _diagnostic(
                    code="structured-field-unavailable",
                    message="strict IR artifact contains no supported metadata scalar",
                    construction_pass=construction_pass,
                    source_ids=(source_id,),
                )
            )
            continue
        for leaf in leaves:
            covering = next(
                (
                    chunk
                    for chunk in chunks_by_source.get(source_id, ())
                    if leaf.block_index in chunk.block_indexes
                ),
                None,
            )
            if covering is None:
                diagnostics.append(
                    _diagnostic(
                        code="structured-field-chunk-unavailable",
                        message=(
                            f"IR metadata at {leaf.json_pointer} has no covering chunk"
                        ),
                        construction_pass=construction_pass,
                        source_ids=(source_id,),
                    )
                )
                continue
            if covering.evidence is None:
                raise ConstructionError("structured-field input chunk lacks evidence")
            resolve_evidence(covering.evidence, source_map)
            input_context = _context(
                recipe,
                construction_pass,
                "input",
                (covering.id,),
                json_pointer=leaf.json_pointer,
            )
            fields_context = _context(
                recipe,
                construction_pass,
                "fields",
                (covering.id,),
                json_pointer=leaf.json_pointer,
            )
            output_value, output_evidence = make_ir_field_evidence(
                source_id=source_id,
                artifact_id=artifact.artifact_id,
                artifact_kind=artifact.artifact_kind,
                document_json=artifact.document_json,
                json_pointer=leaf.json_pointer,
                context=fields_context,
            )
            if not covering.text or not output_value:
                diagnostics.append(
                    _diagnostic(
                        code="structured-field-empty-value",
                        message=(
                            "structured-field objective requires a non-empty value at "
                            f"{leaf.json_pointer}"
                        ),
                        construction_pass=construction_pass,
                        chunks=(covering,),
                    )
                )
                continue
            input_evidence = _clone_evidence(
                covering.evidence,
                value=covering.text,
                context=input_context,
            )
            fields = (
                _source_field(
                    name="input",
                    value=covering.text,
                    evidence=input_evidence,
                ),
                RecordField(
                    name="fields",
                    value=output_value,
                    evidence=output_evidence,
                ),
            )
            drafts.append(
                _draft(
                    chunks=(covering,),
                    transforms=transforms,
                    fields=fields,
                    locators=locators,
                    suffix=leaf.json_pointer,
                )
            )
    return ConstructorOutput(tuple(drafts), tuple(diagnostics))


def construct_explicit_label(
    recipe: DatasetRecipe,
    construction_pass: ConstructionPass,
    sources: Mapping[str, SourceRef],
    chunks: Sequence[Chunk],
    transforms: Sequence[TransformRecord],
    ir_artifacts: Mapping[str, IRArtifactLike],
) -> ConstructorOutput:
    """Refuse document-source invented labels."""
    del recipe, construction_pass, sources, chunks, transforms, ir_artifacts
    from veriformis.families.classification import refuse_document_source_labels

    refuse_document_source_labels()
    raise AssertionError("explicit_label constructor must refuse")


_CONSTRUCTORS: dict[tuple[str, str], Constructor] = {
    ("veriformis.constructor.full-text", "1"): construct_full_text,
    ("veriformis.constructor.continuation", "1"): construct_continuation,
    (
        "veriformis.constructor.section-reconstruction",
        "1",
    ): construct_section_reconstruction,
    (
        "veriformis.constructor.before-after-transformation",
        "1",
    ): construct_before_after_transformation,
    ("veriformis.constructor.structured-field", "1"): construct_structured_field,
    ("veriformis.constructor.explicit-label", "1"): construct_explicit_label,
}


def get_constructor(constructor_id: str, constructor_version: str) -> Constructor:
    """Dispatch only exact supported constructor versions."""
    try:
        return _CONSTRUCTORS[(constructor_id, constructor_version)]
    except KeyError as exc:
        raise ConstructionError(
            f"unsupported constructor {constructor_id!r} version "
            f"{constructor_version!r}"
        ) from exc


__all__ = [
    "CandidateDraft",
    "ConstructorOutput",
    "IRArtifactLike",
    "construct_before_after_transformation",
    "construct_continuation",
    "construct_explicit_label",
    "construct_full_text",
    "construct_section_reconstruction",
    "construct_structured_field",
    "construction_field_context",
    "get_constructor",
]
