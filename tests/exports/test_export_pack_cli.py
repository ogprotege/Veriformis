"""CLI admission tests for the Phase 5.4 export-pack transport profile."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.exports import (
    EXPORT_SURFACE_REQUEST_SCHEMA,
    ExportDryRunRequest,
    ExportExecuteRequest,
    ExportService,
)
from veriformis.identity import sha256_digest


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "regressions"
    / "fixtures"
    / "phase3"
    / "pre-taxonomy-full-text.vfbundle.json"
)
EXPECTED_MANIFEST_SHA256 = (
    "2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733"
)


def _published_export(root: Path) -> tuple[Path, str, str, str, str]:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bundle = root / "source.vfbundle"
    for relative_path, encoded in sorted(fixture["files_base64"].items()):
        target = bundle.joinpath(*relative_path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(encoded, validate=True))

    selection = {
        "schema_version": EXPORT_SURFACE_REQUEST_SCHEMA,
        "bundle": str(bundle),
        "container_id": "split-jsonl-directory",
        "container_version": 1,
        "consumer_id": None,
        "consumer_profile_version": None,
        "source_trust_policy": "require_external_digest",
        "expected_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "overwrite_policy": "refuse",
    }
    service = ExportService()
    plan = service.dry_run_export(
        ExportDryRunRequest(operation="dry_run", **selection)
    )
    destination = root / "generic-export"
    publication = service.execute_export(
        ExportExecuteRequest(
            operation="execute",
            destination_root=str(destination),
            expected_export_plan_id=plan.export_plan_id,
            **selection,
        )
    )
    receipt_sha256 = sha256_digest(
        (destination / "export-receipt.json").read_bytes()
    )
    return (
        destination,
        receipt_sha256,
        plan.export_plan_id,
        publication.receipt.export_receipt_id,
        publication.receipt.output_content_root_sha256,
    )


def _tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_package_cli_archives_and_verifies_an_anchored_export_pack(
    tmp_path: Path,
) -> None:
    export_root, receipt_sha256, plan_id, receipt_id, content_root = _published_export(
        tmp_path
    )
    before = _tree(export_root)
    archive = tmp_path / "generic.vfexport.zip"
    runner = CliRunner()

    packaged = runner.invoke(
        app,
        [
            "package",
            str(export_root),
            "-o",
            str(archive),
            "--export-receipt-sha256",
            receipt_sha256,
        ],
    )

    assert packaged.exit_code == 0, packaged.output
    assert archive.is_file()
    assert f"export receipt SHA-256: {receipt_sha256}" in packaged.output
    assert f"export receipt: {receipt_id}" in packaged.output
    assert f"export plan: {plan_id}" in packaged.output
    assert f"output content root SHA-256: {content_root}" in packaged.output
    assert "source trust grade: external_digest" in packaged.output
    assert "verification grade:" not in packaged.output
    assert _tree(export_root) == before

    verified = runner.invoke(
        app,
        [
            "package-verify",
            str(archive),
            "--export-receipt-sha256",
            receipt_sha256,
        ],
    )

    assert verified.exit_code == 0, verified.output
    assert "transport archive status: accepted" in verified.output
    assert f"export receipt: {receipt_id}" in verified.output
    assert f"export plan: {plan_id}" in verified.output
    assert f"output content root SHA-256: {content_root}" in verified.output
    assert "source trust grade: external_digest" in verified.output
    assert "verification grade:" not in verified.output
