"""Phase 19.2: additive veriformis.project-spec/v1 pin. Loading is not execute."""

from __future__ import annotations

from pathlib import Path

import pytest

from veriformis.contracts import (
    PROJECT_SPEC_CONTRACT_ID,
    PROJECT_SPEC_CONTRACT_VERSION,
    PROJECT_SPEC_SCHEMA_ID,
)
from veriformis.errors import ProjectSpecError
from veriformis.identity import derive_id
from veriformis.mcp.server import create_mcp_server
from veriformis.recipes.pipeline_spec import (
    PIPELINE_SCHEMA_VERSION,
    PipelineSpecError,
    load_pipeline_spec,
    pipeline_spec_from_dict,
)


ROOT = Path(__file__).resolve().parents[2]
DIGEST = "a" * 64
MAPPING_PLAN_ID = derive_id(
    "mpl",
    {
        "confirmation_digest": DIGEST,
        "goal_id": "learn-the-text",
    },
)
PIPELINE = {
    "schema_version": PIPELINE_SCHEMA_VERSION,
    "workspace": "/tmp/veriformis-project-spec-ws",
    "sources": ["source.md"],
    "stages": {
        "parse": {},
        "seal": {"out": "/tmp/veriformis-project-spec.vfbundle"},
    },
}


def _spec(**overrides: object):
    from veriformis.automation import create_project_spec

    defaults: dict[str, object] = {
        "mode": "document-source",
        "goal_id": "learn-the-text",
        "pipeline": PIPELINE,
    }
    defaults.update(overrides)
    return create_project_spec(**defaults)


def test_document_source_spec_loads_and_is_not_execute() -> None:
    from veriformis.automation import load_project_spec

    spec = _spec()
    loaded = load_project_spec(spec.model_dump(mode="json"))
    assert loaded == spec
    assert loaded.schema_id == PROJECT_SPEC_SCHEMA_ID
    assert loaded.contract_id == PROJECT_SPEC_CONTRACT_ID
    assert loaded.contract_version == PROJECT_SPEC_CONTRACT_VERSION
    assert loaded.mode == "document-source"
    assert loaded.mapping is None
    assert loaded.spec_id == derive_id(
        "psp",
        spec.model_dump(mode="json", exclude={"spec_id"}, exclude_none=True),
    )
    assert loaded.generation_allowed is False
    assert loaded.plugin_install_allowed is False
    assert loaded.publication_allowed is False


def test_dataset_row_spec_requires_confirmation_digest() -> None:
    spec = _spec(
        mode="dataset-row",
        goal_id="learn-the-text",
        mapping={
            "mapping_plan_id": MAPPING_PLAN_ID,
            "confirmation_digest": DIGEST,
            "plan_path": "mapping-plan.json",
        },
        pipeline={
            **PIPELINE,
            "sources": ["rows.jsonl"],
        },
    )
    assert spec.mode == "dataset-row"
    assert spec.mapping is not None
    assert spec.mapping.confirmation_digest == DIGEST


def test_unconfirmed_mapping_fails_closed() -> None:
    with pytest.raises(ProjectSpecError, match="unconfirmed mapping"):
        _spec(mode="dataset-row", mapping=None)
    with pytest.raises(ProjectSpecError, match="unconfirmed mapping"):
        _spec(
            mode="dataset-row",
            mapping={
                "mapping_plan_id": MAPPING_PLAN_ID,
                "confirmation_digest": "",
            },
        )


def test_mixed_fused_members_fail_closed() -> None:
    with pytest.raises(ProjectSpecError, match="fusing"):
        _spec(
            mode="mixed",
            mapping={
                "mapping_plan_id": MAPPING_PLAN_ID,
                "confirmation_digest": DIGEST,
            },
            pipeline={
                **PIPELINE,
                "sources": ["source.md", "rows.jsonl"],
            },
        )


def test_family_on_refusing_profile_fails_closed() -> None:
    with pytest.raises(ProjectSpecError, match="refusing profile"):
        _spec(
            mode="dataset-row",
            goal_id="prefer-chosen-over-rejected",
            mapping={
                "mapping_plan_id": MAPPING_PLAN_ID,
                "confirmation_digest": DIGEST,
            },
            consumer_profile="trl",
            pipeline={
                **PIPELINE,
                "sources": ["pairs.jsonl"],
            },
        )
    with pytest.raises(ProjectSpecError, match="refusing profile"):
        _spec(
            mode="dataset-row",
            goal_id=None,
            preset_id="prefer-chosen-over-rejected.safe",
            mapping={
                "mapping_plan_id": MAPPING_PLAN_ID,
                "confirmation_digest": DIGEST,
            },
            consumer_profile="trl",
            pipeline={
                **PIPELINE,
                "sources": ["pairs.jsonl"],
            },
        )


