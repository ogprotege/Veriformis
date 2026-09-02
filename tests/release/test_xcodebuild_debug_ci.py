"""Post-20 remainder: unsigned Debug xcodebuild is optional, not a public Mac claim."""

from __future__ import annotations

from pathlib import Path

from veriformis.release import support_matrix


ROOT = Path(__file__).resolve().parents[2]
CI = ROOT / ".github/workflows/ci.yml"
SCRIPT = ROOT / "scripts/release/xcodebuild_debug.sh"


def _workflows() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / ".github/workflows").glob("*.yml")
    )


def _xcodebuild_job(ci: str) -> str:
    marker = "  xcodebuild-debug:"
    start = ci.index(marker)
    return ci[start:]


def test_unsigned_debug_xcodebuild_is_optional_and_not_a_public_mac_claim() -> None:
    workflows = _workflows()
    ci = CI.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    job = _xcodebuild_job(ci)
    assert "xcodebuild" in workflows
    assert "name: xcodebuild-debug (optional)" in job
    assert "continue-on-error: true" in job
    assert "macos-latest" in job
    assert "xcodebuild_debug.sh" in job
    assert "CODE_SIGNING_ALLOWED=NO" in script
    assert "-scheme Veriformis" in script
    assert "-configuration Debug" in script
    assert "  test \\\n  CODE_SIGNING_ALLOWED=NO" in script
    assert "notarytool" not in workflows
    assert "stapler" not in workflows
    assert "secrets:" not in workflows.lower()
    assert "Signing/notarization remain owner-executed" in ci
    matrix = support_matrix()
    assert matrix.platforms.public_signed_mac is False
    assert matrix.platforms.macos_workbench == "local-dev-thin-adapter"


def test_live_copy_does_not_present_tense_skip_github_xcodebuild() -> None:
    phrase = (
        "GitHub xcodebuild, virtualization, and full localization are skipped"
    )
    for relative in ("docs/current-status.md", "CLAUDE.md", "CONTRIBUTING.md"):
        collapsed = " ".join((ROOT / relative).read_text(encoding="utf-8").split())
        assert phrase not in collapsed, relative


def test_cli_reference_command_count_matches_typer() -> None:
    from veriformis.cli import app

    count = len(app.registered_commands)
    cli = (ROOT / "docs/cli.md").read_text(encoding="utf-8")
    entry = (ROOT / "docs/architecture/entry-points.md").read_text(encoding="utf-8")
    assert f"{count} commands" in cli
    assert f"{count} `@app.command`" in entry


def test_quality_report_contract_names_family_hook_facts() -> None:
    from veriformis.quality.family_hooks import FAMILY_HOOK_FACT_NAMES

    text = (ROOT / "docs/contracts/quality-report-v1.md").read_text(encoding="utf-8")
    for name in FAMILY_HOOK_FACT_NAMES:
        assert name in text, name
    assert "preview-family-missing-label" in text
    assert "not a gate" in text.lower() or "admitted-to-block" in text


def test_isolation_names_do_not_claim_cli_lacks_quality_report() -> None:
    files = (
        ROOT / "tests/automation/test_phase19_automation_isolation.py",
        ROOT / "tests/automation/test_phase19_adversarial_closeout.py",
    )
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "have_no_hub_generator_or_quality_report" not in text
        assert "test_hub_quality_report_and_package_mcp_stay_absent" not in text


def test_tracking_script_pins_remainder_flags() -> None:
    text = (ROOT / "scripts/check_project_tracking.py").read_text(encoding="utf-8")
    assert "quality_report_command" in text
    assert "xcodebuild-debug" in text


def test_remainder_docs_last_reviewed_is_not_pre_remainder() -> None:
    for relative, stale in (
        ("WIP.md", "Last reviewed:** 2026-09-01"),
        ("docs/product-contract.md", "Last reviewed:** 2026-09-01"),
        ("docs/release.md", "Last reviewed:** 2026-08-11"),
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert stale not in text, relative


def test_quality_report_service_does_not_repeat_enforcing_check() -> None:
    import inspect

    from veriformis.pipeline.service import PipelineService

    source = inspect.getsource(PipelineService.quality_report)
    assert "require_quality_report_not_enforcing" in source
    assert "if report.enforcing is not False" not in source


def test_beta_limitations_does_not_claim_no_ocr() -> None:
    text = (ROOT / "docs/beta-limitations.md").read_text(encoding="utf-8")
    assert "**No OCR.**" not in text
    assert "ocr-image" in text
    assert "Last reviewed:** 2026-08-11" not in text
