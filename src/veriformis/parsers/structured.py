"""CSV, JSON, and JSONL recovery into evidence-bearing canonical IR."""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from veriformis.diagnostics import (
    DiagnosticLocation,
    make_diagnostic,
    make_parse_report,
)
from veriformis.errors import ParseError
from veriformis.ir import (
    Cell,
    Document,
    Paragraph,
    Span,
    Table,
    Text,
)
from veriformis.sources import ParseResult, register_source

CSV_PARSER_VERSION = "1.0.0"
JSON_PARSER_VERSION = "1.0.0"
JSONL_PARSER_VERSION = "1.0.0"
_WS = re.compile(r"[ \t]+")


def parse_csv_file(
    path: str | Path,
    *,
    logical_path: str,
    raw_bytes: bytes | None = None,
) -> ParseResult:
    """Parse UTF-8 CSV into one IR table with explicit dialect diagnostics."""
    p = Path(path)
    captured = raw_bytes if raw_bytes is not None else p.read_bytes()
    try:
        text = captured.decode("utf-8")
    except UnicodeDecodeError as exc:
        return _refuse(
            p,
            logical_path=logical_path,
            raw_bytes=captured,
            parser="csv",
            parser_version=CSV_PARSER_VERSION,
            code="csv.not-utf8",
            message=f"CSV source is not valid UTF-8: {exc}",
        )
    if not text.strip():
        return _refuse(
            p,
            logical_path=logical_path,
            raw_bytes=captured,
            parser="csv",
            parser_version=CSV_PARSER_VERSION,
            code="csv.empty",
            message="CSV source contains no rows.",
        )
    # Fixed excel dialect keeps recovery deterministic across platforms.
    dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    sample_rows = list(csv.reader(io.StringIO(text), dialect))
    has_header = False
    if sample_rows:
        first = sample_rows[0]
        rest = sample_rows[1:6]
        # Header heuristic: first row is all non-numeric while a later row has a number.
        if rest and all(not _looks_numeric(cell) for cell in first):
            if any(_looks_numeric(cell) for row in rest for cell in row):
                has_header = True
    rows = [tuple(cell.replace("\r\n", "\n").replace("\r", "\n") for cell in row) for row in reader]
    rows = [row for row in rows if any(cell.strip() for cell in row)]
    if not rows:
        return _refuse(
            p,
            logical_path=logical_path,
            raw_bytes=captured,
            parser="csv",
            parser_version=CSV_PARSER_VERSION,
            code="csv.empty",
            message="CSV source contains no non-empty rows.",
        )
    width = max(len(row) for row in rows)
    normalized_rows = [row + ("",) * (width - len(row)) for row in rows]
    if has_header and len(normalized_rows) > 1:
        headers = [Cell(children=[Text(cell.strip())]) for cell in normalized_rows[0]]
        table_rows = [
            [Cell(children=[Text(cell.strip())]) for cell in row]
            for row in normalized_rows[1:]
        ]
    else:
        headers = []
        table_rows = [
            [Cell(children=[Text(cell.strip())]) for cell in row]
            for row in normalized_rows
        ]
    # Match ir.block_text(Table): header (optional) then body rows, tab-joined.
    stream_rows: list[list[str]] = []
    if headers:
        stream_rows.append([cell.children[0].value for cell in headers])
    stream_rows.extend(
        [[cell.children[0].value for cell in row] for row in table_rows]
    )
    stream = "\n".join("\t".join(row) for row in stream_rows)
    blocks: list = [
        Table(
            headers=headers,
            rows=table_rows,
            span=Span(0, len(stream)),
            block_index=0,
        )
    ]
    source = register_source(
        p,
        "csv",
        stream,
        logical_path=logical_path,
        parser_version=CSV_PARSER_VERSION,
        raw_bytes=captured,
    )
    diagnostics = [
        make_diagnostic(
            source_id=source.id,
            parser_name="csv",
            parser_version=CSV_PARSER_VERSION,
            code="csv.dialect-detected",
            severity="info",
            disposition="normalized",
            loss_kind="presentation",
            location=DiagnosticLocation(
                kind="text",
                line_start=1,
                line_end=max(1, text.count("\n") + 1),
                raw_byte_start=0,
                raw_byte_end=len(captured),
            ),
            message="CSV used the fixed excel dialect for deterministic recovery.",
            details={
                "delimiter": ",",
                "has_header": has_header,
                "row_count": len(normalized_rows),
                "column_count": width,
            },
        )
    ]
    if any(len(row) != width for row in rows):
        diagnostics.append(
            make_diagnostic(
                source_id=source.id,
                parser_name="csv",
                parser_version=CSV_PARSER_VERSION,
                code="csv.ragged-rows-padded",
                severity="warning",
                disposition="normalized",
                loss_kind="structure",
                location=DiagnosticLocation(
                    kind="text",
                    line_start=1,
                    line_end=max(1, text.count("\n") + 1),
                    raw_byte_start=0,
                    raw_byte_end=len(captured),
                ),
                message="Ragged CSV rows were padded with empty cells to a rectangular table.",
            )
        )
    report = make_parse_report(
        source_id=source.id,
        parser_name="csv",
        parser_version=CSV_PARSER_VERSION,
        diagnostics=tuple(diagnostics),
    )
    return ParseResult(
        document=Document(children=blocks, source_id=source.id),
        source=source,
        diagnostics=report,
    )


