"""Phase 14.6: CLI, MCP, and Python agree on review packet identities."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.errors import ReviewError
from veriformis.identity import derive_id
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.review import (
    ReviewDecision,
    ReviewItem,
    ReviewPacket,
    export_review_packet,
    load_review_packet,
    submit_review_packet,
)


RUNNER = CliRunner()


def _item(*, required: bool = True) -> ReviewItem:
    return ReviewItem.create(
        queue_kind="construction-pending",
        subject_id=derive_id("cand", {"phase14": "exchange-subject"}),
        required=required,
    )


def _plan_id() -> str:
    return derive_id("fdp", {"phase14": "review-exchange"})


def _tool_map(server):
    return {tool.name: tool.fn for tool in server._tool_manager.list_tools()}


def test_export_import_submit_round_trip() -> None:
    item = _item()
    plan_id = _plan_id()
    pending = export_review_packet(plan_id=plan_id, items=(item,))
    assert pending.decisions == ()
    reloaded = load_review_packet(pending.model_dump(mode="json"))
    assert reloaded == pending
    with pytest.raises(ReviewError, match="unresolved"):
        submit_review_packet(pending)
    decision = ReviewDecision.create(
        item_id=item.item_id,
        reviewer_id="local-operator",
        verdict="accepted",
        rationale="Exact source text is kept.",
    )
    completed = ReviewPacket.create(
        plan_id=plan_id,
        items=(item,),
        decisions=(decision,),
    )
    bundle = submit_review_packet(completed)
    assert bundle.plan_id == plan_id
    assert bundle.verdicts == (decision.decision_id,)
    assert bundle.blocks_seal is False
    assert bundle.items == (item.item_id,)


def test_python_cli_mcp_export_identities_match(tmp_path) -> None:
    item = _item()
    plan_id = _plan_id()
    items_path = tmp_path / "items.json"
    items_path.write_text(
        json.dumps([item.model_dump(mode="json")], ensure_ascii=False),
        encoding="utf-8",
    )
    python_packet = PipelineService().export_review_packet(
        plan_id,
        [item.model_dump(mode="json")],
    )
    cli = RUNNER.invoke(
        app,
        ["review-export", "--plan-id", plan_id, "--items", str(items_path)],
    )
    assert cli.exit_code == 0, cli.output
    mcp_packet = json.loads(
        _tool_map(create_mcp_server())["export_review"](
            plan_id,
            json.dumps([item.model_dump(mode="json")]),
        )
    )
    assert json.loads(cli.output) == python_packet == mcp_packet
    assert python_packet["packet_id"] == export_review_packet(
        plan_id=plan_id,
        items=(item,),
    ).packet_id


def test_python_cli_mcp_submit_identities_match(tmp_path) -> None:
    item = _item()
    plan_id = _plan_id()
    decision = ReviewDecision.create(
        item_id=item.item_id,
        reviewer_id="local-operator",
        verdict="accepted",
        rationale="Exact source text is kept.",
    )
    packet = ReviewPacket.create(
        plan_id=plan_id,
        items=(item,),
        decisions=(decision,),
    )
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(
        json.dumps(packet.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )
    python_bundle = PipelineService().submit_review(packet.model_dump(mode="json"))
    cli = RUNNER.invoke(app, ["review-submit", str(packet_path)])
    assert cli.exit_code == 0, cli.output
    mcp_bundle = json.loads(
        _tool_map(create_mcp_server())["submit_review"](
            json.dumps(packet.model_dump(mode="json"))
        )
    )
    assert json.loads(cli.output) == python_bundle == mcp_bundle
    assert python_bundle["bundle_id"] == submit_review_packet(packet).bundle_id
