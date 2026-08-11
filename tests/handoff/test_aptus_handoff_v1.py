"""Aptus handoff v1: build, consume, and fail-closed verification."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.handoff import (
    build_aptus_handoff,
    consume_aptus_handoff,
    handoff_path_for_bundle,
    write_aptus_handoff,
)
from veriformis.pipeline import PipelineService

runner = CliRunner()
pytestmark = pytest.mark.aptus_integration


def _seal_supervised(tmp_path: Path) -> tuple[Path, str]:
    source = tmp_path / "source.txt"
    source.write_text(
        "Prompt-bearing first paragraph with enough grounded text.\n\n"
        "Second paragraph continues the supervised construction material.",
        encoding="utf-8",
    )
    workspace = tmp_path / "workspace"
    bundle = tmp_path / "out.vfbundle"
    service = PipelineService()
    service.parse([source], workspace, source_root=tmp_path)
    service.clean(workspace)
    service.chunk(workspace)
    service.construct(workspace, objective="continuation", split_ratio_ppm=400_000)
    service.curate(workspace, evaluation_required=False)
    service.split(workspace)
    service.format(workspace)
    assert service.validate(workspace).exit_status == 0
    sealed = service.seal(workspace, bundle)
    assert sealed.publication is not None
    return bundle, sealed.publication.manifest_sha256


def test_build_and_consume_aptus_handoff_accepts_supervised_bundle(tmp_path):
    bundle, manifest_sha = _seal_supervised(tmp_path)
    handoff = build_aptus_handoff(bundle, expected_manifest_sha256=manifest_sha)
    path = write_aptus_handoff(handoff, handoff_path_for_bundle(bundle))
    assert path.is_file()
    assert handoff.row_schema == "prompt_completion"
    assert handoff.required_verification_grade == "external_digest"
    assert handoff.masking.supervised_boundary == "completion-only"

    report = consume_aptus_handoff(path, bundle=bundle)
    assert report.status == "accepted", report.findings
    assert report.verified_grade == "external_digest"
    assert report.assignment_digest == handoff.assignment_digest
    assert not report.findings


def test_handoff_detects_partition_tamper(tmp_path):
    bundle, manifest_sha = _seal_supervised(tmp_path)
    handoff = build_aptus_handoff(bundle, expected_manifest_sha256=manifest_sha)
    path = write_aptus_handoff(handoff, handoff_path_for_bundle(bundle))
    train = bundle / "data" / "train.jsonl"
    # Overwrite with different valid JSONL so closed-set verify fails and digests diverge.
    train.write_text('{"prompt":"tampered","completion":"payload"}\n', encoding="utf-8")
    report = consume_aptus_handoff(path, bundle=bundle)
    assert report.status == "rejected"
    assert report.findings
    assert any(
        "digest-mismatch" in finding or "bundle-verification-failed" in finding
        for finding in report.findings
    )


def test_cli_seal_writes_handoff_and_handoff_verify(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text(
        "CLI seal path first paragraph for supervised construction.\n\n"
        "CLI seal path second paragraph keeps multi-block text.",
        encoding="utf-8",
    )
    workspace = tmp_path / "ws"
    bundle = tmp_path / "cli.vfbundle"
    commands = [
        ["parse", str(source), "-o", str(workspace), "--source-root", str(tmp_path)],
        ["clean", str(workspace)],
        ["chunk", str(workspace)],
        [
            "construct",
            str(workspace),
            "--objective",
            "continuation",
            "--split-ratio-ppm",
            "400000",
        ],
        ["curate", str(workspace), "--allow-empty-evaluation"],
        ["split", str(workspace)],
        ["format", str(workspace)],
        ["validate", str(workspace)],
        ["seal", str(workspace), "-o", str(bundle), "--aptus-handoff"],
    ]
    for command in commands:
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.output
    handoff_path = handoff_path_for_bundle(bundle)
    assert handoff_path.is_file()
    # Extract manifest sha from seal output
    sealed = runner.invoke(
        app,
        ["seal", str(workspace), "-o", str(bundle), "--aptus-handoff"],
    )
    # second seal recovers exact bundle
    assert sealed.exit_code == 0, sealed.output
    manifest_line = next(
        line for line in sealed.output.splitlines() if line.startswith("manifest SHA-256:")
    )
    manifest_sha = manifest_line.split(":", 1)[1].strip()
    verified = runner.invoke(
        app,
        [
            "handoff-verify",
            str(handoff_path),
            "--bundle",
            str(bundle),
        ],
    )
    assert verified.exit_code == 0, verified.output
    assert "status: accepted" in verified.output

    rebuilt = runner.invoke(
        app,
        [
            "handoff",
            str(bundle),
            "--manifest-sha256",
            manifest_sha,
            "-o",
            str(tmp_path / "explicit.handoff.json"),
        ],
    )
    assert rebuilt.exit_code == 0, rebuilt.output
