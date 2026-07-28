# tests/validate/test_gates.py
from veriformis.chunkers.base import Chunk
from veriformis.sources import SourceRef
from veriformis.validate.gates import (
    gate_encoding, gate_provenance, gate_schema, run_gates,
)


def _source(stream="alpha beta"):
    return SourceRef(id="s1", path="f.txt", sha256="x", size=10, parser="text", extracted_text=stream)


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
    good = Chunk(id="c1", source_id="s1", block_index=0, span=_span(0, 5),
                 heading_path=[], text="alpha", tokens_est=2, transformed=False)
    assert gate_provenance([good], {"s1": src}).passed
    edited = Chunk(id="c2", source_id="s1", block_index=0, span=_span(0, 5),
                   heading_path=[], text="ALPHA", tokens_est=2, transformed=True)
    assert gate_provenance([edited], {"s1": src}).passed  # linkage only
    stale = Chunk(id="c3", source_id="s1", block_index=0, span=_span(0, 5),
                  heading_path=[], text="ALPHA", tokens_est=2, transformed=False)
    assert not gate_provenance([stale], {"s1": src}).passed  # slice mismatch, not marked
    missing = Chunk(id="c4", source_id="nope", block_index=0, span=None,
                    heading_path=[], text="x", tokens_est=1)
    assert not gate_provenance([missing], {"s1": src}).passed


def test_run_gates_order():
    results = run_gates([{"text": "a"}], "completion", [], {})
    assert [r.gate for r in results] == ["schema", "encoding", "provenance"]


def _span(a, b):
    from veriformis.ir import Span

    return Span(a, b)
