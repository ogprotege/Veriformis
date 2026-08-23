"""Phase 9.3: semantic fingerprints independent of library metadata."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from veriformis.contracts import (
    COLUMNAR_FINGERPRINT_CONTRACT_ID,
    COLUMNAR_FINGERPRINT_CONTRACT_VERSION,
    COLUMNAR_FINGERPRINT_SCHEMA_ID,
)
from veriformis.errors import ExportContractError
from veriformis.exports.columnar_fingerprint import (
    COLUMNAR_FINGERPRINT_DATA_NAME,
    EXCLUDED_LIBRARY_METADATA,
    PREIMAGE_FIELDS,
    ColumnarFingerprintContract,
    columnar_dataset_fingerprint,
    columnar_fingerprint_contract,
    columnar_fingerprint_contract_json,
    columnar_partition_fingerprint,
    columnar_partition_preimage,
    discover_columnar_fingerprint_contract,
)
from veriformis.exports.columnar_schemas import columnar_schema_digest
from veriformis.identity import canonical_digest
from veriformis.taxonomy import PLANNED_PHYSICAL_CONTAINERS

DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "veriformis"
    / "exports"
    / COLUMNAR_FINGERPRINT_DATA_NAME
)
ROOT = Path(__file__).resolve().parents[2]


def _text_payloads() -> tuple[dict[str, str], ...]:
    return ({"text": "alpha"}, {"text": "beta"})


def test_fingerprint_contract_constants_are_exact() -> None:
    assert COLUMNAR_FINGERPRINT_CONTRACT_ID == "veriformis.columnar-semantic-fingerprint"
    assert COLUMNAR_FINGERPRINT_CONTRACT_VERSION == 1
    assert COLUMNAR_FINGERPRINT_SCHEMA_ID == (
        "veriformis.columnar-semantic-fingerprint/v1"
    )
    assert COLUMNAR_FINGERPRINT_DATA_NAME == "columnar_fingerprint-v1.json"


def test_packaged_contract_is_canonical() -> None:
    stored = DATA_PATH.read_text(encoding="utf-8")
    payload = json.loads(stored)
    canonical = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    assert stored == canonical
    assert stored == columnar_fingerprint_contract_json()
    assert discover_columnar_fingerprint_contract() == json.loads(stored)
    contract = columnar_fingerprint_contract()
    assert isinstance(contract, ColumnarFingerprintContract)
    assert contract.state == "planned"
    assert contract.determinism_claim == "semantic_content_only"
    assert contract.receipt_binds == "exact_emitted_bytes"
    assert contract.excluded_library_metadata == EXCLUDED_LIBRARY_METADATA
    assert contract.preimage_fields == PREIMAGE_FIELDS


def test_partition_fingerprint_is_stable_and_lossless() -> None:
    first = columnar_partition_fingerprint(
        row_schema="text",
        partition="train",
        payloads=_text_payloads(),
    )
    second = columnar_partition_fingerprint(
        row_schema="text",
        partition="train",
        payloads=_text_payloads(),
    )
    assert first == second
    assert len(first) == 64
    preimage = columnar_partition_preimage(
        row_schema="text",
        partition="train",
        payloads=_text_payloads(),
    )
    assert preimage.schema_pin_digest == columnar_schema_digest()
    assert preimage.schema_id == COLUMNAR_FINGERPRINT_SCHEMA_ID
    assert set(preimage.model_dump(mode="json")) == set(PREIMAGE_FIELDS)
    assert first == canonical_digest(preimage.model_dump(mode="json"))


def test_fingerprint_does_not_include_container_identity() -> None:
    train = _text_payloads()
    evaluation: tuple[dict[str, str], ...] = ()
    digest = columnar_dataset_fingerprint(
        row_schema="text",
        train_payloads=train,
        evaluation_payloads=evaluation,
    )
    again = columnar_dataset_fingerprint(
        row_schema="text",
        train_payloads=train,
        evaluation_payloads=evaluation,
    )
    assert digest == again
    assert PLANNED_PHYSICAL_CONTAINERS == (
        "parquet",
        "arrow",
        "hugging-face-dataset",
    )
    dumped = columnar_partition_preimage(
        row_schema="text",
        partition="train",
        payloads=train,
    ).model_dump(mode="json")
    assert "container_id" not in dumped
    for excluded in EXCLUDED_LIBRARY_METADATA:
        assert excluded not in dumped


def test_partition_order_and_membership_change_the_fingerprint() -> None:
    train = _text_payloads()
    reversed_rows = ({"text": "beta"}, {"text": "alpha"})
    assert columnar_partition_fingerprint(
        row_schema="text",
        partition="train",
        payloads=train,
    ) != columnar_partition_fingerprint(
        row_schema="text",
        partition="train",
        payloads=reversed_rows,
    )
    assert columnar_partition_fingerprint(
        row_schema="text",
        partition="train",
        payloads=train,
    ) != columnar_partition_fingerprint(
        row_schema="text",
        partition="evaluation",
        payloads=train,
    )


def test_unicode_is_lossless_not_nfc_folded() -> None:
    composed = ({"text": "é"},)
    decomposed = ({"text": "e\u0301"},)
    assert composed[0]["text"] != decomposed[0]["text"]
    assert columnar_partition_fingerprint(
        row_schema="text",
        partition="train",
        payloads=composed,
    ) != columnar_partition_fingerprint(
        row_schema="text",
        partition="train",
        payloads=decomposed,
    )


def test_messages_fingerprint_covers_nested_turns() -> None:
    payloads = (
        {
            "messages": [
                {"role": "user", "content": "Ask"},
                {"role": "assistant", "content": "Answer"},
            ]
        },
    )
    digest = columnar_partition_fingerprint(
        row_schema="messages",
        partition="train",
        payloads=payloads,
    )
    swapped = (
        {
            "messages": [
                {"role": "user", "content": "Ask"},
                {"role": "assistant", "content": "Other"},
            ]
        },
    )
    assert digest != columnar_partition_fingerprint(
        row_schema="messages",
        partition="train",
        payloads=swapped,
    )


def test_null_and_malformed_payloads_fail_closed() -> None:
    with pytest.raises(ExportContractError, match="null is unrepresentable"):
        columnar_partition_fingerprint(
            row_schema="text",
            partition="train",
            payloads=({"text": None},),  # type: ignore[list-item]
        )
    with pytest.raises(ExportContractError, match="keys must be exactly"):
        columnar_partition_fingerprint(
            row_schema="text",
            partition="train",
            payloads=({"text": "ok", "extra": "nope"},),
        )
    with pytest.raises(ExportContractError, match="nonempty string"):
        columnar_partition_fingerprint(
            row_schema="text",
            partition="train",
            payloads=({"text": ""},),
        )
    with pytest.raises(ExportContractError, match="exactly two ordered turns"):
        columnar_partition_fingerprint(
            row_schema="messages",
            partition="train",
            payloads=({"messages": [{"role": "user", "content": "only"}]},),
        )
    with pytest.raises(ExportContractError, match="must have role 'user'"):
        columnar_partition_fingerprint(
            row_schema="messages",
            partition="train",
            payloads=(
                {
                    "messages": [
                        {"role": "assistant", "content": "no"},
                        {"role": "user", "content": "no"},
                    ]
                },
            ),
        )


def test_library_metadata_would_not_enter_the_preimage() -> None:
    payloads = _text_payloads()
    preimage = columnar_partition_preimage(
        row_schema="text",
        partition="train",
        payloads=payloads,
    ).model_dump(mode="json")
    polluted = dict(preimage)
    polluted["created_by"] = "parquet-mr"
    polluted["compression"] = "snappy"
    assert canonical_digest(polluted) != columnar_partition_fingerprint(
        row_schema="text",
        partition="train",
        payloads=payloads,
    )
    mutated_pin = dict(preimage)
    mutated_pin["schema_pin_digest"] = "0" * 64
    assert canonical_digest(mutated_pin) != columnar_partition_fingerprint(
        row_schema="text",
        partition="train",
        payloads=payloads,
    )


def test_empty_evaluation_partition_has_a_defined_fingerprint() -> None:
    digest = columnar_partition_fingerprint(
        row_schema="prompt_completion",
        partition="evaluation",
        payloads=(),
    )
    assert digest == columnar_partition_fingerprint(
        row_schema="prompt_completion",
        partition="evaluation",
        payloads=(),
    )
    nonempty = columnar_partition_fingerprint(
        row_schema="prompt_completion",
        partition="evaluation",
        payloads=({"prompt": "p", "completion": "c"},),
    )
    assert digest != nonempty


def test_importing_fingerprint_does_not_import_columnar_libraries() -> None:
    assert "pyarrow" not in sys.modules
    assert "datasets" not in sys.modules
    assert "pandas" not in sys.modules
    columnar_partition_fingerprint(
        row_schema="instruction_output",
        partition="train",
        payloads=({"instruction": "do", "input": "this", "output": "that"},),
    )
    assert "pyarrow" not in sys.modules
    assert "datasets" not in sys.modules
    assert "pandas" not in sys.modules
    toml = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "columnar = []" in toml
