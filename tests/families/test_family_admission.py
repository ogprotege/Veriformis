"""Phase 17.2 family admission: load and refuse pins only."""

from __future__ import annotations

import pytest
from veriformis.cli import app
from veriformis.contracts import (
    ADVANCED_FAMILY_ADMISSION_CONTRACT_VERSION,
    ADVANCED_FAMILY_ADMISSION_SCHEMA_ID,
)
from veriformis.errors import FamilyAdmissionError
from veriformis.families import (
    ADMITTABLE_FAMILY_IDS,
    FAMILY_ADMISSION_LIFECYCLES,
    FAMILY_ADMISSION_LIMITATIONS,
    NOT_ADMITTED_FAMILY_IDS,
    FamilyAdmission,
    create_family_admission,
    load_family_admission,
)
from veriformis.identity import derive_id
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.taxonomy import (
    EXPLICITLY_UNSUPPORTED_TRAINING_FAMILIES,
    IMPLEMENTED_TRAINING_FAMILIES,
    PLANNED_TRAINING_FAMILIES,
)


def _pin(**overrides: object) -> FamilyAdmission:
    defaults: dict[str, object] = {
        "family_id": "explicit-label-classification",
        "lifecycle": "planned",
        "row_schema_ids": ("label-classification",),
        "loss_policy_id": "label-only",
        "evidence_kinds": ("mapped_value",),
        "leakage_grouping_keys": ("annotator", "source"),
        "review_hook_ids": ("label-conflict",),
        "quality_hook_ids": ("missing-label", "singleton-label-set"),
    }
    defaults.update(overrides)
    return create_family_admission(**defaults)  # type: ignore[arg-type]


@pytest.mark.parametrize("family_id", ADMITTABLE_FAMILY_IDS)
def test_load_accepts_each_admittable_family(family_id: str) -> None:
    schemas = {
        "explicit-label-classification": ("label-classification",),
        "preference-and-ranking": ("preference-pair",),
        "tool-call-conversations": ("tool-call-conversation",),
        "stepwise-supervision": ("stepwise-trace",),
    }
    policies = {
        "explicit-label-classification": "label-only",
        "preference-and-ranking": "pair-supervision",
        "tool-call-conversations": "tool-trace-suffix",
        "stepwise-supervision": "final-step-only",
    }
    pin = _pin(
        family_id=family_id,
        row_schema_ids=schemas[family_id],
        loss_policy_id=policies[family_id],
    )
    loaded = load_family_admission(pin.model_dump(mode="json"))
    assert loaded == pin
    assert loaded.contract_version == ADVANCED_FAMILY_ADMISSION_CONTRACT_VERSION
    assert loaded.schema_id == ADVANCED_FAMILY_ADMISSION_SCHEMA_ID
    assert loaded.generation_allowed is False
    assert loaded.missing_invalid_policy == "refuse"
    assert loaded.profile_eligibility == ()
    assert "mapped_value" in loaded.evidence_kinds
    assert "source" in loaded.leakage_grouping_keys


def test_closed_vocabularies_match_the_contract() -> None:
    assert ADMITTABLE_FAMILY_IDS == (
        "preference-and-ranking",
        "explicit-label-classification",
        "tool-call-conversations",
        "stepwise-supervision",
    )
    assert NOT_ADMITTED_FAMILY_IDS == (
        "pre-tokenized-training",
        "governed-generated-candidates",
    )
    assert EXPLICITLY_UNSUPPORTED_TRAINING_FAMILIES == ("multimodal-training",)
    assert FAMILY_ADMISSION_LIFECYCLES == (
        "planned",
        "admitted",
        "deprecated",
        "removed",
    )
    assert "no-execute" in FAMILY_ADMISSION_LIMITATIONS
    assert "no-extension-protocol-admission" in FAMILY_ADMISSION_LIMITATIONS


def test_unknown_family_names_admitted_families() -> None:
    payload = _pin().model_dump(mode="json")
    payload["family_id"] = "summary-generation"
    with pytest.raises(
        FamilyAdmissionError,
        match=(
            "unknown family: 'summary-generation'; admitted families are "
            "preference-and-ranking, explicit-label-classification, "
            "tool-call-conversations, stepwise-supervision"
        ),
    ):
        load_family_admission(payload)


