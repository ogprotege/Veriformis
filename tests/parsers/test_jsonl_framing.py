"""Post-20 defect D-03: every JSONL reader frames on ``\\n`` only.

``str.splitlines()`` also splits on U+2028, U+2029, U+0085, U+000B, and
U+000C. Those characters are legal raw inside JSON strings and Veriformis's own
``ensure_ascii=False`` writers emit them unescaped, so re-importing a Veriformis
export refused a valid file and ``line_number`` evidence drifted from the real
newline-framed lines.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from veriformis._jsonl_frames import frame_jsonl_lines
from veriformis.handoff.aptus_v1 import _load_jsonl_objects
from veriformis.identity import lossless_json_bytes
from veriformis.mapping.capture import capture_jsonl
from veriformis.parsers.structured import parse_jsonl_file

# Legal raw inside a JSON string (JSON escapes only characters below U+0020),
# emitted unescaped by ensure_ascii=False writers, and split by splitlines().
SEPARATORS = ("\u2028", "\u2029", "\u0085")
# Below U+0020: never legal raw in a JSON string, but still split by splitlines().
CONTROL_SEPARATORS = ("\x0b", "\x0c")


def _jsonl_bytes(rows: list[dict[str, object]]) -> bytes:
    # Mirrors how split-jsonl-directory and sealed bundles write rows.
    return b"".join(lossless_json_bytes(row) + b"\n" for row in rows)


@pytest.mark.parametrize("separator", SEPARATORS)
def test_frame_jsonl_lines_keeps_unicode_line_separators_inside_a_record(separator: str) -> None:
    text = json.dumps({"text": f"a{separator}b"}, ensure_ascii=False) + "\n"
    assert separator in text
    assert len(text.splitlines()) == 2  # the defect: splitlines() breaks the record
    framed = list(frame_jsonl_lines(text))
    assert len(framed) == 1
    assert framed[0][0] == 1
    assert json.loads(framed[0][1]) == {"text": f"a{separator}b"}


@pytest.mark.parametrize("separator", CONTROL_SEPARATORS)
def test_frame_jsonl_lines_leaves_raw_control_characters_for_the_decoder(separator: str) -> None:
    text = '{"text": "a' + separator + 'b"}\n'
    framed = list(frame_jsonl_lines(text))
    assert framed == [(1, '{"text": "a' + separator + 'b"}')]
    with pytest.raises(json.JSONDecodeError):
        json.loads(framed[0][1])


def test_frame_jsonl_lines_numbers_physical_lines_and_skips_blanks() -> None:
    text = '{"a": 1}\n\n   \n{"a": 2}\r\n{"a": 3}'
    assert list(frame_jsonl_lines(text)) == [
        (1, '{"a": 1}'),
        (4, '{"a": 2}'),
        (5, '{"a": 3}'),
    ]


def test_crlf_and_lf_frame_identically() -> None:
    lf = '{"a": 1}\n{"a": 2}\n'
    crlf = lf.replace("\n", "\r\n")
    assert list(frame_jsonl_lines(lf)) == list(frame_jsonl_lines(crlf))


def test_lone_carriage_return_stays_in_the_line_and_is_refused_by_json() -> None:
    framed = list(frame_jsonl_lines('{"a": "x\ry"}\n'))
    assert framed == [(1, '{"a": "x\ry"}')]
    with pytest.raises(json.JSONDecodeError):
        json.loads(framed[0][1])


@pytest.mark.parametrize("separator", SEPARATORS)
def test_jsonl_parser_accepts_records_containing_line_separators(
    tmp_path: Path, separator: str
) -> None:
    path = tmp_path / "rows.jsonl"
    path.write_bytes(_jsonl_bytes([{"text": f"first{separator}second"}, {"text": "third"}]))
    result = parse_jsonl_file(path, logical_path=path.name)
    # The record is admitted; the flattener may still normalize whitespace-class
    # characters and report that as a degraded (not refused) recovery.
    assert result.diagnostics.status != "refused"
    assert "jsonl.invalid-line" not in {item.code for item in result.diagnostics.diagnostics}
    assert "first" in result.source.extracted_text
    assert "second" in result.source.extracted_text
    assert "third" in result.source.extracted_text


@pytest.mark.parametrize("separator", SEPARATORS)
def test_dataset_row_capture_accepts_exported_rows_with_line_separators(
    tmp_path: Path, separator: str
) -> None:
    path = tmp_path / "rows.jsonl"
    rows = [{"text": f"first{separator}second"}, {"text": "third"}]
    path.write_bytes(_jsonl_bytes(rows))
    capture = capture_jsonl(path, logical_path=path.name)
    assert capture.row_source.record_count == 2
    assert [record.payload for record in capture.records] == rows
    assert [record.line_number for record in capture.records] == [1, 2]
    assert [record.row_index for record in capture.records] == [1, 2]


def test_dataset_row_capture_line_numbers_count_physical_newlines(tmp_path: Path) -> None:
    path = tmp_path / "rows.jsonl"
    path.write_bytes(b'{"text": "a"}\n\n{"text": "b"}\r\n')
    capture = capture_jsonl(path, logical_path=path.name)
    assert [record.line_number for record in capture.records] == [1, 3]
    assert [record.raw_line for record in capture.records] == ['{"text": "a"}', '{"text": "b"}']


@pytest.mark.parametrize("separator", SEPARATORS)
def test_handoff_loader_shares_the_framer(separator: str) -> None:
    rows = _load_jsonl_objects(_jsonl_bytes([{"text": f"a{separator}b"}]))
    assert rows == [{"text": f"a{separator}b"}]
