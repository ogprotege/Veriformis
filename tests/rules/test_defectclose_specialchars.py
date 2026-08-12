# tests/rules/test_defectclose_specialchars.py
"""Defect closure: the stock 'special-chars' rule must never delete Unicode
combining marks (general category M), and previously persisted cleaning plans
built from the old regex must keep replaying byte-exactly (operation replay)
while configured semantic replay fails closed rather than silently diverging.
"""
from __future__ import annotations

import unicodedata

import pytest

from veriformis.errors import EvidenceError
from veriformis.parsers.text import parse_text
from veriformis.pipeline import PipelineService
from veriformis.rules.cleaning import (
    cleaning_plan_from_dict,
    cleaning_plan_to_dict,
    document_digest,
    plan_cleaning,
    replay_cleaning_plan,
)
from veriformis.rules.engine import RegexRule
from veriformis.rules.library import RULES

# The exact pre-fix library definition, reconstructed for compatibility tests.
_OLD_PATTERN = r"[^\w\s.,!?;:'\"()/-]"


def _apply(text: str) -> str:
    return RULES["special-chars"]().apply(text).text


def test_nfd_latin_accents_survive_and_match_nfc():
    nfc = "café résumé"
    nfd = unicodedata.normalize("NFD", nfc)
    assert "́" in nfd  # guard: the input really is decomposed
    assert _apply(nfd) == nfd
    assert _apply(nfc) == nfc
    # Output no longer depends on the input's normalization form.
    assert unicodedata.normalize("NFC", _apply(nfd)) == _apply(nfc)


def test_arabic_harakat_intact():
    text = "مَرحَبًا"  # مَرحَبًا
    assert _apply(text) == text


def test_devanagari_matras_and_virama_intact():
    text = "हिन्दी"  # हिन्दी
    assert _apply(text) == text


def test_symbol_noise_still_removed():
    assert _apply("a © b • c ★ d") == "a  b  c  d"  # © • ★
    out = _apply("price: $5 (ok) — really!")
    assert "$" not in out and "—" not in out
    assert "price" in out and "really!" in out


def test_plan_cleaning_preserves_marks_end_to_end(tmp_path):
    nfd = unicodedata.normalize("NFD", "café résumé keeps accents © intact.")
    path = tmp_path / "doc.txt"
    path.write_text(nfd, encoding="utf-8")
    parsed = parse_text(path, logical_path=path.name)
    preview = plan_cleaning(parsed.document, [RULES["special-chars"]()])
    from veriformis.ir import block_text

    cleaned = block_text(preview.document.children[0])
    assert "́" in cleaned  # combining acute accents survive
    assert "©" not in cleaned  # genuine symbol noise removed
    replayed = replay_cleaning_plan(parsed.document, preview.plan)
    assert document_digest(replayed) == preview.plan.output_document_sha256


def test_old_pattern_plan_replays_byte_exactly(tmp_path):
    """Plans persist their own operations (expected text + digests); pure replay
    never consults the rule library, so a plan recorded with the old pattern
    still reproduces its old (corrupted) output byte-exactly after the fix."""
    nfd = unicodedata.normalize("NFD", "café résumé stays decomposed here.")
    path = tmp_path / "doc.txt"
    path.write_text(nfd, encoding="utf-8")
    parsed = parse_text(path, logical_path=path.name)

    old_rule = RegexRule("special-chars", _OLD_PATTERN)
    old_preview = plan_cleaning(parsed.document, [old_rule])
    from veriformis.ir import block_text

    corrupted = block_text(old_preview.document.children[0])
    assert "́" not in corrupted  # the old rule really deleted the marks
    assert corrupted.startswith("cafe resume")

    # Round-trip through the persisted schema, then replay operations.
    reloaded = cleaning_plan_from_dict(cleaning_plan_to_dict(old_preview.plan))
    replayed = replay_cleaning_plan(parsed.document, reloaded)
    assert document_digest(replayed) == old_preview.plan.output_document_sha256
    assert block_text(replayed.children[0]) == corrupted

    # The current library rule plans differently, so configured semantic
    # replay (workspace validation re-plans from rule names) detects the
    # definitional change instead of silently diverging.
    new_preview = plan_cleaning(parsed.document, [RULES["special-chars"]()])
    assert new_preview.plan != old_preview.plan
    assert new_preview.plan.id != old_preview.plan.id


def test_workspace_with_old_rule_definition_fails_closed(tmp_path, monkeypatch):
    """A workspace cleaned under the old rule definition must fail closed at
    the next configured semantic replay (chunk commit), never silently diverge."""
    raw = tmp_path / "raw"
    raw.mkdir()
    nfd = unicodedata.normalize(
        "NFD",
        "café résumé keeps the corpus long enough for the safety budget. "
        "More grounded filler text follows the accented words here.",
    )
    (raw / "doc.txt").write_text(nfd, encoding="utf-8")
    workspace = tmp_path / "ws"
    service = PipelineService()
    service.parse([raw / "doc.txt"], workspace, source_root=raw)

    with monkeypatch.context() as patch:
        patch.setitem(
            RULES,
            "special-chars",
            lambda: RegexRule("special-chars", _OLD_PATTERN),
        )
        service.clean(workspace, rules="special-chars")

    # Library definition is restored: the persisted plan no longer matches a
    # configured replay, so the next stage fails closed instead of silently
    # cleaning with the new definition.
    with pytest.raises(EvidenceError, match="not the configured replay"):
        service.chunk(workspace)
