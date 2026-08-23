"""Optional TRL/MLX-LM loader checks. Excluded from core pytest."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.profile_integration


def test_trl_extra_is_not_required_for_core() -> None:
    datasets = pytest.importorskip("datasets")
    rows = [{"text": "hello"}]
    loaded = datasets.Dataset.from_list(rows)
    assert list(loaded) == rows


def test_mlx_lm_extra_is_not_required_for_core() -> None:
    pytest.importorskip("mlx_lm")
