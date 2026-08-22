"""Goal-specific preview v1 over real workspaces for every goal and representation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.datasets import SerializationPlan
from veriformis.datasets.serialization import render_record_payload
from veriformis.errors import GoalCatalogError, MissingStageInputError
from veriformis.goals import (
    GoalPreview,
    goal_catalog,
    goal_for_objective,
)
from veriformis.goals import preview as preview_module
from veriformis.goals.preview import (
    MAX_RECORD_BYTES,
    MAX_RESPONSE_BYTES,
    RECORD_LIMIT_OMISSION,
    RESPONSE_BUDGET_OMISSION,
    SUPERVISED_ROW_KEY,
)
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.pipeline.service import (
    _load_constructed_dataset,
    _load_serialization_output,
)
from veriformis.workspace import Workspace

runner = CliRunner()
SERVICE = PipelineService()

_SOURCES: dict[str, dict[str, str]] = {
    "full_text": {
        "notes.txt": "First paragraph of café training material — naïve but exact.\n\n"
        "Second paragraph continues the grounded source text.",
    },
    "continuation": {
        "notes.txt": "First paragraph of training material that is long enough.\n\n"
        "Second paragraph continues the grounded source text for splitting.",
    },
    "section_reconstruction": {
        "guide.md": "# Recovered heading\n\nBody text beneath the heading for recovery.\n\n"
        "## Second heading\n\nMore body text beneath the second heading.\n",
    },
    # One block per chunk: the before/after constructor requires exactly one
    # recorded edit derivation on a single-component chunk.
    "before_after_transformation": {
        "spaced.txt": "line   one with   extra spaces that cleaning collapses",
    },
    "structured_field": {
        "guide.md": "# Recovered heading\n\nBody with a [site](https://x.test/page) link.\n",
    },
}
_CHUNK_STRATEGY = {"section_reconstruction": "structure"}


def _compile(root: Path, objective: str, *, sources: dict[str, str] | None = None, **kwargs) -> Path:
    source_root = root / "sources"
    source_root.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, text in (sources or _SOURCES[objective]).items():
        path = source_root / name
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    workspace = root / "workspace"
    SERVICE.parse(paths, workspace, source_root=source_root)
    SERVICE.clean(workspace)
    SERVICE.chunk(workspace, strategy=_CHUNK_STRATEGY.get(objective, "paragraph"))
    SERVICE.construct(workspace, objective=objective, **kwargs)
    return workspace


def _snapshot(workspace: Path) -> dict[str, str]:
    return {
        str(path.relative_to(workspace)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(workspace.rglob("*"))
        if path.is_file()
    }


@pytest.fixture(scope="module")
def workspaces(tmp_path_factory) -> dict[str, Path]:
    return {
        objective: _compile(tmp_path_factory.mktemp(objective), objective)
        for objective in _SOURCES
    }


def _cases():
    for goal in goal_catalog().goals:
        for rep_id in goal.compatible_representations:
            yield pytest.param(goal.objective, rep_id, id=f"{goal.goal_id}/{rep_id}")


@pytest.mark.parametrize(("objective", "rep_id"), list(_cases()))
def test_preview_shows_exact_row_and_supervised_span_for_every_goal(
    workspaces, objective, rep_id
) -> None:
    workspace = workspaces[objective]
    rep = goal_catalog().representation(rep_id)
    instruction = (
        goal_for_objective(objective).instruction_template
        if rep.requires_operator_instruction
        else None
    )
    before = _snapshot(workspace)
    outcome = SERVICE.preview_goal(workspace, representation=rep_id, instruction=instruction)
    assert _snapshot(workspace) == before
    preview = outcome.preview
    assert isinstance(preview, GoalPreview)
    assert preview.objective == objective
    assert preview.goal_id == goal_for_objective(objective).goal_id
    assert preview.row_schema == rep.row_schema
    assert preview.loss_policy == rep.loss_policy
    assert preview.available_stages == ("construct",)
    assert preview.records, preview.diagnostics
    assert preview.counts["selected"] == len(preview.records)

    store = Workspace.open(workspace)
    recipe, result, inputs = _load_constructed_dataset(store, store.head())
    sources = {source.id: source for source in inputs.sources}
    by_id = {record.record_id: record for record in result.records}
    plan = SerializationPlan.create(row_schema=rep.row_schema, instruction_text=instruction)
    for entry in preview.records:
        record = by_id[entry.record_id]
        assert entry.omission_reason is None
        expected_row = render_record_payload(plan, recipe, record)
        assert entry.rendered_row == expected_row
        assert entry.supervised.row_key == SUPERVISED_ROW_KEY[rep.row_schema]
        key = entry.supervised.row_key
        if key == "messages[1].content":
            value = expected_row["messages"][1]["content"]
        else:
            value = expected_row[key]
        assert value == list(entry.target.values())[0]
        assert (entry.supervised.start, entry.supervised.end) == (0, len(value))
        for key in entry.context_row_keys:
            if key.startswith("messages"):
                assert expected_row["messages"][0]["content"]
            else:
                assert key in expected_row
        assert entry.recovered_source
        for item in entry.recovered_source:
            assert item.excerpt is not None
            assert hashlib.sha256(item.excerpt.encode("utf-8")).hexdigest() == item.text_sha256
            if item.kind == "ir_field":
                assert item.region_id.startswith("ir:/") and item.start is None
                assert item.excerpt == next(
                    f.value for f in record.fields if f.name == item.field
                )
                continue
            assert sources[item.source_id].extracted_text[item.start : item.end] == item.excerpt
        assert entry.curation_status is None and entry.curation_reason_codes == ()
        assert entry.constructor_id and entry.pass_id and entry.chunk_ids
    assert preview.not_this == goal_for_objective(objective).not_this
    assert preview.non_claims == goal_for_objective(objective).non_claims
    assert len(preview.transport_text().encode("utf-8")) <= MAX_RESPONSE_BYTES


def test_default_representation_follows_the_recipe_and_uses_the_catalog_template(
    workspaces,
) -> None:
    preview = SERVICE.preview_goal(workspaces["continuation"]).preview
    assert preview.representation_id == "prompt-and-completion"
    templated = SERVICE.preview_goal(
        workspaces["continuation"], representation="instruction-and-output"
    ).preview
    expected = goal_for_objective("continuation").instruction_template
    assert templated.records
    for entry in templated.records:
        assert entry.omission_reason is None
        assert entry.rendered_row is not None
        assert entry.rendered_row["instruction"] == expected
        assert entry.target is not None and entry.supervised.end > 0
    assert templated.counts["omitted"] == 0


def test_preview_reports_curation_decisions_and_persisted_instruction(tmp_path) -> None:
    workspace = _compile(tmp_path, "continuation", target_row_schema="instruction_output")
    SERVICE.curate(
        workspace,
        minimum_target_characters=100_000,
        evaluation_required=False,
        instruction=goal_for_objective("continuation").instruction_template,
    )
    preview = SERVICE.preview_goal(workspace).preview
    assert preview.available_stages == ("construct", "curate")
    assert preview.representation_id == "instruction-and-output"
    assert preview.counts["excluded"] >= 1 and preview.counts["included"] == 0
    assert preview.exclusions
    assert all("target-too-short" in item.reason_codes for item in preview.exclusions)
    for entry in preview.records:
        assert entry.curation_status == "excluded"
        assert "target-too-short" in entry.curation_reason_codes
        assert entry.rendered_row["instruction"] == goal_for_objective(
            "continuation"
        ).instruction_template
    assert preview.omitted_exclusion_count == 0


def test_preview_fails_closed_on_incompatible_or_unknown_selection(workspaces, tmp_path) -> None:
    with pytest.raises(GoalCatalogError, match="does not allow representation"):
        SERVICE.preview_goal(workspaces["full_text"], representation="conversation")
    with pytest.raises(GoalCatalogError, match="unknown representation"):
        SERVICE.preview_goal(workspaces["full_text"], representation="chat")
    with pytest.raises(GoalCatalogError, match="unknown accepted record"):
        SERVICE.preview_goal(workspaces["full_text"], record_ids=("rec-v1-" + "0" * 64,))
    source_root = tmp_path / "src"
    source_root.mkdir()
    (source_root / "a.txt").write_text("one paragraph", encoding="utf-8")
    workspace = tmp_path / "ws"
    SERVICE.parse([source_root / "a.txt"], workspace, source_root=source_root)
    with pytest.raises(MissingStageInputError, match="completed construct stage"):
        SERVICE.preview_goal(workspace)


def test_over_limit_record_is_omitted_whole_with_exact_reason(tmp_path) -> None:
    big = "x" * (MAX_RECORD_BYTES // 2 + 1024)
    workspace = _compile(tmp_path, "full_text", sources={"big.txt": big})
    preview = SERVICE.preview_goal(workspace).preview
    assert preview.records and preview.counts["omitted"] == 1
    entry = preview.records[0]
    assert entry.omission_reason == RECORD_LIMIT_OMISSION
    assert entry.exact_size_bytes > MAX_RECORD_BYTES
    assert entry.rendered_row is None and entry.context is None and entry.target is None
    assert all(item.excerpt is None for item in entry.recovered_source)
    assert entry.supervised.end == len(big)


def test_response_budget_omits_later_records_whole(tmp_path) -> None:
    sources = {f"doc{i}.txt": f"{i}" * 20_000 for i in range(6)}
    workspace = _compile(tmp_path, "full_text", sources=sources)
    preview = SERVICE.preview_goal(workspace).preview
    assert len(preview.records) == 6
    reasons = [entry.omission_reason for entry in preview.records]
    assert reasons[0] is None
    assert RESPONSE_BUDGET_OMISSION in reasons
    assert RECORD_LIMIT_OMISSION not in reasons
    assert len(preview.transport_text().encode("utf-8")) <= MAX_RESPONSE_BYTES
    assert preview.counts["omitted"] == reasons.count(RESPONSE_BUDGET_OMISSION)


def test_bound_holds_for_many_records_and_fails_closed_when_skeleton_cannot_fit(
    tmp_path, monkeypatch
) -> None:
    sources = {f"doc{i:03d}.txt": f"paragraph {i} " * 40 for i in range(40)}
    workspace = _compile(tmp_path, "full_text", sources=sources)
    monkeypatch.setattr(preview_module, "MAX_RESPONSE_BYTES", 64 * 1024)
    preview = SERVICE.preview_goal(workspace).preview
    assert len(preview.records) == 40
    assert len(preview.transport_text().encode("utf-8")) <= 64 * 1024
    reasons = [entry.omission_reason for entry in preview.records]
    assert reasons[0] is None and RESPONSE_BUDGET_OMISSION in reasons
    for entry in preview.records:
        if entry.omission_reason is not None:
            assert entry.rendered_row is None and entry.target is None
            assert entry.exact_size_bytes > 0 and entry.supervised.end > 0
    monkeypatch.setattr(preview_module, "MAX_RESPONSE_BYTES", 16 * 1024)
    with pytest.raises(GoalCatalogError, match="cannot fit"):
        SERVICE.preview_goal(workspace)


def test_duplicate_record_ids_fail_closed(workspaces) -> None:
    record_id = SERVICE.preview_goal(workspaces["full_text"]).preview.records[0].record_id
    with pytest.raises(GoalCatalogError, match="must not repeat"):
        SERVICE.preview_goal(workspaces["full_text"], record_ids=(record_id, record_id))


def test_legacy_workspace_fails_closed_with_a_named_upgrade(tmp_path) -> None:
    import importlib.util

    module_path = Path(__file__).parents[1] / "regressions" / "test_workspace_v2_migration.py"
    spec = importlib.util.spec_from_file_location("legacy_helper", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    legacy = module._legacy_workspace(tmp_path)
    from veriformis.errors import UnsupportedWorkspaceVersionError

    with pytest.raises(UnsupportedWorkspaceVersionError, match="upgrade-workspace"):
        SERVICE.preview_goal(legacy.root)

def test_preview_row_equals_the_persisted_product_row(tmp_path) -> None:
    """U2: the preview renders exactly what `format` lowered and sealed rows carry."""
    workspace = _compile(tmp_path, "continuation", split_ratio_ppm=400_000)
    SERVICE.curate(workspace, evaluation_required=False)
    SERVICE.split(workspace)
    SERVICE.format(workspace)
    store = Workspace.open(workspace)
    output = _load_serialization_output(store, store.head())
    rows = {}
    partitions = {"train": output.row_set.train_rows, "evaluation": output.row_set.evaluation_rows}
    for item in output.row_set.provenance:
        rows[item.record_id] = item.payload_sha256
    payload_by_digest = {row.payload_sha256: row.payload for rows_ in partitions.values() for row in rows_}
    preview = SERVICE.preview_goal(workspace, record_ids=tuple(rows)).preview
    assert preview.records
    for entry in preview.records:
        assert entry.rendered_row == payload_by_digest[rows[entry.record_id]]
        assert entry.rendered_row[entry.supervised.row_key] == list(entry.target.values())[0]


def test_cli_and_mcp_emit_identical_ascii_safe_preview(workspaces) -> None:
    workspace = workspaces["full_text"]
    expected = SERVICE.preview_goal(workspace).preview.model_dump(mode="json")
    text = json.dumps(expected, ensure_ascii=True, indent=2, sort_keys=True)
    assert text.isascii()
    result = runner.invoke(app, ["goal-preview", str(workspace)])
    assert result.exit_code == 0, result.output
    assert result.output == text + "\n"
    assert json.loads(result.output) == expected
    assert "café" in json.loads(result.output)["records"][0]["target"]["text"]
    tool = {t.name: t.fn for t in create_mcp_server(SERVICE)._tool_manager.list_tools()}["goal_preview"]
    assert tool(str(workspace)) == text
    selected = runner.invoke(
        app,
        ["goal-preview", str(workspace), "--record", expected["records"][0]["record_id"]],
    )
    assert selected.exit_code == 0, selected.output
    assert json.loads(selected.output)["records"] == expected["records"]


FROZEN_PREVIEW = (
    Path(__file__).parents[1] / "regressions" / "fixtures" / "phase6" / "goal-preview.json"
)


def test_frozen_preview_fixture_is_reproduced_exactly(tmp_path) -> None:
    """The Swift decoder tests share this fixture; it must stay deterministic."""
    source_root = tmp_path / "sources"
    source_root.mkdir()
    (source_root / "guide.md").write_text(_SOURCES["section_reconstruction"]["guide.md"], encoding="utf-8")
    workspace = tmp_path / "workspace"
    SERVICE.parse([source_root / "guide.md"], workspace, source_root=source_root)
    SERVICE.clean(workspace)
    SERVICE.chunk(workspace, strategy="structure")
    SERVICE.construct(workspace, objective="section_reconstruction")
    SERVICE.curate(workspace, evaluation_required=False)
    preview = SERVICE.preview_goal(workspace, representation="conversation").preview
    text = json.dumps(preview.model_dump(mode="json"), ensure_ascii=True, indent=2, sort_keys=True)
    assert text + "\n" == FROZEN_PREVIEW.read_text(encoding="utf-8")
    assert preview.available_stages == ("construct", "curate")
    assert preview.records and preview.records[0].curation_status == "included"
