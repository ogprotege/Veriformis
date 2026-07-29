from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path

import pytest

from veriformis.chunkers.strategies import (
    chunk_fixed, chunk_paragraph, chunk_sentence, chunk_sliding, chunk_structure,
)
from veriformis.chunkers.base import (
    chunk_from_dict,
    chunk_to_dict,
    refresh_chunk_id,
)
from veriformis.evidence import (
    EvidenceEdit, EvidenceError, derivation_from_dict, derivation_to_dict,
    edits_derivation, make_evidence, resolve_evidence, source_evidence_from_dict,
    source_evidence_to_dict,
)
from veriformis.ir import Document, Paragraph, Text
from veriformis.parsers.markdown import parse_md_file as _parse_md_file
from veriformis.parsers.text import parse_text as _parse_text
from veriformis.validate.gates import gate_provenance


def parse_text(path: Path):
    return _parse_text(path, logical_path=path.name)


def parse_md_file(path: Path):
    return _parse_md_file(path, logical_path=path.name)


def test_sentence_chunk_requires_reconstructible_source_ranges(tmp_path):
    path = tmp_path / "sentences.txt"
    path.write_text("Alpha one. Alpha two.\n\nBeta one.", encoding="utf-8")
    result = parse_text(path)
    chunks = chunk_sentence(result.document.children, source=result.source, max_size=1000)

    assert chunks and chunks[0].span is None
    assert chunks[0].evidence is not None
    assert len(chunks[0].evidence.components) == 3
    assert gate_provenance(chunks, {result.source.id: result.source}).passed
    restored = source_evidence_from_dict(asdict(chunks[0].evidence))
    assert restored == chunks[0].evidence
    persisted = json.loads(json.dumps(chunk_to_dict(chunks[0])))
    restored_chunk = chunk_from_dict(persisted)
    assert restored_chunk == chunks[0]
    assert gate_provenance([restored_chunk], {result.source.id: result.source}).passed


def test_chunk_identity_binds_exact_heading_unicode_normalization(tmp_path):
    path = tmp_path / "heading.txt"
    path.write_text("same text", encoding="utf-8")
    result = parse_text(path)
    base = chunk_paragraph(result.document.children, source=result.source)[0]

    composed = refresh_chunk_id(replace(base, heading_path=["café"]))
    decomposed = refresh_chunk_id(replace(base, heading_path=["cafe\u0301"]))

    assert composed.id != decomposed.id


def test_transformed_chunk_requires_replayable_source_evidence(tmp_path):
    path = tmp_path / "transformed.txt"
    path.write_text("Alpha source.", encoding="utf-8")
    result = parse_text(path)
    original = result.document.children[0]
    cleaned = Paragraph(
        children=[Text("ALPHA source.")],
        span=original.span,
        block_index=original.block_index,
    )
    step = edits_derivation(
        "Alpha source.",
        [EvidenceEdit(0, 5, "Alpha", "ALPHA")],
        context={"rule": "uppercase-test", "source_id": result.source.id},
    )
    chunks = chunk_paragraph(
        [cleaned],
        source=result.source,
        transformed=(0,),
        block_derivations={0: (step,)},
    )

    assert chunks[0].transformed
    assert chunks[0].span is None
    assert chunks[0].evidence is not None
    assert gate_provenance(chunks, {result.source.id: result.source}).passed


def test_mutated_spanless_chunk_fails_provenance(tmp_path):
    path = tmp_path / "spanless.txt"
    path.write_text("First sentence. Second sentence.", encoding="utf-8")
    result = parse_text(path)
    chunk = chunk_sentence(result.document.children, source=result.source)[0]
    mutated = replace(chunk, text=chunk.text + " unrelated")

    assert not gate_provenance([mutated], {result.source.id: result.source}).passed


