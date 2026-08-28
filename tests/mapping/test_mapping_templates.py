"""Phase 7.10: packaged mapping templates and U1–U7 anchors."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.identity import lossless_json_bytes, sha256_digest
from veriformis.mapping import mapping_confirmation_digest
from veriformis.mapping.models import FieldMapping
from veriformis.mapping.detect import mapping_detector_catalog
from veriformis.mapping.templates import (
    mapping_plan_from_template,
    mapping_template_catalog,
)
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService

RUNNER = CliRunner()
SERVICE = PipelineService()
DATA = Path(__file__).parents[2] / "src" / "veriformis" / "mapping" / "templates-v1.json"


def test_templates_are_canonical_digest_bound_and_shared() -> None:
    stored = DATA.read_text(encoding="utf-8")
    payload = json.loads(stored)
    canonical = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    assert stored == canonical
    catalog = mapping_template_catalog()
    schemas = {item.row_schema for item in catalog.templates}
    assert schemas == {
        "text",
        "prompt_completion",
        "instruction_output",
        "messages",
        "label-classification",
        "preference-pair",
        "tool-call-conversation",
    }
    detector_shapes = {
        tuple(item.required_paths) for item in mapping_detector_catalog().detectors
    }
    template_shapes = {
        tuple(pair["source_path"] for pair in item.field_mappings)
        for item in catalog.templates
    }
    assert detector_shapes == template_shapes
    python = json.dumps(
        SERVICE.discover_mapping_templates(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    cli = RUNNER.invoke(app, ["mapping-templates"])
    assert cli.exit_code == 0, cli.output
    tools = {
        tool.name: tool.fn
        for tool in create_mcp_server(SERVICE)._tool_manager.list_tools()
    }
    mcp = tools["mapping_templates"]()
    assert python == cli.output.strip()
    assert python == mcp.strip()
    text_template = next(
        item for item in catalog.templates if item.template_id == "flat-text"
    )
    mappings = tuple(
        FieldMapping.create(source_path=item["source_path"], target_key=item["target_key"])
        for item in text_template.field_mappings
    )
    confirmation = mapping_confirmation_digest(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        field_mappings=mappings,
        source_digests=(("rows.jsonl", sha256_digest(b'{"text":"A"}\n')),),
    )
    plan = mapping_plan_from_template(text_template, confirmation_digest=confirmation)
    assert plan.row_schema == "text"
    assert plan.container_kind == "jsonl"
    assert text_template.template_digest == sha256_digest(
        lossless_json_bytes(
            text_template.model_dump(mode="json", exclude={"template_digest"})
        )
    )


def test_u1_through_u7_have_current_tree_anchors() -> None:
    root = Path(__file__).parent
    anchors = {
        "U1": root / "test_input_modes.py",
        "U2": root / "test_mapping_detect.py",
        "U3": root / "test_mapping_preview.py",
        "U4": root / "test_mapping_provenance.py",
        "U5": root / "test_jsonl_row_mapping.py",
        "U6": root / "test_membership.py",
        "U7": root / "test_json_csv_roundtrip.py",
    }
    for criterion, path in anchors.items():
        assert path.is_file(), f"{criterion} missing {path.name}"
