"""Local stdio MCP server. Tools call PipelineService only."""

from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from veriformis.errors import VeriformisError
from veriformis.exports.api import (
    EXPORT_SURFACE_RESPONSE_SCHEMA,
    EXPORT_SURFACE_RESPONSE_SCHEMA_V2,
    ExportOperationCancelled,
    ExportPartialPublicationError,
    _EXPORT_SURFACE_EXCEPTIONS,
    export_discovery_response,
    export_dry_run_preview_response,
    export_error_response,
    export_execution_response,
    export_inspection_response,
    export_request_from_json_bytes,
    export_response_json,
    export_verify_response,
)
from veriformis.pipeline.service import (
    DEFAULT_PIPELINE_SERVICE,
    PipelineService,
    SealPartialPublicationError,
)
from veriformis.recipes import list_named_recipes, load_pipeline_spec, run_pipeline_spec


def _jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return {
            "encoding": "sha256",
            "sha256": __import__(
                "veriformis.identity", fromlist=["sha256_digest"]
            ).sha256_digest(value),
            "byte_size": len(value),
        }
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _outcome_json(outcome: Any) -> str:
    return json.dumps(_jsonable(outcome), ensure_ascii=False, indent=2, sort_keys=True)


def _export_tool_response(
    operation: str,
    response_builder,
    call,
    *,
    response_schema: str = EXPORT_SURFACE_RESPONSE_SCHEMA,
) -> str:
    """Return the same canonical export envelope as the CLI adapter."""
    try:
        payload = response_builder(call())
    except _EXPORT_SURFACE_EXCEPTIONS as exc:
        payload = export_error_response(
            operation,
            exc,
            response_schema=response_schema,
        )
    try:
        return export_response_json(payload)
    except _EXPORT_SURFACE_EXCEPTIONS as exc:
        return export_response_json(
            export_error_response(
                operation,
                exc,
                response_schema=response_schema,
            )
        )


async def _export_tool_response_async(operation: str, response_builder, call) -> str:
    """Run a blocking export call with cooperative MCP-task cancellation."""
    cancellation_requested = threading.Event()

    def cancellation_check() -> None:
        if cancellation_requested.is_set():
            raise ExportOperationCancelled("export operation cancelled")

    worker = asyncio.create_task(asyncio.to_thread(call, cancellation_check))
    try:
        payload = response_builder(await asyncio.shield(worker))
    except asyncio.CancelledError as cancelled:
        cancellation_requested.set()
        while not worker.done():
            try:
                await asyncio.shield(worker)
            except asyncio.CancelledError:
                # Repeated task cancellation must not abandon the worker's
                # service-owned cleanup.
                cancellation_requested.set()
            except Exception:
                break
        if worker.cancelled():
            raise cancelled
        try:
            completed = worker.result()
        except ExportPartialPublicationError as exc:
            payload = export_error_response(operation, exc)
        except Exception:
            raise cancelled
        else:
            payload = response_builder(completed)
    except _EXPORT_SURFACE_EXCEPTIONS as exc:
        payload = export_error_response(operation, exc)
    try:
        return export_response_json(payload)
    except _EXPORT_SURFACE_EXCEPTIONS as exc:
        return export_response_json(export_error_response(operation, exc))


def _partial_publication_payload(exc: SealPartialPublicationError) -> dict[str, Any]:
    """Surface the publication receipt facts a client needs after a torn seal."""
    publication = exc.publication
    return {
        "error": {
            "code": "seal-partial-publication",
            "message": str(exc.cause),
            "bundle_path": str(publication.bundle_path),
            "manifest_sha256": publication.manifest_sha256,
            "explanation": (
                f"published bundle remains visible at {publication.bundle_path}; "
                f"manifest SHA-256 {publication.manifest_sha256}; workspace "
                "receipt did not commit"
            ),
        },
        "exit_status": 1,
    }