def test_embedded_pipeline_null_stage_keeps_identity() -> None:
    pipeline = {
        **PIPELINE,
        "stages": {"parse": None, "seal": {"out": "/tmp/out.vfbundle"}},
    }
    spec = _spec(pipeline=pipeline)
    from veriformis.automation import load_project_spec

    loaded = load_project_spec(spec.model_dump(mode="json"))
    assert loaded == spec
    assert loaded.pipeline is not None
    assert loaded.pipeline["stages"]["parse"] is None


def test_mixed_pipeline_ref_fails_closed_without_reading() -> None:
    with pytest.raises(ProjectSpecError, match="cannot prove members are not fused"):
        _spec(
            mode="mixed",
            mapping={
                "mapping_plan_id": MAPPING_PLAN_ID,
                "confirmation_digest": DIGEST,
            },
            pipeline=None,
            pipeline_ref="fused.yaml",
        )


def test_automation_import_is_self_contained() -> None:
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-c", "from veriformis.automation import load_project_spec"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_unknown_key_fails_closed() -> None:
    from veriformis.automation import load_project_spec

    payload = _spec().model_dump(mode="json")
    payload["hub_token"] = "secret"
    with pytest.raises(ProjectSpecError, match="unknown field hub_token"):
        load_project_spec(payload)


def test_unknown_version_names_requested_and_supported() -> None:
    from veriformis.automation import load_project_spec

    payload = _spec().model_dump(mode="json")
    payload["contract_version"] = 2
    with pytest.raises(
        ProjectSpecError,
        match=(
            r"unknown project spec contract version: requested "
            r"contract_id='veriformis.project-spec' "
            r"contract_version=2 "
            r"schema_id='veriformis.project-spec/v1', supported "
            r"contract_id='veriformis.project-spec' "
            r"contract_version=1 "
            r"schema_id='veriformis.project-spec/v1'"
        ),
    ):
        load_project_spec(payload)


def test_unknown_mode_fails_closed() -> None:
    with pytest.raises(ProjectSpecError, match="unknown input mode"):
        _spec(mode="parquet")


def test_document_source_refuses_mapping() -> None:
    with pytest.raises(ProjectSpecError, match="document-source cannot name mapping"):
        _spec(
            mode="document-source",
            mapping={
                "mapping_plan_id": MAPPING_PLAN_ID,
                "confirmation_digest": DIGEST,
            },
        )


def test_export_plan_is_pin_only_and_overwrite_refuses() -> None:
    spec = _spec(
        export={
            "container": "split-jsonl-directory",
            "profile": "trl",
            "overwrite": "refuse",
        }
    )
    assert spec.export is not None
    assert spec.export.container == "split-jsonl-directory"
    assert spec.export.profile == "trl"
    assert spec.export.overwrite == "refuse"
    with pytest.raises(ProjectSpecError, match="unknown field"):
        _spec(
            export={
                "container": "json",
                "overwrite": "refuse",
                "destination": "/tmp/out",
            }
        )


def test_admitted_sft_profile_is_allowed() -> None:
    spec = _spec(consumer_profile="trl")
    assert spec.consumer_profile == "trl"


def test_unadmitted_profile_fails_closed() -> None:
    with pytest.raises(ProjectSpecError, match="independently admitted"):
        _spec(consumer_profile="unsloth")


def test_pipeline_v1_fixtures_still_load(tmp_path: Path) -> None:
    text = """
schema_version: veriformis.pipeline/v1
workspace: ws
sources:
  - doc.txt
stages:
  parse: {}
  chunk:
    strategy: sentence
    size: 200
    overlap: 20
""".strip()
    path = tmp_path / "pipeline.yaml"
    path.write_text(text, encoding="utf-8")
    loaded = load_pipeline_spec(path)
    assert loaded.schema_version == PIPELINE_SCHEMA_VERSION
    assert "map" not in loaded.stages
    with pytest.raises(PipelineSpecError, match="unknown top-level key"):
        pipeline_spec_from_dict(
            {
                "schema_version": PIPELINE_SCHEMA_VERSION,
                "workspace": "ws",
                "sources": ["doc.txt"],
                "mode": "dataset-row",
                "stages": {"parse": {}},
            },
            base_dir=tmp_path,
        )


def test_project_spec_mcp_has_no_hub_or_quality_report() -> None:
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert "project_spec" not in mcp_names
    assert "hub_upload" not in mcp_names
    assert "quality_report" not in mcp_names


def test_contract_document_exists() -> None:
    path = ROOT / "docs/contracts/project-spec-v1.md"
    text = path.read_text(encoding="utf-8")
    assert PROJECT_SPEC_SCHEMA_ID in text
    assert "Loading a spec is not execute" in text
    assert "veriformis.pipeline/v1" in text
    assert "no-hub-upload" in text
    assert "CLI and MCP wrap the same" in text
