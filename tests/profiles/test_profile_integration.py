"""Optional schema-loader checks. Excluded from core pytest."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.profile_integration


def test_trl_extra_is_not_required_for_core() -> None:
    datasets = pytest.importorskip("datasets")
    dataset_type = getattr(datasets, "Dataset", None)
    if dataset_type is None:
        pytest.skip("huggingface datasets extra is not installed")
    rows = [{"text": "hello"}]
    loaded = dataset_type.from_list(rows)
    assert list(loaded) == rows


def test_mlx_lm_extra_is_not_required_for_core() -> None:
    pytest.importorskip("mlx_lm")


def test_axolotl_and_llama_factory_extras_are_not_required_for_core() -> None:
    pytest.importorskip("datasets")
    with pytest.raises(ImportError):
        __import__("axolotl")
    with pytest.raises(ImportError):
        __import__("llamafactory")
    with pytest.raises(ImportError):
        __import__("unsloth")
