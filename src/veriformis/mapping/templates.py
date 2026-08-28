"""Versioned mapping templates. Discovery data, not CLI or Swift constants."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any, Literal

from pydantic import field_validator, model_validator

from veriformis.errors import MappingError
from veriformis.identity import lossless_json_bytes, sha256_digest, validate_sha256
from veriformis.mapping.models import FieldMapping, MappingPlan, _StrictModel

TEMPLATE_DATA_NAME = "templates-v1.json"
TEMPLATE_SCHEMA = "veriformis.mapping-template/v1"
TEMPLATE_DISCOVERY_SCHEMA = "veriformis.mapping-template-discovery/v1"


class MappingTemplate(_StrictModel):
    schema_version: Literal["veriformis.mapping-template/v1"]
    template_id: str
    template_digest: str
    detector_id: str
    goal_id: str
    representation_id: str
    row_schema: Literal[
        "text",
        "prompt_completion",
        "instruction_output",
        "messages",
        "label-classification",
    ]
    container_kind: Literal["jsonl", "json", "csv"]
    membership_policy: Literal["replaced", "advisory", "authoritative"]
    plain_language: str
    field_mappings: tuple[dict[str, str], ...]

    @field_validator("field_mappings", mode="before")
    @classmethod
    def _mappings(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> MappingTemplate:
        if not self.template_id.strip() or not self.plain_language.strip():
            raise MappingError("mapping template fields must be non-empty")
        if not self.field_mappings:
            raise MappingError("mapping template requires field mappings")
        for item in self.field_mappings:
            if set(item) != {"source_path", "target_key"}:
                raise MappingError("mapping template field mappings are exact pairs")
        expected = sha256_digest(
            lossless_json_bytes(self.model_dump(mode="json", exclude={"template_digest"}))
        )
        validate_sha256(self.template_digest)
        if self.template_digest != expected:
            raise MappingError("mapping template digest mismatch")
        return self


class MappingTemplateCatalog(_StrictModel):
    schema_id: Literal["veriformis.mapping-template-discovery/v1"]
    contract_id: Literal["veriformis.mapping-template"]
    contract_version: Literal[1]
    templates: tuple[MappingTemplate, ...]

    @field_validator("templates", mode="before")
    @classmethod
    def _templates(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value


def _template_from_packaged(item: dict[str, Any]) -> MappingTemplate:
    body = {
        "schema_version": TEMPLATE_SCHEMA,
        "template_id": item["template_id"],
        "detector_id": item["detector_id"],
        "goal_id": item["goal_id"],
        "representation_id": item["representation_id"],
        "row_schema": item["row_schema"],
        "container_kind": item["container_kind"],
        "membership_policy": item["membership_policy"],
        "plain_language": item["plain_language"],
        "field_mappings": item["field_mappings"],
    }
    return MappingTemplate(
        template_digest=sha256_digest(lossless_json_bytes(body)),
        **body,
    )


@lru_cache(maxsize=1)
def _load_templates() -> tuple[str, MappingTemplateCatalog]:
    raw = (
        resources.files("veriformis.mapping")
        .joinpath(TEMPLATE_DATA_NAME)
        .read_text(encoding="utf-8")
    )
    payload = json.loads(raw)
    canonical = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if canonical != raw:
        raise MappingError("mapping template catalog is not canonical JSON")
    templates = tuple(_template_from_packaged(item) for item in payload["templates"])
    catalog = MappingTemplateCatalog(
        schema_id=payload["schema_id"],
        contract_id=payload["contract_id"],
        contract_version=payload["contract_version"],
        templates=templates,
    )
    return canonical, catalog


def mapping_template_catalog() -> MappingTemplateCatalog:
    return _load_templates()[1]


def mapping_template_catalog_json() -> str:
    catalog = mapping_template_catalog()
    return (
        json.dumps(catalog.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )


def mapping_plan_from_template(
    template: MappingTemplate,
    *,
    confirmation_digest: str,
    container_kind: str | None = None,
    membership_policy: str | None = None,
) -> MappingPlan:
    mappings = tuple(
        FieldMapping.create(
            source_path=item["source_path"],
            target_key=item["target_key"],
        )
        for item in template.field_mappings
    )
    return MappingPlan.create(
        goal_id=template.goal_id,
        representation_id=template.representation_id,
        row_schema=template.row_schema,
        container_kind=container_kind or template.container_kind,
        membership_policy=membership_policy or template.membership_policy,
        confirmation_digest=confirmation_digest,
        field_mappings=mappings,
    )
