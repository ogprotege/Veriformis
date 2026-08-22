"""Phase 4.8 CLI and MCP adapters share one strict export protocol."""

from __future__ import annotations

import asyncio
import json
import os
import threading

import pytest
from mcp.types import CallToolResult, TextContent
from typer.testing import CliRunner

import veriformis.cli as cli_module
import veriformis.mcp.server as mcp_module
from veriformis.cli import app
from veriformis.exports.api import (
    EXPORT_SURFACE_REQUEST_SCHEMA,
    ExportDiscovery,
    ExportInspectRequest,
    ExportOperationCancelled,
    ExportPartialPublicationError,
    export_discovery_response,
    export_dry_run_response,
    export_execution_response,
    export_inspection_response,
    export_response_json,
    export_verify_response,
)
from veriformis.identity import derive_id, lossless_json_bytes
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import ExportDiscoveryOutcome, PipelineService

from test_api import (
    _deep_export_tree,
    _dry_run_request,
    _execute_request,
    _materialize_bundle,
    _service,
    _verify_request,
)


async def _call_tool_async(server, name: str, arguments: dict[str, str]) -> str:
    result = await server.call_tool(name, arguments)
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    assert len(result.content) == 1
    content = result.content[0]
    assert isinstance(content, TextContent)
    return content.text


def _call_tool(server, name: str, arguments: dict[str, str]) -> str:
    return asyncio.run(_call_tool_async(server, name, arguments))


def _tool_names(server) -> set[str]:
    async def list_names() -> set[str]:
        return {tool.name for tool in await server.list_tools()}

    return asyncio.run(list_names())


async def _wait_for_thread_event(
    event: threading.Event,
    *,
    timeout: float = 1.0,
) -> None:
    if not await asyncio.to_thread(event.wait, timeout):
        pytest.fail(f"thread event was not set within {timeout} seconds")


class _DiscoveryOnlyPipeline:
    def __init__(self) -> None:
        self.discovery_calls = 0

    def discover_exports(self) -> ExportDiscoveryOutcome:
        self.discovery_calls += 1
        return ExportDiscoveryOutcome(discovery=ExportDiscovery.create(()))

    def dry_run_export(self, _request):
        raise AssertionError("malformed requests must fail before service dispatch")


class _InvalidUnicodeFailurePipeline:
    def discover_exports(self):
        raise ValueError("invalid \ud800 detail")


class _CancellablePipeline:
    def __init__(self, expected_operation: str) -> None:
        self.expected_operation = expected_operation
        self.started = threading.Event()
        self.cancelled = threading.Event()
        self.cleaned = threading.Event()
        self.escape = threading.Event()

    def _block(self, operation, _request, *, cancellation_check):
        assert operation == self.expected_operation
        assert cancellation_check is not None
        self.started.set()
        try:
            while not self.escape.wait(0.001):
                try:
                    cancellation_check()
                except ExportOperationCancelled:
                    self.cancelled.set()
                    raise
            raise AssertionError("MCP cancellation did not reach the worker")
        finally:
            self.cleaned.set()

    def inspect_export(self, request, *, cancellation_check=None):
        return self._block(
            "inspect",
            request,
            cancellation_check=cancellation_check,
        )

    def execute_export(self, request, *, cancellation_check=None):
        return self._block(
            "execute",
            request,
            cancellation_check=cancellation_check,
        )

    def verify_export(self, request, *, cancellation_check=None):
        return self._block(
            "verify",
            request,
            cancellation_check=cancellation_check,
        )


class _PublicationRacePipeline:
    def __init__(self, delegate, *, partial: bool) -> None:
        self.delegate = delegate
        self.partial = partial
        self.visible = threading.Event()
        self.release = threading.Event()

    def execute_export(self, request, *, cancellation_check=None):
        outcome = self.delegate.execute_export(
            request,
            cancellation_check=cancellation_check,
        )
        assert outcome.publication is not None
        self.visible.set()
        assert self.release.wait(1.0)
        if self.partial:
            raise ExportPartialPublicationError(
                outcome.publication,
                RuntimeError("post-visibility fixture failure"),
            )
        return outcome


