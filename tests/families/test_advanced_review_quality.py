"""Phase 17.4 opt-in review queues and preview-only family quality hooks."""

from __future__ import annotations

from types import SimpleNamespace

from veriformis.cli import app
from veriformis.construction import DatasetRecipe
from veriformis.quality.family_hooks import FAMILY_HOOK_FACT_NAMES, family_hook_facts
from veriformis.quality.gates import V1_QUALITY_GATES
from veriformis.review.models import OPT_IN_QUEUE_KINDS, QUEUE_KINDS
from veriformis.taxonomy import (
    IMPLEMENTED_TRAINING_FAMILIES,
    PLANNED_TRAINING_FAMILIES,
)


def _record(**fields: str) -> SimpleNamespace:
    return SimpleNamespace(
        fields=tuple(
            SimpleNamespace(name=name, value=value) for name, value in fields.items()
        )
    )


def test_family_review_queues_are_opt_in_and_not_required() -> None:
    assert app is not None
    assert DatasetRecipe.model_fields["review_policy"].default == "none"
    for kind in (
        "label-conflict",
        "preference-inconsistency",
        "tool-trace-incomplete",
        "stepwise-gap",
    ):
        assert kind in OPT_IN_QUEUE_KINDS
        assert kind in QUEUE_KINDS
        assert kind not in (
            "conflict",
            "construction-pending",
            "mapping",
            "ocr-review",
            "parser-degradation",
        )


def test_family_quality_hooks_are_preview_only() -> None:
    assert FAMILY_HOOK_FACT_NAMES == (
        "family-missing-label-count",
        "family-ranking-tie-count",
        "family-singleton-label-set-count",
        "family-tool-role-gap-count",
        "family-unpaired-without-policy-count",
    )
    family_gates = tuple(
        spec for spec in V1_QUALITY_GATES if spec.gate_id.startswith("preview-family-")
    )
    assert len(family_gates) == 5
    assert all(spec.admitted_to_block is False for spec in family_gates)
    assert all(spec.admitted_to_block is False for spec in V1_QUALITY_GATES)


def test_sft_records_do_not_raise_family_hook_counts() -> None:
    facts = {
        item.name: item.integer_value
        for item in family_hook_facts((_record(text="ordinary source text"),))
    }
    assert facts == {
        "family-missing-label-count": 0,
        "family-ranking-tie-count": 0,
        "family-singleton-label-set-count": 0,
        "family-tool-role-gap-count": 0,
        "family-unpaired-without-policy-count": 0,
    }


def test_explicit_family_fields_are_counted_without_executing_a_family() -> None:
    facts = {
        item.name: item.integer_value
        for item in family_hook_facts(
            (
                _record(label=""),
                _record(label="cat"),
                _record(feedback="down"),
                _record(**{"tool-name": "search", "tool-role": ""}),
                _record(prompt="q", rank="1"),
                _record(prompt="q", rank="1"),
            )
        )
    }
    assert facts["family-missing-label-count"] == 1
    assert facts["family-singleton-label-set-count"] == 1
    assert facts["family-unpaired-without-policy-count"] == 1
    assert facts["family-tool-role-gap-count"] == 1
    assert facts["family-ranking-tie-count"] == 1
    assert IMPLEMENTED_TRAINING_FAMILIES == (
        "source-grounded-language-modeling",
        "source-grounded-supervised-fine-tuning",
        "explicit-label-classification",
        "preference-and-ranking",
    )
    assert "explicit-label-classification" not in PLANNED_TRAINING_FAMILIES
    assert "preference-and-ranking" not in PLANNED_TRAINING_FAMILIES
