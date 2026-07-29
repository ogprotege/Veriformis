import pytest

from veriformis.chunkers.strategies import chunk_paragraph
from veriformis.parsers.text import parse_text
from veriformis.validate.gates import run_gates


@pytest.mark.xfail(strict=True, reason="roadmap-step-8-and-15: field evidence and exact validation")
def test_fabricated_record_without_source_binding_is_rejected(tmp_path):
    path = tmp_path / "source.txt"
    path.write_text("alpha", encoding="utf-8")
    parsed = parse_text(path, logical_path=path.name)
    chunks = chunk_paragraph(
        parsed.document.children,
        source=parsed.source,
    )

    results = run_gates(
        [{"text": "fabricated and unrelated"}],
        "completion",
        chunks,
        {parsed.source.id: parsed.source},
    )

    by_gate = {result.gate: result for result in results}
    assert by_gate["schema"].passed
    assert by_gate["encoding"].passed
    assert by_gate["provenance"].passed
    assert by_gate.get("record-binding") is not None
    assert not by_gate["record-binding"].passed
