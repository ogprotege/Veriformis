"""Veriformis CLI adapter over ``PipelineService``.

The CLI translates arguments, stage outcomes, and failures only. Stage policy
and workspace orchestration live in ``veriformis.pipeline``.
"""

from __future__ import annotations

import signal
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
import json
from pathlib import Path

import typer

from veriformis.errors import VeriformisError
from veriformis.evidence import EvidenceError
from veriformis.exports.api import (
    EXPORT_SURFACE_RESPONSE_SCHEMA,
    EXPORT_SURFACE_RESPONSE_SCHEMA_V2,
    ExportOperationCancelled,
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
    SealOutcome,
    StageOutcome,
    _load_chunks,
    _load_sources,
    _load_transform_records,
    _output_bytes,
    _parse_one,
)

# Re-export private loaders for regression tests and monkeypatch targets.
__all__ = [
    "app",
    "main",
    "_load_chunks",
    "_load_sources",
    "_load_transform_records",
    "_output_bytes",
    "_parse_one",
]

app = typer.Typer(help="Veriformis: local-first dataset compiler.")
export_app = typer.Typer(
    help="Derive and verify exports through PipelineService.",
    no_args_is_help=True,
)
app.add_typer(export_app, name="export")
_SERVICE: PipelineService = DEFAULT_PIPELINE_SERVICE


def _echo_error(exc: Exception, *, status: int = 2) -> None:
    code = getattr(exc, "code", "invalid-data")
    message = getattr(exc, "message", str(exc))
    typer.echo(f"error[{code}]: {message}", err=True)
    raise typer.Exit(code=status) from exc


def _emit_outcome(outcome: StageOutcome) -> None:
    if outcome.durability_warning is not None:
        typer.echo(
            f"warning[commit-durability]: {outcome.durability_warning}",
            err=True,
        )
    for message in outcome.messages:
        typer.echo(message.text, err=message.stream == "stderr")
    if outcome.exit_status != 0:
        raise typer.Exit(code=outcome.exit_status)


def _run(call, *, status: int = 2, extra_exceptions: tuple[type[BaseException], ...] = ()):
    try:
        outcome = call()
    except SealPartialPublicationError as exc:
        publication = exc.publication
        typer.echo(
            f"published bundle remains visible at {publication.bundle_path}; "
            f"manifest SHA-256 {publication.manifest_sha256}; workspace receipt "
            "did not commit",
            err=True,
        )
        _echo_error(exc.cause if isinstance(exc.cause, Exception) else exc, status=1)
    except (
        VeriformisError,
        EvidenceError,
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        *extra_exceptions,
    ) as exc:
        _echo_error(exc, status=status)
    _emit_outcome(outcome)


