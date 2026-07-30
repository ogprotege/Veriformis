"""Exact JSON helpers for persisted dataset-construction artifacts."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel

from veriformis.errors import DuplicateIdentityError
from veriformis.identity import lossless_json_bytes


def reject_floats(value: Any, *, path: str = "$") -> None:
    """Reject floating-point values without rewriting any strings."""
    if isinstance(value, float):
        raise ValueError(f"dataset JSON contains a float at {path}")
    if isinstance(value, BaseModel):
        reject_floats(value.model_dump(mode="json"), path=path)
        return
    if is_dataclass(value) and not isinstance(value, type):
        reject_floats(asdict(value), path=path)
        return
    if isinstance(value, Enum):
        reject_floats(value.value, path=path)
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            reject_floats(item, path=f"{path}[{key!r}]")
        return
    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray, memoryview),
    ):
        for index, item in enumerate(value):
            reject_floats(item, path=f"{path}[{index}]")


def canonical_json_object_from_bytes(data: bytes, *, label: str) -> dict[str, Any]:
    """Load one canonical UTF-8 JSON object with exact string preservation."""
    if not isinstance(data, bytes):
        raise ValueError(f"{label} must be loaded from exact bytes")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise DuplicateIdentityError(
                    f"{label} JSON contains duplicate key {key!r}"
                )
            value[key] = item
        return value

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number {value!r}")

    def reject_float(value: str) -> None:
        raise ValueError(f"floating-point JSON number {value!r}")

    decoded = data.decode("utf-8")
    value = json.loads(
        decoded,
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
        parse_float=reject_float,
    )
    if not isinstance(value, dict):
        raise ValueError(f"{label} JSON root must be an object")
    reject_floats(value)
    if lossless_json_bytes(value) != data:
        raise ValueError(f"{label} JSON bytes are not canonical")
    return value


__all__ = ["canonical_json_object_from_bytes", "reject_floats"]
