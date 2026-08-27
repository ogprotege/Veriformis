"""Named-hardware scale baseline harness. Reports are evidence, not SLAs."""

from __future__ import annotations

import platform
import resource
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

import veriformis
from veriformis.errors import ScaleCancelled, ScaleError
from veriformis.pipeline import PipelineService
from veriformis.scale.corpora import materialize_scale_corpus, spec_by_corpus_id
from veriformis.scale.models import (
    ScaleBaselineMetrics,
    ScaleBaselineReport,
    ScaleCorpusSpec,
    ScaleHardware,
)

CancellationCheck = Callable[[], None]
PPM_DENOMINATOR = 1_000_000


def _tree_bytes(root: Path) -> int:
    if not root.exists():
        return 0
    total = 0
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            total += path.stat().st_size
    return total


def _object_count(workspace: Path) -> int:
    store = workspace / "objects" / "sha256"
    if not store.is_dir():
        return 0
    return sum(1 for path in store.rglob("*") if path.is_file() and not path.is_symlink())


def _peak_rss_bytes() -> int:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    value = int(usage.ru_maxrss)
    if sys.platform == "darwin":
        return value
    return value * 1024


def _cpu_ns(usage: resource.struct_rusage) -> tuple[int, int]:
    return int(usage.ru_utime * 1_000_000_000), int(usage.ru_stime * 1_000_000_000)


def record_scale_hardware() -> ScaleHardware:
    """Capture the current interpreter and machine. Not a product SLA."""
    return ScaleHardware(
        implementation=platform.python_implementation(),
        machine=platform.machine(),
        platform=sys.platform,
        python_version=platform.python_version(),
        veriformis_version=veriformis.__version__,
    )


def compile_document_corpus(
    service: PipelineService,
    paths: Sequence[Path],
    *,
    workspace: Path,
    bundle: Path,
    source_root: Path,
    cancellation_check: CancellationCheck | None = None,
) -> None:
    """Run parse through verify, checking cancellation between stages."""
    collected = [path if path.is_absolute() else source_root / path for path in paths]
    service.parse(collected, workspace, source_root=source_root)
    if cancellation_check is not None:
        cancellation_check()
    service.clean(workspace)
    if cancellation_check is not None:
        cancellation_check()
    service.chunk(workspace)
    if cancellation_check is not None:
        cancellation_check()
    service.construct(workspace, objective="full_text")
    if cancellation_check is not None:
        cancellation_check()
    service.curate(workspace, evaluation_required=False)
    if cancellation_check is not None:
        cancellation_check()
    service.split(workspace)
    if cancellation_check is not None:
        cancellation_check()
    service.format(workspace)
    if cancellation_check is not None:
        cancellation_check()
    validated = service.validate(workspace)
    if validated.exit_status != 0:
        raise ScaleError("scale baseline validation failed")
    if cancellation_check is not None:
        cancellation_check()
    sealed = service.seal(workspace, bundle)
    if sealed.publication is None:
        raise ScaleError("scale baseline seal produced no publication")
    if cancellation_check is not None:
        cancellation_check()
    service.verify(
        bundle,
        manifest_sha256=sealed.publication.manifest_sha256,
    )


def run_scale_baseline(
    spec: ScaleCorpusSpec,
    work_root: Path,
    *,
    service: PipelineService | None = None,
) -> ScaleBaselineReport:
    """Compile one document-source corpus and record named-hardware evidence."""
    if spec.input_mode != "document-source":
        raise ScaleError("scale baseline v1 compiles document-source corpora only")
    root = work_root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise ScaleError("scale baseline work root must be empty")

    started = time.perf_counter_ns()
    pipeline = service or PipelineService()
    startup_ns = time.perf_counter_ns() - started
    if startup_ns < 1:
        startup_ns = 1

    corpus_dir = root / "corpus"
    workspace = root / "workspace"
    bundle = root / "bundle"
    corpus = materialize_scale_corpus(spec, corpus_dir)
    paths = tuple(corpus_dir / item.path for item in corpus.files)

    cpu_before = resource.getrusage(resource.RUSAGE_SELF)
    wall_before = time.perf_counter_ns()
    compile_document_corpus(
        pipeline,
        paths,
        workspace=workspace,
        bundle=bundle,
        source_root=corpus_dir,
    )
    wall_ns = time.perf_counter_ns() - wall_before
    cpu_after = resource.getrusage(resource.RUSAGE_SELF)
    if wall_ns < 1:
        wall_ns = 1
    user_after, system_after = _cpu_ns(cpu_after)
    user_before, system_before = _cpu_ns(cpu_before)
    cpu_user_ns = max(0, user_after - user_before)
    cpu_system_ns = max(0, system_after - system_before)

    cancel_workspace = root / "cancel-workspace"
    pipeline.parse(list(paths), cancel_workspace, source_root=corpus_dir)
    cancel_observed = True
    pipeline.clean(cancel_workspace)
    resume_observed = True

    source_bytes = corpus.total_bytes
    workspace_bytes = _tree_bytes(workspace)
    bundle_bytes = _tree_bytes(bundle)
    metrics = ScaleBaselineMetrics(
        bundle_bytes=bundle_bytes,
        cancel_observed=cancel_observed,
        cpu_system_ns=cpu_system_ns,
        cpu_user_ns=cpu_user_ns,
        disk_amplification_ppm=(
            (workspace_bytes + bundle_bytes) * PPM_DENOMINATOR
        )
        // source_bytes,
        object_count=_object_count(workspace),
        peak_rss_bytes=_peak_rss_bytes(),
        resume_observed=resume_observed,
        source_bytes=source_bytes,
        startup_ns=startup_ns,
        wall_ns=wall_ns,
        workspace_bytes=workspace_bytes,
    )
    return ScaleBaselineReport.create(
        spec_id=spec.spec_id,
        corpus_id=corpus.corpus_id,
        hardware=record_scale_hardware(),
        metrics=metrics,
    )


def run_named_tiny_baseline(
    corpus_id: str,
    work_root: Path,
    *,
    service: PipelineService | None = None,
) -> ScaleBaselineReport:
    """Run the harness on one packaged spec (tiny CI or measurement ladder)."""
    return run_scale_baseline(
        spec_by_corpus_id(corpus_id),
        work_root,
        service=service,
    )


def request_scale_cancellation() -> CancellationCheck:
    """Return a check that stops the compile after the first stage."""

    def check() -> None:
        raise ScaleCancelled("scale baseline cancelled after parse")

    return check
