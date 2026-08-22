"""Goal, preset, and objective selections yield identical recipes on every surface."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.errors import ConstructionError
from veriformis.goals import goal_catalog, preset_catalog, preset_catalog_json, recipe_defaults
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.pipeline.service import _load_constructed_dataset, _load_finished_plan
from veriformis.recipes import load_pipeline_spec, run_pipeline_spec
from veriformis.workspace import Workspace

runner = CliRunner()
SERVICE = PipelineService()
ROOT = Path(__file__).parents[2]

_TEXT = (
    "Alpha paragraph with enough text for a record.\n\n"
    "Beta paragraph keeps the corpus multi-block for splitting."
)


def _sources(root: Path) -> tuple[Path, list[Path]]:
    source_root = root / "sources"
    source_root.mkdir(parents=True, exist_ok=True)
    path = source_root / "doc.txt"
    path.write_text(_TEXT, encoding="utf-8")
    return source_root, [path]


def _prepare(root: Path, name: str, **chunk) -> Path:
    source_root, paths = _sources(root)
    workspace = root / name
    SERVICE.parse(paths, workspace, source_root=source_root)
    SERVICE.clean(workspace)
    SERVICE.chunk(workspace, **chunk)
    return workspace


def _recipe_id(workspace: Path) -> str:
    store = Workspace.open(workspace)
    recipe, _, _ = _load_constructed_dataset(store, store.head())
    return recipe.recipe_id


def _plan_id(workspace: Path) -> str:
    store = Workspace.open(workspace)
    return _load_finished_plan(store, store.head()).plan_id


def test_objective_goal_and_preset_paths_yield_one_recipe_and_plan(tmp_path) -> None:
    by_objective = _prepare(tmp_path, "objective")
    by_goal = _prepare(tmp_path, "goal")
    by_preset = _prepare(tmp_path, "preset", preset="continue-a-passage.safe")
    SERVICE.construct(by_objective, objective="continuation", split_ratio_ppm=400_000)
    SERVICE.construct(by_goal, goal="continue-a-passage", split_ratio_ppm=400_000)
    SERVICE.construct(by_preset, preset="continue-a-passage.safe", split_ratio_ppm=400_000)
    assert _recipe_id(by_objective) == _recipe_id(by_goal) == _recipe_id(by_preset)
    SERVICE.curate(by_objective, evaluation_required=False)
    SERVICE.curate(by_goal, goal="continue-a-passage", evaluation_required=False)
    SERVICE.curate(by_preset, preset="continue-a-passage.safe", evaluation_required=False)
    assert _plan_id(by_objective) == _plan_id(by_goal) == _plan_id(by_preset)


def test_cli_mcp_and_yaml_surfaces_match_the_service_recipe(tmp_path) -> None:
    reference = _prepare(tmp_path, "service")
    SERVICE.construct(reference, goal="continue-a-passage", split_ratio_ppm=400_000)
    expected = _recipe_id(reference)

    cli_ws = _prepare(tmp_path, "cli")
    result = runner.invoke(
        app,
        ["construct", str(cli_ws), "--goal", "continue-a-passage", "--split-ratio-ppm", "400000"],
    )
    assert result.exit_code == 0, result.output
    assert _recipe_id(cli_ws) == expected

    mcp_ws = _prepare(tmp_path, "mcp")
    tools = {t.name: t.fn for t in create_mcp_server(SERVICE)._tool_manager.list_tools()}
    tools["construct"](str(mcp_ws), None, None, None, 400_000, None, None, "continue-a-passage")
    assert _recipe_id(mcp_ws) == expected

    source_root, paths = _sources(tmp_path / "yaml-src")
    yaml_ws = tmp_path / "yaml"
    spec = tmp_path / "pipeline.yaml"
    spec.write_text(
        f"""
schema_version: veriformis.pipeline/v1
workspace: {yaml_ws}
source_root: {source_root}
sources:
  - {paths[0]}
stages:
  parse: {{}}
  clean: {{}}
  chunk:
    goal: continue-a-passage
  construct:
    goal: continue-a-passage
    split_ratio_ppm: 400000
