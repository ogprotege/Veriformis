"""Phase 17 isolation: SFT-only families; no admission contract or generator."""

from __future__ import annotations

import ast
import inspect
import tomllib
from pathlib import Path

from veriformis.cli import app
from veriformis.construction import constructors as constructor_module
from veriformis.contracts import (
    DETERMINISTIC_V1_OBJECTIVE_KINDS,
    V1_FINISHED_DATASET_GATES,
    V1_ROW_SCHEMA_KINDS,
)
from veriformis.datasets.serialization import V1_ROW_SCHEMAS
from veriformis.datasets.splitting import V1_SPLIT_ALGORITHM
from veriformis.exports.constrained_csv import _COLUMNS_BY_ROW_SCHEMA
from veriformis.extensions.protocol import EXTENSION_KINDS
from veriformis.goals import goal_catalog
from veriformis.mapping.models import ROW_SCHEMA_PAYLOAD_KEYS
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.profiles import profile_admission_catalog
from veriformis.quality.gates import V1_QUALITY_GATES
from veriformis.review.models import QUEUE_KINDS
from veriformis.taxonomy import (
    EXPLICITLY_UNSUPPORTED_TRAINING_FAMILIES,
    IMPLEMENTED_TRAINING_FAMILIES,
    LOSS_POLICY_IDS,
    PLANNED_TRAINING_FAMILIES,
    TAXONOMY_AXES,
)


ROOT = Path(__file__).resolve().parents[2]
_FORBIDDEN_OPERATIONS = frozenset(
    {
        "admit-family",
        "admit_family",
        "family-admission",
        "family_admission",
        "generator",
        "generator-pass",
        "generator_pass",
    }
)
_PLANNED_FAMILIES = (
    "preference-and-ranking",
    "explicit-label-classification",
    "tool-call-conversations",
    "stepwise-supervision",
    "pre-tokenized-training",
    "governed-generated-candidates",
)
_ADVANCED_TOKENS = (
    "preference",
    "ranking",
    "classification",
    "label",
    "tool-call",
    "tool_call",
    "stepwise",
    "chosen",
    "rejected",
)


def test_planned_families_remain_planned_and_multimodal_unsupported() -> None:
    assert IMPLEMENTED_TRAINING_FAMILIES == (
        "source-grounded-language-modeling",
        "source-grounded-supervised-fine-tuning",
    )
    assert PLANNED_TRAINING_FAMILIES == _PLANNED_FAMILIES
    assert EXPLICITLY_UNSUPPORTED_TRAINING_FAMILIES == ("multimodal-training",)


def test_v1_row_schemas_remain_the_four_sft_shapes() -> None:
    assert V1_ROW_SCHEMAS == (
        "text",
        "prompt_completion",
        "instruction_output",
        "messages",
    )
    assert V1_ROW_SCHEMA_KINDS == V1_ROW_SCHEMAS
    assert tuple(ROW_SCHEMA_PAYLOAD_KEYS) == V1_ROW_SCHEMAS
    assert LOSS_POLICY_IDS == (
        "full-sequence",
        "completion-only",
        "output-only",
        "final-assistant-suffix",
    )


def test_messages_still_require_exactly_two_turns() -> None:
    mapping_source = inspect.getsource(
        __import__(
            "veriformis.mapping.execute",
            fromlist=["_require_two_turn_messages"],
        )._require_two_turn_messages
    )
    serialization_source = (
        ROOT / "src/veriformis/datasets/serialization.py"
    ).read_text(encoding="utf-8")
    assert "exactly two user/assistant turns" in mapping_source
    assert "len(value) != 2" in mapping_source
    assert "messages payload requires exactly two ordered turns" in serialization_source


def test_mapping_still_has_only_sft_payloads() -> None:
    assert ROW_SCHEMA_PAYLOAD_KEYS == {
        "text": ("text",),
        "prompt_completion": ("prompt", "completion"),
        "instruction_output": ("instruction", "input", "output"),
        "messages": ("messages",),
    }
    payload_names = {name for keys in ROW_SCHEMA_PAYLOAD_KEYS.values() for name in keys}
    assert payload_names.isdisjoint(
        {"chosen", "rejected", "label", "tools", "steps", "ranking"}
    )
    mapping_docs = (ROOT / "docs/mapping.md").read_text(encoding="utf-8")
    assert (
        "No preference, tool-call, multimodal, or arbitrary multi-turn chat family."
        in mapping_docs
    )


def test_constructors_remain_five_sft_constructors() -> None:
    constructors = constructor_module._CONSTRUCTORS
    assert isinstance(constructors, dict)
    assert len(constructors) == 5
    assert set(constructors) == {
        ("veriformis.constructor.full-text", "1"),
        ("veriformis.constructor.continuation", "1"),
        ("veriformis.constructor.section-reconstruction", "1"),
        ("veriformis.constructor.before-after-transformation", "1"),
        ("veriformis.constructor.structured-field", "1"),
    }
    assert DETERMINISTIC_V1_OBJECTIVE_KINDS == (
        "full_text",
        "continuation",
        "section_reconstruction",
        "before_after_transformation",
        "structured_field",
    )
    joined = " ".join(selector[0] for selector in constructors)
    assert all(token not in joined for token in _ADVANCED_TOKENS)


