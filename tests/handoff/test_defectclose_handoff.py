"""Defect closure: JSONL framing, bound-path pinning, and fail-closed reports.

Sealed JSONL frames records on the single byte ``b"\\n"`` and legitimately
preserves raw U+2028/U+2029/U+0085 inside row text. Descriptor bound paths are
contract constants, binding digests must agree with the verified manifest, and
consumer checks report rejection instead of crashing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import veriformis.handoff.aptus_v1 as aptus_module
from veriformis.handoff import (
    AptusHandoffError,
    build_aptus_handoff,
    consume_aptus_handoff,
    handoff_path_for_bundle,
    write_aptus_handoff,
)
from veriformis.identity import derive_id, sha256_digest
from veriformis.pipeline import PipelineService

LINE_SEPARATOR = chr(0x2028)


def _seal_supervised(tmp_path: Path, *, source_text: str | None = None) -> tuple[Path, str]:
    source = tmp_path / "source.txt"
    source.write_text(
        source_text
        if source_text is not None
        else (
            "Prompt-bearing first paragraph with enough grounded text.\n\n"
            "Second paragraph continues the supervised construction material."
        ),
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


def _forge(handoff_dict: dict[str, Any], binding_field: str, **updates: Any) -> dict[str, Any]:
    """Return a self-consistent descriptor whose one binding was tampered."""
    body = {key: value for key, value in handoff_dict.items() if key != "handoff_id"}
    binding = dict(body[binding_field])
    binding.update(updates)
    body[binding_field] = binding
    return {"handoff_id": derive_id("ahd", body), **body}


def test_handoff_round_trip_preserves_raw_line_separator_rows(tmp_path):
    bundle, manifest_sha = _seal_supervised(
        tmp_path,
        source_text=(
            "Prompt-bearing first paragraph with a"
            + LINE_SEPARATOR
            + "line separator embedded in enough grounded text to construct a"
            " supervised continuation record.\n\n"
            "Second paragraph continues the supervised construction material."
        ),
    )
    partitions = (bundle / "data" / "train.jsonl").read_bytes() + (
        bundle / "data" / "evaluation.jsonl"
    ).read_bytes()
    assert LINE_SEPARATOR.encode("utf-8") in partitions

    handoff = build_aptus_handoff(bundle, expected_manifest_sha256=manifest_sha)
    path = write_aptus_handoff(handoff, handoff_path_for_bundle(bundle))
    report = consume_aptus_handoff(path, bundle=bundle)
    assert report.status == "accepted", report.findings
    assert report.verified_grade == "external_digest"
    assert not report.findings


@pytest.mark.parametrize(
    "forged_path",
    ("../outside.jsonl", "/absolute/outside.jsonl", "data/../../outside.jsonl"),
)
def test_descriptor_rejects_noncontract_bound_paths_without_outside_reads(
    tmp_path,
    monkeypatch,
    forged_path,
):
    bundle, manifest_sha = _seal_supervised(tmp_path)
    handoff = build_aptus_handoff(bundle, expected_manifest_sha256=manifest_sha)
    # A digest-consistent sibling outside the bundle: the exact bytes the
    # forged binding still declares, so the old consumer accepted it.
    outside = tmp_path / "outside.jsonl"
    outside.write_bytes((bundle / "data" / "train.jsonl").read_bytes())
    forged = _forge(handoff.to_dict(), "train", path=forged_path)

    observed: list[Path] = []
    original_read_bytes = Path.read_bytes

    def recording_read_bytes(path, *args, **kwargs):
        observed.append(Path(path).resolve())
        return original_read_bytes(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", recording_read_bytes)
    with pytest.raises(AptusHandoffError):
        consume_aptus_handoff(forged, bundle=bundle)

    bundle_root = bundle.resolve()
    assert all(
        path == bundle_root or bundle_root in path.parents for path in observed
    ), observed


def test_forged_binding_digest_is_cross_checked_against_manifest(tmp_path):
    bundle, manifest_sha = _seal_supervised(tmp_path)
    handoff = build_aptus_handoff(bundle, expected_manifest_sha256=manifest_sha)
    forged = _forge(
        handoff.to_dict(),
        "train",
        sha256=sha256_digest(b"forged partition payload"),
    )

    report = consume_aptus_handoff(forged, bundle=bundle)
    assert report.status == "rejected"
    assert any(
        finding == "manifest-binding-mismatch:data/train.jsonl"
        for finding in report.findings
    ), report.findings


def test_missing_bound_file_after_verification_yields_rejected_report(
    tmp_path,
    monkeypatch,
):
    bundle, manifest_sha = _seal_supervised(tmp_path)
    handoff = build_aptus_handoff(bundle, expected_manifest_sha256=manifest_sha)
    real_verify = aptus_module.verify_finished_bundle

    def verify_then_lose_train(bundle_path, **kwargs):
        result = real_verify(bundle_path, **kwargs)
        (Path(bundle_path) / "data" / "train.jsonl").unlink()
        return result

    monkeypatch.setattr(aptus_module, "verify_finished_bundle", verify_then_lose_train)
    report = consume_aptus_handoff(handoff, bundle=bundle)

    assert report.status == "rejected"
    assert any(
        finding.startswith("missing-file:data/train.jsonl")
        for finding in report.findings
    ), report.findings


def test_existing_written_descriptor_still_loads_and_verifies(tmp_path):
    bundle, manifest_sha = _seal_supervised(tmp_path)
    handoff = build_aptus_handoff(bundle, expected_manifest_sha256=manifest_sha)
    path = write_aptus_handoff(handoff, handoff_path_for_bundle(bundle))
    raw = json.loads(path.read_text(encoding="utf-8"))
    # Identity derivation is unchanged: the persisted descriptor re-validates
    # exactly and its handoff_id still matches the derived identity.
    assert raw["handoff_id"] == derive_id(
        "ahd", {key: value for key, value in raw.items() if key != "handoff_id"}
    )
    report = consume_aptus_handoff(path, bundle=bundle)
    assert report.status == "accepted", report.findings
