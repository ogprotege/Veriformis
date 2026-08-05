"""Permanent Group 9 release-gate locks.

These tests lock the automated public-release path that does not require Apple
Developer credentials. They do not claim signed/notarized Mac readiness.
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from veriformis.handoff import (
    build_aptus_handoff,
    consume_aptus_handoff,
    handoff_path_for_bundle,
    write_aptus_handoff,
)
from veriformis.pipeline import PipelineService

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "acceptance" / "v1"
RELEASE_SCRIPTS = REPO_ROOT / "scripts" / "release"


def _golden_sources() -> list[Path]:
    return sorted(
        path
        for path in (FIXTURE_ROOT / "raw" / "corpus").rglob("*")
        if path.is_file()
    )


def _seal_objective(tmp_path: Path, objective: str) -> tuple[Path, str]:
    sources = _golden_sources()
    assert sources
    workspace = tmp_path / f"ws-{objective}"
    bundle = tmp_path / f"{objective}.vfbundle"
    service = PipelineService()
    service.parse(sources, workspace, source_root=FIXTURE_ROOT)
    service.clean(workspace)
    service.chunk(workspace)
    if objective == "continuation":
        service.construct(
            workspace,
            objective=objective,
            split_ratio_ppm=400_000,
        )
    else:
        service.construct(workspace, objective=objective)
    service.curate(workspace, evaluation_required=False)
    service.split(workspace)
    service.format(workspace)
    assert service.validate(workspace).exit_status == 0
    sealed = service.seal(workspace, bundle)
    assert sealed.publication is not None
    verify = service.verify(
        bundle,
        manifest_sha256=sealed.publication.manifest_sha256,
    )
    assert verify.verification is not None
    assert verify.verification.trust_grade == "external_digest"
    # Service seal is surface-neutral; Aptus sibling is built like CLI default.
    handoff = build_aptus_handoff(
        bundle,
        expected_manifest_sha256=sealed.publication.manifest_sha256,
    )
    path = write_aptus_handoff(handoff, handoff_path_for_bundle(bundle))
    return bundle, sealed.publication.manifest_sha256, path


def test_golden_corpus_full_text_external_digest_and_text_schema_handoff(tmp_path):
    """full_text seals and verifies; Aptus v1 rejects plain text row schema."""
    bundle, manifest_sha, handoff = _seal_objective(tmp_path, "full_text")
    assert handoff.is_file()
    report = consume_aptus_handoff(handoff, bundle=bundle)
    assert report.status == "rejected"
    assert any("backend-rejects-row-schema:text" in f for f in report.findings)
    assert len(manifest_sha) == 64
    # Bundle itself remains externally digests-verified (service path above).
    assert (bundle / "manifest.json").is_file()


def test_golden_corpus_continuation_external_digest_and_handoff_accepted(tmp_path):
    """continuation is the Aptus-compatible golden handoff path."""
    bundle, manifest_sha, handoff = _seal_objective(tmp_path, "continuation")
    assert handoff.is_file()
    report = consume_aptus_handoff(handoff, bundle=bundle)
    assert report.status == "accepted", report.findings
    assert report.verified_grade == "external_digest"
    assert len(manifest_sha) == 64


def test_release_scripts_are_executable_entry_points():
    """CI and operators invoke these paths; they must remain present and executable.

    End-to-end script execution is covered by the CI `golden-compile` and
    `install-smoke` jobs (see `.github/workflows/ci.yml` and `docs/release.md`).
    """
    required = (
        "smoke_install.sh",
        "golden_compile.sh",
        "macos_package_local.sh",
    )
    for name in required:
        path = RELEASE_SCRIPTS / name
        assert path.is_file(), name
        mode = path.stat().st_mode
        assert mode & stat.S_IXUSR, f"{name} must be executable"
        text = path.read_text(encoding="utf-8")
        assert text.startswith("#!/"), name
