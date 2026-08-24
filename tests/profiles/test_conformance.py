"""Phase 8.5: official-schema harness. Does not import TRL or mlx-lm."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from veriformis.errors import ExportContractError
import veriformis.exports.service as _export_service  # noqa: F401 — break profile/export cycle
from veriformis.profiles.admission import profile_admission_catalog
from veriformis.profiles import aptus as aptus_module
from veriformis.profiles import axolotl as axolotl_module
from veriformis.profiles import llama_factory as llama_module
from veriformis.profiles import mlx_lm as mlx_module
from veriformis.profiles import trl as trl_module
from veriformis.profiles.aptus import APTUS_EVALUATION_PATH, APTUS_TRAIN_PATH, map_aptus_payload
from veriformis.profiles.axolotl import (
    AXOLOTL_EVALUATION_PATH,
    AXOLOTL_TRAIN_PATH,
    AXOLOTL_YAML_PATH,
    axolotl_dataset_type,
    map_axolotl_payload,
)
from veriformis.profiles.llama_factory import (
    LLAMA_FACTORY_DATASET_INFO_PATH,
    LLAMA_FACTORY_EVALUATION_PATH,
    LLAMA_FACTORY_TRAIN_PATH,
    llama_factory_dataset_info,
    map_llama_factory_payload,
)
from veriformis.profiles.mlx_lm import (
    MLX_LM_EVALUATION_PATH,
    MLX_LM_TRAIN_PATH,
    map_mlx_lm_payload,
)
from veriformis.profiles.trl import TRL_EVALUATION_PATH, TRL_TRAIN_PATH, map_trl_payload

from test_trl import (  # type: ignore[import-not-found]
    _materialize_bundle,
    _row_set_for_schema,
    _source_row_set,
)

REFUSED_KEYS = {
    "chosen",
    "rejected",
    "tools",
    "label",
    "completions",
    "labels",
    "images",
}
ROW_SCHEMAS = ("instruction_output", "messages", "prompt_completion", "text")


def _jsonl_rows(data: bytes) -> list[dict[str, object]]:
    return [json.loads(line) for line in data.decode("utf-8").splitlines() if line]


def _dataset_from_list(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Authoritative Dataset.from_list schema path: a list of column dicts."""
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise AssertionError("loader schema requires a list of objects")
    return list(rows)


@pytest.mark.parametrize("row_schema", ROW_SCHEMAS)
def test_trl_jsonl_matches_admission_and_dataset_from_list_schema(
    tmp_path, row_schema: str
) -> None:
    pin = next(r for r in profile_admission_catalog().records if r.profile_id == "trl")
    mapping = next(m for m in pin.row_mappings if m.source_row_schema == row_schema)
    row_set = _row_set_for_schema(_source_row_set(_materialize_bundle(tmp_path)), row_schema)
    files = dict(trl_module._rendered_files(row_set))
    train = _dataset_from_list(_jsonl_rows(files[TRL_TRAIN_PATH]))
    evaluation = _dataset_from_list(_jsonl_rows(files[TRL_EVALUATION_PATH]))
    dataset_dict = {"train": train, "evaluation": evaluation}
    assert list(dataset_dict) == ["train", "evaluation"]
    for row in (*train, *evaluation):
        assert tuple(sorted(row)) == mapping.destination_keys
        assert REFUSED_KEYS.isdisjoint(row)
    assert len(train) == row_set.train_row_count
    assert len(evaluation) == row_set.evaluation_row_count


@pytest.mark.parametrize("row_schema", ROW_SCHEMAS)
def test_mlx_lm_jsonl_matches_admission_and_omits_test_jsonl(
    tmp_path, row_schema: str
) -> None:
    pin = next(
        r for r in profile_admission_catalog().records if r.profile_id == "mlx-lm"
    )
    mapping = next(m for m in pin.row_mappings if m.source_row_schema == row_schema)
    row_set = _row_set_for_schema(_source_row_set(_materialize_bundle(tmp_path)), row_schema)
    files = dict(mlx_module._rendered_files(row_set))
    assert MLX_LM_TRAIN_PATH in files
    assert MLX_LM_EVALUATION_PATH in files
    assert "test.jsonl" not in files
    train = _dataset_from_list(_jsonl_rows(files[MLX_LM_TRAIN_PATH]))
    for row in train:
        assert tuple(sorted(row)) == mapping.destination_keys
        assert REFUSED_KEYS.isdisjoint(row)


