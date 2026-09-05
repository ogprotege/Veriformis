"""Pipeline path for reproduce-a-recorded-change on packaged single-block sources.

The v1 constructor accepts a chunk only when it has one evidence component,
that component has one edits derivation, and the chunk has no join or slice.
Default paragraph grouping of multi-block sources is the named refuse
transformation-pair-unavailable even after lowercase writes transform records.
"""

from __future__ import annotations

import json
from pathlib import Path

from veriformis.construction import (
    ConstructionResult,
    construction_result_from_json_bytes,
)
from veriformis.pipeline import CleanOutcome, ConstructOutcome, PipelineService
from veriformis.quality import require_quality_report_not_enforcing
from veriformis.workspace import Workspace

ROOT = Path(__file__).resolve().parents[2]
SERVICE = PipelineService()
PRESET = "reproduce-a-recorded-change.safe"
SINGLE_BLOCK = ROOT / "tests/fixtures/matrix/before-after"


def _construct_result(workspace: Path) -> ConstructionResult:
    store = Workspace.open(workspace)
    head = store.head()
    return construction_result_from_json_bytes(
        store.read_artifact(
            head.stages["construct"].outputs["result"],
            revision=head,
        )
    )


def _compile_single_block(
    workspace: Path,
) -> tuple[CleanOutcome, ConstructOutcome]:
    SERVICE.parse(
        [SINGLE_BLOCK / "alpha.txt", SINGLE_BLOCK / "beta.txt"],
        workspace,
        source_root=ROOT,
    )
    cleaned = SERVICE.clean(workspace, rules="lowercase")
    SERVICE.chunk(workspace, preset=PRESET)
    constructed = SERVICE.construct(workspace, preset=PRESET)
    return cleaned, constructed


def test_single_block_fixtures_construct_under_the_safe_preset(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    cleaned, constructed = _compile_single_block(workspace)
    assert cleaned.transform_count == 2
    assert constructed.record_count == 2
    assert constructed.diagnostic_count == 0
    result = _construct_result(workspace)
    pairs = {
        tuple((field.name, field.value) for field in record.fields)
        for record in result.records
    }
    assert pairs == {
        (
            ("before", "Alpha is a single paragraph with ordinary English capitalization."),
            ("after", "alpha is a single paragraph with ordinary english capitalization."),
        ),
        (
            (
                "before",
                "Beta is a different single paragraph with ordinary English capitalization.",
            ),
            (
                "after",
                "beta is a different single paragraph with ordinary english capitalization.",
            ),
        ),
    }


def test_joined_paragraph_chunks_keep_the_named_transformation_pair_refuse(
    tmp_path: Path,
) -> None:
    sources = tmp_path / "src"
    sources.mkdir()
    (sources / "alpha.txt").write_text(
        "Alpha paragraph with enough text for a record.\n\n"
        "Second alpha paragraph keeps the corpus multi-block.\n",
        encoding="utf-8",
    )
    (sources / "beta.txt").write_text(
        "Beta paragraph with enough text for a second leakage group.\n\n"
        "Second beta paragraph keeps the corpus multi-block.\n",
        encoding="utf-8",
    )
    workspace = tmp_path / "workspace"
    SERVICE.parse(
        [sources / "alpha.txt", sources / "beta.txt"],
        workspace,
        source_root=tmp_path,
    )
    cleaned = SERVICE.clean(workspace, rules="lowercase")
    assert cleaned.transform_count == 4
    SERVICE.chunk(workspace, preset=PRESET)
    constructed = SERVICE.construct(workspace, preset=PRESET)
    assert constructed.record_count == 0
    assert constructed.candidate_count == 0
    result = _construct_result(workspace)
    assert {item.code for item in result.diagnostics} == {
        "transformation-pair-unavailable"
    }


def test_single_block_recorded_change_seals_two_leakage_groups(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    bundle = tmp_path / "dataset.vfbundle"
    _compile_single_block(workspace)
    SERVICE.curate(workspace, preset=PRESET)
    split = SERVICE.split(workspace)
    assert split.train_record_count == 1
    assert split.evaluation_record_count == 1
    preview = SERVICE.quality_report(workspace)
    assert preview.report is not None
    require_quality_report_not_enforcing(preview.report)
    assert preview.report.enforcing is False
    gate_preview = json.loads(
        next(
            item.text_value
            for item in preview.report.facts
            if item.name == "quality-gate-preview"
        )
    )
    assert all(row["admitted-to-block"] is False for row in gate_preview)
    SERVICE.format(workspace)
    validated = SERVICE.validate(workspace)
    assert validated.exit_status == 0
    assert validated.report is not None
    assert validated.report.status == "passed"
    sealed = SERVICE.seal(workspace, bundle)
    assert sealed.publication is not None
    verified = SERVICE.verify(
        bundle,
        manifest_sha256=sealed.publication.manifest_sha256,
    )
    assert verified.verification is not None
    assert verified.verification.trust_grade == "external_digest"
    assert verified.verification.declared_record_count == 2
