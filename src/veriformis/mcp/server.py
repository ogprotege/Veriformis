"""Local stdio MCP server. Tools call PipelineService only."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from veriformis.errors import VeriformisError
from veriformis.pipeline.service import (
    DEFAULT_PIPELINE_SERVICE,
    PipelineService,
    SealPartialPublicationError,
)
from veriformis.recipes import list_named_recipes, load_pipeline_spec, run_pipeline_spec
from veriformis.taxonomy import CANONICAL_CONSUMER_PROFILE


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
    def list_recipes() -> str:
        """List named deterministic recipe library identifiers."""
        return json.dumps(list(list_named_recipes()), ensure_ascii=False, indent=2)

    @server.tool()
    def parse(paths: list[str], out: str, source_root: str | None = None) -> str:
        """Capture and parse source files into a workspace."""
        root = Path(source_root) if source_root else None
        return _outcome_json(
            pipeline.parse([Path(p) for p in paths], Path(out), source_root=root)
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
        strategy: str = "paragraph",
        size: int = 1000,
        overlap: int = 100,
    ) -> str:
        """Chunk cleaned documents with reconstructible evidence."""
        return _outcome_json(
            pipeline.chunk(
                Path(workspace),
                strategy=strategy,
                size=size,
                overlap=overlap,
            )
        )

    @server.tool()
    def construct(
        workspace: str,
        objective: str,
        source: list[str] | None = None,
        target_row_schema: str | None = None,
        split_ratio_ppm: int = 500_000,
        require_review: bool = False,
        consumer_profile: str = CANONICAL_CONSUMER_PROFILE,
    ) -> str:
        """Construct candidates and accepted records for one objective."""
        return _outcome_json(
            pipeline.construct(
                Path(workspace),
                objective=objective,
                source=source,
                target_row_schema=target_row_schema,
                split_ratio_ppm=split_ratio_ppm,
                require_review=require_review,
                consumer_profile=consumer_profile,
            )
        )

    @server.tool()
    def curate(
        workspace: str,
        minimum_target_characters: int = 1,
        balance_mode: str = "none",
        maximum_records_per_primary_source: int | None = None,
        evaluation_ratio_ppm: int = 500_000,
        evaluation_required: bool = True,
        split_seed: str = "veriformis-v1",
        instruction: str | None = None,
    ) -> str:
        """Fix the finished plan and curate constructed records."""
        return _outcome_json(
            pipeline.curate(
                Path(workspace),
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
