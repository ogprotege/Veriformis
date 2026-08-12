# tests/recipes/test_defectclose_pipeline_spec.py
"""Defect closure: YAML pipeline specs fail closed on unknown top-level keys,
unknown per-stage config keys, duplicate mapping keys, and unknown recipe
library ids instead of silently sealing datasets with defaults."""
from __future__ import annotations

import pytest

from veriformis.recipes.pipeline_spec import (
    PipelineSpec,
    PipelineSpecError,
    load_pipeline_spec,
)
from veriformis.recipes.runner import run_pipeline_spec

_BASE = """
schema_version: veriformis.pipeline/v1
workspace: ws
sources:
  - doc.txt
stages:
  parse: {}
  chunk:
    strategy: sentence
    size: 200
    overlap: 20
""".strip()


def _load(tmp_path, text):
    spec = tmp_path / "pipeline.yaml"
    spec.write_text(text, encoding="utf-8")
    return load_pipeline_spec(spec)


def test_valid_spec_still_loads(tmp_path):
    spec = _load(tmp_path, _BASE)
    assert spec.ordered_stage_names() == ("parse", "chunk")
    assert spec.stages["chunk"] == {
        "strategy": "sentence",
        "size": 200,
        "overlap": 20,
    }


def test_every_runner_read_key_is_accepted(tmp_path):
    text = """
schema_version: veriformis.pipeline/v1
workspace: ws
source_root: .
sources:
  - doc.txt
recipe_library_id: full_text.default
stages:
  parse: {}
  clean:
    rules: urls
    custom: "x+"
  chunk:
    strategy: paragraph
    size: 500
    overlap: 50
  construct:
    objective: full_text
    source: []
    target_row_schema: text
    split_ratio_ppm: 500000
    require_review: false
  curate:
    evaluation_required: true
    allow_empty_evaluation: false
    minimum_target_characters: 1
    balance_mode: none
    maximum_records_per_primary_source: 5
    evaluation_ratio_ppm: 500000
    split_seed: veriformis-v1
    instruction: hello
  split: {}
  format: {}
  validate: {}
  seal:
    out: out.vfbundle
""".strip()
    spec = _load(tmp_path, text)
    assert spec.recipe_library_id == "full_text.default"


def test_stage_config_typo_fails_closed_naming_key_and_stage(tmp_path):
    text = _BASE.replace("    size: 200", "    siz: 200")
    with pytest.raises(PipelineSpecError) as excinfo:
        _load(tmp_path, text)
    message = str(excinfo.value)
    assert "siz" in message
    assert "chunk" in message


def test_unknown_top_level_key_fails_closed_naming_key(tmp_path):
    text = _BASE + "\nworkspce: elsewhere"
    with pytest.raises(PipelineSpecError) as excinfo:
        _load(tmp_path, text)
    assert "workspce" in str(excinfo.value)


def test_duplicate_stage_config_key_fails_closed(tmp_path):
    text = _BASE + "\n    size: 300"
    with pytest.raises(PipelineSpecError) as excinfo:
        _load(tmp_path, text)
    assert "size" in str(excinfo.value)


def test_duplicate_top_level_key_fails_closed(tmp_path):
    text = _BASE + "\nworkspace: other"
    with pytest.raises(PipelineSpecError) as excinfo:
        _load(tmp_path, text)
    assert "workspace" in str(excinfo.value)


def test_unknown_recipe_library_id_fails_closed_listing_valid_ids(tmp_path):
    text = _BASE + "\nrecipe_library_id: full_text.nonexistent"
    with pytest.raises(PipelineSpecError) as excinfo:
        _load(tmp_path, text)
    message = str(excinfo.value)
    assert "full_text.nonexistent" in message
    assert "full_text.default" in message


def test_runner_rejects_unknown_recipe_library_id(tmp_path):
    spec = PipelineSpec(
        schema_version="veriformis.pipeline/v1",
        workspace=tmp_path / "ws",
        source_paths=(tmp_path / "doc.txt",),
        source_root=None,
        stages={"construct": {}},
        recipe_library_id="full_text.nonexistent",
    )
    with pytest.raises(PipelineSpecError, match="full_text.nonexistent"):
        run_pipeline_spec(spec)