def test_multimodal_family_is_explicitly_unsupported() -> None:
    payload = _pin().model_dump(mode="json")
    payload["family_id"] = "multimodal-training"
    with pytest.raises(
        FamilyAdmissionError,
        match="family 'multimodal-training' is explicitly unsupported",
    ):
        load_family_admission(payload)


@pytest.mark.parametrize("family_id", NOT_ADMITTED_FAMILY_IDS)
def test_named_families_are_not_admitted_here(family_id: str) -> None:
    payload = _pin().model_dump(mode="json")
    payload["family_id"] = family_id
    with pytest.raises(
        FamilyAdmissionError,
        match=(
            f"family {family_id!r} is not admitted by "
            r"veriformis.advanced-family-admission/v1"
        ),
    ):
        load_family_admission(payload)


def test_unknown_contract_version_names_requested_and_supported() -> None:
    payload = _pin().model_dump(mode="json")
    payload["contract_version"] = 2
    with pytest.raises(
        FamilyAdmissionError,
        match=(
            r"unknown family admission contract version: requested "
            r"contract_id='veriformis.advanced-family-admission' "
            r"contract_version=2 "
            r"schema_id='veriformis.advanced-family-admission/v1', supported "
            r"contract_id='veriformis.advanced-family-admission' "
            r"contract_version=1 "
            r"schema_id='veriformis.advanced-family-admission/v1'"
        ),
    ):
        load_family_admission(payload)


def test_missing_contract_version_names_supported_version() -> None:
    payload = _pin().model_dump(mode="json")
    del payload["contract_version"]
    with pytest.raises(
        FamilyAdmissionError,
        match=(
            r"unknown family admission contract version: requested missing "
            r"contract_version, supported "
            r"contract_id='veriformis.advanced-family-admission' "
            r"contract_version=1 "
            r"schema_id='veriformis.advanced-family-admission/v1'"
        ),
    ):
        load_family_admission(payload)


def test_unknown_field_fails_closed() -> None:
    payload = _pin().model_dump(mode="json")
    payload["constructor_id"] = "veriformis.constructor.guess-labels"
    with pytest.raises(
        FamilyAdmissionError,
        match="unknown field constructor_id",
    ):
        load_family_admission(payload)


def test_generation_allowed_fails_closed() -> None:
    payload = _pin().model_dump(mode="json")
    payload["generation_allowed"] = True
    payload["admission_id"] = derive_id(
        "afa",
        {key: value for key, value in payload.items() if key != "admission_id"},
    )
    with pytest.raises(
        FamilyAdmissionError,
        match="cannot allow generation until the generator boundary",
    ):
        load_family_admission(payload)


def test_sft_row_schema_cannot_be_overloaded() -> None:
    with pytest.raises(
        FamilyAdmissionError,
        match="cannot overload SFT row schema 'messages'",
    ):
        _pin(row_schema_ids=("messages",))


def test_sft_loss_policy_cannot_be_reused() -> None:
    with pytest.raises(
        FamilyAdmissionError,
        match="cannot reuse SFT loss policy 'completion-only'",
    ):
        _pin(loss_policy_id="completion-only")


def test_profile_eligibility_must_stay_empty() -> None:
    with pytest.raises(
        FamilyAdmissionError,
        match="profile_eligibility waits for an independently admitted mapping",
    ):
        _pin(profile_eligibility=("trl",))


def test_taxonomy_is_unchanged_by_loading_a_pin() -> None:
    _pin()
    assert IMPLEMENTED_TRAINING_FAMILIES == (
        "source-grounded-language-modeling",
        "source-grounded-supervised-fine-tuning",
        "explicit-label-classification",
        "preference-and-ranking",
    )
    assert "explicit-label-classification" not in PLANNED_TRAINING_FAMILIES
    assert "preference-and-ranking" not in PLANNED_TRAINING_FAMILIES


def test_public_surfaces_still_have_no_family_execute() -> None:
    forbidden = {"admit-family", "family-admission", "generator"}
    cli_names = {command.name for command in app.registered_commands}
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert cli_names.isdisjoint(forbidden)
    assert mcp_names.isdisjoint(forbidden)
    service = PipelineService()
    assert not hasattr(service, "admit_family")
    assert not hasattr(service, "load_family_admission")