def test_mutated_transformed_chunk_fails_provenance(tmp_path):
    path = tmp_path / "edited.txt"
    path.write_text("alpha", encoding="utf-8")
    result = parse_text(path)
    block = result.document.children[0]
    cleaned = Document(
        children=[Paragraph(children=[Text("ALPHA")], span=block.span, block_index=0)],
        source_id=result.source.id,
    )
    step = edits_derivation(
        "alpha",
        [EvidenceEdit(0, 5, "alpha", "ALPHA")],
        context={"rule": "uppercase-test"},
    )
    chunk = chunk_paragraph(
        cleaned.children,
        source=result.source,
        transformed=(0,),
        block_derivations={0: (step,)},
    )[0]
    mutated = replace(chunk, text="fabricated")

    assert not gate_provenance([mutated], {result.source.id: result.source}).passed


def test_missing_evidence_never_uses_span_or_transformed_bypass(tmp_path):
    path = tmp_path / "registered.txt"
    path.write_text("registered source", encoding="utf-8")
    result = parse_text(path)
    valid = chunk_paragraph(result.document.children, source=result.source)[0]
    chunks = [
        replace(valid, id="legacy-spanless", span=None, evidence=None),
        replace(
            valid,
            id="legacy-transformed",
            transformed=True,
            evidence=None,
        ),
    ]

    gate = gate_provenance(chunks, {result.source.id: result.source})

    assert not gate.passed
    assert len(gate.messages) == 2
    assert all("missing reconstructible source evidence" in item for item in gate.messages)


def test_supplied_source_with_unreconstructible_block_fails_closed(tmp_path):
    path = tmp_path / "closed.txt"
    path.write_text("original", encoding="utf-8")
    result = parse_text(path)
    block = result.document.children[0]
    changed = Paragraph(children=[Text("changed")], span=block.span, block_index=0)

    with pytest.raises(EvidenceError, match="derivations do not reconstruct"):
        chunk_paragraph([changed], source=result.source, transformed=(0,))


def test_derivation_persistence_is_strict_and_roundtrips():
    step = edits_derivation(
        "café",
        [EvidenceEdit(3, 4, "é", "e")],
        context={"rule": "accent-normalization", "version": "1"},
    )
    persisted = json.loads(json.dumps(derivation_to_dict(step)))
    assert derivation_from_dict(persisted) == step

    persisted["unexpected"] = True
    with pytest.raises(EvidenceError, match="keys do not match"):
        derivation_from_dict(persisted)


def test_chunk_persistence_rejects_unknown_fields(tmp_path):
    path = tmp_path / "strict.txt"
    path.write_text("strict evidence", encoding="utf-8")
    result = parse_text(path)
    chunk = chunk_paragraph(result.document.children, source=result.source)[0]
    persisted = chunk_to_dict(chunk)
    persisted["unexpected"] = True

    with pytest.raises(EvidenceError, match="chunk keys do not match"):
        chunk_from_dict(persisted)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("sequence", 99),
        ("block_index", 99),
        ("block_indexes", [0, 99]),
        ("span", None),
        ("heading_path", ["forged"]),
        ("text", "forged text"),
        ("tokens_est", 99),
        ("transformed", True),
        ("artifact_id", "art-v1-" + "a" * 64),
    ],
)
def test_chunk_persistence_binds_every_semantic_field(tmp_path, field, replacement):
    path = tmp_path / "bound.txt"
    path.write_text("bound text", encoding="utf-8")
    result = parse_text(path)
    chunk = chunk_paragraph(result.document.children, source=result.source)[0]
    persisted = deepcopy(chunk_to_dict(chunk))
    persisted[field] = replacement

    with pytest.raises(EvidenceError):
        chunk_from_dict(persisted)


def test_chunk_identity_context_and_id_are_recomputed_on_load(tmp_path):
    path = tmp_path / "context.txt"
    path.write_text("context text", encoding="utf-8")
    result = parse_text(path)
    chunk = chunk_paragraph(result.document.children, source=result.source)[0]
    persisted = deepcopy(chunk_to_dict(chunk))
    persisted["identity_context"]["max_size"] = 7

    with pytest.raises(EvidenceError, match="evidence context"):
        chunk_from_dict(persisted)

    persisted = deepcopy(chunk_to_dict(chunk))
    persisted["id"] = "chk-v1-" + "0" * 64
    with pytest.raises(EvidenceError, match="chunk identity mismatch"):
        chunk_from_dict(persisted)


