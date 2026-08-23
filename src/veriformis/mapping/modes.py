"""Versioned compiler-path modes: document-source, dataset-row, and mixed."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from veriformis.contracts import (
    INPUT_MODE_CONTRACT_ID,
    INPUT_MODE_CONTRACT_VERSION,
    INPUT_MODE_SCHEMA_ID,
)
from veriformis.errors import InputModeError

MODE_DATA_NAME = "modes-v1.json"
DOCUMENT_SOURCE_MODE = "document-source"
DATASET_ROW_MODE = "dataset-row"
MIXED_MODE = "mixed"
INPUT_MODE_IDS: tuple[str, ...] = (
    DOCUMENT_SOURCE_MODE,
    DATASET_ROW_MODE,
    MIXED_MODE,
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class InputMode(_StrictModel):
    mode_id: Literal["document-source", "dataset-row", "mixed"]
    state: Literal["implemented", "planned"]
    executable: bool
    opens_in: str | None
    plain_language: str
    refusal: str | None

    @model_validator(mode="after")
    def _state_matches_execution(self) -> InputMode:
        if not self.plain_language.strip():
            raise InputModeError("input mode plain_language must be non-empty")
        if self.executable:
            if self.state != "implemented":
                raise InputModeError(
                    f"executable input mode {self.mode_id!r} must be implemented"
                )
            if self.opens_in is not None or self.refusal is not None:
                raise InputModeError(
                    f"executable input mode {self.mode_id!r} cannot name a later item"
                )
            return self
        if self.state != "planned":
            raise InputModeError(
                f"non-executable input mode {self.mode_id!r} must be planned"
            )
        if not self.opens_in or not self.refusal:
            raise InputModeError(
                f"non-executable input mode {self.mode_id!r} must name its opening item"
            )
        return self


class InputModeCatalog(_StrictModel):
    schema_id: Literal["veriformis.input-mode-discovery/v1"]
    contract_id: Literal["veriformis.input-mode"]
    contract_version: Literal[1]
    default_mode: Literal["document-source"]
    modes: tuple[InputMode, ...] = Field(min_length=3, max_length=3)

    @field_validator("modes", mode="before")
    @classmethod
    def _tuple_modes(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> InputModeCatalog:
        ids = tuple(mode.mode_id for mode in self.modes)
        if ids != INPUT_MODE_IDS:
            raise InputModeError(
                f"input mode catalog must list {INPUT_MODE_IDS!r} in order, not {ids!r}"
            )
        if self.schema_id != INPUT_MODE_SCHEMA_ID:
            raise InputModeError("input mode schema_id mismatch")
        if self.contract_id != INPUT_MODE_CONTRACT_ID:
            raise InputModeError("input mode contract_id mismatch")
        if self.contract_version != INPUT_MODE_CONTRACT_VERSION:
            raise InputModeError("input mode contract_version mismatch")
        return self


def _packaged() -> tuple[str, InputModeCatalog]:
    return _load_packaged()


@lru_cache(maxsize=1)
def _load_packaged() -> tuple[str, InputModeCatalog]:
    raw = resources.files("veriformis.mapping").joinpath(MODE_DATA_NAME).read_text(
        encoding="utf-8"
    )
    payload = json.loads(raw)
    canonical = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if canonical != raw:
        raise InputModeError("input mode catalog is not canonical JSON")
    return canonical, InputModeCatalog.model_validate(payload)


def input_mode_catalog() -> InputModeCatalog:
    return _packaged()[1]


def input_mode_catalog_json() -> str:
    return _packaged()[0]


def discover_modes() -> dict[str, Any]:
    return json.loads(input_mode_catalog_json())


def implemented_input_modes() -> tuple[str, ...]:
    return tuple(
        mode.mode_id for mode in input_mode_catalog().modes if mode.state == "implemented"
    )


def planned_input_modes() -> tuple[str, ...]:
    return tuple(
        mode.mode_id for mode in input_mode_catalog().modes if mode.state == "planned"
    )


def require_executable_mode(mode: str | None) -> str:
    """Return the executable compiler path, defaulting to document-source."""
    selected = DOCUMENT_SOURCE_MODE if mode in (None, "") else mode
    catalog = input_mode_catalog()
    for item in catalog.modes:
        if item.mode_id != selected:
            continue
        if item.executable:
            return item.mode_id
        raise InputModeError(item.refusal or f"input mode {selected!r} is not executable")
    raise InputModeError(
        f"unknown input mode {selected!r}; expected one of {list(INPUT_MODE_IDS)!r}"
    )


IMPLEMENTED_INPUT_MODES = implemented_input_modes()
PLANNED_INPUT_MODES = planned_input_modes()
