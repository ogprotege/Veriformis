"""Permanent Group 9 release-gate locks.

These tests lock the automated public-release path that does not require Apple
Developer credentials. They do not claim signed/notarized Mac readiness.
"""

from __future__ import annotations

import stat
from pathlib import Path

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
    assert not Path(f"{bundle.resolve()}.aptus-handoff.json").exists()
    for relative in (
        "manifest.json",
        "attestation.json",
        "data/train.jsonl",
        "data/evaluation.jsonl",
        "metadata/row-provenance.jsonl",
        "validation.json",
    ):
        assert (bundle / relative).is_file(), relative
    return bundle, sealed.publication.manifest_sha256


def test_golden_corpus_full_text_seals_and_external_digest_verifies(tmp_path):
    """The full-text product path is complete without an integration adapter."""
    bundle, manifest_sha = _seal_objective(tmp_path, "full_text")
    assert len(manifest_sha) == 64
    assert (bundle / "manifest.json").is_file()


def test_golden_corpus_continuation_seals_and_external_digest_verifies(tmp_path):
    """The continuation product path is complete without an integration adapter."""
    bundle, manifest_sha = _seal_objective(tmp_path, "continuation")
    assert len(manifest_sha) == 64
    assert (bundle / "manifest.json").is_file()


def test_release_scripts_are_executable_entry_points():
    """CI and operators invoke these paths; they must remain present and executable.

    End-to-end script execution is covered by the CI `golden-compile` and
    `install-smoke` jobs (see `.github/workflows/ci.yml` and `docs/release.md`).
    """
    required = (
        "check_local.sh",
        "smoke_install.sh",
        "golden_compile.sh",
        "aptus_integration.sh",
        "record_clean_path_evidence.sh",
        "macos_package_local.sh",
    )
    for name in required:
        path = RELEASE_SCRIPTS / name
        assert path.is_file(), name
        mode = path.stat().st_mode
        assert mode & stat.S_IXUSR, f"{name} must be executable"
        text = path.read_text(encoding="utf-8")
        assert text.startswith("#!/"), name


def test_core_golden_does_not_invoke_optional_handoff_commands():
    """The core product proof may assert absence, but never create/consume a handoff."""
    text = (RELEASE_SCRIPTS / "golden_compile.sh").read_text(encoding="utf-8")
    assert "vf handoff " not in text
    assert "vf handoff-verify " not in text
    assert "test ! -e \"$automatic_handoff\"" in text


def test_required_pytest_commands_do_not_collect_adapter_only_module():
    """Optional adapter collection failures cannot block the core test gate."""
    required = (
        RELEASE_SCRIPTS / "check_local.sh",
        REPO_ROOT / ".github/workflows/ci.yml",
    )
    for path in required:
        text = path.read_text(encoding="utf-8")
        assert "--ignore=tests/handoff" in text, path
        assert 'not aptus_integration' in text, path
        assert "not profile_integration" in text, path
        assert "not columnar_integration" in text, path

    ci_text = required[1].read_text(encoding="utf-8")
    assert "continue-on-error: true" in ci_text
    assert 'pytest -q -m "aptus_integration"' in ci_text
    assert 'pytest -q -m "profile_integration"' in ci_text
    assert 'pytest -q -m "columnar_integration"' in ci_text