def test_frozen_chunk_detects_nested_identity_drift_before_serialization(tmp_path):
    path = tmp_path / "frozen.txt"
    path.write_text("frozen text", encoding="utf-8")
    result = parse_text(path)
    chunk = chunk_paragraph(result.document.children, source=result.source)[0]
    chunk.heading_path.append("drift")

    with pytest.raises(EvidenceError, match="chunk identity mismatch"):
        chunk_to_dict(chunk)


def test_structure_chunks_use_the_same_roundtrippable_identity_schema():
    fixture = Path(__file__).parent.parent / "fixtures" / "sample.md"
    result = parse_md_file(fixture)
    chunks = chunk_structure(result.document.children, source=result.source, max_size=200)

    assert chunks
    for chunk in chunks:
        persisted = json.loads(json.dumps(chunk_to_dict(chunk)))
        assert chunk_from_dict(persisted) == chunk
        assert chunk.identity_context["strategy"] == "structure"


def test_span_is_exact_after_a_removed_leading_block(tmp_path):
    path = tmp_path / "leading.txt"
    path.write_text("remove\n\nkeep", encoding="utf-8")
    result = parse_text(path)
    keep = result.document.children[1]

    for strategy in (chunk_fixed, chunk_sliding):
        chunk = strategy([keep], source=result.source, size=100, overlap=10)[0]
        assert chunk.span == keep.span
        assert chunk.span.start > 0


def test_multi_range_paragraph_never_claims_the_removed_middle(tmp_path):
    path = tmp_path / "middle.txt"
    path.write_text("first\n\nremove\n\nthird", encoding="utf-8")
    result = parse_text(path)
    first, _, third = result.document.children
    chunk = chunk_paragraph([first, third], source=result.source)[0]

    assert len(chunk.evidence.components) == 2
    assert chunk.span is None
    assert gate_provenance([chunk], {result.source.id: result.source}).passed


def test_derived_fixed_stream_never_claims_a_canonical_span(tmp_path):
    path = tmp_path / "derived-fixed.txt"
    path.write_text("alpha", encoding="utf-8")
    result = parse_text(path)
    original = result.document.children[0]
    cleaned = Paragraph(
        children=[Text("ALPHA")],
        span=original.span,
        block_index=original.block_index,
    )
    step = edits_derivation(
        "alpha",
        [EvidenceEdit(0, 5, "alpha", "ALPHA")],
        context={"rule": "uppercase-test"},
    )

    for strategy in (chunk_fixed, chunk_sliding):
        chunk = strategy(
            [cleaned],
            source=result.source,
            transformed=(original.block_index,),
            block_derivations={original.block_index: (step,)},
            size=100,
            overlap=10,
        )[0]
        assert chunk.span is None


def _persisted_evidence(tmp_path):
    path = tmp_path / "evidence.txt"
    path.write_text("first\n\nsecond", encoding="utf-8")
    result = parse_text(path)
    chunk = chunk_paragraph(result.document.children, source=result.source)[0]
    return deepcopy(source_evidence_to_dict(chunk.evidence))


def test_evidence_rejects_unsupported_schema_and_zero_components(tmp_path):
    persisted = _persisted_evidence(tmp_path)
    persisted["schema_version"] = "veriformis.source-evidence/v2"
    with pytest.raises(EvidenceError, match="unsupported source evidence schema"):
        source_evidence_from_dict(persisted)

    persisted = _persisted_evidence(tmp_path)
    persisted["components"] = []
    with pytest.raises(EvidenceError, match="at least one component"):
        source_evidence_from_dict(persisted)


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("region_id", "header", "region_id"),
        ("region_id", "footnote:", "region_id"),
        ("range_kind", "bytes", "range kind"),
        ("start", -1, "offsets"),
        ("start", True, "offsets"),
        ("text_sha256", "not-a-digest", "text_sha256"),
        ("artifact_id", "art-invalid", "artifact_id"),
    ],
)
def test_evidence_rejects_malformed_source_ranges(
    tmp_path,
    field,
    replacement,
    message,
):
    persisted = _persisted_evidence(tmp_path)
    persisted["components"][0]["source_range"][field] = replacement

    with pytest.raises(EvidenceError, match=message):
        source_evidence_from_dict(persisted)


