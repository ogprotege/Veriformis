"""Internal extension protocol v1. Declarations only; no loader."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from veriformis.contracts import (
    DETERMINISM_PROFILE,
    EXTENSION_PROTOCOL_CONTRACT_ID,
    EXTENSION_PROTOCOL_CONTRACT_VERSION,
    EXTENSION_PROTOCOL_SCHEMA_ID,
)
from veriformis.errors import ExtensionProtocolError
from veriformis.identity import derive_id, validate_id


EXTENSION_KINDS: tuple[str, ...] = (
    "source-parser",
    "row-mapper",
    "deterministic-constructor",
    "quality-check",
    "container-exporter",
    "consumer-profile",
)
EXTENSION_ORIGINS: tuple[str, ...] = ("builtin", "third_party")
EXTENSION_LIFECYCLES: tuple[str, ...] = (
    "experimental",
    "supported",
    "deprecated",
    "removed",
    "migrated",
)
PROTOCOL_LIMITATIONS: tuple[str, ...] = (
    "internal-only",
    "no-loader",
    "no-public-plugin-api",
    "no-in-process-project-plugins",
    "no-mac-plugin-ui",
    "no-new-families",
    "taxonomy-is-not-the-registry",
)

ExtensionKind = Literal[
    "container-exporter",
    "consumer-profile",
    "deterministic-constructor",
    "quality-check",
    "row-mapper",
    "source-parser",
]
ExtensionOrigin = Literal["builtin", "third_party"]
ExtensionLifecycle = Literal[
    "deprecated",
    "experimental",
    "migrated",
    "removed",
    "supported",
]

_TOKEN = re.compile(r"^[a-z][a-z0-9-]*$")


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


def _tuple_str(value: Any) -> Any:
    return tuple(value) if isinstance(value, list) else value


def _require_token(value: str, label: str) -> str:
    if not value or value.strip() != value or _TOKEN.fullmatch(value) is None:
        raise ExtensionProtocolError(f"{label} must be a lowercase hyphenated token")
    return value


def _require_sorted_tokens(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    for item in values:
        _require_token(item, label)
    if values != tuple(sorted(set(values))):
        raise ExtensionProtocolError(f"{label} must be unique and sorted")
    return values


class DeterministicRequirements(_StrictModel):
    llm_generation: bool
    network: bool
    offline: bool
    profile: str

    @model_validator(mode="after")
    def _closed(self) -> DeterministicRequirements:
        if self.llm_generation is not False:
            raise ExtensionProtocolError(
                "extension declarations cannot use LLM generation"
            )
        if self.network is not False:
            raise ExtensionProtocolError(
                "extension declarations cannot require network"
            )
        if self.offline is not True:
            raise ExtensionProtocolError("extension declarations must be offline")
        if self.profile != DETERMINISM_PROFILE:
            raise ExtensionProtocolError(
                "extension deterministic profile must be "
                f"{DETERMINISM_PROFILE}"
            )
        return self


OFFLINE_DETERMINISTIC_REQUIREMENTS = DeterministicRequirements(
    llm_generation=False,
    network=False,
    offline=True,
    profile=DETERMINISM_PROFILE,
)


class DiscoveryMetadata(_StrictModel):
    consumer_id: str | None
    selector: str
    title: str

    @model_validator(mode="after")
    def _closed(self) -> DiscoveryMetadata:
        _require_token(self.selector, "discovery selector")
        if self.consumer_id is not None:
            _require_token(self.consumer_id, "discovery consumer_id")
        if not self.title or self.title.strip() != self.title:
            raise ExtensionProtocolError(
                "discovery title must be a non-empty exact string"
            )
        return self


class CapabilityDeclaration(_StrictModel):
    contract_id: str
    contract_version: int
    declaration_id: str
    diagnostic_ids: tuple[str, ...]
    discovery: DiscoveryMetadata
    extra: str | None
    fixture_ids: tuple[str, ...]
    kind: ExtensionKind
    lifecycle: ExtensionLifecycle
    origin: ExtensionOrigin
    requirements: DeterministicRequirements
    schema_id: str

    @field_validator("diagnostic_ids", "fixture_ids", mode="before")
    @classmethod
    def _tuples(cls, value: Any) -> Any:
        return _tuple_str(value)

    @model_validator(mode="after")
    def _closed(self) -> CapabilityDeclaration:
        if self.contract_id != EXTENSION_PROTOCOL_CONTRACT_ID:
            raise ExtensionProtocolError(
                "unknown extension contract version: requested "
                f"contract_id={self.contract_id!r}, supported "
                f"contract_id={EXTENSION_PROTOCOL_CONTRACT_ID!r} "
                f"contract_version={EXTENSION_PROTOCOL_CONTRACT_VERSION} "
                f"schema_id={EXTENSION_PROTOCOL_SCHEMA_ID}"
            )
        if self.contract_version != EXTENSION_PROTOCOL_CONTRACT_VERSION:
            raise ExtensionProtocolError(
                "unknown extension contract version: requested "
                f"{self.contract_version}, supported "
                f"{EXTENSION_PROTOCOL_CONTRACT_VERSION} "
                f"({EXTENSION_PROTOCOL_SCHEMA_ID})"
            )
        if self.schema_id != EXTENSION_PROTOCOL_SCHEMA_ID:
            raise ExtensionProtocolError(
                "unknown extension contract version: requested "
                f"schema_id={self.schema_id!r}, supported "
                f"{EXTENSION_PROTOCOL_SCHEMA_ID}"
            )
        if self.kind not in EXTENSION_KINDS:
            raise ExtensionProtocolError(
                f"unknown extension kind: {self.kind!r}; admitted kinds are "
                + ", ".join(EXTENSION_KINDS)
            )
        if self.origin not in EXTENSION_ORIGINS:
            raise ExtensionProtocolError(
                f"unknown extension origin: {self.origin!r}; admitted origins are "
                + ", ".join(EXTENSION_ORIGINS)
            )
        if self.lifecycle not in EXTENSION_LIFECYCLES:
            raise ExtensionProtocolError(
                f"unknown extension lifecycle: {self.lifecycle!r}; "
                "admitted lifecycles are " + ", ".join(EXTENSION_LIFECYCLES)
            )
        if self.extra is not None:
            _require_token(self.extra, "extra")
        _require_sorted_tokens(self.diagnostic_ids, "diagnostic_ids")
        _require_sorted_tokens(self.fixture_ids, "fixture_ids")
        if self.kind == "consumer-profile":
            if self.discovery.consumer_id is None:
                raise ExtensionProtocolError(
                    "consumer-profile declaration requires discovery.consumer_id"
                )
        elif self.discovery.consumer_id is not None:
            raise ExtensionProtocolError(
                "only consumer-profile declarations may set discovery.consumer_id"
            )
        try:
            validate_id(self.declaration_id, kind="exd")
        except ValueError as exc:
            raise ExtensionProtocolError(
                "extension declaration identity mismatch"
            ) from exc
        expected = derive_id(
            "exd",
            self.model_dump(mode="json", exclude={"declaration_id"}),
        )
        if self.declaration_id != expected:
            raise ExtensionProtocolError("extension declaration identity mismatch")
        return self


def create_capability_declaration(
    *,
    kind: ExtensionKind,
    origin: ExtensionOrigin,
    lifecycle: ExtensionLifecycle,
    extra: str | None,
    selector: str,
    title: str,
    diagnostic_ids: tuple[str, ...] = (),
    fixture_ids: tuple[str, ...] = (),
    consumer_id: str | None = None,
    requirements: DeterministicRequirements | None = None,
) -> CapabilityDeclaration:
    """Build a closed declaration. This does not register or load code."""
    payload: dict[str, Any] = {
        "contract_id": EXTENSION_PROTOCOL_CONTRACT_ID,
        "contract_version": EXTENSION_PROTOCOL_CONTRACT_VERSION,
        "diagnostic_ids": diagnostic_ids,
        "discovery": DiscoveryMetadata(
            consumer_id=consumer_id,
            selector=selector,
            title=title,
        ),
        "extra": extra,
        "fixture_ids": fixture_ids,
        "kind": kind,
        "lifecycle": lifecycle,
        "origin": origin,
        "requirements": requirements or OFFLINE_DETERMINISTIC_REQUIREMENTS,
        "schema_id": EXTENSION_PROTOCOL_SCHEMA_ID,
    }
    return CapabilityDeclaration(
        declaration_id=derive_id("exd", payload),
        **payload,
    )


def _supported_contract_label() -> str:
    return (
        f"contract_id={EXTENSION_PROTOCOL_CONTRACT_ID!r} "
        f"contract_version={EXTENSION_PROTOCOL_CONTRACT_VERSION} "
        f"schema_id={EXTENSION_PROTOCOL_SCHEMA_ID!r}"
    )


def _require_known_contract(payload: dict[str, Any]) -> None:
    missing = [
        name
        for name in ("contract_id", "contract_version", "schema_id")
        if name not in payload
    ]
    if missing:
        raise ExtensionProtocolError(
            "unknown extension contract version: requested missing "
            f"{', '.join(missing)}, supported {_supported_contract_label()}"
        )
    requested_id = payload["contract_id"]
    requested_version = payload["contract_version"]
    requested_schema = payload["schema_id"]
    if (
        requested_id != EXTENSION_PROTOCOL_CONTRACT_ID
        or requested_version != EXTENSION_PROTOCOL_CONTRACT_VERSION
        or requested_schema != EXTENSION_PROTOCOL_SCHEMA_ID
    ):
        raise ExtensionProtocolError(
            "unknown extension contract version: requested "
            f"contract_id={requested_id!r} "
            f"contract_version={requested_version!r} "
            f"schema_id={requested_schema!r}, supported "
            f"{_supported_contract_label()}"
        )


def _require_closed_token(
    payload: dict[str, Any],
    field: str,
    admitted: tuple[str, ...],
    label: str,
) -> None:
    if field not in payload:
        raise ExtensionProtocolError(f"extension declaration missing {field}")
    value = payload[field]
    if value not in admitted:
        raise ExtensionProtocolError(
            f"unknown extension {label}: {value!r}; admitted {label}s are "
            + ", ".join(admitted)
        )


def _protocol_error_from_validation(exc: ValidationError) -> ExtensionProtocolError:
    for error in exc.errors():
        loc = ".".join(str(part) for part in error.get("loc", ()))
        error_type = error.get("type")
        if error_type == "extra_forbidden":
            return ExtensionProtocolError(
                f"extension declaration contains unknown field {loc}"
            )
        if error_type == "missing":
            return ExtensionProtocolError(
                f"extension declaration missing {loc or 'required field'}"
            )
        if loc == "kind":
            return ExtensionProtocolError(
                f"unknown extension kind: {error.get('input')!r}; "
                "admitted kinds are " + ", ".join(EXTENSION_KINDS)
            )
        if loc == "origin":
            return ExtensionProtocolError(
                f"unknown extension origin: {error.get('input')!r}; "
                "admitted origins are " + ", ".join(EXTENSION_ORIGINS)
            )
        if loc == "lifecycle":
            return ExtensionProtocolError(
                f"unknown extension lifecycle: {error.get('input')!r}; "
                "admitted lifecycles are " + ", ".join(EXTENSION_LIFECYCLES)
            )
        if loc in {"contract_version", "contract_id", "schema_id"}:
            return ExtensionProtocolError(
                "unknown extension contract version: requested "
                f"{error.get('input')!r}, supported "
                f"{_supported_contract_label()}"
            )
    return ExtensionProtocolError("extension declaration is invalid")


def load_capability_declaration(payload: object) -> CapabilityDeclaration:
    """Load one declaration. Unknown kinds, versions, and fields fail closed."""
    if not isinstance(payload, dict):
        raise ExtensionProtocolError("extension declaration must be an object")
    _require_known_contract(payload)
    _require_closed_token(payload, "kind", EXTENSION_KINDS, "kind")
    _require_closed_token(payload, "origin", EXTENSION_ORIGINS, "origin")
    _require_closed_token(payload, "lifecycle", EXTENSION_LIFECYCLES, "lifecycle")
    try:
        return CapabilityDeclaration.model_validate(payload)
    except ExtensionProtocolError:
        raise
    except ValidationError as exc:
        raise _protocol_error_from_validation(exc) from exc
