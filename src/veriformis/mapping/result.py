"""Mapping recipe and mapping-result identities for dataset-row workspaces."""

from __future__ import annotations

from collections.abc import Mapping as MappingABC
from typing import Any, Literal

from pydantic import field_validator, model_validator

from veriformis.errors import MappingError
from veriformis.goals import goal_catalog
from veriformis.goals.catalog import goal_catalog_json
from veriformis.identity import derive_id, sha256_digest, validate_id, validate_sha256
from veriformis.mapping.models import (
    ADMITTED_CONTAINERS,
    ROW_SCHEMA_PAYLOAD_KEYS,
    ContainerKind,
    ImportedRecord,
    MappingPlan,
    RowSchema,
    _StrictModel,
)

ROW_JSONL_PARSER_ID = "row-jsonl"
ROW_JSON_PARSER_ID = "row-json"
ROW_CSV_PARSER_ID = "row-csv"
ROW_JSONL_PARSER_VERSION = "1"
ROW_PARSER_VERSION = ROW_JSONL_PARSER_VERSION
_ROW_PARSER_IDS: dict[str, str] = {
    "jsonl": ROW_JSONL_PARSER_ID,
    "json": ROW_JSON_PARSER_ID,
    "csv": ROW_CSV_PARSER_ID,
}
ROW_PARSER_IDS: tuple[str, ...] = (
    ROW_JSONL_PARSER_ID,
    ROW_JSON_PARSER_ID,
    ROW_CSV_PARSER_ID,
)


def row_parser_id(container_kind: str) -> str:
    try:
        return _ROW_PARSER_IDS[container_kind]
    except KeyError as exc:
        raise MappingError(
            f"unsupported mapping container {container_kind!r}"
        ) from exc
MAPPING_STAGE_SCHEMA_ID = "veriformis.mapping-stage/v1"
MAPPING_RECIPE_SCHEMA = "veriformis.mapping-recipe/v1"
MAPPING_RESULT_SCHEMA = "veriformis.mapping-result/v1"