def parse_json_file(
    path: str | Path,
    *,
    logical_path: str,
    raw_bytes: bytes | None = None,
) -> ParseResult:
    """Parse one UTF-8 JSON document into path-labeled paragraphs."""
    p = Path(path)
    captured = raw_bytes if raw_bytes is not None else p.read_bytes()
    try:
        text = captured.decode("utf-8")
    except UnicodeDecodeError as exc:
        return _refuse(
            p,
            logical_path=logical_path,
            raw_bytes=captured,
            parser="json",
            parser_version=JSON_PARSER_VERSION,
            code="json.not-utf8",
            message=f"JSON source is not valid UTF-8: {exc}",
        )
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        return _refuse(
            p,
            logical_path=logical_path,
            raw_bytes=captured,
            parser="json",
            parser_version=JSON_PARSER_VERSION,
            code="json.invalid",
            message=f"JSON source is not valid JSON: {exc}",
        )
    return _structured_value_result(
        p,
        logical_path=logical_path,
        raw_bytes=captured,
        value=value,
        parser="json",
        parser_version=JSON_PARSER_VERSION,
        line_count=max(1, text.count("\n") + 1),
    )


def parse_jsonl_file(
    path: str | Path,
    *,
    logical_path: str,
    raw_bytes: bytes | None = None,
) -> ParseResult:
    """Parse UTF-8 JSONL into one paragraph per non-empty line object."""
    p = Path(path)
    captured = raw_bytes if raw_bytes is not None else p.read_bytes()
    try:
        text = captured.decode("utf-8")
    except UnicodeDecodeError as exc:
        return _refuse(
            p,
            logical_path=logical_path,
            raw_bytes=captured,
            parser="jsonl",
            parser_version=JSONL_PARSER_VERSION,
            code="jsonl.not-utf8",
            message=f"JSONL source is not valid UTF-8: {exc}",
        )
    records: list[Any] = []
    bad_lines: list[int] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            bad_lines.append(number)
    if bad_lines:
        return _refuse(
            p,
            logical_path=logical_path,
            raw_bytes=captured,
            parser="jsonl",
            parser_version=JSONL_PARSER_VERSION,
            code="jsonl.invalid-line",
            message=(
                "JSONL contains invalid JSON on line(s): "
                + ", ".join(str(item) for item in bad_lines)
            ),
            details={"lines": bad_lines},
        )
    if not records:
        return _refuse(
            p,
            logical_path=logical_path,
            raw_bytes=captured,
            parser="jsonl",
            parser_version=JSONL_PARSER_VERSION,
            code="jsonl.empty",
            message="JSONL source contains no records.",
        )
    return _structured_value_result(
        p,
        logical_path=logical_path,
        raw_bytes=captured,
        value=records,
        parser="jsonl",
        parser_version=JSONL_PARSER_VERSION,
        line_count=max(1, text.count("\n") + 1),
        root_label="record",
    )


