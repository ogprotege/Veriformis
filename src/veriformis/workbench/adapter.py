"""Workbench adapter contract v1. Pins only; no screen execute."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from veriformis.contracts import (
    WORKBENCH_ADAPTER_CONTRACT_ID,
    WORKBENCH_ADAPTER_CONTRACT_VERSION,
    WORKBENCH_ADAPTER_SCHEMA_ID,
)
from veriformis.errors import WorkbenchAdapterError
from veriformis.identity import derive_id, validate_id


WRAP_COMMANDS: tuple[str, ...] = (
    "chunk",
    "clean",
    "collect",
    "construct",
    "curate",
    "export-discover",
    "export-dry-run",
    "export-execute",
    "export-inspect",
    "export-verify",
    "format",
    "goal-preview",
    "goals",
    "map",
    "mapping-contracts",
    "mapping-detect",
    "mapping-preview",
    "mapping-rejections",
    "mapping-templates",
    "modes",
    "ocr-preview",
    "parse",
    "preflight",
    "presets",
    "review-export",
    "review-import",
    "review-submit",
    "seal",
    "split",
    "taxonomy",
    "validate",
    "verify",
)
WRAP_SURFACES: tuple[str, ...] = ("discover", "execute", "preview")
POLICY_OWNERS: tuple[str, ...] = ("pipeline-service",)
ADAPTER_KINDS: tuple[str, ...] = ("process-cli",)
CATALOG_SOURCES: tuple[str, ...] = ("shared-service",)
FAIL_CLOSED_REASONS: tuple[str, ...] = ("cancelled", "schema-invalid", "truncated")
REVIEW_POLICY_DEFAULTS: tuple[str, ...] = ("none",)
WORKBENCH_ADAPTER_LIMITATIONS: tuple[str, ...] = (
    "no-execute",
    "no-second-catalog",
    "no-swift-policy",
    "no-plugin-ui",
    "no-generator-ui",
    "no-invented-review-policy",
    "no-invented-trainer-policy",
    "no-invented-family-policy",
)

WrapCommand = Literal[
    "chunk",
    "clean",
    "collect",
    "construct",
    "curate",
    "export-discover",
    "export-dry-run",
    "export-execute",
    "export-inspect",
    "export-verify",
    "format",
    "goal-preview",
    "goals",
    "map",
    "mapping-contracts",
    "mapping-detect",
    "mapping-preview",
    "mapping-rejections",
    "mapping-templates",
    "modes",
    "ocr-preview",
    "parse",
    "preflight",
    "presets",
    "review-export",
    "review-import",
    "review-submit",
    "seal",
    "split",
    "taxonomy",
    "validate",
    "verify",
]
WrapSurface = Literal["discover", "execute", "preview"]
FailClosedReason = Literal["cancelled", "schema-invalid", "truncated"]

_TOKEN = re.compile(r"^[a-z][a-z0-9-]*$")
_SCHEMA_ID = re.compile(r"^veriformis\.[a-z][a-z0-9.-]*/v[1-9][0-9]*$")


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


def _tuple_str(value: Any) -> Any:
    return tuple(value) if isinstance(value, list) else value


def _require_schema_id(value: str, label: str) -> str:
    if not value or value.strip() != value or _SCHEMA_ID.fullmatch(value) is None:
        raise WorkbenchAdapterError(
            f"{label} must be a versioned veriformis schema id"
        )
    return value


class WorkbenchAdapter(_StrictModel):
    """One wrap pin. Loading a pin is not a screen execute."""

    adapter_id: str
    adapter_kind: str
    catalog_source: str
    command: WrapCommand
    contract_id: Literal["veriformis.workbench-adapter"]
    contract_version: Literal[1]
    fail_closed_on: tuple[FailClosedReason, ...]
    generation_allowed: bool
    may_invent_family_policy: bool
    may_invent_review_policy: bool
    may_invent_trainer_policy: bool
    plugin_install_allowed: bool
    policy_owner: str
    request_schema_id: str
    response_schema_id: str
    review_policy_default: str
    schema_id: Literal["veriformis.workbench-adapter/v1"]
    surface: WrapSurface

    @field_validator("fail_closed_on", mode="before")
    @classmethod
    def _tuple_fields(cls, value: Any) -> Any:
        return _tuple_str(value)

    @model_validator(mode="after")
    def _closed(self) -> WorkbenchAdapter:
        if self.contract_id != WORKBENCH_ADAPTER_CONTRACT_ID:
            raise WorkbenchAdapterError("workbench adapter contract_id mismatch")
        if self.contract_version != WORKBENCH_ADAPTER_CONTRACT_VERSION:
            raise WorkbenchAdapterError("workbench adapter contract_version mismatch")
        if self.schema_id != WORKBENCH_ADAPTER_SCHEMA_ID:
            raise WorkbenchAdapterError("workbench adapter schema_id mismatch")
        if self.command not in WRAP_COMMANDS:
            raise WorkbenchAdapterError(
                f"unknown workbench wrap command: {self.command!r}; "
                "admitted commands are " + ", ".join(WRAP_COMMANDS)
            )
        if self.surface not in WRAP_SURFACES:
            raise WorkbenchAdapterError(
                f"unknown workbench wrap surface: {self.surface!r}; "
                "admitted surfaces are " + ", ".join(WRAP_SURFACES)
            )
        if self.policy_owner != "pipeline-service":
            raise WorkbenchAdapterError(
                "workbench adapter policy_owner must be pipeline-service; "
                "ADR-0019 Decision A forbids a Swift policy engine"
            )
        if self.adapter_kind != "process-cli":
            raise WorkbenchAdapterError(
                "workbench adapter adapter_kind must be process-cli"
            )
        if self.catalog_source != "shared-service":
            raise WorkbenchAdapterError(
                "workbench adapter catalog_source must be shared-service; "
                "ADR-0019 Decision A forbids a second catalog"
            )
        if self.review_policy_default != "none":
            raise WorkbenchAdapterError(
                "workbench adapter review_policy_default must be none"
            )
        if self.generation_allowed is not False:
            raise WorkbenchAdapterError(
                "workbench-adapter/v1 cannot allow generation; "
                "ADR-0018 Decision A forbids a compile-path generator"
            )
        if self.plugin_install_allowed is not False:
            raise WorkbenchAdapterError(
                "workbench-adapter/v1 cannot allow plugin install; "
                "ADR-0017 Decision A forbids an untrusted loader"
            )
        if self.may_invent_review_policy is not False:
            raise WorkbenchAdapterError(
                "workbench adapter cannot invent review policy; "
                "ADR-0019 Decision A keeps default review_policy none"
            )
        if self.may_invent_trainer_policy is not False:
            raise WorkbenchAdapterError(
                "workbench adapter cannot invent trainer policy; "
                "ADR-0019 Decision A forbids a required trainer"
            )
        if self.may_invent_family_policy is not False:
            raise WorkbenchAdapterError(
                "workbench adapter cannot invent family policy; "
                "ADR-0019 Decision A forbids a Swift family catalog"
            )
        reasons = self.fail_closed_on
        if reasons != FAIL_CLOSED_REASONS:
            raise WorkbenchAdapterError(
                "workbench adapter fail_closed_on must be cancelled, "
                "schema-invalid, truncated"
            )
        _require_schema_id(self.request_schema_id, "request_schema_id")
        _require_schema_id(self.response_schema_id, "response_schema_id")
        validate_id(self.adapter_id, kind="wba")
        expected = derive_id(
            "wba",
            self.model_dump(mode="json", exclude={"adapter_id"}),
        )
        if self.adapter_id != expected:
            raise WorkbenchAdapterError("workbench adapter identity mismatch")
        return self


def create_workbench_adapter(
    *,
    command: str,
    surface: str,
    request_schema_id: str,
    response_schema_id: str,
    fail_closed_on: tuple[str, ...] = FAIL_CLOSED_REASONS,
    generation_allowed: bool = False,
    plugin_install_allowed: bool = False,
    may_invent_review_policy: bool = False,
    may_invent_trainer_policy: bool = False,
    may_invent_family_policy: bool = False,
    policy_owner: str = "pipeline-service",
    adapter_kind: str = "process-cli",
    catalog_source: str = "shared-service",
    review_policy_default: str = "none",
) -> WorkbenchAdapter:
    """Build one pin with a derived identity. This is not a screen execute."""
    payload = {
        "contract_id": WORKBENCH_ADAPTER_CONTRACT_ID,
        "contract_version": WORKBENCH_ADAPTER_CONTRACT_VERSION,
        "schema_id": WORKBENCH_ADAPTER_SCHEMA_ID,
        "command": command,
        "surface": surface,
        "request_schema_id": request_schema_id,
        "response_schema_id": response_schema_id,
        "policy_owner": policy_owner,
        "adapter_kind": adapter_kind,
        "catalog_source": catalog_source,
        "fail_closed_on": list(fail_closed_on),
        "generation_allowed": generation_allowed,
        "plugin_install_allowed": plugin_install_allowed,
        "may_invent_review_policy": may_invent_review_policy,
        "may_invent_trainer_policy": may_invent_trainer_policy,
        "may_invent_family_policy": may_invent_family_policy,
        "review_policy_default": review_policy_default,
    }
    return WorkbenchAdapter(
        adapter_id=derive_id("wba", payload),
        **payload,
    )


def _supported_contract_label() -> str:
    return (
        f"contract_id={WORKBENCH_ADAPTER_CONTRACT_ID!r} "
        f"contract_version={WORKBENCH_ADAPTER_CONTRACT_VERSION} "
        f"schema_id={WORKBENCH_ADAPTER_SCHEMA_ID!r}"
    )


def _require_known_contract(payload: dict[str, Any]) -> None:
    missing = [
        name
        for name in ("contract_id", "contract_version", "schema_id")
        if name not in payload
    ]
    if missing:
        raise WorkbenchAdapterError(
            "unknown workbench adapter contract version: requested missing "
            f"{', '.join(missing)}, supported {_supported_contract_label()}"
        )
    requested_id = payload["contract_id"]
    requested_version = payload["contract_version"]
    requested_schema = payload["schema_id"]
    if (
        requested_id != WORKBENCH_ADAPTER_CONTRACT_ID
        or requested_version != WORKBENCH_ADAPTER_CONTRACT_VERSION
        or requested_schema != WORKBENCH_ADAPTER_SCHEMA_ID
    ):
        raise WorkbenchAdapterError(
            "unknown workbench adapter contract version: requested "
            f"contract_id={requested_id!r} "
            f"contract_version={requested_version!r} "
            f"schema_id={requested_schema!r}, supported "
            f"{_supported_contract_label()}"
        )


def _require_known_command(payload: dict[str, Any]) -> None:
    if "command" not in payload:
        raise WorkbenchAdapterError("workbench adapter missing command")
    command = payload["command"]
    if not isinstance(command, str) or _TOKEN.fullmatch(command) is None:
        raise WorkbenchAdapterError(
            f"unknown workbench wrap command: {command!r}; "
            "admitted commands are " + ", ".join(WRAP_COMMANDS)
        )
    if command not in WRAP_COMMANDS:
        raise WorkbenchAdapterError(
            f"unknown workbench wrap command: {command!r}; "
            "admitted commands are " + ", ".join(WRAP_COMMANDS)
        )


def _adapter_error_from_validation(exc: ValidationError) -> WorkbenchAdapterError:
    for error in exc.errors():
        loc = ".".join(str(part) for part in error.get("loc", ()))
        error_type = error.get("type")
        if error_type == "extra_forbidden":
            return WorkbenchAdapterError(
                f"workbench adapter contains unknown field {loc}"
            )
        if error_type == "missing":
            return WorkbenchAdapterError(
                f"workbench adapter missing {loc or 'required field'}"
            )
        if loc == "command":
            return WorkbenchAdapterError(
                f"unknown workbench wrap command: {error.get('input')!r}; "
                "admitted commands are " + ", ".join(WRAP_COMMANDS)
            )
        if loc == "surface":
            return WorkbenchAdapterError(
                f"unknown workbench wrap surface: {error.get('input')!r}; "
                "admitted surfaces are " + ", ".join(WRAP_SURFACES)
            )
        if loc in {"contract_version", "contract_id", "schema_id"}:
            return WorkbenchAdapterError(
                "unknown workbench adapter contract version: requested "
                f"{error.get('input')!r}, supported "
                f"{_supported_contract_label()}"
            )
    return WorkbenchAdapterError("workbench adapter is invalid")


def load_workbench_adapter(payload: object) -> WorkbenchAdapter:
    """Load one pin. Unknown commands, versions, and fields fail closed."""
    if not isinstance(payload, dict):
        raise WorkbenchAdapterError("workbench adapter must be an object")
    _require_known_contract(payload)
    _require_known_command(payload)
    if "surface" not in payload:
        raise WorkbenchAdapterError("workbench adapter missing surface")
    if payload["surface"] not in WRAP_SURFACES:
        raise WorkbenchAdapterError(
            f"unknown workbench wrap surface: {payload['surface']!r}; "
            "admitted surfaces are " + ", ".join(WRAP_SURFACES)
        )
    try:
        return WorkbenchAdapter.model_validate(payload)
    except WorkbenchAdapterError:
        raise
    except ValidationError as exc:
        raise _adapter_error_from_validation(exc) from exc
