"""Apply a confirmed mapping plan to captured JSONL objects."""

from __future__ import annotations

import json
from typing import Any

from veriformis.datasets.serialization import _payload_contract
from veriformis.errors import MappingError
from veriformis.identity import lossless_json_bytes, sha256_digest
from veriformis.mapping.capture import CapturedRow, JsonlCapture
from veriformis.mapping.models import (
    ROW_SCHEMA_PAYLOAD_KEYS,
    FieldMapping,
    ImportedField,
    ImportedRecord,
    MappedValueEvidence,
    MappingPlan,
)
from veriformis.mapping.result import MappingRecipe


def resolve_json_pointer(document: Any, pointer: str) -> Any:
    """Resolve a JSON pointer or a bare object key against one captured row."""
    if not pointer or not pointer.strip():
        raise MappingError("mapping source_path must be a non-empty JSON pointer")
    normalized = pointer if pointer.startswith("/") else f"/{pointer}"
    current = document
    for raw_token in normalized.split("/")[1:]:
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if token not in current:
                raise MappingError(f"missing source path {pointer!r}")
            current = current[token]
            continue
        if isinstance(current, list):
            try:
                index = int(token)
            except ValueError as exc:
                raise MappingError(
                    f"source path {pointer!r} indexes a list with a non-integer"
                ) from exc
            if index < 0 or index >= len(current):
                raise MappingError(f"missing source path {pointer!r}")
            current = current[index]
            continue
        raise MappingError(f"source path {pointer!r} does not name a value")
    return current


def execute_mapping(
    plan: MappingPlan,
    capture: JsonlCapture,
    *,
    source_id: str,
    recipe: MappingRecipe,
) -> tuple[ImportedRecord, ...]:
    """Map every captured object under one confirmed plan.

    Extra unmapped object keys, missing required keys, empty required strings,
    and invalid messages shapes refuse that row. A file with no accepted rows
    still fails closed. Replay from the same bytes and plan reconstructs the
    same imported-record identities.
    """
    mapped, _rejected = execute_mapping_rows(
        plan,
        capture,
        source_id=source_id,
        recipe=recipe,
    )
    return mapped


def execute_mapping_rows(
    plan: MappingPlan,
    capture: JsonlCapture,
    *,
    source_id: str,
    recipe: MappingRecipe,
) -> tuple[tuple[ImportedRecord, ...], tuple[Any, ...]]:
    """Map each captured object independently.

    Accepted rows are returned. Rejected rows become mapping-rejection records
    instead of failing the whole file. Zero accepted rows still fail closed.
    """
    from veriformis.mapping.reject import rejection_from_error

    if plan.mapping_plan_id != recipe.mapping_plan_id:
        raise MappingError("mapping recipe names another mapping plan")
    if plan.row_schema != recipe.row_schema:
        raise MappingError("mapping recipe row schema does not match the plan")
    if source_id not in recipe.source_ids:
        raise MappingError("mapping recipe does not include this source")
    if capture.row_source.container_kind != plan.container_kind:
        raise MappingError(
            f"captured container {capture.row_source.container_kind!r} does not "
            f"match plan container {plan.container_kind!r}"
        )
    mapped: list[ImportedRecord] = []
    rejected: list[Any] = []
    last_error: MappingError | None = None
    for record in capture.records:
        try:
            mapped.append(
                _map_one(
                    plan,
                    record,
                    source_id=source_id,
                    recipe=recipe,
                )
            )
        except MappingError as exc:
            last_error = exc
            rejected.append(
                rejection_from_error(
                    record=record,
                    logical_path=capture.row_source.logical_path,
                    mapping_plan_id=plan.mapping_plan_id,
                    message=exc.message,
                )
            )
    if not mapped:
        if last_error is not None:
            raise last_error
        raise MappingError("mapping produced no records")
    return tuple(mapped), tuple(rejected)


def replay_mapping(
    plan: MappingPlan,
    capture: JsonlCapture,
    *,
    source_id: str,
    recipe: MappingRecipe,
    records: tuple[ImportedRecord, ...],
) -> tuple[ImportedRecord, ...]:
    """Re-execute a mapping and require byte-identical imported records."""
    replayed = execute_mapping(
        plan,
        capture,
        source_id=source_id,
        recipe=recipe,
    )
    if replayed != records:
        raise MappingError("imported records do not match mapping replay")
    return replayed


def _map_one(
    plan: MappingPlan,
    record: CapturedRow,
    *,
    source_id: str,
    recipe: MappingRecipe,
) -> ImportedRecord:
    mapped_keys = {_pointer_head(item.source_path) for item in plan.field_mappings}
    ignored = {"partition"} if plan.membership_policy != "replaced" else set()
    extra = sorted(set(record.payload) - mapped_keys - ignored)
    if extra:
        raise MappingError(
            f"row {record.row_index} has unmapped keys {extra!r}; v1 mapping refuses "
            "unmapped fields"
        )
    fields: list[ImportedField] = []
    for mapping in plan.field_mappings:
        fields.append(
            _map_field(
                plan,
                mapping,
                record,
                source_id=source_id,
            )
        )
    expected = ROW_SCHEMA_PAYLOAD_KEYS[plan.row_schema]
    names = tuple(field.name for field in fields)
    if names != expected:
        raise MappingError(
            f"mapped fields {names!r} do not match {plan.row_schema!r} keys {expected!r}"
        )
    payload = _payload_from_fields(plan.row_schema, fields)
    _payload_contract(plan.row_schema, payload)
    partition_hint = _partition_hint(plan, record.payload, row_index=record.row_index)
    return ImportedRecord.create(
        source_id=source_id,
        row_index=record.row_index,
        mapping_plan_id=plan.mapping_plan_id,
        goal_id=plan.goal_id,
        recipe_id=recipe.recipe_id,
        objective_id=recipe.objective_id,
        fields=tuple(fields),
        partition_hint=partition_hint,
    )


