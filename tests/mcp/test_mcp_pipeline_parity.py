"""MCP tools are thin adapters: identical results to PipelineService."""

from __future__ import annotations

import json
from pathlib import Path

from veriformis.handoff import build_aptus_handoff, consume_aptus_handoff
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService


def _tool_map(server):
    manager = server._tool_manager
    return {tool.name: tool.fn for tool in manager.list_tools()}


def test_mcp_tools_match_pipeline_service_digests(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text(
        "First paragraph for MCP parity construction coverage.\n\n"
        "Second paragraph keeps multi-block evidence intact.",
        encoding="utf-8",
    )
    service = PipelineService()
    server = create_mcp_server(service)
    tools = _tool_map(server)

    api_ws = tmp_path / "api-ws"
    mcp_ws = tmp_path / "mcp-ws"
    api_bundle = tmp_path / "api.vfbundle"
    mcp_bundle = tmp_path / "mcp.vfbundle"

    # API path
    service.parse([source], api_ws, source_root=tmp_path)
    service.clean(api_ws)
    service.chunk(api_ws)
    service.construct(api_ws, objective="continuation", split_ratio_ppm=400_000)
    service.curate(api_ws, evaluation_required=False)
    service.split(api_ws)
    service.format(api_ws)
    assert service.validate(api_ws).exit_status == 0
    api_seal = service.seal(api_ws, api_bundle)
    assert api_seal.publication is not None
    api_handoff = build_aptus_handoff(
        api_bundle,
        expected_manifest_sha256=api_seal.publication.manifest_sha256,
    )

    # MCP tool path (same service class, independent workspace)
    parse_fn = tools["parse"]
    clean_fn = tools["clean"]
    chunk_fn = tools["chunk"]
    construct_fn = tools["construct"]
    curate_fn = tools["curate"]
    split_fn = tools["split"]
    format_fn = tools["format_rows"]
    validate_fn = tools["validate"]
    seal_fn = tools["seal"]

    # Tools may be async or sync
    def call(fn, *args, **kwargs):
        result = fn(*args, **kwargs)
        if hasattr(result, "__await__"):
            import asyncio

            result = asyncio.get_event_loop().run_until_complete(result)
        return result

    call(parse_fn, [str(source)], str(mcp_ws), str(tmp_path))
    call(clean_fn, str(mcp_ws))
    call(chunk_fn, str(mcp_ws))
    call(
        construct_fn,
        str(mcp_ws),
        "continuation",
        None,
        None,
        400_000,
        False,
    )
    call(
        curate_fn,
        str(mcp_ws),
        1,
        "none",
        None,
        500_000,
        False,
        "veriformis-v1",
        None,
    )
    call(split_fn, str(mcp_ws))
    call(format_fn, str(mcp_ws))
    validate_payload = json.loads(call(validate_fn, str(mcp_ws)))
    assert validate_payload["exit_status"] == 0
    seal_payload = json.loads(call(seal_fn, str(mcp_ws), str(mcp_bundle), True))
    assert "aptus_handoff_path" in seal_payload
    assert Path(seal_payload["aptus_handoff_path"]).is_file()

    mcp_handoff = build_aptus_handoff(
        mcp_bundle,
        expected_manifest_sha256=seal_payload["publication"]["manifest_sha256"],
    )
    assert mcp_handoff.assignment_digest == api_handoff.assignment_digest
    assert mcp_handoff.row_schema == api_handoff.row_schema
    assert mcp_handoff.content_root_sha256 == api_handoff.content_root_sha256
    assert mcp_handoff.train.sha256 == api_handoff.train.sha256
    assert mcp_handoff.evaluation.sha256 == api_handoff.evaluation.sha256

    report = consume_aptus_handoff(
        Path(seal_payload["aptus_handoff_path"]),
        bundle=mcp_bundle,
    )
    assert report.status == "accepted", report.findings


def test_mcp_server_registers_required_tools():
    server = create_mcp_server()
    tools = _tool_map(server)
    required = {
        "version",
        "list_recipes",
        "parse",
        "clean",
        "chunk",
        "construct",
        "curate",
        "split",
        "format_rows",
        "validate",
        "seal",
        "verify",
        "preview",
        "run_pipeline",
        "build_handoff",
        "consume_handoff",
    }
    assert required <= set(tools)
