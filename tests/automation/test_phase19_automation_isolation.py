"""Phase 19 isolation: pipeline/v1 stays, no Hub execute, no MCP spec tools."""

from __future__ import annotations

import ast
import inspect
import tomllib
from pathlib import Path

import pytest

from veriformis.cli import app
from veriformis.goals import recipe_defaults
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.quality.gates import V1_QUALITY_GATES
from veriformis.recipes.pipeline_spec import (
    PIPELINE_SCHEMA_VERSION,
    PipelineSpecError,
    _STAGE_CONFIG_KEYS,
    _STAGE_ORDER,
    _TOP_LEVEL_KEYS,
    pipeline_spec_from_dict,
)
from veriformis.recipes.runner import run_pipeline_spec


ROOT = Path(__file__).resolve().parents[2]
_FORBIDDEN_OPERATIONS = frozenset(
    {
        "generator",
        "generator-pass",
        "generator_pass",
        "hub-upload",
        "hub_upload",
        "install-extension",
        "install_extension",
        "install-plugin",
        "install_plugin",
        "quality-report",
        "quality_report",
    }
)
_PROJECT_SPEC_OPERATIONS = frozenset(
    {
        "hub-upload",
        "hub_upload",
    }
)
_NETWORK_MODULES = frozenset(
    {
        "httpx",
        "huggingface_hub",
        "openai",
        "requests",
    }
)
_COMPILE_SOURCES = (
    ROOT / "src/veriformis/recipes/runner.py",
    ROOT / "src/veriformis/recipes/pipeline_spec.py",
    ROOT / "src/veriformis/pipeline/service.py",
)


def _minimal_pipeline_document(**extra: object) -> dict[str, object]:
    document: dict[str, object] = {
        "schema_version": PIPELINE_SCHEMA_VERSION,
        "workspace": "/tmp/veriformis-phase19-workspace",
        "sources": ["source.md"],
        "stages": {
            "parse": {},
            "seal": {"out": "/tmp/veriformis-phase19.vfbundle"},
        },
    }
    document.update(extra)
    return document


def _cli_names() -> set[str]:
    return {command.name for command in app.registered_commands}


def _mcp_names() -> set[str]:
    return {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}


def test_pipeline_schema_remains_v1_without_map() -> None:
    assert PIPELINE_SCHEMA_VERSION == "veriformis.pipeline/v1"
    assert "map" not in _STAGE_ORDER
    assert "export" not in _STAGE_ORDER
    assert _STAGE_ORDER == (
        "parse",
        "clean",
        "chunk",
        "construct",
        "curate",
        "split",
        "format",
        "validate",
        "seal",
    )
    assert "mode" not in _TOP_LEVEL_KEYS
    assert "map" not in _TOP_LEVEL_KEYS
    assert "export" not in _TOP_LEVEL_KEYS
    assert "mode" not in _STAGE_CONFIG_KEYS["parse"]
    assert _STAGE_CONFIG_KEYS["parse"] == frozenset()


def test_pipeline_spec_refuses_mode_map_export_and_unknown_keys() -> None:
    base = Path("/tmp")
    loaded = pipeline_spec_from_dict(_minimal_pipeline_document(), base_dir=base)
    assert loaded.schema_version == PIPELINE_SCHEMA_VERSION
    assert "map" not in loaded.stages
    with pytest.raises(PipelineSpecError, match="unknown top-level key"):
        pipeline_spec_from_dict(
            _minimal_pipeline_document(mode="dataset-row"),
            base_dir=base,
        )
    with pytest.raises(PipelineSpecError, match="unknown top-level key"):
        pipeline_spec_from_dict(
            _minimal_pipeline_document(export={"container": "json"}),
            base_dir=base,
        )
    with pytest.raises(PipelineSpecError, match="unsupported pipeline schema"):
        pipeline_spec_from_dict(
            _minimal_pipeline_document(schema_version="veriformis.project-spec/v1"),
            base_dir=base,
        )
    mapped = _minimal_pipeline_document()
    mapped["stages"] = {
        "parse": {},
        "map": {},
        "seal": {"out": "/tmp/out.vfbundle"},
    }
    with pytest.raises(PipelineSpecError, match="unknown names"):
        pipeline_spec_from_dict(mapped, base_dir=base)
    parse_mode = _minimal_pipeline_document()
    parse_mode["stages"] = {
        "parse": {"mode": "dataset-row"},
        "seal": {"out": "/tmp/out.vfbundle"},
    }
    with pytest.raises(PipelineSpecError, match="unknown key"):
        pipeline_spec_from_dict(parse_mode, base_dir=base)


def test_run_exists_and_parse_omits_mode() -> None:
    assert "run" in _cli_names()
    parse_block = inspect.getsource(run_pipeline_spec).split(
        'if stage == "parse":',
        1,
    )[1].split("elif stage ==", 1)[0]
    assert "mode" not in parse_block
    assert "source_root=spec.source_root" in parse_block


def test_public_surfaces_have_no_hub_generator_or_quality_report() -> None:
    cli_names = _cli_names()
    mcp_names = _mcp_names()
    assert cli_names.isdisjoint(_FORBIDDEN_OPERATIONS)
    assert mcp_names.isdisjoint(_FORBIDDEN_OPERATIONS)
    service = PipelineService()
    for name in _FORBIDDEN_OPERATIONS:
        assert not hasattr(service, name.replace("-", "_"))
    assert "run_pipeline" in mcp_names
    assert "quality-report" not in cli_names
    assert "quality_report" not in mcp_names


def test_package_metadata_has_no_hub_token() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "HF_TOKEN" not in text
    assert "hf_token" not in text.lower()
    project = tomllib.loads(text)
    dependencies = " ".join(project["project"]["dependencies"])
    assert "huggingface_hub" not in dependencies
    assert "httpx" not in dependencies
    assert "requests" not in dependencies
    assert project["project"]["scripts"] == {"veriformis": "veriformis.cli:main"}


def test_default_review_policy_stays_none() -> None:
    assert recipe_defaults().review_policy == "none"
    assert recipe_defaults().construction.require_review is False


def test_quality_gates_remain_preview_only() -> None:
    assert V1_QUALITY_GATES
    assert all(item.admitted_to_block is False for item in V1_QUALITY_GATES)


def test_core_compile_names_no_network_client() -> None:
    for path in _COMPILE_SOURCES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        assert names.isdisjoint(_NETWORK_MODULES), path
        assert imported.isdisjoint(_NETWORK_MODULES), path


def test_project_spec_execute_surfaces_keep_hub_absent() -> None:
    assert (ROOT / "docs/contracts/project-spec-v1.md").is_file()
    assert (ROOT / "docs/contracts/project-lock-v1.md").is_file()
    assert (ROOT / "docs/contracts/project-spec-diagnostic-v1.md").is_file()
    assert (ROOT / "src/veriformis/automation/spec.py").is_file()
    assert not (ROOT / "docs/adr/0020-publication-boundary.md").exists()
    cli_names = _cli_names()
    mcp_names = _mcp_names()
    assert cli_names.isdisjoint(_PROJECT_SPEC_OPERATIONS)
    assert mcp_names.isdisjoint(_PROJECT_SPEC_OPERATIONS)
    assert "spec-schema" in cli_names
    assert "spec-dry-run" in cli_names
    assert "spec-lock" in cli_names
    assert "env-inspect" in cli_names
    assert "spec-run" in cli_names
    assert "spec-resume" in cli_names
    assert "spec_run" not in mcp_names
    assert "spec_resume" not in mcp_names
    assert "spec_dry_run" not in mcp_names
    assert "hub_upload" not in mcp_names
