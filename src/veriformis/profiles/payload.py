"""Map verified payloads onto admitted consumer-profile columns."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from veriformis.errors import ExportContractError
from veriformis.profiles.admission import require_profile_messages_payload


def map_admitted_payload(mapping: Any, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Apply one admission mapping. Does not change membership or loss-policy IDs."""
    kind = mapping.mapping_kind
    schema = mapping.source_row_schema
    if kind == "identity":
        if schema == "messages":
            require_profile_messages_payload(payload)
        mapped = dict(payload)
    elif kind == "assemble-prompt":
        instruction = payload["instruction"]
        context = payload["input"]
        prompt = f"{instruction}\n{context}" if str(context) else str(instruction)
        mapped = {"completion": payload["output"], "prompt": prompt}
    elif kind == "remap":
        if schema == "prompt_completion":
            mapped = {
                "input": "",
                "instruction": payload["prompt"],
                "output": payload["completion"],
            }
        elif schema == "messages":
            require_profile_messages_payload(payload)
            user, assistant = payload["messages"]
            mapped = {
                "conversations": [
                    {"from": "human", "value": user["content"]},
                    {"from": "gpt", "value": assistant["content"]},
                ]
            }
        else:
            raise ExportContractError(
                f"remap is not defined for source row schema {schema!r}"
            )
    else:
        raise ExportContractError(f"mapping kind {kind!r} is not executable")
    keys = tuple(sorted(mapped))
    if keys != mapping.destination_keys:
        raise ExportContractError(
            "mapped keys differ from the admission pin "
            f"{mapping.destination_keys!r}: {keys!r}"
        )
    return mapped
