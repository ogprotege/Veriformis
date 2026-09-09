"""Optional trainer-library loader checks. Excluded from core pytest.

Post-20 defect D-28: the ``profile-integration`` CI job installed nothing the
tests imported, so every test skipped and the green check carried no signal.
The job now installs extra ``columnar`` (which brings Hugging Face
``datasets``) and sets ``VERIFORMIS_REQUIRE_PROFILE_LIBRARIES=1``; under that
variable a missing loader fails instead of skipping. Locally, without the
variable, the loader tests still skip when ``datasets`` is absent.

Nothing here imports TRL, MLX-LM, Axolotl, LLaMA-Factory, or Unsloth: the
exporter renders their dataset files and the *official loader library* reads
them back. The exporter does not train.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


import veriformis.exports.service as _export_service  # noqa: F401 — break profile/export cycle
from veriformis.profiles import axolotl as axolotl_module
from veriformis.profiles import llama_factory as llama_module
from veriformis.profiles import mlx_lm as mlx_module
from veriformis.profiles import trl as trl_module
from veriformis.profiles.admission import profile_admission_catalog
from veriformis.profiles.axolotl import AXOLOTL_EVALUATION_PATH, AXOLOTL_TRAIN_PATH
from veriformis.profiles.llama_factory import (
    LLAMA_FACTORY_EVALUATION_PATH,
    LLAMA_FACTORY_TRAIN_PATH,
)
from veriformis.profiles.mlx_lm import MLX_LM_EVALUATION_PATH, MLX_LM_TRAIN_PATH
from veriformis.profiles.trl import TRL_EVALUATION_PATH, TRL_TRAIN_PATH

from support.profile_rows import (
    _row_set_for_schema,
    _source_row_set,
)

from support.bundles import (
    _materialize_bundle,
)

pytestmark = pytest.mark.profile_integration

REQUIRE_LIBRARIES = os.environ.get("VERIFORMIS_REQUIRE_PROFILE_LIBRARIES") == "1"
ROW_SCHEMAS = ("instruction_output", "messages", "prompt_completion", "text")
TRAINER_LIBRARIES = ("trl", "mlx_lm", "mlx", "axolotl", "llamafactory", "unsloth", "torch")


def _datasets():
    """Return the Hugging Face ``datasets`` module or skip/fail per the job policy."""
    try:
        import datasets  # noqa: PLC0415 - optional loader is the subject under test
    except ImportError:
        if REQUIRE_LIBRARIES:
            raise AssertionError(
                "VERIFORMIS_REQUIRE_PROFILE_LIBRARIES=1 but the datasets loader is not "
                "installed; the profile-integration job must sync --extra columnar"
            )
        pytest.skip("huggingface datasets extra is not installed")
    return datasets


def _write_partitions(tmp_path: Path, files: dict[str, bytes], train: str, evaluation: str):
    root = tmp_path / "emitted"
    for relative in (train, evaluation):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(files[relative])
    return root / train, root / evaluation


def _load_jsonl(datasets, path: Path):
    """Load one emitted JSONL partition through the official loader."""
    if path.stat().st_size == 0:
        return []
    loaded = datasets.load_dataset("json", data_files=str(path), split="train")
    return [dict(row) for row in loaded]


def _admitted_keys(profile_id: str, row_schema: str) -> tuple[str, ...]:
    pin = next(r for r in profile_admission_catalog().records if r.profile_id == profile_id)
    return next(m for m in pin.row_mappings if m.source_row_schema == row_schema).destination_keys


@pytest.mark.parametrize("row_schema", ROW_SCHEMAS)
def test_trl_partitions_load_through_the_official_datasets_loader(tmp_path, row_schema):
    datasets = _datasets()
    row_set = _row_set_for_schema(_source_row_set(_materialize_bundle(tmp_path)), row_schema)
    files = dict(trl_module._rendered_files(row_set))
    train_path, evaluation_path = _write_partitions(
        tmp_path, files, TRL_TRAIN_PATH, TRL_EVALUATION_PATH
    )
    train = _load_jsonl(datasets, train_path)
    evaluation = _load_jsonl(datasets, evaluation_path)
    assert len(train) == row_set.train_row_count
    assert len(evaluation) == row_set.evaluation_row_count
    expected_keys = _admitted_keys("trl", row_schema)
    for row in (*train, *evaluation):
        assert tuple(sorted(row)) == expected_keys
    # Dataset.from_list is the schema path TRL itself documents.
    listed = datasets.Dataset.from_list(train) if train else None
    if listed is not None:
        assert listed.num_rows == len(train)
        assert tuple(sorted(listed.column_names)) == expected_keys


@pytest.mark.parametrize("row_schema", ROW_SCHEMAS)
def test_axolotl_partitions_load_through_the_official_datasets_loader(tmp_path, row_schema):
    datasets = _datasets()
    row_set = _row_set_for_schema(_source_row_set(_materialize_bundle(tmp_path)), row_schema)
    files = dict(axolotl_module._rendered_files(row_set))
    train_path, evaluation_path = _write_partitions(
        tmp_path, files, AXOLOTL_TRAIN_PATH, AXOLOTL_EVALUATION_PATH
    )
    train = _load_jsonl(datasets, train_path)
    assert len(train) == row_set.train_row_count
    expected_keys = _admitted_keys("axolotl", row_schema)
    for row in train:
        assert tuple(sorted(row)) == expected_keys


@pytest.mark.parametrize("row_schema", ROW_SCHEMAS)
def test_llama_factory_partitions_load_through_the_official_datasets_loader(
    tmp_path, row_schema
):
    datasets = _datasets()
    row_set = _row_set_for_schema(_source_row_set(_materialize_bundle(tmp_path)), row_schema)
    files = dict(llama_module._rendered_files(row_set))
    train_path, evaluation_path = _write_partitions(
        tmp_path, files, LLAMA_FACTORY_TRAIN_PATH, LLAMA_FACTORY_EVALUATION_PATH
    )
    train = _load_jsonl(datasets, train_path)
    assert len(train) == row_set.train_row_count
    expected_keys = _admitted_keys("llama-factory", row_schema)
    for row in train:
        assert tuple(sorted(row)) == expected_keys


@pytest.mark.parametrize("row_schema", ROW_SCHEMAS)
def test_mlx_lm_partitions_load_through_the_official_datasets_loader(tmp_path, row_schema):
    datasets = _datasets()
    row_set = _row_set_for_schema(_source_row_set(_materialize_bundle(tmp_path)), row_schema)
    files = dict(mlx_module._rendered_files(row_set))
    train_path, evaluation_path = _write_partitions(
        tmp_path, files, MLX_LM_TRAIN_PATH, MLX_LM_EVALUATION_PATH
    )
    train = _load_jsonl(datasets, train_path)
    assert len(train) == row_set.train_row_count
    expected_keys = _admitted_keys("mlx-lm", row_schema)
    for row in train:
        assert tuple(sorted(row)) == expected_keys


def test_rendering_every_profile_imports_no_trainer_library(tmp_path):
    """The exporter emits trainer files without the trainer being installed."""
    before = {name for name in TRAINER_LIBRARIES if name in sys.modules}
    row_set = _row_set_for_schema(
        _source_row_set(_materialize_bundle(tmp_path)), "prompt_completion"
    )
    for module in (trl_module, mlx_module, axolotl_module, llama_module):
        assert dict(module._rendered_files(row_set))
    after = {name for name in TRAINER_LIBRARIES if name in sys.modules}
    assert after == before == set(), sorted(after)


def test_trainer_libraries_are_absent_from_the_test_environment():
    """Trainer extras stay empty: none of the trainer packages may be importable."""
    for name in ("axolotl", "llamafactory", "unsloth", "trl", "mlx_lm"):
        with pytest.raises(ImportError):
            __import__(name)