def test_goal_catalog_still_resolves_only_sft_objectives() -> None:
    catalog = goal_catalog()
    assert tuple(goal.objective for goal in catalog.goals) == DETERMINISTIC_V1_OBJECTIVE_KINDS
    joined = " ".join(goal.goal_id for goal in catalog.goals)
    assert all(family not in joined for family in _PLANNED_FAMILIES)


def test_no_generator_pass_exists_in_product_code() -> None:
    hits = [
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "src/veriformis").rglob("*.py")
        if "GeneratorPass" in path.read_text(encoding="utf-8")
    ]
    assert hits == []
    contract = (ROOT / "docs/product-contract.md").read_text(encoding="utf-8")
    assert "future `GeneratorPass` is optional, post-v1 work" in contract


def test_trainer_profiles_still_refuse_advanced_dataset_types() -> None:
    required = {
        "preference",
        "tools",
        "unpaired-preference",
        "vision",
    }
    for record in profile_admission_catalog().records:
        refused = set(record.refused_dataset_types)
        assert required <= refused, record.profile_id
        assert set(record.admitted_row_schemas) <= set(V1_ROW_SCHEMAS)


def test_constrained_csv_still_admits_only_three_flat_sft_schemas() -> None:
    assert dict(_COLUMNS_BY_ROW_SCHEMA) == {
        "instruction_output": ("instruction", "input", "output"),
        "prompt_completion": ("prompt", "completion"),
        "text": ("text",),
    }
    assert "messages" not in _COLUMNS_BY_ROW_SCHEMA


def test_adr_0017_still_forbids_a_loader_and_family_admission() -> None:
    adr = (ROOT / "docs/adr/0017-no-untrusted-extension-loader.md").read_text(
        encoding="utf-8"
    )
    assert "Phase 16 does not install an untrusted loader." in adr
    assert "Phase 17 MUST NOT admit new families through this protocol." in adr
    assert not (ROOT / "src/veriformis/extensions/loader.py").exists()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    assert project["scripts"] == {"veriformis": "veriformis.cli:main"}
    assert "entry-points" not in project


def test_extension_protocol_has_no_family_kind() -> None:
    assert EXTENSION_KINDS == (
        "source-parser",
        "row-mapper",
        "deterministic-constructor",
        "quality-check",
        "container-exporter",
        "consumer-profile",
    )
    assert all("family" not in kind for kind in EXTENSION_KINDS)
    assert (ROOT / "docs/contracts/advanced-family-admission-v1.md").is_file()
    assert (ROOT / "src/veriformis/families/admission.py").is_file()
    assert not (ROOT / "src/veriformis/families.py").exists()
    assert not (ROOT / "src/veriformis/families/execute.py").exists()
    from veriformis.families import __all__ as exported

    assert "load_family_admission" in exported
    assert "create_family_admission" in exported
    assert "keyed_leakage_groups" in exported
    assert (ROOT / "src/veriformis/families/leakage.py").is_file()
    assert "admit" not in exported
    assert "execute" not in exported


def test_split_quality_and_review_hooks_are_still_sft_only() -> None:
    assert V1_SPLIT_ALGORITHM == "transitive-leakage-prefix-v1"
    assert V1_QUALITY_GATES
    assert all(item.admitted_to_block is False for item in V1_QUALITY_GATES)
    assert QUEUE_KINDS == (
        "conflict",
        "construction-pending",
        "detector-finding",
        "mapping",
        "near-duplicate",
        "ocr-review",
        "parser-degradation",
        "sample-acceptance",
    )
    assert set(QUEUE_KINDS).isdisjoint(
        {
            "label-conflict",
            "preference-inconsistency",
            "tool-trace-incomplete",
            "stepwise-gap",
        }
    )


def test_public_surfaces_have_no_family_or_generator_operation() -> None:
    cli_names = {command.name for command in app.registered_commands}
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert cli_names.isdisjoint(_FORBIDDEN_OPERATIONS)
    assert mcp_names.isdisjoint(_FORBIDDEN_OPERATIONS)
    service = PipelineService()
    for name in _FORBIDDEN_OPERATIONS:
        assert not hasattr(service, name.replace("-", "_"))


def test_taxonomy_still_has_seven_axes() -> None:
    assert TAXONOMY_AXES == (
        "training_family",
        "objective",
        "semantic_row",
        "physical_container",
        "consumer_profile",
        "loss_policy",
        "input_family",
    )


def test_seventeen_finished_dataset_gates_are_unchanged() -> None:
    assert len(V1_FINISHED_DATASET_GATES) == 17
    assert V1_FINISHED_DATASET_GATES[-1] == "snapshot"


def test_pipeline_service_ast_does_not_name_a_generator() -> None:
    source = (ROOT / "src/veriformis/pipeline/service.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert "GeneratorPass" not in names
    assert "httpx" not in names
    assert "openai" not in names
