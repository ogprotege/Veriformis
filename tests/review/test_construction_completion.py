"""Required review can finish through the service, CLI, and MCP without schema changes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.errors import ReviewError
from veriformis.identity import derive_id
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.pipeline.service import _load_constructed_dataset
from veriformis.review import ReviewDecision, ReviewPacket, ReviewWaiver
from veriformis.workspace import Workspace


def _pending(tmp_path: Path):
    service = PipelineService()
    sources = []
    for name, text in (("a", "Alpha exact source passage retained for review."),
                       ("b", "Beta independent document with different words.")):
        source = tmp_path / f"{name}.txt"
        source.write_text(text, encoding="utf-8")
        sources.append(source)
    workspace = tmp_path / "workspace"
    service.parse(sources, workspace, source_root=tmp_path)
    service.clean(workspace)
    service.chunk(workspace)
    service.construct(workspace, goal="learn-the-text", require_review=True)
    service.curate(workspace, evaluation_required=False)
    pending = ReviewPacket.model_validate(service.export_review_packet(workspace=workspace))
    return service, workspace, pending


def _complete(packet, *, rejected=False, waiver=False):
    return ReviewPacket.create(
        plan_id=packet.plan_id, items=packet.items,
        decisions=tuple(
            ReviewDecision.create(
                item_id=item.item_id, reviewer_id="local-reviewer",
                verdict="rejected" if rejected and index == 0 else "accepted",
                rationale="I checked this exact candidate.",
            )
            for index, item in enumerate(packet.items) if not (waiver and index == 0)
        ),
        waivers=tuple(ReviewWaiver.create(
            item_id=item.item_id, reviewer_id="local-reviewer", rationale="Explicit waiver.",
        ) for index, item in enumerate(packet.items) if waiver and index == 0),
    )


@pytest.mark.parametrize("surface", ["python", "cli", "mcp"])
@pytest.mark.parametrize("resolution", ["accepted", "rejected", "waiver"])
def test_review_recommit_can_seal_and_replay(tmp_path: Path, surface: str, resolution: str) -> None:
    service, workspace, pending = _pending(tmp_path)
    packet = _complete(pending, rejected=resolution == "rejected", waiver=resolution == "waiver")
    before = Workspace.open(workspace).head_id
    if surface == "python":
        service.construct(workspace, goal="learn-the-text", review_packet=packet)
    elif surface == "cli":
        path = tmp_path / "review.json"
        path.write_text(packet.model_dump_json(), encoding="utf-8")
        result = CliRunner().invoke(app, [
            "construct", str(workspace), "--goal", "learn-the-text", "--review-packet", str(path),
        ])
        assert result.exit_code == 0, result.output
    else:
        tools = {t.name: t.fn for t in create_mcp_server(service)._tool_manager.list_tools()}
        result = json.loads(tools["construct"](
            str(workspace), goal="learn-the-text", review_packet=packet.model_dump_json(),
        ))
        assert result["exit_status"] == 0
    store = Workspace.open(workspace)
    assert store.head_id != before
    recipe, construction, _ = _load_constructed_dataset(store, store.head())
    assert recipe.review_policy == "required"
    assert all(item.status != "pending_review" for item in construction.decisions)
    assert len(construction.records) == (1 if resolution == "rejected" else 2)
    bundle = service.submit_review(packet.model_dump_json())
    for decision in construction.decisions:
        receipt = json.loads(decision.review.rationale)
        assert receipt["review_bundle_id"] == bundle["bundle_id"]
        assert receipt["review_packet_id"] == packet.packet_id
        assert receipt["resolution"]["rationale"] in {"I checked this exact candidate.", "Explicit waiver."}
    service.curate(workspace, evaluation_required=False)
    service.split(workspace)
    service.format(workspace)
    validation = service.validate(workspace)
    if resolution == "rejected":
        # Rejecting the only candidate from one selected source still fails
        # coverage. Completing review cannot waive independent dataset gates.
        assert validation.exit_status != 0
        assert any(gate.gate_id == "coverage" and gate.status == "failed" for gate in validation.report.gate_results)
        return
    assert validation.exit_status == 0
    sealed = service.seal(workspace, tmp_path / "bundle")
    assert service.verify(tmp_path / "bundle", manifest_sha256=sealed.publication.manifest_sha256).verification.trust_grade == "external_digest"


@pytest.mark.parametrize("defect", ["pending", "foreign-plan", "missing-candidate", "changed-recipe", "unchecked-copy"])
def test_review_mismatch_refuses_without_advancing_head(tmp_path: Path, defect: str) -> None:
    service, workspace, pending = _pending(tmp_path)
    packet = _complete(pending)
    options = {}
    if defect == "pending":
        packet = pending
    elif defect == "foreign-plan":
        packet = ReviewPacket.create(plan_id=derive_id("fdp", {"foreign": True}), items=packet.items, decisions=packet.decisions)
    elif defect == "missing-candidate":
        packet = ReviewPacket.create(plan_id=packet.plan_id, items=packet.items[:1], decisions=packet.decisions[:1])
    elif defect == "changed-recipe":
        options["require_review"] = False
    else:
        packet = packet.model_copy(update={"packet_id": derive_id("rpk", {"forged": True})})
    before = Workspace.open(workspace).head_id
    with pytest.raises(ReviewError):
        service.construct(workspace, goal="learn-the-text", review_packet=packet, **options)
    assert Workspace.open(workspace).head_id == before


def test_review_export_workspace_matches_all_surfaces(tmp_path: Path) -> None:
    service, workspace, packet = _pending(tmp_path)
    cli = CliRunner().invoke(app, ["review-export", "--workspace", str(workspace)])
    assert cli.exit_code == 0, cli.output
    tools = {t.name: t.fn for t in create_mcp_server(service)._tool_manager.list_tools()}
    assert json.loads(cli.output) == json.loads(tools["export_review"](workspace=str(workspace))) == packet.model_dump(mode="json")
