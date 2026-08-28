"""Executable tool-call-conversations family. User-provided tool traces only."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from veriformis.errors import ConstructionError, SplitError
from veriformis.families.admission import FamilyAdmission, create_family_admission


TOOL_CALL_FAMILY_ID = "tool-call-conversations"
TOOL_CALL_OBJECTIVE = "tool_call"
TOOL_CALL_ROW_SCHEMA = "tool-call-conversation"
TOOL_CALL_LOSS_POLICY = "tool-trace-suffix"
TOOL_CALL_GOAL_ID = "use-provided-tool-traces"
TOOL_CALL_REPRESENTATION_ID = "conversation-and-tool-trace"
TOOL_CALL_CONTRACT_VERSION = 1
TOOL_CALL_PAYLOAD_KEYS: tuple[str, ...] = ("conversation_id", "turns")
_TURN_ROLES = {"assistant", "function", "tool", "user"}


class _DisjointSet:
    def __init__(self, size: int):
        self._parents = list(range(size))

    def find(self, item: int) -> int:
        root = item
        while self._parents[root] != root:
            root = self._parents[root]
        while self._parents[item] != root:
            self._parents[item], item = root, self._parents[item]
        return root

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        low, high = sorted((left_root, right_root))
        self._parents[high] = low


def tool_call_admission() -> FamilyAdmission:
    """Return the admitted pin. Loading it is not a mapping execute."""
    return create_family_admission(
        family_id=TOOL_CALL_FAMILY_ID,
        lifecycle="admitted",
        row_schema_ids=(TOOL_CALL_ROW_SCHEMA,),
        loss_policy_id=TOOL_CALL_LOSS_POLICY,
        evidence_kinds=("mapped_value",),
        leakage_grouping_keys=("conversation", "source"),
        review_hook_ids=("tool-trace-incomplete",),
        quality_hook_ids=("tool-role-gap",),
        generation_allowed=False,
        profile_eligibility=(),
    )


def refuse_document_source_tool_traces() -> None:
    """Document-source construction cannot invent tool traces."""
    raise ConstructionError(
        "tool_call requires dataset-row mapped_value tool traces; "
        "document-source construction cannot invent tool traces"
    )


def normalize_tool_turns(value: object) -> list[dict[str, Any]]:
    """Admit one ordered user-provided tool trace. Malformed traces fail closed."""
    if not isinstance(value, list) or len(value) < 3:
        raise ValueError(
            "tool-call-conversation turns must be a list of at least three ordered turns"
        )
    normalized: list[dict[str, Any]] = []
    saw_tool = False
    for index, turn in enumerate(value):
        if not isinstance(turn, dict):
            raise ValueError(
                f"tool-call-conversation turn {index} has an invalid shape"
            )
        role = turn.get("role")
        content = turn.get("content")
        if role not in _TURN_ROLES:
            raise ValueError(
                f"tool-call-conversation turn {index} has an unknown role"
            )
        if type(content) is not str or content == "":
            raise ValueError(
                f"tool-call-conversation turn {index} content must be a non-empty string"
            )
        if role == "user":
            if set(turn) != {"content", "role"}:
                raise ValueError(
                    f"tool-call-conversation turn {index} has an invalid shape"
                )
            normalized.append({"content": content, "role": "user"})
            continue
        if role == "assistant":
            extra = set(turn) - {"content", "role", "tool_calls"}
            if extra:
                raise ValueError(
                    f"tool-call-conversation turn {index} has an invalid shape"
                )
            item: dict[str, Any] = {"content": content, "role": "assistant"}
            if "tool_calls" in turn:
                item["tool_calls"] = _normalize_tool_calls(turn["tool_calls"], index)
                saw_tool = True
            normalized.append(item)
            continue
        if set(turn) != {"content", "role", "tool_call_id"}:
            raise ValueError(
                f"tool-call-conversation turn {index} has an invalid shape"
            )
        tool_call_id = turn.get("tool_call_id")
        if type(tool_call_id) is not str or tool_call_id == "":
            raise ValueError(
                f"tool-call-conversation turn {index} tool_call_id must be a "
                "non-empty string"
            )
        saw_tool = True
        normalized.append(
            {"content": content, "role": role, "tool_call_id": tool_call_id}
        )
    if not saw_tool:
        raise ValueError(
            "tool-call-conversation turns must include a tool or function trace"
        )
    last = normalized[-1]
    if last["role"] != "assistant" or "tool_calls" in last:
        raise ValueError(
            "tool-call-conversation turns must end with a final assistant turn"
        )
    return normalized


def _normalize_tool_calls(value: object, turn_index: int) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ValueError(
            f"tool-call-conversation turn {turn_index} tool_calls must be a "
            "non-empty list"
        )
    calls: list[dict[str, str]] = []
    for call in value:
        if not isinstance(call, dict) or set(call) != {"arguments", "id", "name"}:
            raise ValueError(
                f"tool-call-conversation turn {turn_index} tool_calls has an "
                "invalid shape"
            )
        identifier = call.get("id")
        name = call.get("name")
        arguments = call.get("arguments")
        if any(type(item) is not str or item == "" for item in (identifier, name, arguments)):
            raise ValueError(
                f"tool-call-conversation turn {turn_index} tool_calls require "
                "non-empty id, name, and arguments strings"
            )
        calls.append({"arguments": arguments, "id": identifier, "name": name})
    return calls


def imported_tool_call_groups(
    included: Sequence[object],
    raw_digests: Mapping[str, str],
) -> tuple[object, ...]:
    """Union imported tool-call rows by source and conversation identity."""
    from veriformis.mapping.finish import ImportedLeakageGroup, exact_imported_fingerprint

    ordered = tuple(sorted(included, key=lambda item: item.record_id))
    if not ordered:
        raise SplitError("tool-call split requires at least one included record")
    disjoint = _DisjointSet(len(ordered))
    token_owner: dict[tuple[str, str], int] = {}
    fingerprints: dict[str, str] = {}
    for index, record in enumerate(ordered):
        fields = {field.name: field.value for field in record.fields}
        conversation_id = fields.get("conversation_id")
        if type(conversation_id) is not str or conversation_id == "":
            raise SplitError(
                f"grouping key 'conversation' is missing or empty for {record.record_id}"
            )
        fingerprint = exact_imported_fingerprint(record)
        fingerprints[record.record_id] = fingerprint
        digest = raw_digests.get(record.source_id)
        if type(digest) is not str or digest == "":
            raise SplitError(
                f"raw digest is missing for tool-call source {record.source_id}"
            )
        tokens = (
            ("conversation", conversation_id),
            ("exact-record-fingerprint", fingerprint),
            ("raw-sha256", digest),
            ("source", record.source_id),
        )
        for token in tokens:
            owner = token_owner.setdefault(token, index)
            disjoint.union(index, owner)
    members_by_root: dict[int, list[object]] = {}
    for index, record in enumerate(ordered):
        members_by_root.setdefault(disjoint.find(index), []).append(record)
    groups = []
    for members in members_by_root.values():
        source_ids = tuple(sorted({item.source_id for item in members}))
        groups.append(
            ImportedLeakageGroup.create(
                record_ids=tuple(item.record_id for item in members),
                source_ids=source_ids,
                raw_sha256_values=tuple(
                    raw_digests[source_id] for source_id in source_ids
                ),
                exact_record_fingerprints=tuple(
                    sorted({fingerprints[item.record_id] for item in members})
                ),
            )
        )
    return tuple(sorted(groups, key=lambda item: item.group_id))
