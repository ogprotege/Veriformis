"""UTF-8 JSONL row-source capture. No flattening and no document recovery."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from veriformis.errors import RowSourceError
from veriformis.identity import lossless_json_bytes, normalize_logical_path, sha256_digest
from veriformis.mapping.models import RowSource

JSONL_SUFFIX = ".jsonl"


@dataclass(frozen=True)
class CapturedRow:
    """One JSON object recovered from a nonempty JSONL line."""

    row_index: int
    line_number: int
    payload: dict[str, Any]
    raw_line: str


@dataclass(frozen=True)
class JsonlCapture:
    """Exact-byte JSONL capture bound to a row-source identity."""

    row_source: RowSource
    records: tuple[CapturedRow, ...]
    raw_bytes: bytes


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


def _load_json_object(raw_line: str, *, logical_path: str, line: int) -> dict[str, Any]:
    import json

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
