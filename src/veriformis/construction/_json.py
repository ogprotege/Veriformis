"""Construction-specific exact JSON validation helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel


def reject_floats(value: Any, *, path: str = "$") -> None:
    """Reject floating-point values anywhere in a construction payload.

    Construction identities deliberately omit floating-point canonicalization.
    Callers must choose an exact integer or string representation instead.
    """
    if isinstance(value, float):
        raise ValueError(f"construction JSON contains a float at {path}")
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
        value, (str, bytes, bytearray, memoryview)
    ):
        for index, item in enumerate(value):
            reject_floats(item, path=f"{path}[{index}]")


__all__ = ["reject_floats"]
