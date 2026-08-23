"""Phase 8.6: config/launch sidecars do not start training."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import veriformis.exports.service as _export_service  # noqa: F401 — break profile/export cycle
from veriformis.datasets import RowSet
from veriformis.profiles.mlx_lm import (
    MLX_LM_LAUNCH_PATH,
    MlxLmLoraLaunchSidecar,
)
from veriformis.profiles.trl import TRL_EVALUATION_PATH, TRL_LAUNCH_PATH, TrlSftLaunchSidecar
from veriformis.profiles import mlx_lm as mlx_module
from veriformis.profiles import trl as trl_module

from test_trl import (  # type: ignore[import-not-found]
    _materialize_bundle,
    _source_row_set,
)

_PROFILES_DIR = Path(__file__).resolve().parents[2] / "src" / "veriformis" / "profiles"
_FORBIDDEN_CALLS = frozenset(
    {
        "Popen",
        "call",
        "check_call",
        "check_output",
        "exec",
        "execl",
        "execv",
        "execve",
        "fork",
        "popen",
        "posix_spawn",
        "run",
        "spawn",
        "spawnl",
        "spawnv",
        "system",
    }
)
_FORBIDDEN_MODULES = frozenset({"multiprocessing", "subprocess"})


def _call_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


def _imported_modules(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".", 1)[0])
    return names


def test_profile_renderers_do_not_import_process_launchers() -> None:
    for filename in ("trl.py", "mlx_lm.py"):
        source = (_PROFILES_DIR / filename).read_text(encoding="utf-8")
        tree = ast.parse(source)
        assert _imported_modules(tree).isdisjoint(_FORBIDDEN_MODULES)
        assert _call_names(tree).isdisjoint(_FORBIDDEN_CALLS)
        assert "os.system" not in source
        assert "SFTTrainer.train" not in source


def test_trl_sidecar_is_dataset_only_and_does_not_launch(tmp_path: Path) -> None:
    row_set = _source_row_set(_materialize_bundle(tmp_path))
    files = dict(trl_module._rendered_files(row_set))
    sidecar = TrlSftLaunchSidecar.from_json_bytes(files[TRL_LAUNCH_PATH])
    assert sidecar.launches_training is False
    assert sidecar.selects_model is False
    assert sidecar.selects_hyperparameters is False
    assert sidecar.command_argv == ("trl", "sft", "--dataset_name", "json")
    assert "--train" not in sidecar.command_argv
    assert sidecar.data_files.train == "data/train.jsonl"
    assert sidecar.data_files.evaluation == "data/evaluation.jsonl"
    assert sidecar.huggingface_builder == "json"
    assert "model" in sidecar.operator_must_supply
    plans = {
        item.path: item
        for item in trl_module._file_plans(trl_module.TRL_DESCRIPTOR, row_set)
    }
    assert plans[TRL_LAUNCH_PATH].role == "config-sidecar"
    assert plans[TRL_LAUNCH_PATH].membership_scope == "none"


def test_trl_empty_evaluation_keeps_file_but_omits_eval_dataset(
    tmp_path: Path,
) -> None:
    source = _source_row_set(_materialize_bundle(tmp_path))
    empty = RowSet.create(
        plan_id=source.plan_id,
        serialization_plan_id=source.serialization_plan_id,
        recipe_id=source.recipe_id,
        construction_result_id=source.construction_result_id,
        curation_result_id=source.curation_result_id,
        split_result_id=source.split_result_id,
        row_schema=source.row_schema,
        train_rows=source.train_rows,
        evaluation_rows=(),
        provenance=tuple(
            item for item in source.provenance if item.partition == "train"
        ),
    )
    files = dict(trl_module._rendered_files(empty))
    sidecar = TrlSftLaunchSidecar.from_json_bytes(files[TRL_LAUNCH_PATH])
    assert sidecar.use_eval_dataset is False
    assert sidecar.evaluation_row_count == 0
    assert sidecar.data_files.evaluation == TRL_EVALUATION_PATH
    assert sidecar.launches_training is False
    assert TRL_EVALUATION_PATH in files


def test_mlx_lm_sidecar_is_dataset_only_and_does_not_launch(tmp_path: Path) -> None:
    row_set = _source_row_set(_materialize_bundle(tmp_path))
    files = dict(mlx_module._rendered_files(row_set))
    sidecar = MlxLmLoraLaunchSidecar.from_json_bytes(files[MLX_LM_LAUNCH_PATH])
    assert sidecar.launches_training is False
    assert sidecar.selects_model is False
    assert sidecar.selects_hyperparameters is False
    assert sidecar.command_argv == ("mlx_lm.lora", "--data", ".")
    assert "--train" not in sidecar.command_argv
    assert sidecar.data_directory == "."
    assert sidecar.train_path == "train.jsonl"
    assert sidecar.valid_path == "valid.jsonl"
    assert sidecar.test_path is None
    assert sidecar.emits_test_jsonl is False
    assert sidecar.mask_prompt_supported is False
    plans = {
        item.path: item
        for item in mlx_module._file_plans(mlx_module.MLX_LM_DESCRIPTOR, row_set)
    }
    assert plans[MLX_LM_LAUNCH_PATH].role == "config-sidecar"
    assert plans[MLX_LM_LAUNCH_PATH].membership_scope == "none"
