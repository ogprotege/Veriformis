"""Pipeline path for extract-a-structured-value on markdown.

v1 curation quarantines conflicting-target when one covering chunk supplies
the same input for distinct IR scalars. Typical multi-block markdown under
the safe paragraph grouping hits that named refuse. A markdown source whose
recovered structure is one untitled link (one href, no title) is one field
per covering chunk and can seal.
"""

from __future__ import annotations

import json
from pathlib import Path

from veriformis.construction import (
    ConstructionResult,
    construction_result_from_json_bytes,
)
from veriformis.datasets import curation_result_from_json_bytes
from veriformis.pipeline import ConstructOutcome, PipelineService
from veriformis.quality import require_quality_report_not_enforcing
from veriformis.workspace import Workspace

ROOT = Path(__file__).resolve().parents[2]
SERVICE = PipelineService()
PRESET = "extract-a-structured-value.safe"
SINGLE_LEAF = ROOT / "tests/fixtures/matrix/structured-field"
MULTI_LEAF = (
    ROOT / "tests/fixtures/acceptance/v1/raw/corpus/markdown/source.md",
    ROOT / "tests/fixtures/sample.md",
)


def _construct_result(workspace: Path) -> ConstructionResult:
    store = Workspace.open(workspace)
    head = store.head()
    return construction_result_from_json_bytes(
        store.read_artifact(
            head.stages["construct"].outputs["result"],
            revision=head,
        )
    )


def _compile_single_leaf(workspace: Path) -> ConstructOutcome:
    SERVICE.parse(
        [SINGLE_LEAF / "alpha.md", SINGLE_LEAF / "beta.md"],
        workspace,
        source_root=ROOT,
    )
    SERVICE.clean(workspace)
    SERVICE.chunk(workspace, preset=PRESET)
    return SERVICE.construct(workspace, preset=PRESET)


def test_single_untitled_link_markdown_constructs_one_field_per_chunk(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    constructed = _compile_single_leaf(workspace)
    assert constructed.record_count == 2
    assert constructed.diagnostic_count == 0
    result = _construct_result(workspace)
    pairs = {
        tuple((field.name, field.value) for field in record.fields)
        for record in result.records
    }
    assert pairs == {
        (
            ("input", "Alpha source"),
            ("fields", "https://example.test/alpha"),
        ),
        (
            ("input", "Beta source"),
            ("fields", "https://example.test/beta"),
        ),
    }


def test_typical_markdown_keeps_conflicting_target_quarantine(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    SERVICE.parse(list(MULTI_LEAF), workspace, source_root=ROOT)
    SERVICE.clean(workspace)
    SERVICE.chunk(workspace, preset=PRESET)
    constructed = SERVICE.construct(workspace, preset=PRESET)
    assert constructed.record_count > 1
    curated = SERVICE.curate(workspace, preset=PRESET)
    assert curated.included_count == 0
    assert curated.quarantined_count == constructed.record_count
    assert "no-included-contribution" in curated.coverage_blockers
    store = Workspace.open(workspace)
    head = store.head()
    cur = curation_result_from_json_bytes(
        store.read_artifact(head.stages["curate"].outputs["result"], revision=head)
    )
    assert {tuple(item.reason_codes) for item in cur.decisions} == {
        ("conflicting-target",)
    }


def test_single_untitled_link_markdown_seals_two_leakage_groups(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    bundle = tmp_path / "dataset.vfbundle"
    _compile_single_leaf(workspace)
    curated = SERVICE.curate(workspace, preset=PRESET)
    assert curated.included_count == 2
    assert curated.quarantined_count == 0
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
