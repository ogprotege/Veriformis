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
def seal(workspace: Path, out: Path = typer.Option(..., "-o")) -> None:
    """Revalidate, atomically publish, and receipt one finished dataset."""
    _run(lambda: _SERVICE.seal(workspace, out), status=1)


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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
