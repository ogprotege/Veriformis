"""Phase 17.10: adversarial family refusals, unchanged goldens, skipped generator."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from veriformis.contracts import PRODUCT_ROW_SCHEMA_KINDS, V1_ROW_SCHEMA_KINDS
from veriformis.errors import ConstructionError, FamilyAdmissionError, SplitError
from veriformis.exports.constrained_csv import _COLUMNS_BY_ROW_SCHEMA
from veriformis.families.admission import create_family_admission, load_family_admission
from veriformis.families.classification import refuse_document_source_labels
from veriformis.families.leakage import EXTRA_GROUPING_KEYS, keyed_leakage_groups
from veriformis.families.preference import (
    preference_admission,
    refuse_document_source_preference,
)
from veriformis.families.stepwise import normalize_steps, refuse_document_source_steps
from veriformis.families.tool_call import (
    normalize_tool_turns,
    refuse_document_source_tool_traces,
)
from veriformis.identity import derive_id, sha256_digest
from veriformis.pipeline import PipelineService
from veriformis.taxonomy import (
    EXPLICITLY_UNSUPPORTED_TRAINING_FAMILIES,
    PLANNED_TRAINING_FAMILIES,
    PROFILE_FORBIDDEN_ROW_SCHEMAS,
    assert_profile_row_compatible,
)


ROOT = Path(__file__).resolve().parents[2]
ADR = ROOT / "docs/adr/0018-no-compile-path-generator.md"
KIT = ROOT / "tests/regressions/fixtures/phase16/compatibility-kit.json"
KIT_SHA256 = "746f258df2ae41445df6d2a108e7169279304aa4db156f6407ebf437e132b8f7"
EXPECTED_MANIFEST_SHA256 = (
    "2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733"
)
EXPECTED_BUNDLE_ID = (
    "bundle-v1-49a6b50ed50218b8a22ce834dc69a64eb8d47f0605267bc029b3f938a6b13b4a"
)
_FAMILY_SCHEMAS = (
    "label-classification",
    "preference-pair",
    "tool-call-conversation",
    "stepwise-trace",
)


def test_generation_is_skipped_under_decision_a() -> None:
    text = ADR.read_text(encoding="utf-8")
    assert "**Decision A.** Phase 17 does not install a compile-path generator." in text
    assert not (ROOT / "src/veriformis/generation").exists()
    assert not (ROOT / "src/veriformis/generator.py").exists()
    payload = preference_admission().model_dump(mode="json")
    payload["generation_allowed"] = True
    payload["admission_id"] = derive_id(
        "afa",
        {key: value for key, value in payload.items() if key != "admission_id"},
    )
    with pytest.raises(
        FamilyAdmissionError,
        match="ADR-0018 Decision A forbids a compile-path generator",
    ):
        load_family_admission(payload)


def test_multimodal_and_pre_tokenized_are_skipped() -> None:
    assert EXPLICITLY_UNSUPPORTED_TRAINING_FAMILIES == ("multimodal-training",)
    assert "pre-tokenized-training" in PLANNED_TRAINING_FAMILIES
    assert "governed-generated-candidates" in PLANNED_TRAINING_FAMILIES
    payload = preference_admission().model_dump(mode="json")
    payload["family_id"] = "multimodal-training"
    with pytest.raises(
        FamilyAdmissionError,
        match="family 'multimodal-training' is explicitly unsupported",
    ):
        load_family_admission(payload)
    payload["family_id"] = "pre-tokenized-training"
    with pytest.raises(
        FamilyAdmissionError,
        match="family 'pre-tokenized-training' is not admitted",
    ):
        load_family_admission(payload)


def test_trainer_profile_mappings_are_skipped() -> None:
    assert preference_admission().profile_eligibility == ()
    for profile in ("trl", "mlx-lm", "axolotl", "llama-factory", "aptus"):
        forbidden = set(PROFILE_FORBIDDEN_ROW_SCHEMAS[profile])
        assert set(_FAMILY_SCHEMAS) <= forbidden
        for schema in _FAMILY_SCHEMAS:
            with pytest.raises(Exception, match=schema):
                assert_profile_row_compatible(profile, schema)


def test_unknown_family_and_row_schema_fail_closed() -> None:
    payload = preference_admission().model_dump(mode="json")
    payload["family_id"] = "summary-generation"
    with pytest.raises(
        FamilyAdmissionError,
        match="unknown family: 'summary-generation'",
    ):
        load_family_admission(payload)
    assert "mystery-schema" not in PRODUCT_ROW_SCHEMA_KINDS
    assert "mystery-schema" not in V1_ROW_SCHEMA_KINDS
    with pytest.raises(
        FamilyAdmissionError,
        match="cannot overload SFT row schema 'messages'",
    ):
        create_family_admission(
            family_id="preference-and-ranking",
            lifecycle="admitted",
            row_schema_ids=("messages",),
            loss_policy_id="pair-supervision",
        )


def test_missing_label_pair_and_trace_fail_closed() -> None:
    with pytest.raises(ValueError, match="at least two nonempty strings"):
        normalize_steps([])
    with pytest.raises(ValueError, match="at least three ordered turns"):
        normalize_tool_turns([])
    with pytest.raises(ValueError, match="step 1 must be a non-empty string"):
        normalize_steps(["only-one", ""])


def test_shared_prompt_cannot_be_omitted_from_preference() -> None:
    assert "shared-prompt" in EXTRA_GROUPING_KEYS
    assert "shared-prompt" in preference_admission().leakage_grouping_keys
    with pytest.raises(SplitError, match="unknown leakage grouping key"):
        keyed_leakage_groups(
            (),
            {},
            {},
            grouping_keys=("invented-key",),
            values_by_record={},
        )


def test_two_turn_messages_remain_exact() -> None:
    mapping_source = (
        ROOT / "src/veriformis/mapping/execute.py"
    ).read_text(encoding="utf-8")
    serialization_source = (
        ROOT / "src/veriformis/datasets/serialization.py"
    ).read_text(encoding="utf-8")
    assert "exactly two user/assistant turns" in mapping_source
    assert "messages payload requires exactly two ordered turns" in serialization_source
    assert "messages" in V1_ROW_SCHEMA_KINDS
    assert "tool-call-conversation" in PRODUCT_ROW_SCHEMA_KINDS
    assert "tool-call-conversation" not in V1_ROW_SCHEMA_KINDS


def test_constrained_csv_refuses_nested_family_rows() -> None:
    assert dict(_COLUMNS_BY_ROW_SCHEMA) == {
        "instruction_output": ("instruction", "input", "output"),
        "prompt_completion": ("prompt", "completion"),
        "text": ("text",),
    }
    for schema in _FAMILY_SCHEMAS:
        assert schema not in _COLUMNS_BY_ROW_SCHEMA


def test_invented_supervision_fails_closed() -> None:
    with pytest.raises(ConstructionError, match="cannot invent labels"):
        refuse_document_source_labels()
    with pytest.raises(ConstructionError, match="cannot invent preference pairs"):
        refuse_document_source_preference()
    with pytest.raises(ConstructionError, match="cannot invent tool traces"):
        refuse_document_source_tool_traces()
    with pytest.raises(ConstructionError, match="cannot invent stepwise traces"):
        refuse_document_source_steps()


def test_admission_tamper_fails_closed() -> None:
    payload = preference_admission().model_dump(mode="json")
    payload["admission_id"] = (
        "afa-v1-deadbeefdeadbeefdeadbeefdeadbeef"
        "deadbeefdeadbeefdeadbeefdeadbeef"
    )
    with pytest.raises(
        FamilyAdmissionError,
        match="family admission identity mismatch",
    ):
        load_family_admission(payload)
    payload = preference_admission().model_dump(mode="json")
    payload["constructor_id"] = "veriformis.constructor.guess-labels"
    with pytest.raises(FamilyAdmissionError, match="unknown field constructor_id"):
        load_family_admission(payload)


def test_phase16_kit_and_sft_sealed_bundle_identities_hold(tmp_path: Path) -> None:
    kit_bytes = KIT.read_bytes()
    assert sha256_digest(kit_bytes) == KIT_SHA256
    fixture = json.loads(
        (
            ROOT
            / "tests/regressions/fixtures/phase3/pre-taxonomy-full-text.vfbundle.json"
        ).read_text(encoding="utf-8")
    )
    bundle = tmp_path / "sealed.vfbundle"
    for relative_path, encoded in fixture["files_base64"].items():
        destination = bundle.joinpath(*relative_path.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(base64.b64decode(encoded, validate=True))
    assert (
        sha256_digest((bundle / "manifest.json").read_bytes())
        == EXPECTED_MANIFEST_SHA256
    )
    outcome = PipelineService().verify(
        bundle,
        manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    assert outcome.exit_status == 0
    assert outcome.verification is not None
    assert outcome.verification.bundle_id == EXPECTED_BUNDLE_ID
