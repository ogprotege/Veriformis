"""Phase 14.3 core queues over construction pending_review facts."""

from __future__ import annotations

from pathlib import Path

from veriformis.identity import (
    derive_id,
)
from veriformis.review import (
    CORE_QUEUE_KINDS,
    OPT_IN_QUEUE_KINDS,
    report_core_queues,
)

from support.review import (
    _construct,
)


def test_required_review_construction_fills_pending_queue(tmp_path: Path) -> None:
    construction = _construct(
        tmp_path,
        (
            ("a.txt", "Alpha exact kept text for source one."),
            ("b.txt", "Beta completely different omega text."),
        ),
        review_policy="required",
    )
    pending = tuple(
        decision.candidate_id
        for decision in construction.decisions
        if decision.status == "pending_review"
    )
    assert pending
    plan_id = derive_id("fdp", {"phase14": construction.result_id})
    report = report_core_queues(plan_id=plan_id, construction=construction)
    assert report.queues == CORE_QUEUE_KINDS
    assert len(report.items) == len(pending)
    assert report.blocks_seal is True
    assert not (set(OPT_IN_QUEUE_KINDS) & set(report.queues))


def test_default_none_review_has_empty_pending_items(tmp_path: Path) -> None:
    construction = _construct(
        tmp_path,
        (
            ("a.txt", "Alpha exact kept text for source one."),
            ("b.txt", "Beta completely different omega text."),
        ),
    )
    assert all(decision.status == "accepted" for decision in construction.decisions)
    plan_id = derive_id("fdp", {"phase14": construction.result_id})
    report = report_core_queues(plan_id=plan_id, construction=construction)
    assert report.queues == CORE_QUEUE_KINDS
    assert report.items == ()
    opt_in = report_core_queues(
        plan_id=plan_id,
        construction=construction,
        include_opt_in=True,
    )
    assert set(OPT_IN_QUEUE_KINDS) <= set(opt_in.queues)
    assert opt_in.items == ()
