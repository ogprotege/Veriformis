"""Phase 18.2 workbench adapter: load and refuse pins only."""

from __future__ import annotations

from pathlib import Path

import pytest

from veriformis.cli import app
from veriformis.contracts import (
    WORKBENCH_ADAPTER_CONTRACT_VERSION,
    WORKBENCH_ADAPTER_SCHEMA_ID,
)
from veriformis.errors import WorkbenchAdapterError
from veriformis.identity import derive_id
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.workbench import (
    FAIL_CLOSED_REASONS,
    WRAP_COMMANDS,
    WRAP_SURFACES,
    WORKBENCH_ADAPTER_LIMITATIONS,
    WorkbenchAdapter,
    create_workbench_adapter,
    load_workbench_adapter,
)


ROOT = Path(__file__).resolve().parents[2]
MACOS = ROOT / "macos/Sources"
ADR = ROOT / "docs/adr/0019-thin-workbench-adapter.md"


def _pin(**overrides: object) -> WorkbenchAdapter:
    defaults: dict[str, object] = {
        "command": "goals",
        "surface": "discover",
        "request_schema_id": "veriformis.goal-catalog/v1",
        "response_schema_id": "veriformis.goal-catalog/v1",
    }
    defaults.update(overrides)
    return create_workbench_adapter(**defaults)  # type: ignore[arg-type]


def test_load_accepts_a_discover_pin() -> None:
    pin = _pin()
    loaded = load_workbench_adapter(pin.model_dump(mode="json"))
    assert loaded == pin
    assert loaded.contract_version == WORKBENCH_ADAPTER_CONTRACT_VERSION
    assert loaded.schema_id == WORKBENCH_ADAPTER_SCHEMA_ID
    assert loaded.policy_owner == "pipeline-service"
    assert loaded.adapter_kind == "process-cli"
    assert loaded.catalog_source == "shared-service"
    assert loaded.fail_closed_on == FAIL_CLOSED_REASONS
    assert loaded.generation_allowed is False
    assert loaded.plugin_install_allowed is False
    assert loaded.may_invent_review_policy is False
    assert loaded.may_invent_trainer_policy is False
    assert loaded.may_invent_family_policy is False
    assert loaded.review_policy_default == "none"


@pytest.mark.parametrize("command", WRAP_COMMANDS)
def test_load_accepts_each_admitted_command(command: str) -> None:
    surfaces = {
        "goals": "discover",
        "presets": "discover",
        "taxonomy": "discover",
        "modes": "discover",
        "mapping-detect": "discover",
        "mapping-preview": "preview",
        "mapping-contracts": "discover",
        "mapping-templates": "discover",
        "mapping-rejections": "discover",
        "export-discover": "discover",
        "export-dry-run": "preview",
        "export-inspect": "discover",
        "export-execute": "execute",
        "export-verify": "execute",
        "goal-preview": "preview",
        "preflight": "preview",
        "ocr-preview": "preview",
        "review-export": "discover",
        "review-import": "execute",
        "review-submit": "execute",
    }
    pin = _pin(command=command, surface=surfaces.get(command, "execute"))
    loaded = load_workbench_adapter(pin.model_dump(mode="json"))
    assert loaded.command == command
    assert loaded.surface in WRAP_SURFACES


def test_closed_vocabularies_match_the_contract() -> None:
    assert WRAP_COMMANDS == tuple(sorted(WRAP_COMMANDS))
    assert "parse" in WRAP_COMMANDS
    assert "export-execute" in WRAP_COMMANDS
    assert "review-submit" in WRAP_COMMANDS
    assert "map" in WRAP_COMMANDS
    assert "mcp" not in WRAP_COMMANDS
    assert "run" not in WRAP_COMMANDS
    assert "handoff" not in WRAP_COMMANDS
    assert "generator" not in WRAP_COMMANDS
    assert "install-extension" not in WRAP_COMMANDS
    assert WRAP_SURFACES == ("discover", "execute", "preview")
    assert FAIL_CLOSED_REASONS == ("cancelled", "schema-invalid", "truncated")
    assert "no-execute" in WORKBENCH_ADAPTER_LIMITATIONS
    assert "no-second-catalog" in WORKBENCH_ADAPTER_LIMITATIONS
    assert "no-swift-policy" in WORKBENCH_ADAPTER_LIMITATIONS