@pytest.mark.parametrize("row_schema", ROW_SCHEMAS)
def test_axolotl_jsonl_and_yaml_match_admission(tmp_path, row_schema: str) -> None:
    pin = next(
        r for r in profile_admission_catalog().records if r.profile_id == "axolotl"
    )
    mapping = next(m for m in pin.row_mappings if m.source_row_schema == row_schema)
    row_set = _row_set_for_schema(_source_row_set(_materialize_bundle(tmp_path)), row_schema)
    files = dict(axolotl_module._rendered_files(row_set))
    train = _dataset_from_list(_jsonl_rows(files[AXOLOTL_TRAIN_PATH]))
    evaluation = _dataset_from_list(_jsonl_rows(files[AXOLOTL_EVALUATION_PATH]))
    for row in (*train, *evaluation):
        assert tuple(sorted(row)) == mapping.destination_keys
        assert REFUSED_KEYS.isdisjoint(row)
    yaml_text = files[AXOLOTL_YAML_PATH].decode("utf-8")
    assert f"type: {axolotl_dataset_type(row_schema)}" in yaml_text
    assert "base_model:" not in yaml_text


@pytest.mark.parametrize("row_schema", ROW_SCHEMAS)
def test_llama_factory_jsonl_and_dataset_info_match_admission(
    tmp_path, row_schema: str
) -> None:
    pin = next(
        r
        for r in profile_admission_catalog().records
        if r.profile_id == "llama-factory"
    )
    mapping = next(m for m in pin.row_mappings if m.source_row_schema == row_schema)
    row_set = _row_set_for_schema(_source_row_set(_materialize_bundle(tmp_path)), row_schema)
    files = dict(llama_module._rendered_files(row_set))
    train = _dataset_from_list(_jsonl_rows(files[LLAMA_FACTORY_TRAIN_PATH]))
    for row in train:
        assert tuple(sorted(row)) == mapping.destination_keys
        assert REFUSED_KEYS.isdisjoint(row)
    info = json.loads(files[LLAMA_FACTORY_DATASET_INFO_PATH].decode("utf-8"))
    assert info == llama_factory_dataset_info(
        row_schema, has_evaluation=row_set.evaluation_row_count > 0
    )
    assert info["veriformis_train"]["file_name"] == "train.jsonl"
    assert LLAMA_FACTORY_EVALUATION_PATH in files


@pytest.mark.parametrize(
    "row_schema", ("instruction_output", "messages", "prompt_completion")
)
def test_aptus_jsonl_is_identity_and_never_emits_text(
    tmp_path, row_schema: str
) -> None:
    pin = next(r for r in profile_admission_catalog().records if r.profile_id == "aptus")
    mapping = next(m for m in pin.row_mappings if m.source_row_schema == row_schema)
    row_set = _row_set_for_schema(_source_row_set(_materialize_bundle(tmp_path)), row_schema)
    files = dict(aptus_module._rendered_files(row_set))
    train = _dataset_from_list(_jsonl_rows(files[APTUS_TRAIN_PATH]))
    evaluation = _dataset_from_list(_jsonl_rows(files[APTUS_EVALUATION_PATH]))
    for row in (*train, *evaluation):
        assert tuple(sorted(row)) == mapping.destination_keys
        assert REFUSED_KEYS.isdisjoint(row)
        assert "text" not in row


def test_incompatible_payloads_never_reach_the_schema_loader() -> None:
    with pytest.raises((ExportContractError, KeyError, TypeError)):
        map_trl_payload(
            "instruction_output",
            {"chosen": "yes", "rejected": "no"},
        )
    with pytest.raises((ExportContractError, KeyError, TypeError)):
        map_mlx_lm_payload("messages", {"messages": [], "tools": [{}]})
    with pytest.raises((ExportContractError, KeyError, TypeError)):
        map_axolotl_payload("instruction_output", {"chosen": "yes", "rejected": "no"})
    with pytest.raises((ExportContractError, KeyError, TypeError)):
        map_llama_factory_payload("messages", {"messages": [], "tools": [{}]})
    with pytest.raises((ExportContractError, KeyError, TypeError)):
        map_aptus_payload("messages", {"messages": [], "tools": [{}]})


def test_unknown_row_schema_is_refused_in_veriformis() -> None:
    with pytest.raises(ExportContractError, match="does not map"):
        map_trl_payload("preference", {"chosen": "a", "rejected": "b"})
    with pytest.raises(ExportContractError, match="does not map"):
        map_mlx_lm_payload("preference", {"chosen": "a", "rejected": "b"})
    with pytest.raises(ExportContractError, match="does not map"):
        map_axolotl_payload("preference", {"chosen": "a", "rejected": "b"})
    with pytest.raises(ExportContractError, match="does not map"):
        map_llama_factory_payload("preference", {"chosen": "a", "rejected": "b"})
    with pytest.raises(ExportContractError, match="does not map"):
        map_aptus_payload("text", {"text": "no"})
    with pytest.raises(ExportContractError, match="does not map"):
        map_aptus_payload("preference", {"chosen": "a", "rejected": "b"})
