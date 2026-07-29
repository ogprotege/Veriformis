"""Deterministic, domain-separated identities for persisted Veriformis data."""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import PurePath
from typing import Any, Mapping

from pydantic import BaseModel

from veriformis.errors import InvalidSourceLocatorError

_ID_KIND = re.compile(r"^[a-z][a-z0-9-]*$")
_PERSISTED_ID = re.compile(r"^(?P<kind>[a-z][a-z0-9-]*)-v(?P<version>[1-9][0-9]*)-(?P<digest>[0-9a-f]{64})$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:/")


def _json_value(value: Any) -> Any:
    """Return the restricted JSON value used by the NFC-equivalence helper."""
    if isinstance(value, BaseModel):
        return _json_value(value.model_dump(mode="json"))
    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value))
    if isinstance(value, Enum):
        return _json_value(value.value)
    if isinstance(value, PurePath):
        return unicodedata.normalize("NFC", value.as_posix())
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("identity payload cannot contain NaN or infinity")
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("identity payload object keys must be strings")
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in normalized:
                raise ValueError(f"identity payload has duplicate normalized key: {normalized_key!r}")
            normalized[normalized_key] = _json_value(item)
        return normalized
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    raise TypeError(f"unsupported identity payload type: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize a restricted payload with NFC string equivalence.

    This compatibility helper rewrites all string values and object keys.
    Durable identities, configuration digests, and persisted artifacts use
    :func:`lossless_json_bytes` instead. Callers normalize only locator fields
    whose contracts explicitly define NFC equivalence.
    """
    return json.dumps(
        _json_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _lossless_json_value(value: Any) -> Any:
    """Return a restricted JSON value without rewriting any string content."""
    if isinstance(value, BaseModel):
        return _lossless_json_value(value.model_dump(mode="json"))
    if is_dataclass(value) and not isinstance(value, type):
        return _lossless_json_value(asdict(value))
    if isinstance(value, Enum):
        return _lossless_json_value(value.value)
    if isinstance(value, PurePath):
        return value.as_posix()
    if isinstance(value, str):
        return value
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("persisted JSON cannot contain NaN or infinity")
        return value
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("persisted JSON object keys must be strings")
            result[key] = _lossless_json_value(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_lossless_json_value(item) for item in value]
    raise TypeError(f"unsupported persisted JSON type: {type(value).__name__}")


def lossless_json_bytes(value: Any) -> bytes:
    """Serialize deterministic UTF-8 JSON while preserving exact strings."""
    return json.dumps(
        _lossless_json_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_digest(data: bytes | bytearray | memoryview | str) -> str:
    """Return the lowercase SHA-256 hex digest of exact bytes or UTF-8 text."""
    if isinstance(data, str):
        payload = data.encode("utf-8")
    elif isinstance(data, (bytes, bytearray, memoryview)):
        payload = bytes(data)
    else:
        raise TypeError("sha256_digest accepts bytes-like data or str")
    return hashlib.sha256(payload).hexdigest()


def canonical_digest(value: Any) -> str:
    """Return a SHA-256 digest of exact-string, deterministically sorted JSON.

    Durable semantic digests preserve Unicode string and object-key sequences.
    Callers normalize only fields whose contracts explicitly define NFC
    equivalence, such as logical source locators, before constructing the
    payload.
    """
    return sha256_digest(lossless_json_bytes(value))


def derive_id(kind: str, payload: Any, *, version: int = 1) -> str:
    """Derive a full-width, domain-separated ID from exact-string JSON.

    The payload preserves Unicode string and object-key sequences. Explicit
    locator fields must be normalized by their field-specific constructors.
    """
    if not _ID_KIND.fullmatch(kind):
        raise ValueError(f"invalid identity kind: {kind!r}")
    if version < 1:
        raise ValueError("identity version must be positive")
    domain = b"veriformis-id\0" + kind.encode("ascii") + b"\0v" + str(version).encode("ascii") + b"\0"
    digest = sha256_digest(domain + lossless_json_bytes(payload))
    return f"{kind}-v{version}-{digest}"


def validate_id(value: str, *, kind: str | None = None) -> str:
    """Validate and return a persisted identity."""
    match = _PERSISTED_ID.fullmatch(value)
    if match is None:
        raise ValueError(f"invalid persisted identity: {value!r}")
    if kind is not None and match.group("kind") != kind:
        raise ValueError(f"expected {kind!r} identity, got {match.group('kind')!r}")
    return value


def validate_sha256(value: str) -> str:
    """Validate and return a lowercase full-width SHA-256 digest."""
    if not _SHA256.fullmatch(value):
        raise ValueError("SHA-256 digest must contain exactly 64 lowercase hex characters")
    return value


def normalize_logical_path(path: str | PurePath) -> str:
    """Normalize a stable workspace-relative source locator.

    Logical paths are portable NFC-normalized POSIX paths. Absolute paths and
    aliases such as ``.`` or ``..`` are rejected rather than silently resolved.
    """
    if not isinstance(path, (str, PurePath)):
        raise InvalidSourceLocatorError(
            f"logical source path must be a string or pure path, got {type(path).__name__}"
        )
    raw = str(path)
    if "\\" in raw:
        raise InvalidSourceLocatorError(
            f"logical source paths must use POSIX separators: {raw!r}"
        )
    text = unicodedata.normalize("NFC", raw)
    if not text or "\x00" in text or text.startswith("/") or _WINDOWS_DRIVE.match(text):
        raise InvalidSourceLocatorError(f"invalid logical source path: {text!r}")
    parts = text.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise InvalidSourceLocatorError(f"invalid logical source path: {text!r}")
    return "/".join(parts)


def derive_source_id(logical_path: str | PurePath, raw_sha256: str) -> str:
    """Derive a source-instance ID from stable location and exact raw bytes."""
    return derive_id(
        "src",
        {
            "logical_path": normalize_logical_path(logical_path),
            "raw_sha256": validate_sha256(raw_sha256),
        },
    )


def derive_artifact_id(
    *,
    kind: str,
    content_sha256: str,
    source_ids: tuple[str, ...] | list[str] = (),
    producer_id: str,
    producer_version: str,
    config_digest: str,
) -> str:
    """Derive an immutable artifact ID from content, scope, and producer."""
    normalized_sources = tuple(sorted(validate_id(source_id, kind="src") for source_id in source_ids))
    if len(normalized_sources) != len(set(normalized_sources)):
        raise ValueError("artifact source_ids contain duplicates")
    return derive_id(
        "art",
        {
            "kind": kind,
            "content_sha256": validate_sha256(content_sha256),
            "source_ids": normalized_sources,
            "producer_id": producer_id,
            "producer_version": producer_version,
            "config_digest": validate_sha256(config_digest),
        },
    )
