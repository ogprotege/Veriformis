"""MCP tools are thin adapters: identical results to PipelineService."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from veriformis.errors import ConstructionError
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.taxonomy import implemented_discovery


def _tool_map(server):
    manager = server._tool_manager
    return {tool.name: tool.fn for tool in manager.list_tools()}


def _call(fn, *args, **kwargs):
    """Call one registered MCP tool regardless of sync wrapper choice."""
    result = fn(*args, **kwargs)
    if hasattr(result, "__await__"):
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(result)
    return result


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
    api_verify = service.verify(
        api_bundle,
        manifest_sha256=api_seal.publication.manifest_sha256,
    )
    assert api_verify.verification is not None

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

    _call(parse_fn, [str(source)], str(mcp_ws), str(tmp_path))
    _call(clean_fn, str(mcp_ws))
    _call(chunk_fn, str(mcp_ws))
    _call(
        construct_fn,
        str(mcp_ws),
        "continuation",
        None,
        None,
        400_000,
        False,
    )
    _call(
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
    _call(split_fn, str(mcp_ws))
    _call(format_fn, str(mcp_ws))
    validate_payload = json.loads(_call(validate_fn, str(mcp_ws)))
    assert validate_payload["exit_status"] == 0
    # Omit the integration argument: a core MCP seal is standalone by default.
    seal_payload = json.loads(_call(seal_fn, str(mcp_ws), str(mcp_bundle)))
    assert not {
        "aptus_handoff_path",
        "aptus_handoff_id",
        "assignment_digest",
    } & seal_payload.keys()
    assert not Path(f"{mcp_bundle.resolve()}.aptus-handoff.json").exists()

    mcp_manifest_sha = seal_payload["publication"]["manifest_sha256"]
    mcp_verify = json.loads(
        _call(tools["verify"], str(mcp_bundle), mcp_manifest_sha)
    )
    assert mcp_verify["verification"]["trust_grade"] == "external_digest"
    assert (
        mcp_verify["verification"]["content_root_sha256"]
        == api_verify.verification.content_root_sha256
    )
    assert (
        mcp_verify["verification"]["declared_record_count"]
        == api_verify.verification.declared_record_count
    )
    for relative in (
        "data/train.jsonl",
        "data/evaluation.jsonl",
        "metadata/row-provenance.jsonl",
    ):
        assert (mcp_bundle / relative).read_bytes() == (api_bundle / relative).read_bytes()


@pytest.mark.aptus_integration
def test_mcp_seal_can_explicitly_opt_in_to_aptus_handoff(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text(
        "First paragraph for explicit MCP handoff coverage.\n\n"
        "Second paragraph preserves a supervised completion target.",
        encoding="utf-8",
    )
    workspace = tmp_path / "workspace"
    bundle = tmp_path / "out.vfbundle"
    service = PipelineService()
    service.parse([source], workspace, source_root=tmp_path)
    service.clean(workspace)
    service.chunk(workspace)
    service.construct(workspace, objective="continuation", split_ratio_ppm=400_000)
    service.curate(workspace, evaluation_required=False)
    service.split(workspace)
    service.format(workspace)
    assert service.validate(workspace).exit_status == 0

    tools = _tool_map(create_mcp_server(service))
    payload = json.loads(_call(tools["seal"], str(workspace), str(bundle), True))
    handoff_path = Path(payload["aptus_handoff_path"])
    assert handoff_path.is_file()
    assert payload["aptus_handoff_id"]
    assert payload["assignment_digest"]

    report = json.loads(
        _call(tools["consume_handoff"], str(handoff_path), str(bundle))
    )
    assert report["status"] == "accepted", report["findings"]
    assert report["verified_grade"] == "external_digest"


def test_mcp_server_registers_required_tools():
    server = create_mcp_server()
    tools = _tool_map(server)
    required = {
        "version",
        "taxonomy",
        "list_recipes",
        "collect",
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


def test_mcp_taxonomy_delegates_to_service_with_exact_json_parity():
    class TrackingPipelineService(PipelineService):
        def __init__(self) -> None:
            self.discovery_calls = 0

        def discover_taxonomy(self) -> dict[str, tuple[str, ...]]:
            self.discovery_calls += 1
            return super().discover_taxonomy()

    service = TrackingPipelineService()
    taxonomy = _tool_map(create_mcp_server(service))["taxonomy"]
    expected = json.dumps(
        dict(implemented_discovery()),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )

    payload = _call(taxonomy)

    assert payload == expected
    assert service.discovery_calls == 1
    assert "format" not in json.loads(payload)


def test_mcp_construct_refuses_incompatible_profile_before_workspace_open(tmp_path):
    missing = tmp_path / "not-created"
    construct = _tool_map(create_mcp_server())["construct"]

    with pytest.raises(ConstructionError, match="aptus-handoff-v1"):
        _call(
            construct,
            str(missing),
            "full_text",
            None,
            None,
            500_000,
            False,
            "aptus-handoff-v1",
        )

    assert not missing.exists()
