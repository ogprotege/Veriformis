# tests/validate/test_gates.py
from veriformis.chunkers.base import Chunk
from veriformis.evidence import (
    EvidenceComponent, EvidenceEdit, edits_derivation, make_evidence, source_range,
)
from veriformis.identity import (
    canonical_digest, derive_artifact_id, derive_source_id, sha256_digest,
)
from veriformis.sources import SourceRef
from veriformis.validate.gates import (
    gate_encoding,
    gate_nonempty,
    gate_provenance,
    gate_record_binding,
    gate_schema,
    run_gates,
)


def _source(stream="alpha beta"):
    stream_digest = sha256_digest(stream)
    source_id = derive_source_id("f.txt", stream_digest)
    return SourceRef(
        id=source_id,
        path="f.txt",
        sha256=stream_digest,
        size=len(stream.encode("utf-8")),
        parser="text",
        extracted_text=stream,
        stream_sha256=stream_digest,
        artifact_id=derive_artifact_id(
            kind="canonical-source-text",
            content_sha256=stream_digest,
            source_ids=(source_id,),
            producer_id="veriformis.test",
            producer_version="1",
            config_digest=canonical_digest({"fixture": "gate-provenance"}),
        ),
    )


def _evidence(src, start, end, text, derivations=()):
    component = EvidenceComponent(source_range(src, start, end), tuple(derivations))
    return make_evidence(
        source_id=src.id,
        components=[component],
        output_text=text,
        context={"test": "gate-provenance"},
    )


def test_schema_gate():
    assert gate_schema([{"text": "a"}], "completion").passed
    bad = gate_schema([{"txt": "a"}], "completion")
    assert not bad.passed and bad.messages


def test_encoding_gate():
    assert gate_encoding(["clean text\nwith\ttabs"]).passed
    assert not gate_encoding(["mojibake â€™ here"]).passed
    assert not gate_encoding(["control\x01char"]).passed


def test_provenance_gate_exact_and_transformed():
    src = _source()
    good = Chunk(id="c1", source_id=src.id, block_index=0, span=_span(0, 5),
                 heading_path=[], text="alpha", tokens_est=2, transformed=False,
                 evidence=_evidence(src, 0, 5, "alpha"))
    assert gate_provenance([good], {src.id: src}).passed
    edit = edits_derivation(
        "alpha",
        [EvidenceEdit(0, 5, "alpha", "ALPHA")],
        context={"rule": "uppercase-test"},
    )
    edited = Chunk(id="c2", source_id=src.id, block_index=0, span=None,
                   heading_path=[], text="ALPHA", tokens_est=2, transformed=True,
                   evidence=_evidence(src, 0, 5, "ALPHA", (edit,)))
    assert gate_provenance([edited], {src.id: src}).passed
    stale = Chunk(id="c3", source_id=src.id, block_index=0, span=_span(0, 5),
                  heading_path=[], text="ALPHA", tokens_est=2, transformed=False,
                  evidence=_evidence(src, 0, 5, "alpha"))
    assert not gate_provenance([stale], {src.id: src}).passed
    missing_source_id = derive_source_id("missing.txt", "0" * 64)
    missing = Chunk(id="c4", source_id=missing_source_id, block_index=0, span=None,
                    heading_path=[], text="x", tokens_est=1)
    assert not gate_provenance([missing], {src.id: src}).passed


def test_run_gates_order():
    src = _source("a")
    chunk = Chunk(
        id="c1",
        source_id=src.id,
        block_index=0,
        span=_span(0, 1),
        heading_path=[],
        text="a",
        tokens_est=1,
        transformed=False,
        evidence=_evidence(src, 0, 1, "a"),
    )
    results = run_gates([{"text": "a"}], "completion", [chunk], {src.id: src})
    assert [r.gate for r in results] == [
        "schema",
        "encoding",
        "provenance",
        "nonempty",
        "record-binding",
    ]
    assert all(result.passed for result in results)


def test_nonempty_and_record_binding_gates():
    assert not gate_nonempty([]).passed
    assert gate_nonempty([{"text": "alpha"}]).passed
    assert not gate_record_binding(
        [{"text": "fabricated"}], "completion", []
    ).passed


def _span(a, b):
    from veriformis.ir import Span

    return Span(a, b)
