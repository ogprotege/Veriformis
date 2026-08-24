"""Phase 8.7: discovery truthfulness, refusals, and dual-profile membership."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import veriformis.exports.service as _export_service  # noqa: F401 — break profile/export cycle
from veriformis.errors import ExportContractError
from veriformis.exports import ExportDryRunRequest, ExportService
from veriformis.profiles.admission import (
    discover_profile_admissions,
    require_profile_messages_payload,
)
from veriformis.profiles.axolotl import AXOLOTL_CONSUMER_ID, map_axolotl_payload
from veriformis.profiles.llama_factory import (
    LLAMA_FACTORY_CONSUMER_ID,
    map_llama_factory_payload,
)
from veriformis.profiles.mlx_lm import MLX_LM_CONSUMER_ID, map_mlx_lm_payload
from veriformis.profiles.trl import TRL_CONSUMER_ID, map_trl_payload
from veriformis.profiles import axolotl as axolotl_module
from veriformis.profiles import llama_factory as llama_module
from veriformis.profiles import mlx_lm as mlx_module
from veriformis.profiles import trl as trl_module

from veriformis.datasets import RowSet
from veriformis.taxonomy import loss_policy_for_row

from test_trl import (  # type: ignore[import-not-found]
    _materialize_bundle,
    _row_set_for_schema,
    _selection,
    _source_row_set,
)


def test_admission_discovery_names_accepted_transformed_and_rejected() -> None:
    catalog = discover_profile_admissions()
    by_id = {record["profile_id"]: record for record in catalog["records"]}
    assert set(by_id) == {"trl", "mlx-lm", "axolotl", "llama-factory", "aptus"}
    for record in catalog["records"]:
        assert record["state"] == "implemented"
        assert "preference" in record["refused_dataset_types"]
        assert "tools" in record["refused_dataset_types"]
        assert "vision" in record["refused_dataset_types"]
        assert "accepted_goals" in record
        assert "transformed_row_schemas" in record
        assert "rejected_goals" in record
    assert by_id["trl"]["transformed_row_schemas"] == ["instruction_output"]
    assert by_id["axolotl"]["transformed_row_schemas"] == ["prompt_completion"]
    assert by_id["llama-factory"]["transformed_row_schemas"] == [
        "messages",
        "prompt_completion",
    ]
    assert by_id["aptus"]["rejected_goals"] == ["full_text"]
    assert "text" not in by_id["aptus"]["admitted_row_schemas"]


def test_system_roles_and_extra_assistant_turns_are_refused() -> None:
    with pytest.raises(ExportContractError, match="system"):
        require_profile_messages_payload(
            {
                "messages": [
                    {"role": "system", "content": "Be brief."},
                    {"role": "assistant", "content": "OK."},
                ]
            }
        )
    with pytest.raises(ExportContractError, match="exactly two"):
        require_profile_messages_payload(
            {
                "messages": [
                    {"role": "user", "content": "One"},
                    {"role": "assistant", "content": "Two"},
                    {"role": "assistant", "content": "Three"},
                ]
            }
        )
    with pytest.raises(ExportContractError, match="nonempty string"):
        require_profile_messages_payload(
            {
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": "nested"}]},
                    {"role": "assistant", "content": "OK."},
                ]
            }
        )
    with pytest.raises(ExportContractError, match="system"):
        map_trl_payload(
            "messages",
            {
                "messages": [
                    {"role": "system", "content": "Be brief."},
                    {"role": "assistant", "content": "OK."},
                ]
            },
        )
    with pytest.raises(ExportContractError, match="exactly two"):
        map_mlx_lm_payload(
            "messages",
            {
                "messages": [
                    {"role": "user", "content": "One"},
                    {"role": "assistant", "content": "Two"},
                    {"role": "assistant", "content": "Three"},
                ]
            },
        )


def test_same_bundle_exports_to_implemented_profiles_without_changing_membership(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    source = _source_row_set(bundle)
    service = ExportService()
    plans = {}
    for consumer_id in (
        TRL_CONSUMER_ID,
        MLX_LM_CONSUMER_ID,
        AXOLOTL_CONSUMER_ID,
        LLAMA_FACTORY_CONSUMER_ID,
    ):
        request = _selection(
            bundle, schema_version="veriformis.export-surface-request/v1"
        )
        request["consumer_id"] = consumer_id
        plan = service.dry_run_export(
            ExportDryRunRequest(operation="dry_run", **request)
        )
        plans[consumer_id] = plan
        assert plan.consumer_profile is not None
        assert plan.consumer_profile.consumer_id == consumer_id
        assert plan.row_set_id == source.row_set_id
        assert plan.loss_policy == loss_policy_for_row(source.row_schema)
    aptus_request = _selection(
        bundle, schema_version="veriformis.export-surface-request/v1"
    )
    aptus_request["consumer_id"] = "aptus"
    with pytest.raises(ExportContractError, match="does not support source row schema 'text'"):
        service.dry_run_export(
            ExportDryRunRequest(operation="dry_run", **aptus_request)
        )
    trl_files = dict(trl_module._rendered_files(source))
    mlx_files = dict(mlx_module._rendered_files(source))
    axolotl_files = dict(axolotl_module._rendered_files(source))
    llama_files = dict(llama_module._rendered_files(source))
    trl_train = [
        json.loads(line) for line in trl_files["data/train.jsonl"].decode().splitlines()
    ]
    mlx_train = [
        json.loads(line) for line in mlx_files["train.jsonl"].decode().splitlines()
    ]
    axolotl_train = [
        json.loads(line)
        for line in axolotl_files["data/train.jsonl"].decode().splitlines()
    ]
    llama_train = [
        json.loads(line)
        for line in llama_files["data/train.jsonl"].decode().splitlines()
    ]
    assert len(trl_train) == len(mlx_train) == source.train_row_count
    assert len(axolotl_train) == len(llama_train) == source.train_row_count
    assert trl_train == mlx_train


def test_partition_stems_and_empty_eval_policy(tmp_path: Path) -> None:
    source = _row_set_for_schema(_source_row_set(_materialize_bundle(tmp_path)), "text")
    trl_files = dict(trl_module._rendered_files(source))
    mlx_files = dict(mlx_module._rendered_files(source))
    assert "data/train.jsonl" in trl_files
    assert "data/evaluation.jsonl" in trl_files
    assert "train.jsonl" in mlx_files
    assert "valid.jsonl" in mlx_files
    assert "test.jsonl" not in mlx_files
    empty = RowSet.create(
        plan_id=source.plan_id,
        serialization_plan_id=source.serialization_plan_id,
        recipe_id=source.recipe_id,
        construction_result_id=source.construction_result_id,
        curation_result_id=source.curation_result_id,
        split_result_id=source.split_result_id,
        row_schema="text",
        train_rows=source.train_rows,
        evaluation_rows=(),
        provenance=tuple(item for item in source.provenance if item.partition == "train"),
    )
    empty_mlx = dict(mlx_module._rendered_files(empty))
    assert "valid.jsonl" not in empty_mlx
    assert "train.jsonl" in empty_mlx


def test_unicode_payloads_survive_both_profiles(tmp_path: Path) -> None:
    source = _row_set_for_schema(
        _source_row_set(_materialize_bundle(tmp_path)), "prompt_completion"
    )
    exact = next(iter(source.train_rows)).payload
    assert "composed=\u00e9" in exact["prompt"]
    assert map_trl_payload("prompt_completion", exact) == exact
    assert map_mlx_lm_payload("prompt_completion", exact) == exact
    remapped = map_axolotl_payload("prompt_completion", exact)
    assert remapped["instruction"] == exact["prompt"]
    assert remapped["output"] == exact["completion"]
    llama = map_llama_factory_payload("prompt_completion", exact)
    assert llama["instruction"] == exact["prompt"]
