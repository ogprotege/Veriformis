"""Phase 6.2 goal contracts: evidence, defaults, exports, and non-claims closure."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
from typer.models import OptionInfo

from veriformis.cli import curate as cli_curate
from veriformis.contracts import V1_CONSTRUCTION_DIAGNOSTIC_CODES
from veriformis.errors import GoalCatalogError
from veriformis.goals import (
    GENERIC_EXPORT_CONTAINERS,
    NON_CLAIM_CODES,
    REVIEW_POLICY_OPTIONS,
    goal_catalog,
    parse_goal_catalog,
)
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.recipes.library import build_default_finished_plan
from veriformis.taxonomy import IMPLEMENTED_INPUT_FAMILIES

DATA_PATH = Path(__file__).parents[2] / "src" / "veriformis" / "goals" / "catalog-v1.json"
_DEFAULT_FIELDS = (
    "minimum_target_characters",
    "balance_mode",
    "maximum_records_per_primary_source",
    "evaluation_ratio_ppm",
    "evaluation_required",
    "split_seed",
)


def _payload() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _defaults_of(callable_obj, *, option_info: bool = False) -> dict:
    signature = inspect.signature(callable_obj)
    observed = {}
    for name in _DEFAULT_FIELDS:
        default = signature.parameters[name].default
        if option_info and isinstance(default, OptionInfo):
            default = default.default
        observed[name] = default
    return observed


def test_every_goal_states_the_defaults_every_surface_executes() -> None:
    """Surfaces carry no literal defaults; omitted settings resolve from the data."""
    from veriformis.goals import recipe_defaults, resolve_recipe_settings

    for surface in (PipelineService.curate, build_default_finished_plan, cli_curate):
        observed = _defaults_of(surface, option_info=surface is cli_curate)
        assert all(value is None for value in observed.values()), surface
    mcp_curate = next(
        tool.fn
        for tool in create_mcp_server()._tool_manager.list_tools()
        if tool.name == "curate"
    )
    assert all(value is None for value in _defaults_of(mcp_curate).values())
    data = recipe_defaults().curation.model_dump(mode="json")
    for goal in goal_catalog().goals:
        stated = goal.curation_defaults.model_dump(mode="json")
        assert stated == data, goal.goal_id
        effective = resolve_recipe_settings(goal=goal.goal_id).curation.model_dump(mode="json")
        assert effective == stated, goal.goal_id
        assert goal.review_policy_default == "none"
        assert goal.review_policy_options == REVIEW_POLICY_OPTIONS
        assert goal.non_claims == NON_CLAIM_CODES

def test_representation_exports_equal_the_production_export_catalog() -> None:
    discovery = PipelineService().discover_exports().discovery
    assert discovery is not None
    generic = [
        profile
        for profile in discovery.profiles
        if profile.consumer_profile is None
        and profile.container_profile.container_id in GENERIC_EXPORT_CONTAINERS
    ]
    supported: dict[str, list[str]] = {}
    for profile in generic:
        container = profile.container_profile.container_id
        for row_schema in profile.supported_row_schemas:
            supported.setdefault(row_schema, []).append(container)
    assert set(GENERIC_EXPORT_CONTAINERS) == {
        profile.container_profile.container_id for profile in generic
    }
    for rep in goal_catalog().representations:
        expected = tuple(
            container
            for container in GENERIC_EXPORT_CONTAINERS
            if container in supported.get(rep.row_schema, [])
        )
        assert rep.compatible_generic_exports == expected, rep.representation_id
    conversation = next(
        rep for rep in goal_catalog().representations if rep.row_schema == "messages"
    )
    assert "constrained-csv" not in conversation.compatible_generic_exports


def test_goal_evidence_bindings_are_closed_and_ordered() -> None:
    catalog = goal_catalog()
    for goal in catalog.goals:
        assert goal.eligible_input_families
        assert goal.eligible_input_families == tuple(
            family
            for family in IMPLEMENTED_INPUT_FAMILIES
            if family in goal.eligible_input_families
        )
        assert set(goal.required_evidence_diagnostics) <= set(V1_CONSTRUCTION_DIAGNOSTIC_CODES)
        assert goal.required_evidence_diagnostics
        for field in (
            "required_source_evidence",
            "target_construction",
            "supervision_boundary",
        ):
            assert getattr(goal, field).strip() == getattr(goal, field) != ""
    by_id = {goal.goal_id: goal for goal in catalog.goals}
    assert by_id["learn-the-text"].eligible_input_families == IMPLEMENTED_INPUT_FAMILIES
    assert by_id["continue-a-passage"].eligible_input_families == IMPLEMENTED_INPUT_FAMILIES
    assert by_id["reproduce-a-recorded-change"].eligible_input_families == tuple(
        family for family in IMPLEMENTED_INPUT_FAMILIES if family != "source-code"
    )
    assert by_id["recover-a-section-from-its-heading"].eligible_input_families == (
        "markdown",
        "word-document",
        "html",
    )
    assert by_id["extract-a-structured-value"].eligible_input_families == (
        "source-code",
        "markdown",
        "word-document",
        "html",
    )
    assert "delimited-table" not in by_id["extract-a-structured-value"].eligible_input_families
    assert "json-records" not in by_id["extract-a-structured-value"].eligible_input_families
    assert "pdf-text" not in by_id["extract-a-structured-value"].eligible_input_families
    assert "pdf-text" not in by_id["recover-a-section-from-its-heading"].eligible_input_families
    for goal in catalog.goals:
        assert "source-chunks-unavailable" in goal.required_evidence_diagnostics, goal.goal_id
    assert by_id["recover-a-section-from-its-heading"].required_evidence_diagnostics == (
        "source-chunks-unavailable",
        "section-structure-unavailable",
    )


def _mutated(edit) -> dict:
    payload = _payload()
    edit(payload)
    return payload


@pytest.mark.parametrize(
    ("label", "edit", "message"),
    [
        (
            "unknown input family",
            lambda p: p["goals"][0].__setitem__(
                "eligible_input_families", ["plain-text", "ocr-image"]
            ),
            "eligible_input_families",
        ),
        (
            "families out of taxonomy order",
            lambda p: p["goals"][0].__setitem__(
                "eligible_input_families", ["markdown", "plain-text"]
            ),
            "taxonomy order",
        ),
        (
            "empty families",
            lambda p: p["goals"][0].__setitem__("eligible_input_families", []),
            "eligible_input_families",
        ),
        (
            "unknown diagnostic",
            lambda p: p["goals"][0].__setitem__(
                "required_evidence_diagnostics", ["summary-unavailable"]
            ),
            "required_evidence_diagnostics",
        ),
        (
            "non-claims drift",
            lambda p: p["goals"][0].__setitem__("non_claims", ["no-generated-text"]),
            "non_claims",
        ),
        (
            "review options drift",
            lambda p: p["goals"][0].__setitem__("review_policy_options", ["none"]),
            "review_policy_options",
        ),
        (
            "review default outside options",
            lambda p: p["goals"][0].__setitem__("review_policy_default", "optional"),
            "review_policy_default",
        ),
        (
            "export outside production catalog",
            lambda p: p["representations"][0].__setitem__(
                "compatible_generic_exports", ["minimal-v1"]
            ),
            "compatible_generic_exports",
        ),
        (
            "exports out of order",
            lambda p: p["representations"][0].__setitem__(
                "compatible_generic_exports", ["json", "split-jsonl-directory"]
            ),
            "taxonomy order",
        ),
        (
            "zero minimum target characters",
            lambda p: p["goals"][0]["curation_defaults"].__setitem__(
                "minimum_target_characters", 0
            ),
            "minimum_target_characters",
        ),
        (
            "ratio beyond ppm",
            lambda p: p["goals"][0]["curation_defaults"].__setitem__(
                "evaluation_ratio_ppm", 1_000_001
            ),
            "evaluation_ratio_ppm",
        ),
        (
            "surface balance-mode spelling",
            lambda p: p["goals"][0]["curation_defaults"].__setitem__(
                "balance_mode", "primary-source-cap"
            ),
            "balance_mode",
        ),
        (
            "negative per-source cap",
            lambda p: p["goals"][0]["curation_defaults"].__setitem__(
                "maximum_records_per_primary_source", -5
            ),
            "executable policy",
        ),
        (
            "cap without balance mode",
            lambda p: p["goals"][0]["curation_defaults"].__setitem__(
                "maximum_records_per_primary_source", 3
            ),
            "executable policy",
        ),
        (
            "balance mode without cap",
            lambda p: p["goals"][0]["curation_defaults"].__setitem__(
                "balance_mode", "primary_source_cap"
            ),
            "executable policy",
        ),
        (
            "control character in split seed",
            lambda p: p["goals"][0]["curation_defaults"].__setitem__(
                "split_seed", "veriformis\u0000v1"
            ),
            "split_seed",
        ),
        (
            "unknown curation key",
            lambda p: p["goals"][0]["curation_defaults"].__setitem__("shuffle", True),
            "shuffle",
        ),
        (
            "supervision boundary claims a summary",
            lambda p: p["goals"][0].__setitem__(
                "supervision_boundary", "The summary is the target."
            ),
            "summar",
        ),
    ],
)
def test_malformed_contract_fields_fail_closed(label, edit, message) -> None:
    with pytest.raises(GoalCatalogError) as excinfo:
        parse_goal_catalog(json.dumps(_mutated(edit)))
    assert message.lower() in excinfo.value.message.lower(), label
