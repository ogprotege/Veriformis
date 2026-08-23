"""UTF-8 JSONL, JSON, and compatible CSV row-source capture.

This path does not flatten, trim, pad, or call document recovery.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from veriformis.errors import RowSourceError
from veriformis.identity import lossless_json_bytes, normalize_logical_path, sha256_digest
from veriformis.mapping.models import RowSource

JSONL_SUFFIX = ".jsonl"
JSON_SUFFIX = ".json"
CSV_SUFFIX = ".csv"
ROW_SUFFIXES = (JSONL_SUFFIX, JSON_SUFFIX, CSV_SUFFIX)
JSON_RECORD_KEYS = ("records", "rows")


@dataclass(frozen=True)
class CapturedRow:
    """One JSON object recovered from a nonempty JSONL line or tabular row."""

    row_index: int
    line_number: int
    payload: dict[str, Any]
    raw_line: str


@dataclass(frozen=True)
class JsonlCapture:
    """Exact-byte row-source capture bound to a row-source identity."""

    row_source: RowSource
    records: tuple[CapturedRow, ...]
    raw_bytes: bytes


def capture_row_source(
    path: Path,
    *,
    logical_path: str,
    raw_bytes: bytes | None = None,
) -> JsonlCapture:
    """Capture JSONL, JSON array, or compatible CSV as ordered objects."""
    suffix = path.suffix.lower()
    if suffix == JSONL_SUFFIX:
        return capture_jsonl(path, logical_path=logical_path, raw_bytes=raw_bytes)
    if suffix == JSON_SUFFIX:
        return capture_json(path, logical_path=logical_path, raw_bytes=raw_bytes)
    if suffix == CSV_SUFFIX:
        return capture_csv(path, logical_path=logical_path, raw_bytes=raw_bytes)
    raise RowSourceError(
        f"{logical_path}: dataset-row capture admits only {ROW_SUFFIXES} files"
    )


def capture_json(
    path: Path,
    *,
    logical_path: str,
    raw_bytes: bytes | None = None,
) -> JsonlCapture:
    """Capture a UTF-8 JSON array of objects or one object with a records array."""
    payload = path.read_bytes() if raw_bytes is None else raw_bytes
    try:
        text = payload.decode("utf-8")
        value = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RowSourceError(f"{logical_path}: JSON is not valid UTF-8 JSON") from exc
    objects = _json_record_objects(value, logical_path=logical_path)
    records = tuple(
        CapturedRow(
            row_index=index,
            line_number=index,
            payload=item,
            raw_line=lossless_json_bytes(item).decode("utf-8"),
        )
        for index, item in enumerate(objects, start=1)
    )
    source = RowSource.create(
        logical_path=normalize_logical_path(logical_path),
        sha256=sha256_digest(payload),
        size=len(payload),
        record_count=len(records),
        container_kind="json",
    )
    return JsonlCapture(row_source=source, records=records, raw_bytes=payload)


def capture_csv(
    path: Path,
    *,
    logical_path: str,
    raw_bytes: bytes | None = None,
) -> JsonlCapture:
    """Capture UTF-8 comma CSV with a required header and no silent trim or pad."""
    payload = path.read_bytes() if raw_bytes is None else raw_bytes
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RowSourceError(f"{logical_path}: CSV is not valid UTF-8") from exc
    if text.startswith("\ufeff"):
        raise RowSourceError(f"{logical_path}: CSV must be UTF-8 without a byte-order mark")
    try:
        rows = list(
            csv.reader(
                io.StringIO(text),
                delimiter=",",
                quotechar='"',
                doublequote=True,
                skipinitialspace=False,
                strict=True,
            )
        )
    except csv.Error as exc:
        raise RowSourceError(f"{logical_path}: CSV is not a valid comma-delimited file") from exc
    if not rows:
        raise RowSourceError(f"{logical_path}: CSV requires a header row")
    header = rows[0]
    if not header or any(name == "" for name in header):
        raise RowSourceError(f"{logical_path}: CSV requires a non-empty header row")
    if len(header) != len(set(header)):
        raise RowSourceError(f"{logical_path}: CSV header columns must be unique")
    if "messages" in header:
        raise RowSourceError(
            f"{logical_path}: CSV cannot represent nested messages; "
            "use split-jsonl-directory or json"
        )
    records: list[CapturedRow] = []
    for index, row in enumerate(rows[1:], start=1):
        if len(row) != len(header):
            raise RowSourceError(
                f"{logical_path}: CSV row {index} is jagged; nested or padded CSV is refused"
            )
        payload_obj: dict[str, str] = {}
        for key, value in zip(header, row, strict=True):
            if value.lstrip().startswith("{") or value.lstrip().startswith("["):
                raise RowSourceError(
                    f"{logical_path}: CSV row {index} is nested; nested CSV is refused. "
                    "Use split-jsonl-directory or json"
                )
            payload_obj[key] = value
        records.append(
            CapturedRow(
                row_index=index,
                line_number=index + 1,
                payload=payload_obj,
                raw_line=lossless_json_bytes(payload_obj).decode("utf-8"),
            )
        )
    if not records:
        raise RowSourceError(f"{logical_path}: CSV file contains no data rows")
    source = RowSource.create(
        logical_path=normalize_logical_path(logical_path),
        sha256=sha256_digest(payload),
        size=len(payload),
        record_count=len(records),
        container_kind="csv",
    )
    return JsonlCapture(row_source=source, records=tuple(records), raw_bytes=payload)


def capture_jsonl(
    path: Path,
    *,
    logical_path: str,
    raw_bytes: bytes | None = None,
) -> JsonlCapture:
    """Capture one UTF-8 JSONL file as ordered JSON objects.

    Blank lines are skipped. Valid empty-string fields are kept. Invalid UTF-8,
    invalid JSON, non-object lines, and empty files fail closed.
    """
    payload = path.read_bytes() if raw_bytes is None else raw_bytes
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RowSourceError(
            f"{logical_path}: JSONL is not valid UTF-8"
        ) from exc
    if path.suffix.lower() != JSONL_SUFFIX:
        raise RowSourceError(
            f"{logical_path}: dataset-row capture admits only {JSONL_SUFFIX} files"
        )
    records: list[CapturedRow] = []
    row_index = 0
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip():
            continue
        row_index += 1
        try:
            parsed = _load_json_object(raw_line, logical_path=logical_path, line=line_number)
        except RowSourceError:
            raise
        records.append(
            CapturedRow(
                row_index=row_index,
                line_number=line_number,
                payload=parsed,
                raw_line=raw_line,
            )
        )
    if not records:
        raise RowSourceError(f"{logical_path}: JSONL file contains no objects")
    normalized = normalize_logical_path(logical_path)
    source = RowSource.create(
        logical_path=normalized,
        sha256=sha256_digest(payload),
        size=len(payload),
        record_count=len(records),
        container_kind="jsonl",
    )
    return JsonlCapture(row_source=source, records=tuple(records), raw_bytes=payload)


def _json_record_objects(value: Any, *, logical_path: str) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return _require_object_records(value, logical_path=logical_path)
    if not isinstance(value, dict):
        raise RowSourceError(
            f"{logical_path}: JSON import refuses scalar files; "
            "use a top-level array of objects or one object with a records array"
        )
    declared = [
        key
        for key in JSON_RECORD_KEYS
        if key in value and isinstance(value[key], list)
    ]
    if len(declared) > 1:
        raise RowSourceError(
            f"{logical_path}: JSON import refuses an object that declares both "
            "records and rows arrays"
        )
    if not declared:
        raise RowSourceError(
            f"{logical_path}: JSON import requires a non-empty array of objects "
            "or one object with a records or rows array; "
            "document-mode flattened JSON is not a row source"
        )
    return _require_object_records(value[declared[0]], logical_path=logical_path)


def _require_object_records(value: Any, *, logical_path: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise RowSourceError(
            f"{logical_path}: JSON import requires a non-empty array of objects"
        )
    if not all(isinstance(item, dict) for item in value):
        raise RowSourceError(
            f"{logical_path}: JSON import refuses non-object records"
        )
    return list(value)


def _load_json_object(raw_line: str, *, logical_path: str, line: int) -> dict[str, Any]:
    try:
        value = json.loads(raw_line)
    except json.JSONDecodeError as exc:
        raise RowSourceError(
            f"{logical_path}:{line}: JSONL line is not valid JSON"
        ) from exc
    if not isinstance(value, dict):
        raise RowSourceError(
            f"{logical_path}:{line}: JSONL line must be a JSON object"
        )
    # Re-encode through the lossless codec so later mapping hashes are stable
    # without rewriting string values or dropping empty-string fields.
    lossless_json_bytes(value)
    return value
