"""Post-20 defect D-14: OCR confidence is derived from Tesseract TSV output.

The provider previously ran ``tesseract ... stdout`` (plain text only) and
never populated ``confidence``, so ``decide_confidence(None)`` accepted every
OCR page and the refuse / review / warn thresholds were dead code.
"""

from __future__ import annotations

from veriformis.ocr.tesseract import parse_tsv_confidence
from veriformis.ocr.thresholds import decide_confidence

HEADER = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"


def _row(level: int, conf: str, text: str) -> str:
    return f"{level}\t1\t1\t1\t1\t1\t0\t0\t10\t10\t{conf}\t{text}"


def test_word_rows_produce_mean_minimum_and_count() -> None:
    tsv = "\n".join(
        [
            HEADER,
            _row(1, "-1", ""),
            _row(4, "-1", ""),
            _row(5, "96.5", "Hello"),
            _row(5, "40", "wor1d"),
            _row(5, "80", "again"),
        ]
    )
    confidence = parse_tsv_confidence(tsv)
    assert confidence is not None
    assert confidence.word_count == 3
    assert confidence.minimum == 40.0
    assert round(confidence.mean, 3) == round((96.5 + 40 + 80) / 3, 3)
    assert decide_confidence(confidence) == "warn"


def test_low_minimum_refuses() -> None:
    tsv = "\n".join([HEADER, _row(5, "95", "ok"), _row(5, "12", "?")])
    assert decide_confidence(parse_tsv_confidence(tsv)) == "refuse"


def test_no_scored_words_yields_none_and_requires_review() -> None:
    assert parse_tsv_confidence("") is None
    assert parse_tsv_confidence(HEADER) is None
    assert parse_tsv_confidence("\n".join([HEADER, _row(5, "-1", ""), _row(5, "77", "  ")])) is None
    assert decide_confidence(None) == "review"


def test_unexpected_header_yields_none() -> None:
    assert parse_tsv_confidence("a\tb\tc\n1\t2\t3") is None


def test_scores_are_clamped_to_the_policy_range() -> None:
    confidence = parse_tsv_confidence("\n".join([HEADER, _row(5, "100.4", "x")]))
    assert confidence is not None
    assert confidence.mean == confidence.minimum == 100.0
