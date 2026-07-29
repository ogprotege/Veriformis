# src/veriformis/validate/gates.py
"""Validation gates. All gates report; sealing requires every gate to pass."""
from __future__ import annotations

from dataclasses import dataclass, field

from veriformis.chunkers.base import Chunk, exact_span_from_evidence
from veriformis.evidence import EvidenceError, resolve_evidence
from veriformis.sources import SourceRef


@dataclass
class GateResult:
    gate: str
    passed: bool
    messages: list[str] = field(default_factory=list)


RECORD_SCHEMAS: dict[str, set[str]] = {
    "completion": {"text"},
    "instruction": {"instruction", "input", "output"},
    "chat": {"text"},
}

_MOJIBAKE = ("â€™", "Ã©", "Ã¨", "Ã¶", "Ã¼", "Ã¤", "Â", "�")


def gate_schema(records: list[dict], format: str) -> GateResult:
    required = RECORD_SCHEMAS[format]
    problems = [
        f"record {i}: keys {sorted(r)} != required {sorted(required)}"
        for i, r in enumerate(records)
        if set(r) != required or not all(isinstance(r[k], str) for k in required)
    ]
    return GateResult("schema", not problems, problems[:20])


def gate_encoding(texts: list[str]) -> GateResult:
    problems = []
    for i, text in enumerate(texts):
        for marker in _MOJIBAKE:
            if marker in text:
                problems.append(f"text {i}: mojibake marker {marker!r}")
                break
        bad = [c for c in text if ord(c) < 0x20 and c not in "\n\t"]
        if bad:
            problems.append(f"text {i}: control char U+{ord(bad[0]):04X}")
    return GateResult("encoding", not problems, problems[:20])


def gate_provenance(chunks: list[Chunk], sources: dict[str, SourceRef]) -> GateResult:
    problems = []
    for chunk in chunks:
        source = sources.get(chunk.source_id)
        if source is None:
            problems.append(f"{chunk.id}: unregistered source {chunk.source_id!r}")
            continue
        if chunk.block_index < 0:
            problems.append(f"{chunk.id}: invalid block_index")
        if chunk.evidence is None:
            problems.append(f"{chunk.id}: missing reconstructible source evidence")
            continue
        if chunk.span != exact_span_from_evidence(chunk.evidence):
            problems.append(f"{chunk.id}: span is not exactly proved by evidence")
            continue
        try:
            reconstructed = resolve_evidence(chunk.evidence, sources)
        except EvidenceError as exc:
            problems.append(f"{chunk.id}: invalid source evidence: {exc}")
            continue
        if reconstructed != chunk.text:
            problems.append(f"{chunk.id}: evidence content mismatch")
    return GateResult("provenance", not problems, problems[:20])


def run_gates(records, format, chunks, sources) -> list[GateResult]:
    texts = [r.get("text") or r.get("output", "") for r in records]
    return [
        gate_schema(records, format),
        gate_encoding(texts),
        gate_provenance(chunks, sources),
    ]