def _cancellable_request(operation: str) -> str:
    value = {
        "destination_root": "/tmp/veriformis-export-adapter-test",
        "operation": operation,
        "schema_version": EXPORT_SURFACE_REQUEST_SCHEMA,
    }
    if operation != "inspect":
        value.update(
            {
                "bundle": "/tmp/veriformis-source-adapter-test.vfbundle",
                "consumer_id": None,
                "consumer_profile_version": None,
                "container_id": "adapter-test",
                "container_version": 1,
                "expected_export_plan_id": derive_id(
                    "export-plan",
                    {"fixture": operation},
                ),
                "expected_manifest_sha256": None,
                "overwrite_policy": "refuse",
                "source_trust_policy": "allow_self_consistent",
            }
        )
    return lossless_json_bytes(value).decode("utf-8")


def test_cli_and_mcp_export_discovery_have_exact_canonical_parity(monkeypatch):
    service = _DiscoveryOnlyPipeline()
    monkeypatch.setattr(cli_module, "_SERVICE", service)
    expected = export_response_json(
        export_discovery_response(ExportDiscovery.create(()))
    )

    cli_result = CliRunner().invoke(app, ["export", "discover"])
    mcp_result = _call_tool(
        create_mcp_server(service),
        "export_discover",
        {},
    )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.stdout == f"{expected}\n"
    assert mcp_result == expected
    assert service.discovery_calls == 2
    assert json.loads(expected)["result"]["profiles"] == []


def test_cli_and_mcp_reject_the_same_strict_malformed_request(monkeypatch):
    service = _DiscoveryOnlyPipeline()
    monkeypatch.setattr(cli_module, "_SERVICE", service)
    request_json = lossless_json_bytes(
        {
            "operation": "dry_run",
            "schema_version": EXPORT_SURFACE_REQUEST_SCHEMA,
        }
    ).decode("utf-8")

    cli_result = CliRunner().invoke(
        app,
        ["export", "dry-run", "--request-json", request_json],
    )
    mcp_result = _call_tool(
        create_mcp_server(service),
        "export_dry_run",
        {"request_json": request_json},
    )

    assert cli_result.exit_code == 2
    cli_payload = json.loads(cli_result.stdout)
    mcp_payload = json.loads(mcp_result)
    assert cli_payload == mcp_payload
    assert cli_payload["operation"] == "dry_run"
    assert cli_payload["status"] == "error"
    assert cli_payload["error"]["code"] == "export-contract-invalid"


def test_cli_and_mcp_fail_closed_with_the_same_oversized_response(monkeypatch):
    service = _DiscoveryOnlyPipeline()
    monkeypatch.setattr(cli_module, "_SERVICE", service)

    def oversized_response(_discovery):
        return {
            "error": None,
            "operation": "discover",
            "result": {"value": "x" * (1024 * 1024)},
            "schema_version": "veriformis.export-surface-response/v1",
            "status": "ok",
        }

    monkeypatch.setattr(cli_module, "export_discovery_response", oversized_response)
    monkeypatch.setattr(mcp_module, "export_discovery_response", oversized_response)

    cli_result = CliRunner().invoke(app, ["export", "discover"])
    mcp_result = _call_tool(
        create_mcp_server(service),
        "export_discover",
        {},
    )

    assert cli_result.exit_code == 2
    assert json.loads(cli_result.stdout) == json.loads(mcp_result)
    assert json.loads(mcp_result)["error"]["code"] == "export-contract-invalid"


def test_cli_and_mcp_sanitize_invalid_unicode_errors_identically(monkeypatch):
    service = _InvalidUnicodeFailurePipeline()
    monkeypatch.setattr(cli_module, "_SERVICE", service)

    cli_result = CliRunner().invoke(app, ["export", "discover"])
    mcp_result = _call_tool(
        create_mcp_server(service),
        "export_discover",
        {},
    )

    assert cli_result.exit_code == 1
    assert json.loads(cli_result.stdout) == json.loads(mcp_result)
    assert json.loads(mcp_result)["error"] == {
        "code": "invalid-data",
        "message": "invalid ? detail",
    }


def test_cli_and_mcp_reject_excessive_tree_depth_without_traceback(
    tmp_path,
    monkeypatch,
):
    service = PipelineService()
    monkeypatch.setattr(cli_module, "_SERVICE", service)
    request_json = lossless_json_bytes(
        {
            "destination_root": str(_deep_export_tree(tmp_path)),
            "operation": "inspect",
            "schema_version": EXPORT_SURFACE_REQUEST_SCHEMA,
        }
    ).decode("utf-8")

    cli_result = CliRunner().invoke(
        app,
        ["export", "inspect", "--request-json", request_json],
    )
    mcp_result = _call_tool(
        create_mcp_server(service),
        "export_inspect",
        {"request_json": request_json},
    )

    assert cli_result.exit_code == 1
    assert "Traceback" not in cli_result.output
    assert json.loads(cli_result.stdout) == json.loads(mcp_result)
    assert json.loads(mcp_result)["error"]["code"] == "export-verification-invalid"


