"""Canonical block derivations produced by one replayable cleaning plan."""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from veriformis.errors import EvidenceError
from veriformis.evidence import (
    DerivationStep,
    EvidenceEdit,
    derivation_from_dict,
    derivation_to_dict,
    edits_derivation,
)
from veriformis.ir import Document, block_text, iter_document_blocks
from veriformis.sources import SourceRef


def _diff_edits(before: str, after: str) -> list[EvidenceEdit]:
    return [
        EvidenceEdit(i1, i2, before[i1:i2], after[j1:j2])
        for tag, i1, i2, j1, j2 in SequenceMatcher(
            a=before,
            b=after,
            autojunk=False,
        ).get_opcodes()
        if tag != "equal"
    ]


def build_block_derivations(
    source: SourceRef,
    document: Document,
    *,
    cleaning_plan_id: str,
) -> dict[int, tuple[DerivationStep, ...]]:
    """Build the unique edit script for every cleaned canonical block."""
    derivations: dict[int, tuple[DerivationStep, ...]] = {}
    for block in iter_document_blocks(document):
        if block.span is None or block.block_index < 0:
            raise EvidenceError(
                "cleaned top-level block lacks immutable source attribution"
            )
        original = source.extracted_text[block.span.start : block.span.end]
        cleaned = block_text(block)
        if original == cleaned:
            derivations[block.block_index] = ()
            continue
        step = edits_derivation(
            original,
            _diff_edits(original, cleaned),
            context={
                "cleaning_plan_id": cleaning_plan_id,
                "source_id": source.id,
                "block_index": block.block_index,
            },
        )
        derivations[block.block_index] = (step,)
    return derivations


def block_derivations_to_dict(
    derivations: dict[int, tuple[DerivationStep, ...]],
) -> dict[str, list[dict]]:
    return {
        str(block_index): [derivation_to_dict(step) for step in steps]
        for block_index, steps in sorted(derivations.items())
    }


def block_derivations_from_dict(
    value: Any,
) -> dict[int, tuple[DerivationStep, ...]]:
    if not isinstance(value, dict):
        raise EvidenceError("block derivations must be a JSON object")
    result: dict[int, tuple[DerivationStep, ...]] = {}
    for raw_index, steps in value.items():
        if not isinstance(raw_index, str) or not raw_index.isdigit():
            raise EvidenceError(
                "block derivation keys must be non-negative integer strings"
            )
        index = int(raw_index)
        if index in result or not isinstance(steps, list):
            raise EvidenceError(
                "block derivations contain a duplicate or invalid entry"
            )
        result[index] = tuple(derivation_from_dict(step) for step in steps)
    return result


def load_exact_block_derivations(
    value: Any,
    *,
    source: SourceRef,
    document: Document,
    cleaning_plan_id: str,
) -> dict[int, tuple[DerivationStep, ...]]:
    actual = block_derivations_from_dict(value)
    expected = build_block_derivations(
        source,
        document,
        cleaning_plan_id=cleaning_plan_id,
    )
    if actual != expected:
        raise EvidenceError(
            "block derivations do not match the canonical cleaning derivation"
        )
    return actual