def _partition_hint(plan: MappingPlan, payload: dict[str, Any], *, row_index: int) -> str | None:
    if plan.membership_policy == "replaced":
        return None
    value = payload.get("partition")
    if value not in {"train", "evaluation"}:
        raise MappingError(
            f"row {row_index} membership policy {plan.membership_policy!r} requires "
            "partition train or evaluation"
        )
    return value


def _map_field(
    plan: MappingPlan,
    mapping: FieldMapping,
    record: CapturedRow,
    *,
    source_id: str,
) -> ImportedField:
    try:
        original = resolve_json_pointer(record.payload, mapping.source_path)
    except MappingError as exc:
        raise MappingError(
            f"row {record.row_index} {exc.message}"
        ) from exc
    value, original_digest = _normalized_field_value(
        plan.row_schema,
        mapping.target_key,
        original,
        row_index=record.row_index,
    )
    output_digest = sha256_digest(value)
    evidence = MappedValueEvidence.create(
        source_id=source_id,
        row_index=record.row_index,
        field_path=_canonical_pointer(mapping.source_path),
        original_value_sha256=original_digest,
        mapping_rule_id=mapping.mapping_rule_id,
        output_sha256=output_digest,
    )
    return ImportedField(name=mapping.target_key, value=value, evidence=evidence)


def _normalized_field_value(
    row_schema: str,
    target_key: str,
    original: Any,
    *,
    row_index: int,
) -> tuple[str, str]:
    if row_schema == "messages" and target_key == "messages":
        messages = _require_two_turn_messages(original, row_index=row_index)
        encoded = lossless_json_bytes(messages).decode("utf-8")
        return encoded, sha256_digest(lossless_json_bytes(original))
    if row_schema == "tool-call-conversation" and target_key == "turns":
        from veriformis.families.tool_call import normalize_tool_turns

        try:
            turns = normalize_tool_turns(original)
        except ValueError as exc:
            raise MappingError(f"row {row_index} {exc}") from exc
        encoded = lossless_json_bytes(turns).decode("utf-8")
        return encoded, sha256_digest(lossless_json_bytes(original))
    if row_schema == "stepwise-trace" and target_key == "steps":
        from veriformis.families.stepwise import normalize_steps

        try:
            steps = normalize_steps(original)
        except ValueError as exc:
            raise MappingError(f"row {row_index} {exc}") from exc
        encoded = lossless_json_bytes(steps).decode("utf-8")
        return encoded, sha256_digest(lossless_json_bytes(original))
    if not isinstance(original, str):
        raise MappingError(
            f"row {row_index} field {target_key!r} must be a string; coercion is refused"
        )
    if original == "":
        raise MappingError(
            f"row {row_index} field {target_key!r} is an empty string"
        )
    return original, sha256_digest(original)


def _require_two_turn_messages(value: Any, *, row_index: int) -> list[dict[str, str]]:
    if not isinstance(value, list) or len(value) != 2:
        raise MappingError(
            f"row {row_index} messages must be exactly two user/assistant turns"
        )
    expected_roles = ("user", "assistant")
    normalized: list[dict[str, str]] = []
    for index, (turn, role) in enumerate(zip(value, expected_roles)):
        if not isinstance(turn, dict) or set(turn) != {"role", "content"}:
            raise MappingError(f"row {row_index} messages turn {index} has an invalid shape")
        if turn["role"] != role:
            raise MappingError(
                f"row {row_index} messages turn {index} must have role {role!r}"
            )
        content = turn["content"]
        if not isinstance(content, str) or content == "":
            raise MappingError(
                f"row {row_index} messages turn {index} content must be a non-empty string"
            )
        normalized.append({"role": role, "content": content})
    return normalized


def _payload_from_fields(
    row_schema: str,
    fields: list[ImportedField],
) -> dict[str, Any]:
    values = {field.name: field.value for field in fields}
    if row_schema == "messages":
        return {"messages": json.loads(values["messages"])}
    if row_schema == "tool-call-conversation":
        return {
            "conversation_id": values["conversation_id"],
            "turns": json.loads(values["turns"]),
        }
    if row_schema == "stepwise-trace":
        return {
            "prompt": values["prompt"],
            "steps": json.loads(values["steps"]),
        }
    return dict(values)


def _pointer_head(source_path: str) -> str:
    normalized = source_path if source_path.startswith("/") else f"/{source_path}"
    head = normalized.split("/")[1].replace("~1", "/").replace("~0", "~")
    if not head:
        raise MappingError(f"source path {source_path!r} does not name an object key")
    return head


def _canonical_pointer(source_path: str) -> str:
    return source_path if source_path.startswith("/") else f"/{source_path}"
