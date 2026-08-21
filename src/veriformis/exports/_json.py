"""Exact JSON boundary for persisted verified-export models."""

from __future__ import annotations

import json
from typing import Any

from veriformis.errors import ExportVerificationError
from veriformis.identity import lossless_json_bytes


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ExportVerificationError(
                f"verified export JSON contains duplicate key {key!r}"
            )
        value[key] = item
    return value


def _reject_float(value: str) -> None:
    raise ExportVerificationError(
        f"floating-point JSON number is not allowed: {value!r}"
    )


def _reject_constant(value: str) -> None:
    raise ExportVerificationError(
        f"non-finite JSON number is not allowed: {value!r}"
    )


def canonical_export_object_from_bytes(
    data: bytes,
    *,
    label: str,
) -> dict[str, Any]:
    """Load one unique canonical UTF-8 JSON object without rewriting strings."""
    if type(data) is not bytes:
        raise ExportVerificationError(f"{label} must be loaded from exact bytes")
    try:
        decoded = data.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_unique_object,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except ExportVerificationError:
        raise
    except RecursionError as exc:
        raise ExportVerificationError(f"invalid {label} JSON: nesting too deep") from exc
    except (UnicodeError, ValueError) as exc:
        raise ExportVerificationError(f"invalid {label} JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ExportVerificationError(f"{label} JSON root must be an object")
    try:
        canonical = lossless_json_bytes(value)
    except RecursionError as exc:
        raise ExportVerificationError(f"invalid {label} JSON: nesting too deep") from exc
    except (TypeError, UnicodeError, ValueError) as exc:
        raise ExportVerificationError(f"invalid {label} JSON: {exc}") from exc
    if canonical != data:
        raise ExportVerificationError(f"{label} JSON bytes are not canonical")
    return value


__all__ = ["canonical_export_object_from_bytes"]