def test_export_surfaces_expose_no_force_or_replacement_control():
    runner = CliRunner()
    execute_help = runner.invoke(app, ["export", "execute", "--help"])
    verify_help = runner.invoke(app, ["export-verify", "--help"])

    assert execute_help.exit_code == 0, execute_help.output
    assert verify_help.exit_code == 0, verify_help.output
    combined = f"{execute_help.output}\n{verify_help.output}".lower()
    assert "--force" not in combined
    assert "--replace" not in combined
    assert "--overwrite" not in combined


def test_mcp_registers_all_five_thin_export_tools():
    tools = _tool_names(create_mcp_server())
    assert {
        "export_discover",
        "export_dry_run",
        "export_inspect",
        "export_execute",
        "export_verify",
    } <= tools


def test_cli_signal_handler_only_marks_cooperative_cancellation():
    token = cli_module._ExportCancellationToken()
    token.request(15, None)

    with pytest.raises(ExportOperationCancelled, match="cancelled"):
        token.check()


@pytest.mark.parametrize(
    ("tool_name", "operation"),
    (
        ("export_inspect", "inspect"),
        ("export_execute", "execute"),
        ("export_verify", "verify"),
    ),
)
def test_mcp_blocking_export_tools_wait_for_cooperative_cleanup_before_cancel(
    tool_name,
    operation,
):
    service = _CancellablePipeline(operation)
    server = create_mcp_server(service)

    async def exercise() -> None:
        task = asyncio.create_task(
            _call_tool_async(
                server,
                tool_name,
                {"request_json": _cancellable_request(operation)},
            )
        )
        await _wait_for_thread_event(service.started)
        escape = asyncio.get_running_loop().call_later(1.0, service.escape.set)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        escape.cancel()

    asyncio.run(exercise())

    assert service.cancelled.is_set()
    assert service.cleaned.is_set()


@pytest.mark.parametrize(
    ("partial", "expected_status"),
    ((False, "ok"), (True, "visible_partial")),
)
def test_mcp_cancellation_race_preserves_visible_publication_outcome(
    tmp_path,
    partial,
    expected_status,
):
    bundle = _materialize_bundle(tmp_path)
    export_service, _ = _service()
    delegate = PipelineService(export_service=export_service)
    plan_outcome = delegate.dry_run_export(_dry_run_request(bundle))
    assert plan_outcome.plan is not None
    destination = tmp_path / "published"
    request = _execute_request(bundle, destination, plan_outcome.plan)
    service = _PublicationRacePipeline(delegate, partial=partial)
    server = create_mcp_server(service)

    async def exercise() -> str:
        task = asyncio.create_task(
            _call_tool_async(
                server,
                "export_execute",
                {
                    "request_json": request.canonical_bytes().decode("utf-8"),
                },
            )
        )
        await _wait_for_thread_event(service.visible)
        task.cancel()
        await asyncio.sleep(0)
        service.release.set()
        return await task

    payload = json.loads(asyncio.run(exercise()))

    assert payload["status"] == expected_status
    assert payload["result"]["destination_root"] == os.path.abspath(destination)
    assert destination.is_dir()