def test_unknown_command_names_admitted_commands() -> None:
    payload = _pin().model_dump(mode="json")
    payload["command"] = "generator"
    with pytest.raises(
        WorkbenchAdapterError,
        match=(
            "unknown workbench wrap command: 'generator'; admitted commands are "
            + ", ".join(WRAP_COMMANDS)
        ),
    ):
        load_workbench_adapter(payload)


@pytest.mark.parametrize("command", ("mcp", "run", "handoff", "install-extension"))
def test_unwrappable_commands_fail_closed(command: str) -> None:
    payload = _pin().model_dump(mode="json")
    payload["command"] = command
    with pytest.raises(
        WorkbenchAdapterError,
        match=rf"unknown workbench wrap command: {command!r}",
    ):
        load_workbench_adapter(payload)


def test_unknown_contract_version_names_requested_and_supported() -> None:
    payload = _pin().model_dump(mode="json")
    payload["contract_version"] = 2
    with pytest.raises(
        WorkbenchAdapterError,
        match=(
            r"unknown workbench adapter contract version: requested "
            r"contract_id='veriformis.workbench-adapter' "
            r"contract_version=2 "
            r"schema_id='veriformis.workbench-adapter/v1', supported "
            r"contract_id='veriformis.workbench-adapter' "
            r"contract_version=1 "
            r"schema_id='veriformis.workbench-adapter/v1'"
        ),
    ):
        load_workbench_adapter(payload)


def test_missing_contract_version_names_supported_version() -> None:
    payload = _pin().model_dump(mode="json")
    del payload["contract_version"]
    with pytest.raises(
        WorkbenchAdapterError,
        match=(
            r"unknown workbench adapter contract version: requested missing "
            r"contract_version, supported "
            r"contract_id='veriformis.workbench-adapter' "
            r"contract_version=1 "
            r"schema_id='veriformis.workbench-adapter/v1'"
        ),
    ):
        load_workbench_adapter(payload)


def test_unknown_field_fails_closed() -> None:
    payload = _pin().model_dump(mode="json")
    payload["swift_catalog"] = {"chunker": "guess"}
    with pytest.raises(
        WorkbenchAdapterError,
        match="unknown field swift_catalog",
    ):
        load_workbench_adapter(payload)


def test_generation_allowed_fails_closed() -> None:
    payload = _pin().model_dump(mode="json")
    payload["generation_allowed"] = True
    payload["adapter_id"] = derive_id(
        "wba",
        {key: value for key, value in payload.items() if key != "adapter_id"},
    )
    with pytest.raises(
        WorkbenchAdapterError,
        match="ADR-0018 Decision A forbids a compile-path generator",
    ):
        load_workbench_adapter(payload)


def test_plugin_install_allowed_fails_closed() -> None:
    payload = _pin().model_dump(mode="json")
    payload["plugin_install_allowed"] = True
    payload["adapter_id"] = derive_id(
        "wba",
        {key: value for key, value in payload.items() if key != "adapter_id"},
    )
    with pytest.raises(
        WorkbenchAdapterError,
        match="ADR-0017 Decision A forbids an untrusted loader",
    ):
        load_workbench_adapter(payload)


def test_invented_review_policy_fails_closed() -> None:
    with pytest.raises(
        WorkbenchAdapterError,
        match="cannot invent review policy",
    ):
        _pin(may_invent_review_policy=True)


def test_invented_trainer_policy_fails_closed() -> None:
    with pytest.raises(
        WorkbenchAdapterError,
        match="cannot invent trainer policy",
    ):
        _pin(may_invent_trainer_policy=True)


def test_invented_family_policy_fails_closed() -> None:
    with pytest.raises(
        WorkbenchAdapterError,
        match="cannot invent family policy",
    ):
        _pin(may_invent_family_policy=True)


def test_incomplete_fail_closed_set_is_refused() -> None:
    with pytest.raises(
        WorkbenchAdapterError,
        match="fail_closed_on must be cancelled, schema-invalid, truncated",
    ):
        _pin(fail_closed_on=("cancelled", "truncated"))


