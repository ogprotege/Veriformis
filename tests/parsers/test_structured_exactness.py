"""Post-20 defect D-13: JSON, JSONL, CSV, and text recovery are exact and closed.

Before the fix the JSON flattener admitted ``NaN``/``Infinity``, let the last
duplicate key win, rounded floats through ``.15g``, collapsed whitespace inside
string values, and re-sorted object keys; CSV carried a UTF-8 BOM into the
first header cell and trimmed cells and dropped blank rows silently; the text
parser raised a bare ``UnicodeDecodeError`` for invalid UTF-8.
"""

from __future__ import annotations

import codecs
from pathlib import Path

from veriformis.parsers.structured import (
    CSV_PARSER_VERSION,
    JSON_PARSER_VERSION,
    JSONL_PARSER_VERSION,
    parse_csv_file,
    parse_json_file,
    parse_jsonl_file,
)
from veriformis.parsers.text import PARSER_VERSION as TEXT_PARSER_VERSION
from veriformis.parsers.text import parse_text


def _write(tmp_path: Path, name: str, raw: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(raw)
    return path


def _codes(result) -> dict[str, object]:
    return {item.code: item for item in result.diagnostics.diagnostics}


def test_parser_pins_advanced() -> None:
    assert CSV_PARSER_VERSION == JSON_PARSER_VERSION == JSONL_PARSER_VERSION == "1.1.0"
    assert TEXT_PARSER_VERSION == "1.2.0"


def test_json_non_finite_numbers_are_refused(tmp_path: Path) -> None:
    result = parse_json_file(_write(tmp_path, "nan.json", b'{"a": NaN, "b": 1}'), logical_path="nan.json")
    assert result.diagnostics.status == "refused"
    refusal = _codes(result)["json.invalid"]
    assert "NaN" in refusal.message


def test_json_duplicate_keys_are_refused(tmp_path: Path) -> None:
    result = parse_json_file(
        _write(tmp_path, "dup.json", b'{"a": 1, "a": 2}'), logical_path="dup.json"
    )
    assert result.diagnostics.status == "refused"
    assert "duplicate JSON object key 'a'" in _codes(result)["json.invalid"].message


def test_jsonl_duplicate_key_line_is_refused(tmp_path: Path) -> None:
    result = parse_jsonl_file(
        _write(tmp_path, "dup.jsonl", b'{"a": 1}\n{"a": 1, "a": 2}\n'), logical_path="dup.jsonl"
    )
    assert result.diagnostics.status == "refused"
    assert _codes(result)["jsonl.invalid-line"].details == {"lines": [2]}


def test_json_floats_keep_their_shortest_round_trip_form(tmp_path: Path) -> None:
    result = parse_json_file(
        _write(tmp_path, "f.json", b'{"x": 0.30000000000000004, "y": 1e21, "z": 2.5}'),
        logical_path="f.json",
    )
    assert result.source.extracted_text == "x: 0.30000000000000004\n\ny: 1e+21\n\nz: 2.5"


def test_json_string_values_are_exact(tmp_path: Path) -> None:
    raw = '{"text": "  two  spaces\\tand a tab \\r\\nline two  "}'.encode("utf-8")
    result = parse_json_file(_write(tmp_path, "s.json", raw), logical_path="s.json")
    assert result.source.extracted_text == "text:   two  spaces\tand a tab \r\nline two  "


def test_json_object_keys_keep_source_order(tmp_path: Path) -> None:
    result = parse_json_file(
        _write(tmp_path, "o.json", b'{"zeta": 1, "alpha": {"b": 2, "a": 3}}'), logical_path="o.json"
    )
    assert result.source.extracted_text == "zeta: 1\n\nalpha.b: 2\n\nalpha.a: 3"


def test_json_empty_string_projects_as_bare_label(tmp_path: Path) -> None:
    result = parse_json_file(_write(tmp_path, "e.json", b'{"a": ""}'), logical_path="e.json")
    assert result.source.extracted_text == "a:"


def test_csv_bom_is_removed_and_diagnosed(tmp_path: Path) -> None:
    raw = codecs.BOM_UTF8 + b"name,age\nAda,36\n"
    result = parse_csv_file(_write(tmp_path, "bom.csv", raw), logical_path="bom.csv")
    assert result.source.extracted_text.startswith("name\tage")
    assert "\ufeff" not in result.source.extracted_text
    bom = _codes(result)["csv.bom-removed"]
    assert bom.loss_kind == "metadata"
    assert bom.disposition == "normalized"


def test_csv_trimmed_cells_and_blank_rows_are_diagnosed(tmp_path: Path) -> None:
    raw = b"name,age\n  Ada  ,36\n,\nGrace, 45\n"
    result = parse_csv_file(_write(tmp_path, "trim.csv", raw), logical_path="trim.csv")
    codes = _codes(result)
    assert codes["csv.cells-trimmed"].details == {"count": 2}
    assert codes["csv.blank-rows-omitted"].details == {"count": 1}
    assert result.source.extracted_text == "name\tage\nAda\t36\nGrace\t45"


def test_clean_csv_has_no_normalization_diagnostics(tmp_path: Path) -> None:
    result = parse_csv_file(_write(tmp_path, "clean.csv", b"a,b\n1,2\n"), logical_path="clean.csv")
    codes = _codes(result)
    assert "csv.cells-trimmed" not in codes
    assert "csv.blank-rows-omitted" not in codes
    assert "csv.bom-removed" not in codes


def test_text_invalid_utf8_is_a_typed_refusal(tmp_path: Path) -> None:
    result = parse_text(_write(tmp_path, "bad.txt", b"\xff\xfe not utf8"), logical_path="bad.txt")
    assert result.diagnostics.status == "refused"
    refusal = _codes(result)["text.not-utf8"]
    assert refusal.disposition == "refused"
    assert result.source.extracted_text == ""


def test_text_bom_is_removed_and_diagnosed(tmp_path: Path) -> None:
    result = parse_text(
        _write(tmp_path, "bom.txt", codecs.BOM_UTF8 + b"First.\n\nSecond.\n"), logical_path="bom.txt"
    )
    assert result.source.extracted_text == "First.\n\nSecond."
    assert "text.bom-removed" in _codes(result)


def test_code_bom_is_removed_and_diagnosed(tmp_path: Path) -> None:
    result = parse_text(
        _write(tmp_path, "bom.py", codecs.BOM_UTF8 + b"print(1)\n"),
        logical_path="bom.py",
        language="python",
    )
    assert result.source.extracted_text == "print(1)\n"
    assert "text.bom-removed" in _codes(result)