def test_evidence_rejects_range_kind_offset_contradictions(tmp_path):
    persisted = _persisted_evidence(tmp_path)
    item = persisted["components"][0]["source_range"]
    item["end"] = item["start"]
    with pytest.raises(EvidenceError, match="text source ranges must not be empty"):
        source_evidence_from_dict(persisted)

    persisted = _persisted_evidence(tmp_path)
    persisted["components"][0]["source_range"]["range_kind"] = "anchor"
    with pytest.raises(EvidenceError, match="anchor source ranges must be empty"):
        source_evidence_from_dict(persisted)


def test_evidence_rejects_cross_source_artifact_and_region_components(tmp_path):
    persisted = _persisted_evidence(tmp_path)
    persisted["components"][1]["source_range"]["source_id"] = "src-v1-" + "a" * 64
    with pytest.raises(EvidenceError, match="crosses source identities"):
        source_evidence_from_dict(persisted)

    persisted = _persisted_evidence(tmp_path)
    persisted["components"][1]["source_range"]["artifact_id"] = "art-v1-" + "b" * 64
    with pytest.raises(EvidenceError, match="different source artifacts"):
        source_evidence_from_dict(persisted)

    persisted = _persisted_evidence(tmp_path)
    persisted["components"][1]["source_range"]["region_id"] = "footnote:n"
    with pytest.raises(EvidenceError, match="cross canonical source regions"):
        source_evidence_from_dict(persisted)


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("evidence_id", "evd-invalid", "evidence_id"),
        ("source_id", "src-invalid", "source_id"),
        ("output_sha256", "invalid", "output_sha256"),
        ("context_digest", "invalid", "context_digest"),
    ],
)
def test_evidence_rejects_malformed_top_level_ids_and_digests(
    tmp_path,
    field,
    replacement,
    message,
):
    persisted = _persisted_evidence(tmp_path)
    persisted[field] = replacement

    with pytest.raises(EvidenceError, match=message):
        source_evidence_from_dict(persisted)


def test_runtime_evidence_construction_and_resolution_reject_malformed_ids(tmp_path):
    path = tmp_path / "runtime-ids.txt"
    path.write_text("runtime evidence", encoding="utf-8")
    result = parse_text(path)
    chunk = chunk_paragraph(result.document.children, source=result.source)[0]
    component = chunk.evidence.components[0]
    malformed_range = replace(component.source_range, artifact_id="art-invalid")

    with pytest.raises(EvidenceError, match="artifact_id"):
        make_evidence(
            source_id=result.source.id,
            components=(replace(component, source_range=malformed_range),),
            output_text=chunk.text,
            context={"test": "runtime-malformed-artifact"},
        )

    malformed_evidence = replace(chunk.evidence, source_id="src-invalid")
    with pytest.raises(EvidenceError, match="source_id"):
        resolve_evidence(malformed_evidence, {result.source.id: result.source})


def test_note_region_roundtrips_without_body_heading_context():
    fixture = Path(__file__).parent.parent / "fixtures" / "sample.md"
    result = parse_md_file(fixture)
    note = result.document.footnotes["n"]
    chunk = chunk_paragraph(
        note.children,
        source=result.source,
        region_id="footnote:n",
    )[0]

    assert chunk.heading_path == []
    assert {
        component.source_range.region_id for component in chunk.evidence.components
    } == {"footnote:n"}
    assert chunk.identity_context["region_id"] == "footnote:n"
    persisted = json.loads(json.dumps(chunk_to_dict(chunk)))
    assert chunk_from_dict(persisted) == chunk