def create_mcp_server(
    service: PipelineService | None = None,
) -> MCPServer:
    """Create the constrained Veriformis MCP server bound to one service."""
    pipeline = service or DEFAULT_PIPELINE_SERVICE
    server = MCPServer(
        name="veriformis",
        title="Veriformis",
        description=(
            "Local-first dataset compiler. Tools are thin adapters over "
            "PipelineService; stage policy is never reimplemented here."
        ),
        version=__import__("veriformis").__version__,
        instructions=(
            "Use only these tools for Veriformis stage operations. Do not invent "
            "cleaning, construction, or sealing behavior outside tool results."
        ),
    )

    @server.tool()
    def version() -> str:
        """Return the Veriformis package version."""
        return _outcome_json(pipeline.version())

    @server.tool()
    def taxonomy() -> str:
        """Return implemented taxonomy discovery from PipelineService."""
        return json.dumps(
            pipeline.discover_taxonomy(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    @server.tool()
    def goals() -> str:
        """Return the plain-language goal catalog from PipelineService."""
        return (
            json.dumps(
                pipeline.discover_goals(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )

    @server.tool()
    def presets() -> str:
        """Return the versioned recipe presets and defaults from PipelineService."""
        return json.dumps(
            pipeline.discover_presets(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    @server.tool()
    def modes() -> str:
        """Return compiler-path input modes from PipelineService."""
        return json.dumps(
            pipeline.discover_modes(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    @server.tool()
    def mapping_detect(
        path: str,
        source_root: str | None = None,
        goal: str | None = None,
        representation: str | None = None,
    ) -> str:
        """Propose mapping plans for one JSONL file without writing a workspace."""
        root = Path(source_root) if source_root else None
        return json.dumps(
            pipeline.detect_mapping(
                Path(path),
                source_root=root,
                goal=goal,
                representation=representation,
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n"

    @server.tool()
    def mapping_contracts() -> str:
        """Return row-mapping contract discovery from PipelineService."""
        return json.dumps(
            pipeline.discover_mapping_contracts(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    @server.tool()
    def preflight(
        paths: list[str],
        source_root: str | None = None,
        goal: str | None = None,
        preset: str | None = None,
        representation: str | None = None,
        instruction: str | None = None,
        rules: str = "",
        custom: str = "",
        strategy: str | None = None,
        size: int | None = None,
        overlap: int | None = None,
        split_ratio_ppm: int | None = None,
        require_review: bool | None = None,
        consumer_profile: str | None = None,
        minimum_target_characters: int | None = None,
        balance_mode: str | None = None,
        maximum_records_per_primary_source: int | None = None,
        evaluation_ratio_ppm: int | None = None,
        evaluation_required: bool | None = None,
        split_seed: str | None = None,
        review_policy: str | None = None,
        mode: str | None = None,
    ) -> str:
        """Evaluate raw-source compile readiness without creating a workspace."""
        outcome = pipeline.preflight(
            [Path(path) for path in paths],
            source_root=None if source_root is None else Path(source_root),
            goal=goal,
            preset=preset,
            representation=representation,
            instruction=instruction,
            rules=rules,
            custom=custom,
            strategy=strategy,
            size=size,
            overlap=overlap,
            split_ratio_ppm=split_ratio_ppm,
            require_review=require_review,
            consumer_profile=consumer_profile,
            minimum_target_characters=minimum_target_characters,
            balance_mode=balance_mode,
            maximum_records_per_primary_source=maximum_records_per_primary_source,
            evaluation_ratio_ppm=evaluation_ratio_ppm,
            evaluation_required=evaluation_required,
            split_seed=split_seed,
            review_policy=review_policy,
            mode=mode,
        )
        assert outcome.preflight is not None
        return outcome.preflight.transport_text()

    @server.tool()
    def goal_preview(
        workspace: str,
        representation: str | None = None,
        instruction: str | None = None,
        record_ids: list[str] | None = None,
    ) -> str:
        """Show exactly what each record is and which region receives loss."""
        outcome = pipeline.preview_goal(
            Path(workspace),
            representation=representation,
            instruction=instruction,
            record_ids=tuple(record_ids or ()),
        )
        return outcome.preview.transport_text()

    @server.tool()
    def export_discover() -> str:
        """Discover executable export profiles from PipelineService."""

        def run():
            outcome = pipeline.discover_exports()
            assert outcome.discovery is not None
            return outcome.discovery

        return _export_tool_response(
            "discover",
            export_discovery_response,
            run,
        )

    @server.tool()
    def export_dry_run(request_json: str) -> str:
        """Derive an export plan without destination access."""

        def run():
            request = export_request_from_json_bytes(
                request_json.encode("utf-8"),
                expected_operation="dry_run",
            )
            outcome = pipeline.dry_run_export(request)
            assert outcome.preview is not None
            return outcome.preview

        return _export_tool_response(
            "dry_run",
            export_dry_run_preview_response,
            run,
            response_schema=EXPORT_SURFACE_RESPONSE_SCHEMA_V2,
        )

    @server.tool()
    async def export_inspect(request_json: str) -> str:
        """Inspect self-described export bytes without asserting source trust."""

        def run(cancellation_check):
            request = export_request_from_json_bytes(
                request_json.encode("utf-8"),
                expected_operation="inspect",
            )
            outcome = pipeline.inspect_export(
                request,
                cancellation_check=cancellation_check,
            )
            assert outcome.inspection is not None
            return outcome.inspection

        return await _export_tool_response_async(
            "inspect",
            export_inspection_response,
            run,
        )

    @server.tool()
    async def export_execute(request_json: str) -> str:
        """Atomically publish one operator-confirmed export plan."""

        def run(cancellation_check):
            request = export_request_from_json_bytes(
                request_json.encode("utf-8"),
                expected_operation="execute",
            )
            outcome = pipeline.execute_export(
                request,
                cancellation_check=cancellation_check,
            )
            assert outcome.publication is not None
            return outcome.publication

        return await _export_tool_response_async(
            "execute",
            export_execution_response,
            run,
        )

    @server.tool()
    async def export_verify(request_json: str) -> str:
        """Source-bind and independently verify one visible export tree."""

        def run(cancellation_check):
            request = export_request_from_json_bytes(
                request_json.encode("utf-8"),
                expected_operation="verify",
            )
            outcome = pipeline.verify_export(
                request,
                cancellation_check=cancellation_check,
            )
            assert outcome.verified is not None
            return outcome.verified

        return await _export_tool_response_async(
            "verify",
            export_verify_response,
            run,
        )

    @server.tool()
    def list_recipes() -> str:
        """List named deterministic recipe library identifiers."""
        return json.dumps(list(list_named_recipes()), ensure_ascii=False, indent=2)

    @server.tool()
    def parse(
        paths: list[str],
        out: str,
        source_root: str | None = None,
        mode: str | None = None,
    ) -> str:
        """Capture and parse source files into a workspace."""
        root = Path(source_root) if source_root else None
        return _outcome_json(
            pipeline.parse(
                [Path(p) for p in paths],
                Path(out),
                source_root=root,
                mode=mode,
            )
        )

    @server.tool()
    def clean(workspace: str, rules: str = "", custom: str = "") -> str:
        """Plan and commit deterministic cleaning."""
        return _outcome_json(
            pipeline.clean(Path(workspace), rules=rules, custom=custom)
        )

    @server.tool()
    def chunk(
        workspace: str,
        strategy: str | None = None,
        size: int | None = None,
        overlap: int | None = None,
        goal: str | None = None,
        preset: str | None = None,
    ) -> str:
        """Chunk cleaned documents with reconstructible evidence."""
        return _outcome_json(
            pipeline.chunk(
                Path(workspace),
                strategy=strategy,
                size=size,
                overlap=overlap,
                goal=goal,
                preset=preset,
            )
        )

    @server.tool()
    def construct(
        workspace: str,
        objective: str | None = None,
        source: list[str] | None = None,
        target_row_schema: str | None = None,
        split_ratio_ppm: int | None = None,
        require_review: bool | None = None,
        consumer_profile: str | None = None,
        goal: str | None = None,
        preset: str | None = None,
        representation: str | None = None,
        mode: str | None = None,
    ) -> str:
        """Construct candidates and accepted records for one goal or objective."""
        return _outcome_json(
            pipeline.construct(
                Path(workspace),
                objective=objective,
                goal=goal,
                preset=preset,
                representation=representation,
                source=source,
                target_row_schema=target_row_schema,
                split_ratio_ppm=split_ratio_ppm,
                require_review=require_review,
                consumer_profile=consumer_profile,
                mode=mode,
            )
        )

    @server.tool()
    def map_rows(
        workspace: str,
        goal: str,
        representation: str,
        mapping_plan: str,
    ) -> str:
        """Map captured JSONL row sources into imported semantic records."""
        return _outcome_json(
            pipeline.map_rows(
                Path(workspace),
                goal=goal,
                representation=representation,
                mapping_plan=json.loads(mapping_plan),
            )
        )

    @server.tool()
    def curate(
        workspace: str,
        minimum_target_characters: int | None = None,
        balance_mode: str | None = None,
        maximum_records_per_primary_source: int | None = None,
        evaluation_ratio_ppm: int | None = None,
        evaluation_required: bool | None = None,
        split_seed: str | None = None,
        instruction: str | None = None,
        goal: str | None = None,
        preset: str | None = None,
    ) -> str:
        """Fix the finished plan and curate constructed records."""
        return _outcome_json(
            pipeline.curate(
                Path(workspace),
                goal=goal,
                preset=preset,
                minimum_target_characters=minimum_target_characters,
                balance_mode=balance_mode,
                maximum_records_per_primary_source=maximum_records_per_primary_source,
                evaluation_ratio_ppm=evaluation_ratio_ppm,
                evaluation_required=evaluation_required,
                split_seed=split_seed,
                instruction=instruction,
            )
        )

    @server.tool()
    def split(workspace: str) -> str:
        """Assign leakage-safe train and evaluation partitions."""
        return _outcome_json(pipeline.split(Path(workspace)))

    @server.tool()
    def format_rows(workspace: str) -> str:
        """Lower included records into the plan's product row schema."""
        return _outcome_json(pipeline.format(Path(workspace)))

    @server.tool()
    def validate(workspace: str) -> str:
        """Validate one exact finished-dataset snapshot."""
        return _outcome_json(pipeline.validate(Path(workspace)))

    @server.tool()
    def seal(workspace: str, out: str, write_handoff: bool = False) -> str:
        """Seal a bundle; optionally opt in to an Aptus handoff sibling."""
        try:
            outcome = pipeline.seal(Path(workspace), Path(out))
        except SealPartialPublicationError as exc:
            return json.dumps(
                _partial_publication_payload(exc),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        # The seal outcome is secured first: a handoff failure must report
        # alongside — never instead of — the successful seal result.
        payload = _jsonable(outcome)
        if write_handoff and outcome.publication is not None:
            import veriformis.handoff as handoff_module

            try:
                handoff = handoff_module.build_aptus_handoff(
                    outcome.publication.bundle_path,
                    expected_manifest_sha256=outcome.publication.manifest_sha256,
                )
                path = handoff_module.write_aptus_handoff(
                    handoff,
                    handoff_module.handoff_path_for_bundle(
                        outcome.publication.bundle_path
                    ),
                )
            except (
                VeriformisError,
                OSError,
                UnicodeError,
                ValueError,
                TypeError,
            ) as exc:
                payload["aptus_handoff_error"] = {
                    "code": getattr(exc, "code", "invalid-data"),
                    "message": getattr(exc, "message", str(exc)),
                }
            else:
                payload["aptus_handoff_path"] = str(path)
                payload["aptus_handoff_id"] = handoff.handoff_id
                payload["assignment_digest"] = handoff.assignment_digest
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)

    @server.tool()
    def verify(bundle: str, manifest_sha256: str | None = None) -> str:
        """Independently verify one closed finished-dataset bundle."""
        return _outcome_json(
            pipeline.verify(Path(bundle), manifest_sha256=manifest_sha256)
        )

    @server.tool()
    def preview(
        path: str,
        rules: str = "",
        custom: str = "",
        source_root: str | None = None,
    ) -> str:
        """Plan and replay cleaning without writing workspace state."""
        root = Path(source_root) if source_root else None
        return _outcome_json(
            pipeline.preview(
                Path(path),
                rules=rules,
                custom=custom,
                source_root=root,
            )
        )

    @server.tool()
    def run_pipeline(pipeline_path: str) -> str:
        """Execute one versioned YAML pipeline document."""
        spec = load_pipeline_spec(Path(pipeline_path))
        try:
            result = run_pipeline_spec(spec, service=pipeline)
        except SealPartialPublicationError as exc:
            return json.dumps(
                _partial_publication_payload(exc),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        return json.dumps(_jsonable(result), ensure_ascii=False, indent=2, sort_keys=True)

    @server.tool()
    def build_handoff(bundle: str, manifest_sha256: str, out: str | None = None) -> str:
        """Build and write the versioned Aptus handoff for a sealed bundle."""
        from veriformis.handoff import (
            build_aptus_handoff,
            handoff_path_for_bundle,
            write_aptus_handoff,
        )

        handoff = build_aptus_handoff(
            Path(bundle),
            expected_manifest_sha256=manifest_sha256,
        )
        target = Path(out) if out else handoff_path_for_bundle(Path(bundle))
        write_aptus_handoff(handoff, target)
        return json.dumps(
            {
                "handoff_path": str(target),
                "handoff": handoff.to_dict(),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    @server.tool()
    def consume_handoff(handoff_path: str, bundle: str) -> str:
        """Consume/verify an Aptus handoff against a sealed bundle."""
        from veriformis.handoff import consume_aptus_handoff

        report = consume_aptus_handoff(
            Path(handoff_path),
            bundle=Path(bundle),
        )
        return json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)

    return server


def run_mcp_stdio(service: PipelineService | None = None) -> None:
    """Run the Veriformis MCP server on stdio."""
    server = create_mcp_server(service)
    server.run(transport="stdio")
