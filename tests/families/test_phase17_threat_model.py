"""Phase 17.9: ADR-0018 is policy. There is still no compile-path generator."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

import pytest

from veriformis.cli import app
from veriformis.families.admission import FamilyAdmissionError, load_family_admission
from veriformis.families.classification import classification_admission
from veriformis.identity import derive_id
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService


ROOT = Path(__file__).resolve().parents[2]
ADR = ROOT / "docs/adr/0018-no-compile-path-generator.md"
_FORBIDDEN_OPERATIONS = frozenset(
    {
        "generate",
        "generator",
        "generator-pass",
        "generator_pass",
        "llm-complete",
        "llm_complete",
        "complete-prompt",
        "complete_prompt",
    }
)
_HOSTED_EXTRA_NAMES = frozenset(
    {
        "generate",
        "generator",
        "openai",
        "anthropic",
        "llm",
        "hosted-model",
        "hosted_model",
    }
)


def test_adr_0018_records_decision_a_and_required_threats() -> None:
    text = ADR.read_text(encoding="utf-8")
    assert text.startswith("# ADR-0018 — No Compile-Path Generator in Phase 17\n")
    assert "**Status:** Accepted" in text
    assert "**Decision A.** Phase 17 does not install a compile-path generator." in text
    for heading in (
        "Offline default vs explicit network opt-in",
        "Model identity, revision, prompt/system digests, parameters",
        "Source evidence supplied to the model",
        "Output identity, reproducibility limit, cost/network disclosure",
        "Required review policy",
        "Isolation from deterministic v1 release claims",
        "Dataset-project code execution",
    ):
        assert heading in text
    assert "Decision B" in text
    assert "Decision C" in text
    assert "This item is policy. It adds no generator." in text
    assert "ADR-0017 Decision A stands" in text


def test_no_generator_module_or_hosted_model_extra() -> None:
    assert not (ROOT / "src/veriformis/generation").exists()
    assert not (ROOT / "src/veriformis/generator.py").exists()
    assert not (ROOT / "src/veriformis/construction/generator.py").exists()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    extras = project["optional-dependencies"]
    assert set(extras) == {
        "axolotl",
        "columnar",
        "llama-factory",
        "mlx-lm",
        "ocr",
        "test",
        "trl",
        "unsloth",
    }
    assert set(extras).isdisjoint(_HOSTED_EXTRA_NAMES)
    for name, packages in extras.items():
        if name == "test":
            continue
        assert packages == []


def test_public_surfaces_still_have_no_generate_operation() -> None:
    cli_names = {command.name for command in app.registered_commands}
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert cli_names.isdisjoint(_FORBIDDEN_OPERATIONS)
    assert mcp_names.isdisjoint(_FORBIDDEN_OPERATIONS)
    service = PipelineService()
    for name in _FORBIDDEN_OPERATIONS:
        assert not hasattr(service, name.replace("-", "_"))


def test_pipeline_and_construction_still_name_no_generator() -> None:
    forbidden = {"GeneratorPass", "openai", "anthropic", "httpx", "requests"}
    for relative in (
        "src/veriformis/pipeline/service.py",
        "src/veriformis/construction/constructors.py",
        "src/veriformis/families/admission.py",
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        tree = ast.parse(source)
        names = {
            node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
        }
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert names.isdisjoint(forbidden), relative
        assert imported.isdisjoint(forbidden), relative
        assert "GeneratorPass" not in source


def test_generation_allowed_remains_false_after_adr() -> None:
    pin = classification_admission()
    assert pin.generation_allowed is False
    payload = pin.model_dump(mode="json")
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