class _ExportCancellationToken:
    """Signal-safe state observed only at service-owned checkpoints."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def request(self, _signum: int, _frame: object) -> None:
        self._event.set()

    def check(self) -> None:
        if self._event.is_set():
            raise ExportOperationCancelled("export operation cancelled")


@contextmanager
def _export_cancellation_check() -> Iterator[Callable[[], None]]:
    """Translate SIGINT/SIGTERM into cooperative service cancellation."""
    token = _ExportCancellationToken()
    installed: dict[int, signal.Handlers] = {}
    if threading.current_thread() is threading.main_thread():
        for signum in (signal.SIGINT, signal.SIGTERM):
            installed[signum] = signal.getsignal(signum)
            signal.signal(signum, token.request)
    try:
        yield token.check
    finally:
        for signum, handler in installed.items():
            signal.signal(signum, handler)


def _export_exit_status(payload: dict[str, object]) -> int:
    status = payload["status"]
    if status == "ok":
        return 0
    if status == "cancelled":
        return 130
    if status == "visible_partial":
        return 1
    error = payload.get("error")
    if isinstance(error, dict) and error.get("code") == "export-contract-invalid":
        return 2
    return 1


def _emit_export_response(payload: dict[str, object], response_json: str) -> None:
    """Emit exactly one canonical JSON object on stdout."""
    typer.echo(response_json)
    status = _export_exit_status(payload)
    if status != 0:
        raise typer.Exit(code=status)


def _run_export_operation(
    operation: str,
    response_builder,
    call,
    *,
    response_schema: str = EXPORT_SURFACE_RESPONSE_SCHEMA,
) -> None:
    try:
        payload = response_builder(call())
    except _EXPORT_SURFACE_EXCEPTIONS as exc:
        payload = export_error_response(
            operation,
            exc,
            response_schema=response_schema,
        )
    try:
        response_json = export_response_json(payload)
    except _EXPORT_SURFACE_EXCEPTIONS as exc:
        payload = export_error_response(
            operation,
            exc,
            response_schema=response_schema,
        )
        response_json = export_response_json(payload)
    _emit_export_response(payload, response_json)


@app.command()
def parse(
    paths: list[Path],
    out: Path = typer.Option(..., "-o"),
    source_root: Path | None = typer.Option(None, "--source-root"),
    mode: str | None = typer.Option(
        None,
        "--mode",
        help="Compiler path: document-source (default), dataset-row, or mixed.",
    ),
) -> None:
    """Capture raw files and commit one canonical parse revision."""
    _run(lambda: _SERVICE.parse(paths, out, source_root=source_root, mode=mode))


@app.command()
def clean(
    workspace: Path,
    rules: str = typer.Option("", "--rules"),
    custom: str = typer.Option("", "--custom"),
) -> None:
    """Plan, replay, and atomically commit cleaning for every source."""
    import re

    _run(
        lambda: _SERVICE.clean(workspace, rules=rules, custom=custom),
        extra_exceptions=(re.error,),
    )


@app.command()
def chunk(
    workspace: Path,
    strategy: str | None = typer.Option(
        None, "--strategy", help="Chunk strategy; defaults come from the preset data."
    ),
    size: int | None = typer.Option(None, "--size"),
    overlap: int | None = typer.Option(None, "--overlap"),
    goal: str | None = typer.Option(None, "--goal", help="Plain-language goal id."),
    preset: str | None = typer.Option(None, "--preset", help="Recipe preset id."),
) -> None:
    """Chunk cleaned documents with exact reconstructible source evidence."""
    _run(
        lambda: _SERVICE.chunk(
            workspace,
            strategy=strategy,
            size=size,
            overlap=overlap,
            goal=goal,
            preset=preset,
        )
    )


@app.command(name="upgrade-workspace")
def upgrade_workspace(workspace: Path) -> None:
    """Advance a verified workspace through every supported revision migration."""
    _run(lambda: _SERVICE.upgrade_workspace(workspace))


@app.command()
def construct(
    workspace: Path,
    objective: str | None = typer.Option(
        None, "--objective", help="Persisted objective kind (legacy selection)."
    ),
    goal: str | None = typer.Option(None, "--goal", help="Plain-language goal id."),
    preset: str | None = typer.Option(None, "--preset", help="Recipe preset id."),
    representation: str | None = typer.Option(
        None, "--representation", help="Catalog representation id."
    ),
    source: list[str] | None = typer.Option(
        None,
        "--source",
        help="Repeat a source ID or logical path to select a subset.",
    ),
    target_row_schema: str | None = typer.Option(
        None,
        "--target-row-schema",
    ),
    split_ratio_ppm: int | None = typer.Option(
        None, "--split-ratio-ppm", help="Override; defaults come from the preset data."
    ),
    require_review: bool | None = typer.Option(
        None, "--require-review/--no-require-review"
    ),
    consumer_profile: str | None = typer.Option(
        None,
        "--consumer-profile",
    ),
    mode: str | None = typer.Option(
        None,
        "--mode",
        help="Compiler path: document-source (default), dataset-row, or mixed.",
    ),
) -> None:
    """Construct evidence-bearing candidates and immutable accepted records."""
    _run(
        lambda: _SERVICE.construct(
            workspace,
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


@app.command(name="map")
def map_cmd(
    workspace: Path,
    goal: str = typer.Option(..., "--goal", help="Plain-language goal id."),
    representation: str = typer.Option(
        ..., "--representation", help="Catalog representation id."
    ),
    plan: Path = typer.Option(
        ...,
        "--plan",
        help="Confirmed mapping-plan/v1 JSON file.",
    ),
) -> None:
    """Map captured JSONL row sources into imported semantic records."""
    payload = json.loads(plan.read_text(encoding="utf-8"))
    _run(
        lambda: _SERVICE.map_rows(
            workspace,
            goal=goal,
            representation=representation,
            mapping_plan=payload,
        )
    )


@app.command()
def curate(
    workspace: Path,
    goal: str | None = typer.Option(None, "--goal", help="Plain-language goal id."),
    preset: str | None = typer.Option(None, "--preset", help="Recipe preset id."),
    minimum_target_characters: int | None = typer.Option(
        None, "--minimum-target-characters"
    ),
    balance_mode: str | None = typer.Option(None, "--balance-mode"),
    maximum_records_per_primary_source: int | None = typer.Option(
        None,
        "--maximum-records-per-primary-source",
    ),
    evaluation_ratio_ppm: int | None = typer.Option(None, "--evaluation-ratio-ppm"),
    evaluation_required: bool | None = typer.Option(
        None,
        "--require-evaluation/--allow-empty-evaluation",
    ),
    split_seed: str | None = typer.Option(None, "--split-seed"),
    instruction: str | None = typer.Option(
        None,
        "--instruction",
        help=(
            "Operator instruction for instruction-and-output; omitted uses the "
            "goal's catalog template after the truthfulness check."
        ),
    ),
) -> None:
    """Fix the complete dataset plan, then curate constructed records.

    Omitted settings come from the selected preset or the constructed goal's
    safe preset; every surface executes the same versioned defaults.
    """
    _run(
        lambda: _SERVICE.curate(
            workspace,
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


@app.command()
def split(workspace: Path) -> None:
    """Assign complete transitive leakage groups to fixed partitions."""
    _run(lambda: _SERVICE.split(workspace))


@app.command(name="format")
def format_cmd(workspace: Path) -> None:
    """Lower curated records into the row schema bound by their dataset plan."""
    _run(lambda: _SERVICE.format(workspace))


@app.command()
def validate(workspace: Path) -> None:
    """Replay and validate one exact finished-dataset byte snapshot."""
    _run(lambda: _SERVICE.validate(workspace), status=1)


@app.command()
def seal(
    workspace: Path,
    out: Path = typer.Option(..., "-o"),
    aptus_handoff: bool = typer.Option(
        False,
        "--aptus-handoff/--no-aptus-handoff",
        help=(
            "Opt in to writing the sibling Aptus handoff descriptor after a "
            "successful standalone seal."
        ),
    ),
) -> None:
    """Revalidate, atomically publish, and receipt one finished dataset."""
    outcome: SealOutcome | None = None
    try:
        outcome = _SERVICE.seal(workspace, out)
    except SealPartialPublicationError as exc:
        publication = exc.publication
        typer.echo(
            f"published bundle remains visible at {publication.bundle_path}; "
            f"manifest SHA-256 {publication.manifest_sha256}; workspace receipt "
            "did not commit",
            err=True,
        )
        _echo_error(exc.cause if isinstance(exc.cause, Exception) else exc, status=1)
    except (
        VeriformisError,
        EvidenceError,
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
    ) as exc:
        _echo_error(exc, status=1)
    assert outcome is not None
    _emit_outcome(outcome)
    if aptus_handoff and outcome.publication is not None:
        from veriformis.handoff import (
            build_aptus_handoff,
            handoff_path_for_bundle,
            write_aptus_handoff,
        )

        try:
            handoff = build_aptus_handoff(
                outcome.publication.bundle_path,
                expected_manifest_sha256=outcome.publication.manifest_sha256,
            )
            path = write_aptus_handoff(
                handoff,
                handoff_path_for_bundle(outcome.publication.bundle_path),
            )
        except (
            VeriformisError,
            EvidenceError,
            OSError,
            UnicodeError,
            ValueError,
            TypeError,
        ) as exc:
            _echo_error(exc, status=1)
        typer.echo(f"aptus handoff: {path}")
        typer.echo(f"assignment digest: {handoff.assignment_digest}")


@app.command(name="verify")
def verify_cmd(
    bundle: Path,
    manifest_sha256: str | None = typer.Option(None, "--manifest-sha256"),
) -> None:
    """Independently verify one closed finished-dataset bundle."""
    _run(
        lambda: _SERVICE.verify(bundle, manifest_sha256=manifest_sha256),
        status=1,
    )


@app.command(name="package")
def package_cmd(
    bundle: Path,
    out: Path = typer.Option(..., "-o"),
    manifest_sha256: str | None = typer.Option(None, "--manifest-sha256"),
    export_receipt_sha256: str | None = typer.Option(
        None,
        "--export-receipt-sha256",
    ),
) -> None:
    """Archive a bundle or export pack under one explicit external anchor."""
    _run(
        lambda: _SERVICE.package(
            bundle,
            out,
            manifest_sha256=manifest_sha256,
            export_receipt_sha256=export_receipt_sha256,
        ),
        status=1,
    )


@app.command(name="package-verify")
def package_verify_cmd(
    archive: Path,
    manifest_sha256: str | None = typer.Option(None, "--manifest-sha256"),
    export_receipt_sha256: str | None = typer.Option(
        None,
        "--export-receipt-sha256",
    ),
) -> None:
    """Verify deterministic bytes under one explicit external anchor."""
    _run(
        lambda: _SERVICE.package_verify(
            archive,
            manifest_sha256=manifest_sha256,
            export_receipt_sha256=export_receipt_sha256,
        ),
        status=1,
    )


@app.command()
def preview(
    path: Path,
    rules: str = typer.Option("", "--rules"),
    custom: str = typer.Option("", "--custom"),
    source_root: Path | None = typer.Option(None, "--source-root"),
) -> None:
    """Plan and replay cleaning without writing state.

    Passing a workspace previews the exact durable plan that ``clean`` will
    commit. A raw-file preview uses the same portable parse-input binding;
    ``--source-root`` supplies the locator used by a later parse.
    """
    import re

    _run(
        lambda: _SERVICE.preview(
            path,
            rules=rules,
            custom=custom,
            source_root=source_root,
        ),
        extra_exceptions=(re.error,),
    )


@export_app.command(name="discover")
def export_discover() -> None:
    """Discover executable export profiles from the shared service."""

    def run():
        outcome = _SERVICE.discover_exports()
        assert outcome.discovery is not None
        return outcome.discovery

    _run_export_operation(
        "discover",
        export_discovery_response,
        run,
    )


@export_app.command(name="dry-run")
def export_dry_run(
    request_json: str = typer.Option(..., "--request-json"),
) -> None:
    """Derive and summarize an export plan without destination access."""

    def run():
        request = export_request_from_json_bytes(
            request_json.encode("utf-8"),
            expected_operation="dry_run",
        )
        outcome = _SERVICE.dry_run_export(request)
        assert outcome.preview is not None
        return outcome.preview

    _run_export_operation(
        "dry_run",
        export_dry_run_preview_response,
        run,
        response_schema=EXPORT_SURFACE_RESPONSE_SCHEMA_V2,
    )


@export_app.command(name="inspect")
def export_inspect(
    request_json: str = typer.Option(..., "--request-json"),
) -> None:
    """Inspect one self-described export tree without asserting source trust."""

    with _export_cancellation_check() as cancellation_check:

        def run():
            request = export_request_from_json_bytes(
                request_json.encode("utf-8"),
                expected_operation="inspect",
            )
            outcome = _SERVICE.inspect_export(
                request,
                cancellation_check=cancellation_check,
            )
            assert outcome.inspection is not None
            return outcome.inspection

        _run_export_operation("inspect", export_inspection_response, run)


@export_app.command(name="execute")
def export_execute(
    request_json: str = typer.Option(..., "--request-json"),
) -> None:
    """Atomically publish one operator-confirmed export plan."""

    with _export_cancellation_check() as cancellation_check:

        def run():
            request = export_request_from_json_bytes(
                request_json.encode("utf-8"),
                expected_operation="execute",
            )
            outcome = _SERVICE.execute_export(
                request,
                cancellation_check=cancellation_check,
            )
            assert outcome.publication is not None
            return outcome.publication

        _run_export_operation("execute", export_execution_response, run)


@app.command(name="export-verify")
def export_verify(
    request_json: str = typer.Option(..., "--request-json"),
) -> None:
    """Source-bind and independently verify one visible export tree."""

    with _export_cancellation_check() as cancellation_check:

        def run():
            request = export_request_from_json_bytes(
                request_json.encode("utf-8"),
                expected_operation="verify",
            )
            outcome = _SERVICE.verify_export(
                request,
                cancellation_check=cancellation_check,
            )
            assert outcome.verified is not None
            return outcome.verified

        _run_export_operation("verify", export_verify_response, run)


@app.command()
def version() -> None:
    _emit_outcome(_SERVICE.version())


@app.command(name="taxonomy")
def taxonomy() -> None:
    """Print implemented taxonomy discovery as deterministic JSON."""
    typer.echo(
        json.dumps(
            _SERVICE.discover_taxonomy(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@app.command(name="goals")
def goals() -> None:
    """Print the plain-language goal catalog as deterministic JSON."""
    typer.echo(
        json.dumps(
            _SERVICE.discover_goals(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@app.command(name="presets")
def presets() -> None:
    """Print the versioned recipe presets and defaults as deterministic JSON."""
    typer.echo(
        json.dumps(
            _SERVICE.discover_presets(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@app.command(name="modes")
def modes() -> None:
    """Print compiler-path input modes as deterministic JSON."""
    typer.echo(
        json.dumps(
            _SERVICE.discover_modes(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@app.command(name="mapping-rejections")
def mapping_rejections(
    path: Path,
    plan: Path = typer.Option(..., "--plan"),
    output: Path = typer.Option(..., "--output", help="Directory for the report."),
    source_root: Path | None = typer.Option(None, "--source-root"),
) -> None:
    """Write a content-addressed mapping rejection report. Not a verified export."""
    try:
        payload = _SERVICE.export_mapping_rejections(
            path,
            json.loads(plan.read_text(encoding="utf-8")),
            output,
            source_root=source_root,
        )
    except VeriformisError as exc:
        _echo_error(exc)
        return
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


@app.command(name="mapping-preview")
def mapping_preview(
    path: Path,
    plan: Path = typer.Option(..., "--plan"),
    source_root: Path | None = typer.Option(None, "--source-root"),
) -> None:
    """Preview mapping across the full JSONL file without writing a workspace."""
    try:
        payload = _SERVICE.preview_mapping(
            path,
            json.loads(plan.read_text(encoding="utf-8")),
            source_root=source_root,
        )
    except VeriformisError as exc:
        _echo_error(exc)
        return
    typer.echo(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))


@app.command(name="mapping-detect")
def mapping_detect(
    path: Path,
    source_root: Path | None = typer.Option(None, "--source-root"),
    goal: str | None = typer.Option(None, "--goal"),
    representation: str | None = typer.Option(None, "--representation"),
) -> None:
    """Propose mapping plans for one JSONL file without writing a workspace."""
    try:
        payload = _SERVICE.detect_mapping(
            path,
            source_root=source_root,
            goal=goal,
            representation=representation,
        )
    except VeriformisError as exc:
        _echo_error(exc)
        return
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    if payload.get("refusal"):
        raise typer.Exit(code=2)


@app.command(name="mapping-templates")
def mapping_templates() -> None:
    """Print packaged mapping templates as deterministic JSON."""
    typer.echo(
        json.dumps(
            _SERVICE.discover_mapping_templates(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@app.command(name="mapping-contracts")
def mapping_contracts() -> None:
    """Print row-mapping contract discovery as deterministic JSON."""
    typer.echo(
        json.dumps(
            _SERVICE.discover_mapping_contracts(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@app.command(name="profile-admissions")
def profile_admissions() -> None:
    """Print implemented TRL and MLX-LM admission pins as deterministic JSON."""
    typer.echo(
        json.dumps(
            _SERVICE.discover_profile_admissions(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@app.command(name="candidate-profile-admissions")
def candidate_profile_admissions() -> None:
    """Print Phase 10 candidate admission pins as deterministic JSON."""
    typer.echo(
        json.dumps(
            _SERVICE.discover_candidate_profile_admissions(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@app.command(name="columnar-schemas")
def columnar_schemas() -> None:
    """Print packaged Arrow and Hugging Face feature schema pins as JSON."""
    typer.echo(
        json.dumps(
            _SERVICE.discover_columnar_schemas(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


@app.command(name="preflight")
def preflight(
    paths: list[Path],
    source_root: Path | None = typer.Option(None, "--source-root"),
    goal: str | None = typer.Option(None, "--goal", help="Plain-language goal id."),
    preset: str | None = typer.Option(None, "--preset", help="Recipe preset id."),
    representation: str | None = typer.Option(
        None, "--representation", help="Catalog representation id."
    ),
    instruction: str | None = typer.Option(
        None,
        "--instruction",
        help=(
            "Operator instruction for instruction-and-output; omitted uses the "
            "goal's catalog template after the truthfulness check."
        ),
    ),
    rules: str = typer.Option("", "--rules"),
    custom: str = typer.Option("", "--custom"),
    strategy: str | None = typer.Option(None, "--strategy"),
    size: int | None = typer.Option(None, "--size"),
    overlap: int | None = typer.Option(None, "--overlap"),
    split_ratio_ppm: int | None = typer.Option(None, "--split-ratio-ppm"),
    require_review: bool | None = typer.Option(
        None, "--require-review/--no-require-review"
    ),
    consumer_profile: str | None = typer.Option(None, "--consumer-profile"),
    minimum_target_characters: int | None = typer.Option(
        None, "--minimum-target-characters"
    ),
    balance_mode: str | None = typer.Option(None, "--balance-mode"),
    maximum_records_per_primary_source: int | None = typer.Option(
        None, "--maximum-records-per-primary-source"
    ),
    evaluation_ratio_ppm: int | None = typer.Option(None, "--evaluation-ratio-ppm"),
    evaluation_required: bool | None = typer.Option(
        None, "--require-evaluation/--allow-empty-evaluation"
    ),
    split_seed: str | None = typer.Option(None, "--split-seed"),
    review_policy: str | None = typer.Option(None, "--review-policy"),
    mode: str | None = typer.Option(
        None,
        "--mode",
        help="Compiler path: document-source (default), dataset-row, or mixed.",
    ),
) -> None:
    """Evaluate raw-source compile readiness without creating a workspace."""

    def run():
        outcome = _SERVICE.preflight(
            paths,
            source_root=source_root,
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
        typer.echo(outcome.preflight.transport_text())
        return outcome

    _run(run)


@app.command(name="goal-preview")
def goal_preview(
    workspace: Path,
    representation: str | None = typer.Option(
        None,
        "--representation",
        help="Catalog representation id; defaults to the recipe's row schema.",
    ),
    instruction: str | None = typer.Option(
        None,
        "--instruction",
        help=(
            "Operator instruction for instruction-and-output; omitted uses the "
            "goal's catalog template after the truthfulness check."
        ),
    ),
    record: list[str] | None = typer.Option(
        None,
        "--record",
        help="Repeat an accepted record id to preview specific records.",
    ),
) -> None:
    """Show exactly what each record is and which region receives loss."""

    def run():
        outcome = _SERVICE.preview_goal(
            workspace,
            representation=representation,
            instruction=instruction,
            record_ids=tuple(record or ()),
        )
        typer.echo(outcome.preview.transport_text())
        return outcome

    _run(run)


@app.command(name="list-recipes")
def list_recipes() -> None:
    """List named deterministic recipe library identifiers."""
    from veriformis.recipes import list_named_recipes

    for item in list_named_recipes():
        typer.echo(
            f"{item['recipe_library_id']}: objective={item['objective']} "
            f"row_schema={item['target_row_schema']}"
        )


@app.command(name="run")
def run_pipeline(pipeline: Path) -> None:
    """Execute one versioned YAML pipeline document through PipelineService."""
    from veriformis.recipes import load_pipeline_spec, run_pipeline_spec

    try:
        spec = load_pipeline_spec(pipeline)
        result = run_pipeline_spec(spec, service=_SERVICE)
    except SealPartialPublicationError as exc:
        publication = exc.publication
        typer.echo(
            f"published bundle remains visible at {publication.bundle_path}; "
            f"manifest SHA-256 {publication.manifest_sha256}; workspace receipt "
            "did not commit",
            err=True,
        )
        _echo_error(exc.cause if isinstance(exc.cause, Exception) else exc, status=1)
    except (
        VeriformisError,
        EvidenceError,
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
    ) as exc:
        _echo_error(exc)
    for outcome in result.outcomes:
        _emit_outcome(outcome)
    if result.bundle is not None:
        typer.echo(f"pipeline bundle: {result.bundle}")
    typer.echo(f"pipeline workspace: {result.workspace}")


@app.command(name="mcp")
def mcp_serve() -> None:
    """Run the constrained local MCP adapter over PipelineService (stdio)."""
    from veriformis.mcp import run_mcp_stdio

    run_mcp_stdio(_SERVICE)


@app.command(name="handoff")
def handoff_cmd(
    bundle: Path,
    manifest_sha256: str = typer.Option(..., "--manifest-sha256"),
    out: Path | None = typer.Option(None, "-o", help="Handoff path (default sibling)."),
) -> None:
    """Build the versioned Aptus handoff descriptor for a sealed bundle."""
    from veriformis.handoff import (
        build_aptus_handoff,
        handoff_path_for_bundle,
        write_aptus_handoff,
    )

    try:
        handoff = build_aptus_handoff(
            bundle,
            expected_manifest_sha256=manifest_sha256,
        )
        target = out if out is not None else handoff_path_for_bundle(bundle)
        write_aptus_handoff(handoff, target)
    except (
        VeriformisError,
        EvidenceError,
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
    ) as exc:
        _echo_error(exc)
    typer.echo(f"aptus handoff: {target}")
    typer.echo(f"handoff id: {handoff.handoff_id}")
    typer.echo(f"assignment digest: {handoff.assignment_digest}")
    typer.echo(f"row schema: {handoff.row_schema}")


@app.command(name="handoff-verify")
def handoff_verify_cmd(
    handoff: Path,
    bundle: Path = typer.Option(..., "-b", "--bundle"),
) -> None:
    """Independently verify that a sealed bundle satisfies an Aptus handoff."""
    from veriformis.handoff import consume_aptus_handoff

    try:
        report = consume_aptus_handoff(handoff, bundle=bundle)
    except (
        VeriformisError,
        EvidenceError,
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
    ) as exc:
        _echo_error(exc, status=1)
    typer.echo(f"status: {report.status}")
    typer.echo(f"handoff id: {report.handoff_id}")
    typer.echo(f"bundle: {report.bundle_id}")
    typer.echo(f"assignment digest: {report.assignment_digest}")
    typer.echo(f"verification grade: {report.verified_grade}")
    for finding in report.findings:
        typer.echo(f"finding: {finding}", err=True)
    if report.status != "accepted":
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