def test_injected_exact_export_has_python_cli_mcp_evidence_parity(
    tmp_path,
    monkeypatch,
):
    bundle = _materialize_bundle(tmp_path)
    export_service, runtime = _service()
    pipeline = PipelineService(export_service=export_service)
    monkeypatch.setattr(cli_module, "_SERVICE", pipeline)
    server = create_mcp_server(pipeline)

    dry_request = _dry_run_request(bundle)
    dry_json = dry_request.canonical_bytes().decode("utf-8")

    python_plan_outcome = pipeline.dry_run_export(dry_request)
    assert python_plan_outcome.plan is not None
    plan = python_plan_outcome.plan
    python_dry = export_dry_run_response(plan)

    cli_dry_result = CliRunner().invoke(
        app,
        ["export", "dry-run", "--request-json", dry_json],
    )
    assert cli_dry_result.exit_code == 0, cli_dry_result.output
    cli_dry = json.loads(cli_dry_result.stdout)
    mcp_dry = json.loads(
        _call_tool(server, "export_dry_run", {"request_json": dry_json})
    )
    assert python_dry == cli_dry == mcp_dry

    destinations = {
        "python": tmp_path / "python-export",
        "cli": tmp_path / "cli-export",
        "mcp": tmp_path / "mcp-export",
    }

    python_execute_request = _execute_request(
        bundle,
        destinations["python"],
        plan,
    )
    python_execution_outcome = pipeline.execute_export(python_execute_request)
    assert python_execution_outcome.publication is not None
    python_execute = export_execution_response(python_execution_outcome.publication)

    cli_execute_request = _execute_request(bundle, destinations["cli"], plan)
    cli_execute_result = CliRunner().invoke(
        app,
        [
            "export",
            "execute",
            "--request-json",
            cli_execute_request.canonical_bytes().decode("utf-8"),
        ],
    )
    assert cli_execute_result.exit_code == 0, cli_execute_result.output
    cli_execute = json.loads(cli_execute_result.stdout)

    mcp_execute_request = _execute_request(bundle, destinations["mcp"], plan)
    mcp_execute = json.loads(
        _call_tool(
            server,
            "export_execute",
            {
                "request_json": mcp_execute_request.canonical_bytes().decode(
                    "utf-8"
                ),
            },
        )
    )

    inspect_payloads = []
    verify_payloads = []
    for surface, destination in destinations.items():
        inspect_request = ExportInspectRequest(
            schema_version=EXPORT_SURFACE_REQUEST_SCHEMA,
            operation="inspect",
            destination_root=str(destination),
        )
        inspect_json = inspect_request.canonical_bytes().decode("utf-8")
        verify_request = _verify_request(bundle, destination, plan)
        verify_json = verify_request.canonical_bytes().decode("utf-8")

        if surface == "python":
            inspection_outcome = pipeline.inspect_export(inspect_request)
            assert inspection_outcome.inspection is not None
            inspect_payload = export_inspection_response(inspection_outcome.inspection)
            verify_outcome = pipeline.verify_export(verify_request)
            assert verify_outcome.verified is not None
            verify_payload = export_verify_response(verify_outcome.verified)
        elif surface == "cli":
            inspect_result = CliRunner().invoke(
                app,
                ["export", "inspect", "--request-json", inspect_json],
            )
            assert inspect_result.exit_code == 0, inspect_result.output
            inspect_payload = json.loads(inspect_result.stdout)
            verify_result = CliRunner().invoke(
                app,
                ["export-verify", "--request-json", verify_json],
            )
            assert verify_result.exit_code == 0, verify_result.output
            verify_payload = json.loads(verify_result.stdout)
        else:
            inspect_payload = json.loads(
                _call_tool(
                    server,
                    "export_inspect",
                    {"request_json": inspect_json},
                )
            )
            verify_payload = json.loads(
                _call_tool(
                    server,
                    "export_verify",
                    {"request_json": verify_json},
                )
            )

        assert inspect_payload["status"] == "ok"
        assert inspect_payload["result"]["inspection_scope"] == (
            "self_described_physical"
        )
        assert "verification" not in inspect_payload["result"]
        assert verify_payload["status"] == "ok"
        inspect_payloads.append(inspect_payload)
        verify_payloads.append(verify_payload)

    execute_payloads = (python_execute, cli_execute, mcp_execute)
    all_plan_summaries = [python_dry["result"]["plan"]]
    all_plan_summaries.extend(
        payload["result"]["plan"]
        for payload in (*execute_payloads, *inspect_payloads, *verify_payloads)
    )
    assert all(item == all_plan_summaries[0] for item in all_plan_summaries)
    assert all_plan_summaries[0]["export_plan_id"] == plan.export_plan_id

    receipt_summaries = [
        payload["result"]["receipt"]
        for payload in (*execute_payloads, *inspect_payloads, *verify_payloads)
    ]
    assert all(item == receipt_summaries[0] for item in receipt_summaries)

    verification_summaries = [
        payload["result"]["verification"]
        for payload in (*execute_payloads, *verify_payloads)
    ]
    assert all(item == verification_summaries[0] for item in verification_summaries)

    observed_destinations = {
        payload["result"]["destination_root"]
        for payload in (*execute_payloads, *inspect_payloads, *verify_payloads)
    }
    assert observed_destinations == {
        os.path.abspath(destination) for destination in destinations.values()
    }
    assert runtime.render_calls == 6
    assert runtime.planner_calls == 9