""".strip(),
        encoding="utf-8",
    )
    run_pipeline_spec(load_pipeline_spec(spec))
    assert _recipe_id(yaml_ws) == expected


def test_preset_enforces_its_segmentation_against_the_workspace_chunks(tmp_path) -> None:
    workspace = _prepare(tmp_path, "mismatch")  # paragraph chunks
    with pytest.raises(ConstructionError, match="re-run `veriformis chunk"):
        SERVICE.construct(workspace, preset="recover-a-section-from-its-heading.safe")
    good = _prepare(tmp_path, "match", preset="recover-a-section-from-its-heading.safe")
    store = Workspace.open(good)
    assert store.head().stages["chunk"].config["strategy"] == "structure"


def test_every_surface_executes_the_packaged_defaults(tmp_path) -> None:
    workspace = _prepare(tmp_path, "defaults")
    store = Workspace.open(workspace)
    defaults = recipe_defaults()
    assert store.head().stages["chunk"].config == defaults.segmentation.model_dump()
    SERVICE.construct(workspace, goal="learn-the-text")
    SERVICE.curate(workspace, evaluation_required=False)
    plan = _load_finished_plan(store, store.head())
    curation = defaults.curation
    assert plan.curation_policy.minimum_target_characters == curation.minimum_target_characters
    assert plan.curation_policy.balance_mode == curation.balance_mode
    assert plan.split_policy.evaluation_ratio_ppm == curation.evaluation_ratio_ppm
    assert plan.split_policy.seed == curation.split_seed


def test_presets_discovery_is_byte_identical_on_cli_and_mcp() -> None:
    result = runner.invoke(app, ["presets"])
    assert result.exit_code == 0, result.output
    assert result.output == preset_catalog_json()
    tools = {t.name: t.fn for t in create_mcp_server(SERVICE)._tool_manager.list_tools()}
    assert tools["presets"]() + "\n" == preset_catalog_json()
    assert json.loads(result.output)["defaults"]["construction"]["split_ratio_ppm"] == 500_000


_LITERAL_PATTERNS = (
    re.compile(r"\b500[_]?000\b"),
    re.compile(r"\"veriformis-v1\""),
    re.compile(r"Option\(\s*1000\b"),
    re.compile(r"Option\(\s*100\b"),
    re.compile(r"Option\(\s*\"paragraph\""),
    re.compile(r"\.get\(\"(size|overlap|split_ratio_ppm|evaluation_ratio_ppm|strategy|split_seed)\",\s*[^N]"),
)
_SURFACE_FILES = (
    "src/veriformis/cli.py",
    "src/veriformis/mcp/server.py",
    "src/veriformis/pipeline/service.py",
    "src/veriformis/recipes/runner.py",
    "src/veriformis/recipes/library.py",
)


@pytest.mark.parametrize("relative", _SURFACE_FILES)
def test_no_surface_holds_a_recipe_default_literal(relative: str) -> None:
    """Roadmap 6.4: defaults are versioned data, not duplicated CLI/Swift constants."""
    text = (ROOT / relative).read_text(encoding="utf-8")
    hits = [pattern.pattern for pattern in _LITERAL_PATTERNS if pattern.search(text)]
    assert hits == [], (relative, hits)


def test_constructor_fallback_equals_the_packaged_split_ratio_default() -> None:
    """The replay fallback in the continuation constructor must track the data."""
    text = (ROOT / "src/veriformis/construction/constructors.py").read_text(encoding="utf-8")
    match = re.search(r"params\.get\(\"split_ratio_ppm\",\s*([0-9_]+)\)", text)
    assert match is not None
    assert int(match.group(1).replace("_", "")) == recipe_defaults().construction.split_ratio_ppm


def test_preset_goal_and_representation_closure_against_catalog() -> None:
    goals = {goal.goal_id: goal for goal in goal_catalog().goals}
    for preset in preset_catalog().presets:
        assert preset.representation_id in goals[preset.goal_id].compatible_representations
