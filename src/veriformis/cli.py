"""Veriformis CLI adapter over ``PipelineService``.

The CLI translates arguments, stage outcomes, and failures only. Stage policy
and workspace orchestration live in ``veriformis.pipeline``.
"""

from __future__ import annotations

from pathlib import Path

import typer

from veriformis.errors import VeriformisError
from veriformis.evidence import EvidenceError
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


@app.command()
def parse(
    paths: list[Path],
    out: Path = typer.Option(..., "-o"),
    source_root: Path | None = typer.Option(None, "--source-root"),
) -> None:
    """Capture raw files and commit one canonical parse revision."""
    _run(lambda: _SERVICE.parse(paths, out, source_root=source_root))


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
    strategy: str = typer.Option("paragraph", "--strategy"),
    size: int = typer.Option(1000, "--size"),
    overlap: int = typer.Option(100, "--overlap"),
) -> None:
    """Chunk cleaned documents with exact reconstructible source evidence."""
    _run(
        lambda: _SERVICE.chunk(
            workspace,
            strategy=strategy,
            size=size,
            overlap=overlap,
        )
    )


@app.command(name="upgrade-workspace")
def upgrade_workspace(workspace: Path) -> None:
    """Advance a verified workspace through every supported revision migration."""
    _run(lambda: _SERVICE.upgrade_workspace(workspace))


@app.command()
def construct(
    workspace: Path,
    objective: str = typer.Option(..., "--objective"),
    source: list[str] | None = typer.Option(
        None,
        "--source",
        help="Repeat a source ID or logical path to select a subset.",
    ),
    target_row_schema: str | None = typer.Option(
        None,
        "--target-row-schema",
    ),
    split_ratio_ppm: int = typer.Option(500_000, "--split-ratio-ppm"),
    require_review: bool = typer.Option(False, "--require-review"),
) -> None:
    """Construct evidence-bearing candidates and immutable accepted records."""
    _run(
        lambda: _SERVICE.construct(
            workspace,
            objective=objective,
            source=source,
            target_row_schema=target_row_schema,
            split_ratio_ppm=split_ratio_ppm,
            require_review=require_review,
        )
    )


@app.command()
def curate(
    workspace: Path,
    minimum_target_characters: int = typer.Option(
        1,
        "--minimum-target-characters",
    ),
    balance_mode: str = typer.Option("none", "--balance-mode"),
    maximum_records_per_primary_source: int | None = typer.Option(
        None,
        "--maximum-records-per-primary-source",
    ),
    evaluation_ratio_ppm: int = typer.Option(500_000, "--evaluation-ratio-ppm"),
    evaluation_required: bool = typer.Option(
        True,
        "--require-evaluation/--allow-empty-evaluation",
    ),
    split_seed: str = typer.Option("veriformis-v1", "--split-seed"),
    instruction: str | None = typer.Option(None, "--instruction"),
) -> None:
    """Fix the complete dataset plan, then curate constructed records."""
    _run(
        lambda: _SERVICE.curate(
            workspace,
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


@app.command()
def version() -> None:
    _emit_outcome(_SERVICE.version())


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