def _structured_value_result(
    path: Path,
    *,
    logical_path: str,
    raw_bytes: bytes,
    value: Any,
    parser: str,
    parser_version: str,
    line_count: int,
    root_label: str = "$",
) -> ParseResult:
    lines = list(_flatten_json(value, path=root_label))
    if not lines:
        return _refuse(
            path,
            logical_path=logical_path,
            raw_bytes=raw_bytes,
            parser=parser,
            parser_version=parser_version,
            code=f"{parser}.empty-projection",
            message=f"{parser.upper()} value projected no textual fields.",
        )
    stream = "\n\n".join(lines)
    blocks = []
    pos = 0
    for index, line in enumerate(lines):
        if index:
            pos += 2
        start = pos
        end = start + len(line)
        blocks.append(
            Paragraph(
                children=[Text(line)],
                span=Span(start, end),
                block_index=index,
            )
        )
        pos = end
    source = register_source(
        path,
        parser,
        stream,
        logical_path=logical_path,
        parser_version=parser_version,
        raw_bytes=raw_bytes,
    )
    diagnostics = [
        make_diagnostic(
            source_id=source.id,
            parser_name=parser,
            parser_version=parser_version,
            code=f"{parser}.path-projection",
            severity="info",
            disposition="normalized",
            loss_kind="structure",
            location=DiagnosticLocation(
                kind="text",
                line_start=1,
                line_end=line_count,
                raw_byte_start=0,
                raw_byte_end=len(raw_bytes),
            ),
            message=(
                f"{parser.upper()} was projected into path-labeled text lines for "
                "deterministic construction."
            ),
            details={"line_count": len(lines)},
        )
    ]
    report = make_parse_report(
        source_id=source.id,
        parser_name=parser,
        parser_version=parser_version,
        diagnostics=tuple(diagnostics),
    )
    return ParseResult(
        document=Document(children=blocks, source_id=source.id),
        source=source,
        diagnostics=report,
    )


def _looks_numeric(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    try:
        float(text)
    except ValueError:
        return False
    return True


def _flatten_json(value: Any, *, path: str) -> list[str]:
    if value is None:
        return [f"{path}: null"]
    if isinstance(value, bool):
        return [f"{path}: {'true' if value else 'false'}"]
    if isinstance(value, (int, float)):
        # Reject non-finite floats implicitly via JSON load; format stably.
        if isinstance(value, float):
            text = format(value, ".15g")
        else:
            text = str(value)
        return [f"{path}: {text}"]
    if isinstance(value, str):
        cleaned = _WS.sub(" ", value.replace("\r\n", "\n").replace("\r", "\n")).strip()
        return [f"{path}: {cleaned}"] if cleaned else [f"{path}:"]
    if isinstance(value, list):
        if not value:
            return [f"{path}: []"]
        lines: list[str] = []
        for index, item in enumerate(value):
            lines.extend(_flatten_json(item, path=f"{path}[{index}]"))
        return lines
    if isinstance(value, dict):
        if not value:
            return [f"{path}: {{}}"]
        lines = []
        for key in sorted(value, key=lambda item: str(item)):
            child_path = f"{path}.{key}" if path != "$" else str(key)
            lines.extend(_flatten_json(value[key], path=child_path))
        return lines
    raise ParseError(f"unsupported JSON value type at {path}: {type(value)!r}")


def _refuse(
    path: Path,
    *,
    logical_path: str,
    raw_bytes: bytes,
    parser: str,
    parser_version: str,
    code: str,
    message: str,
    details: dict | None = None,
) -> ParseResult:
    source = register_source(
        path,
        parser,
        "",
        logical_path=logical_path,
        parser_version=parser_version,
        raw_bytes=raw_bytes,
    )
    report = make_parse_report(
        source_id=source.id,
        parser_name=parser,
        parser_version=parser_version,
        diagnostics=(
            make_diagnostic(
                source_id=source.id,
                parser_name=parser,
                parser_version=parser_version,
                code=code,
                severity="error",
                disposition="refused",
                loss_kind="structure",
                location=DiagnosticLocation(kind="source"),
                message=message,
                details=details,
            ),
        ),
    )
    return ParseResult(
        document=Document(children=[], source_id=source.id),
        source=source,
        diagnostics=report,
    )