class MappingRecipe(_StrictModel):
    """Executable mapping settings. Not a DatasetRecipe and not construction."""

    schema_version: Literal["veriformis.mapping-recipe/v1"]
    recipe_id: str
    goal_id: str
    representation_id: str
    row_schema: RowSchema
    objective_id: str
    objective_kind: str
    mapping_plan_id: str
    mapping_rule_ids: tuple[str, ...]
    goal_catalog_sha256: str
    source_ids: tuple[str, ...]

    @field_validator("source_ids", "mapping_rule_ids", mode="before")
    @classmethod
    def _tuple_sources(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _identity(self) -> MappingRecipe:
        catalog = goal_catalog()
        try:
            goal = catalog.goal(self.goal_id)
        except Exception as exc:
            raise MappingError(f"unknown mapping goal {self.goal_id!r}") from exc
        if self.representation_id not in goal.compatible_representations:
            raise MappingError(
                f"representation {self.representation_id!r} is incompatible with "
                f"goal {self.goal_id!r}"
            )
        representation = catalog.representation(self.representation_id)
        if representation.row_schema != self.row_schema:
            raise MappingError(
                f"row schema {self.row_schema!r} does not match representation "
                f"{self.representation_id!r}"
            )
        if self.objective_kind != goal.objective:
            raise MappingError(
                f"mapping recipe objective {self.objective_kind!r} does not match "
                f"goal {self.goal_id!r}"
            )
        validate_id(self.mapping_plan_id, kind="mpl")
        validate_id(self.objective_id, kind="obj")
        validate_sha256(self.goal_catalog_sha256)
        expected_catalog = sha256_digest(goal_catalog_json())
        if self.goal_catalog_sha256 != expected_catalog:
            raise MappingError("mapping recipe goal catalog digest mismatch")
        if not self.mapping_rule_ids:
            raise MappingError("mapping recipe requires mapping-rule ids")
        if len(self.mapping_rule_ids) != len(set(self.mapping_rule_ids)):
            raise MappingError("mapping recipe mapping_rule_ids must be unique")
        for rule_id in self.mapping_rule_ids:
            validate_id(rule_id, kind="mrl")
        if self.mapping_rule_ids != tuple(sorted(self.mapping_rule_ids)):
            raise MappingError("mapping recipe mapping_rule_ids must be sorted")
        if not self.source_ids:
            raise MappingError("mapping recipe requires at least one source")
        if self.source_ids != tuple(sorted(set(self.source_ids))):
            raise MappingError("mapping recipe source_ids must be sorted and unique")
        for source_id in self.source_ids:
            validate_id(source_id, kind="src")
        expected = derive_id(
            "rcp",
            self.model_dump(mode="json", exclude={"recipe_id"}),
        )
        if self.recipe_id != expected:
            raise MappingError("mapping recipe identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        plan: MappingPlan,
        source_ids: tuple[str, ...] | list[str],
    ) -> MappingRecipe:
        catalog = goal_catalog()
        goal = catalog.goal(plan.goal_id)
        sources = tuple(sorted(set(source_ids)))
        objective_body = {
            "schema_version": "veriformis.mapping-objective/v1",
            "kind": goal.objective,
            "goal_id": plan.goal_id,
            "representation_id": plan.representation_id,
            "row_schema": plan.row_schema,
            "field_names": list(ROW_SCHEMA_PAYLOAD_KEYS[plan.row_schema]),
        }
        body = {
            "schema_version": MAPPING_RECIPE_SCHEMA,
            "goal_id": plan.goal_id,
            "representation_id": plan.representation_id,
            "row_schema": plan.row_schema,
            "objective_id": derive_id("obj", objective_body),
            "objective_kind": goal.objective,
            "mapping_plan_id": plan.mapping_plan_id,
            "mapping_rule_ids": sorted(
                item.mapping_rule_id for item in plan.field_mappings
            ),
            "goal_catalog_sha256": sha256_digest(goal_catalog_json()),
            "source_ids": list(sources),
        }
        return cls(recipe_id=derive_id("rcp", body), **body)


class MappingResult(_StrictModel):
    """Complete imported records for one mapping plan and source set."""

    schema_version: Literal["veriformis.mapping-result/v1"]
    result_id: str
    mapping_plan_id: str
    recipe_id: str
    objective_id: str
    row_schema: RowSchema
    container_kind: ContainerKind
    membership_policy: Literal["authoritative", "advisory", "replaced"]
    source_ids: tuple[str, ...]
    row_source_ids: tuple[str, ...]
    records: tuple[ImportedRecord, ...]

    @field_validator("source_ids", "row_source_ids", "records", mode="before")
    @classmethod
    def _tuple_seq(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _identity(self) -> MappingResult:
        validate_id(self.mapping_plan_id, kind="mpl")
        validate_id(self.recipe_id, kind="rcp")
        validate_id(self.objective_id, kind="obj")
        if self.container_kind not in ADMITTED_CONTAINERS:
            raise MappingError(
                f"unsupported mapping result container {self.container_kind!r}"
            )
        if not self.source_ids:
            raise MappingError("mapping result requires at least one source")
        if self.source_ids != tuple(sorted(set(self.source_ids))):
            raise MappingError("mapping result source_ids must be sorted and unique")
        for source_id in self.source_ids:
            validate_id(source_id, kind="src")
        if not self.row_source_ids:
            raise MappingError("mapping result requires at least one row source")
        if self.row_source_ids != tuple(sorted(set(self.row_source_ids))):
            raise MappingError(
                "mapping result row_source_ids must be sorted and unique"
            )
        for row_source_id in self.row_source_ids:
            validate_id(row_source_id, kind="rws")
        if not self.records:
            raise MappingError("mapping result requires at least one imported record")
        ids = tuple(record.record_id for record in self.records)
        if len(ids) != len(set(ids)):
            raise MappingError("mapping result contains duplicate imported records")
        ordered = tuple(sorted(self.records, key=lambda item: item.record_id))
        if self.records != ordered:
            raise MappingError("mapping result records must be ordered by record_id")
        expected_keys = ROW_SCHEMA_PAYLOAD_KEYS[self.row_schema]
        for record in self.records:
            if record.mapping_plan_id != self.mapping_plan_id:
                raise MappingError("imported record names another mapping plan")
            if record.recipe_id != self.recipe_id:
                raise MappingError("imported record names another mapping recipe")
            if record.objective_id != self.objective_id:
                raise MappingError("imported record names another objective")
            if record.source_id not in self.source_ids:
                raise MappingError("imported record names a source outside the result")
            names = tuple(field.name for field in record.fields)
            if names != expected_keys:
                raise MappingError(
                    f"imported record fields {names!r} do not match {self.row_schema!r}"
                )
        expected = derive_id(
            "imr",
            self.model_dump(mode="json", exclude={"result_id"}),
        )
        if self.result_id != expected:
            raise MappingError("mapping-result identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        plan: MappingPlan,
        recipe: MappingRecipe,
        row_source_ids: tuple[str, ...] | list[str],
        records: tuple[ImportedRecord, ...] | list[ImportedRecord],
    ) -> MappingResult:
        body = {
            "schema_version": MAPPING_RESULT_SCHEMA,
            "mapping_plan_id": plan.mapping_plan_id,
            "recipe_id": recipe.recipe_id,
            "objective_id": recipe.objective_id,
            "row_schema": plan.row_schema,
            "container_kind": plan.container_kind,
            "membership_policy": plan.membership_policy,
            "source_ids": list(recipe.source_ids),
            "row_source_ids": list(sorted(set(row_source_ids))),
            "records": [
                record.model_dump(mode="json")
                for record in sorted(records, key=lambda item: item.record_id)
            ],
        }
        return cls(result_id=derive_id("imr", body), **body)


def mapping_recipe_from_dict(value: MappingABC[str, Any]) -> MappingRecipe:
    return MappingRecipe.model_validate(dict(value))


def mapping_result_from_dict(value: MappingABC[str, Any]) -> MappingResult:
    return MappingResult.model_validate(dict(value))


def mapping_plan_from_dict(value: MappingABC[str, Any]) -> MappingPlan:
    return MappingPlan.model_validate(dict(value))
