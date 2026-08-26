"""Phase 14.2 review contracts: identity, waiver, correction, empty bundle."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from veriformis.cli import app
from veriformis.construction import DatasetRecipe
from veriformis.contracts import REVIEW_BUNDLE_SCHEMA_ID
from veriformis.errors import ReviewError
from veriformis.identity import derive_id
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.review import (
    CORE_QUEUE_KINDS,
    OPT_IN_QUEUE_KINDS,
    QUEUE_KINDS,
    SAMPLING_QUEUE_KIND,
    ReviewBundle,
    ReviewCorrection,
    ReviewerRef,
    ReviewWaiver,
    empty_review_bundle,
)


def _plan_id() -> str:
    return derive_id("fdp", {"phase14": "review-contracts"})


def test_empty_bundle_is_bound_and_does_not_block_seal() -> None:
    plan_id = _plan_id()
    first = empty_review_bundle(plan_id=plan_id)
    second = empty_review_bundle(plan_id=plan_id)
    assert first == second
    assert first.blocks_seal is False
    assert first.queues == ()
    assert first.items == ()
    assert first.waivers == ()
    assert first.corrections == ()
    assert first.supersessions == ()
    assert first.schema_id == REVIEW_BUNDLE_SCHEMA_ID
    assert first.plan_id == plan_id


def test_queue_kinds_are_closed_and_sorted() -> None:
    assert QUEUE_KINDS == tuple(sorted(QUEUE_KINDS))
    assert set(CORE_QUEUE_KINDS) <= set(QUEUE_KINDS)
    assert set(OPT_IN_QUEUE_KINDS) <= set(QUEUE_KINDS)
    assert SAMPLING_QUEUE_KIND in QUEUE_KINDS
    assert "near-duplicate" in OPT_IN_QUEUE_KINDS
    assert "detector-finding" in OPT_IN_QUEUE_KINDS


def test_waiver_cannot_change_bytes() -> None:
    item_id = derive_id("rit", {"phase14": "waiver-item"})
    waiver = ReviewWaiver.create(
        item_id=item_id,
        reviewer_id="local-operator",
        rationale="Keep the finding. Bytes stay.",
    )
    assert waiver.changes_bytes is False
    payload = waiver.model_dump(mode="json")
    payload["changes_bytes"] = True
    with pytest.raises((ReviewError, ValidationError)):
        ReviewWaiver.model_validate(payload)


def test_correction_must_be_transform_or_mapping_revision() -> None:
    item_id = derive_id("rit", {"phase14": "correction-item"})
    result_id = derive_id("trn", {"phase14": "new-transform"})
    correction = ReviewCorrection.create(
        item_id=item_id,
        kind="transform",
        result_id=result_id,
    )
    assert correction.kind == "transform"
    assert correction.result_id == result_id
    payload = correction.model_dump(mode="json")
    payload["kind"] = "in-place"
    with pytest.raises(ValidationError):
        ReviewCorrection.model_validate(payload)


def test_reviewer_ref_is_unsigned() -> None:
    ref = ReviewerRef(reviewer_id="local-operator")
    assert ref.reviewer_id == "local-operator"
    assert not hasattr(ref, "signature")
    with pytest.raises(ReviewError, match="exact token"):
        ReviewerRef(reviewer_id=" padded ")


def test_default_review_policy_stays_none() -> None:
    assert DatasetRecipe.model_fields["review_policy"].default == "none"


def test_cli_mcp_and_service_share_review_submit() -> None:
    names = {command.name for command in app.registered_commands}
    assert "review-submit" in names
    assert hasattr(PipelineService(), "submit_review")
    tools = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert "submit_review" in tools


def test_empty_bundle_does_not_block_seal() -> None:
    plan_id = _plan_id()
    empty = empty_review_bundle(plan_id=plan_id)
    assert empty.blocks_seal is False
    payload = empty.model_dump(mode="json")
    payload["blocks_seal"] = True
    payload["bundle_id"] = derive_id(
        "rvb",
        {key: value for key, value in payload.items() if key != "bundle_id"},
    )
    blocked = ReviewBundle.model_validate(payload)
    assert blocked.blocks_seal is True