def test_swift_policy_owner_is_refused() -> None:
    payload = _pin().model_dump(mode="json")
    payload["policy_owner"] = "swift"
    payload["adapter_id"] = derive_id(
        "wba",
        {key: value for key, value in payload.items() if key != "adapter_id"},
    )
    with pytest.raises(
        WorkbenchAdapterError,
        match="ADR-0019 Decision A forbids a Swift policy engine",
    ):
        load_workbench_adapter(payload)


def test_second_catalog_source_is_refused() -> None:
    payload = _pin().model_dump(mode="json")
    payload["catalog_source"] = "swift-constants"
    payload["adapter_id"] = derive_id(
        "wba",
        {key: value for key, value in payload.items() if key != "adapter_id"},
    )
    with pytest.raises(
        WorkbenchAdapterError,
        match="ADR-0019 Decision A forbids a second catalog",
    ):
        load_workbench_adapter(payload)


def test_public_surfaces_still_have_no_adapter_execute() -> None:
    forbidden = {
        "workbench-adapter",
        "load-workbench-adapter",
        "wrap-command",
        "generator",
        "install-extension",
    }
    cli_names = {command.name for command in app.registered_commands}
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert cli_names.isdisjoint(forbidden)
    assert mcp_names.isdisjoint(forbidden)
    service = PipelineService()
    assert not hasattr(service, "load_workbench_adapter")
    assert not hasattr(service, "create_workbench_adapter")


def test_loading_an_export_or_review_pin_does_not_add_screens() -> None:
    load_workbench_adapter(
        _pin(
            command="export-execute",
            surface="execute",
            request_schema_id="veriformis.export-plan/v1",
            response_schema_id="veriformis.export-receipt/v1",
        ).model_dump(mode="json")
    )
    load_workbench_adapter(
        _pin(
            command="review-submit",
            surface="execute",
            request_schema_id="veriformis.review-packet/v1",
            response_schema_id="veriformis.review-bundle/v1",
        ).model_dump(mode="json")
    )
    load_workbench_adapter(
        _pin(
            command="map",
            surface="execute",
            request_schema_id="veriformis.row-mapping/v1",
            response_schema_id="veriformis.row-mapping/v1",
        ).model_dump(mode="json")
    )
    views = {path.name for path in (MACOS / "Views").glob("*.swift")}
    assert "ReviewView.swift" not in views
    assert "ExportsView.swift" not in views
    assert "MappingView.swift" not in views


def test_adr_0019_records_decision_a_and_required_threats() -> None:
    text = ADR.read_text(encoding="utf-8")
    assert text.startswith("# ADR-0019 — Thin Workbench Adapter\n")
    assert "**Status:** Accepted" in text
    assert (
        "**Decision A.** The Mac workbench is a process adapter over "
        "PipelineService and the CLI."
    ) in text
    for heading in (
        "Swift as a second policy engine",
        "Truncated CLI JSON",
        "Cancelled child process",
        "Schema-invalid payload",
        "Dataset-project code execution",
        "Generator or plugin UI",
        "Invented review, trainer, or family policy",
    ):
        assert heading in text
    assert "Decision B" in text
    assert "Decision C" in text
    assert "This item is policy. It adds no screen." in text
    assert "ADR-0017 Decision A stands" in text
    assert "ADR-0018 Decision A stands" in text


def test_swift_already_fails_closed_on_truncated_and_cancelled_discovery() -> None:
    cli = (MACOS / "Services/VeriformisCLI.swift").read_text(encoding="utf-8")
    assert "standardOutputTruncated" in cli
    assert "outputTruncated" in cli
    assert "cancelledWithoutResponse" in cli
    assert "TaxonomyDiscoveryError.outputTruncated" in cli
    assert "invalidPayload" in cli
    views = "\n".join(
        path.read_text(encoding="utf-8") for path in (MACOS / "Views").glob("*.swift")
    )
    model = (MACOS / "ViewModels/WorkbenchViewModel.swift").read_text(encoding="utf-8")
    for haystack in (views, model):
        assert "executeExport" not in haystack
        assert "mapping-detect" not in haystack
        assert "review-submit" not in haystack
