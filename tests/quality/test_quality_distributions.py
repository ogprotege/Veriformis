"""Phase 13.3 quality report: plan-bound dataset distributions."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from veriformis.chunkers.base import Chunk
from veriformis.chunkers.strategies import chunk_paragraph
from veriformis.cli import app
from veriformis.construction import (
    ConstructionInputs,
    ConstructionPass,
    ConstructionResult,
    DatasetRecipe,
    IRArtifactInput,
    SegmentationPolicy,
    TrainingObjective,
    construct_dataset,
)
from veriformis.datasets.curation import curate_dataset
from veriformis.datasets.models import CurationPolicy, CurationResult
from veriformis.datasets.plan import FinishedDatasetPlan
from veriformis.datasets.serialization import SerializationPlan
from veriformis.datasets.splitting import SplitPolicy, SplitResult, split_dataset
from veriformis.errors import QualityReportError
from veriformis.identity import (
    canonical_digest,
    derive_artifact_id,
    lossless_json_bytes,
    sha256_digest,
)
from veriformis.ir import (
    Block,
    CodeBlock,
    Document,
    Paragraph,
    Text,
    attach_canonical_provenance,
)
from veriformis.ir.serde import document_to_dict
from veriformis.pipeline import PipelineService
from veriformis.quality import (
    DISTRIBUTION_FACT_NAMES,
    LANGUAGE_UNQUALIFIED,
    report_dataset_distributions,
    require_quality_report_not_enforcing,
)
from veriformis.sources import SourceRef, register_source


@dataclass(frozen=True)
class SourceBundle:
    source: SourceRef
    document: Document
    chunks: tuple[Chunk, ...]
    artifact: IRArtifactInput


@dataclass(frozen=True)
class DistributionCase:
    recipe: DatasetRecipe
    construction: ConstructionResult
    curation: CurationResult
    split: SplitResult
    plan_id: str


def source_bundle(
    tmp_path: Path,
    *,
    logical_path: str,
    blocks: Sequence[Block],
) -> SourceBundle:
    document = Document(children=list(blocks))
    stream = attach_canonical_provenance(document)
    source = register_source(
        tmp_path / logical_path,
        "fixture",
        stream,
        logical_path=logical_path,
        raw_bytes=stream.encode("utf-8"),
    )
    document.source_id = source.id
    chunks = chunk_paragraph(
        document.children,
        max_size=1_000,
        source=source,
        transformed=set(),
        block_derivations={},
        region_id="body",
    )
    document_json = lossless_json_bytes(document_to_dict(document))
    artifact_config_digest = canonical_digest({"fixture": logical_path})
    artifact_id = derive_artifact_id(
        kind="cleaned-document-ir",
        content_sha256=sha256_digest(document_json),
        source_ids=(source.id,),
        producer_id="veriformis.test.quality-distributions",
        producer_version="1",
        config_digest=artifact_config_digest,
    )
    artifact = IRArtifactInput.create(
        source_id=source.id,
        artifact_id=artifact_id,
        artifact_kind="cleaned-document-ir",
        document_json=document_json,
        producer_id="veriformis.test.quality-distributions",
        producer_version="1",
        config_digest=artifact_config_digest,
    )
    return SourceBundle(source, document, tuple(chunks), artifact)


def recipe_for(
    sources: Sequence[SourceRef],
    objective_kind: str,
    *,
    row_schema: str,
) -> DatasetRecipe:
    return DatasetRecipe.create(
        objective=TrainingObjective.create(objective_kind),
        source_ids=tuple(source.id for source in sources),
        cleaning_config_digest=canonical_digest({"cleaning": "fixture-v1"}),
        segmentation=SegmentationPolicy(
            schema_version="veriformis.segmentation-policy/v1",
            strategy="paragraph",
            size=1_000,
            overlap=100,
        ),
        passes=(
            ConstructionPass.create(sequence=1, objective_kind=objective_kind),
        ),
        target_row_schema=row_schema,
    )


def inputs_for(bundles: Sequence[SourceBundle]) -> ConstructionInputs:
    return ConstructionInputs.create(
        cleaning_config_digest=canonical_digest({"cleaning": "fixture-v1"}),
        sources=tuple(bundle.source for bundle in bundles),
        chunks=tuple(chunk for bundle in bundles for chunk in bundle.chunks),
        transforms=(),
        ir_artifacts=tuple(bundle.artifact for bundle in bundles),
    )


def _finished(
    tmp_path: Path,
    *,
    texts: tuple[tuple[str, str], ...],
    objective_kind: str,
    row_schema: str,
    minimum_target_characters: int = 1,
) -> DistributionCase:
    bundles = tuple(
        source_bundle(
            tmp_path,
            logical_path=logical_path,
            blocks=[Paragraph(children=[Text(text)])],
        )
        for logical_path, text in texts
    )
    recipe = recipe_for(
        tuple(item.source for item in bundles),
        objective_kind,
        row_schema=row_schema,
    )
    return _complete(
        recipe,
        bundles,
        instruction_text=(
            "Preserve the exact source-derived relation."
            if row_schema == "instruction_output"
            else None
        ),
        seed="quality-distributions-v1",
        minimum_target_characters=minimum_target_characters,
    )


def _complete(
    recipe: DatasetRecipe,
    bundles: Sequence[SourceBundle],
    *,
    instruction_text: str | None,
    seed: str,
    minimum_target_characters: int = 1,
) -> DistributionCase:
    construction = construct_dataset(recipe, inputs_for(bundles))
    finished_plan = FinishedDatasetPlan.create(
        recipe_id=recipe.recipe_id,
        construction_result_id=construction.result_id,
        curation_policy=CurationPolicy.create(
            minimum_target_characters=minimum_target_characters
        ),
        split_policy=SplitPolicy.create(
            evaluation_ratio_ppm=500_000,
            evaluation_required=True,
            seed=seed,
        ),
        serialization_plan=SerializationPlan.create(
            row_schema=recipe.target_row_schema,
            instruction_text=instruction_text,
        ),
    )
    curation = curate_dataset(
        finished_plan,
        recipe,
        inputs_for(bundles),
        construction,
    )
    split = split_dataset(
        finished_plan,
        construction,
        curation,
        {bundle.source.id: bundle.source.sha256 for bundle in bundles},
    )
    return DistributionCase(
        recipe=recipe,
        construction=construction,
        curation=curation,
        split=split,
        plan_id=finished_plan.plan_id,
    )


def _fact(report, name: str):
    return next(item for item in report.facts if item.name == name)


def _json(report, name: str):
    return json.loads(_fact(report, name).text_value)


def _report(case: DistributionCase):
    return report_dataset_distributions(
        recipe=case.recipe,
        construction=case.construction,
        curation=case.curation,
        split=case.split,
    )


def test_full_text_distributions_reproduce_and_stay_non_enforcing(
    tmp_path: Path,
) -> None:
    case = _finished(
        tmp_path,
        texts=(
            ("full-alpha.txt", "  Alpha exact text.  "),
            ("full-beta.txt", "Beta Café text."),
        ),
        objective_kind="full_text",
        row_schema="text",
    )
    first = _report(case)
    second = _report(case)
    assert first == second
    assert first.enforcing is False
    assert first.policy_decisions == ()
    assert first.recommendations == ()
    assert first.plan_id == case.plan_id
    assert tuple(item.name for item in first.facts) == DISTRIBUTION_FACT_NAMES
    require_quality_report_not_enforcing(first)
    assert _fact(first, "included-record-count").integer_value == 2
    assert _fact(first, "excluded-record-count").integer_value == 0
    assert _fact(first, "quarantined-record-count").integer_value == 0
    assert _fact(first, "train-record-count").integer_value == 1
    assert _fact(first, "evaluation-record-count").integer_value == 1
    assert _fact(first, "distinct-source-count").integer_value == 2
    assert _fact(first, "distinct-objective-count").integer_value == 1
    assert _json(first, "row-schema-distribution") == {"text": 2}
    assert _json(first, "role-distribution") == {}
    assert _json(first, "label-distribution") == {"text": 2}
    assert _json(first, "split-distribution") == {"evaluation": 1, "train": 1}
    assert _json(first, "exclusion-distribution") == {}
    assert _json(first, "language-distribution") == {LANGUAGE_UNQUALIFIED: 2}
    assert _fact(first, "language-evidence-qualified-count").integer_value == 0
    assert _fact(first, "language-evidence-unqualified-count").integer_value == 2
    assert _json(first, "source-distribution") == {
        source_id: 1 for source_id in sorted(case.recipe.source_ids)
    }
    target_hist = _json(first, "target-length-distribution")
    assert target_hist == _json(first, "context-length-distribution")
    assert target_hist
    assert all(len(pair) == 2 and pair[0] > 0 and pair[1] > 0 for pair in target_hist)
    coverage = _json(first, "coverage-distribution")
    assert set(coverage) == set(case.recipe.source_ids)
    for entry in coverage.values():
        assert entry["included-count"] == 1
        assert entry["blocker-codes"] == []


def test_short_target_exclusion_and_coverage_blockers(tmp_path: Path) -> None:
    case = _finished(
        tmp_path,
        texts=(
            ("keep-alpha.txt", "Alpha exact kept text."),
            ("keep-beta.txt", "Beta exact kept text."),
            ("drop-gamma.txt", "xy"),
        ),
        objective_kind="full_text",
        row_schema="text",
        minimum_target_characters=5,
    )
    report = _report(case)
    assert _fact(report, "included-record-count").integer_value == 2
    assert _fact(report, "excluded-record-count").integer_value == 1
    assert _fact(report, "quarantined-record-count").integer_value == 0
    assert _json(report, "exclusion-distribution") == {"target-too-short": 1}
    assert _fact(report, "coverage-blocker-count").integer_value == 1
    coverage = _json(report, "coverage-distribution")
    blocked = [
        entry
        for entry in coverage.values()
        if entry["blocker-codes"] == ["no-included-contribution"]
    ]
    assert len(blocked) == 1
    assert blocked[0]["excluded-count"] == 1
    assert blocked[0]["included-count"] == 0


def test_messages_rows_count_user_and_assistant_roles(tmp_path: Path) -> None:
    case = _finished(
        tmp_path,
        texts=(
            ("continuation-alpha.txt", "abcdeFGHIJ"),
            ("continuation-beta.txt", "klmnoPQRST"),
        ),
        objective_kind="continuation",
        row_schema="messages",
    )
    report = _report(case)
    assert _json(report, "row-schema-distribution") == {"messages": 2}
    assert _json(report, "role-distribution") == {"assistant": 2, "user": 2}
    assert _json(report, "label-distribution") == {"completion": 2, "prompt": 2}


def test_codeblock_language_is_evidence_qualified(tmp_path: Path) -> None:
    bundles = (
        source_bundle(
            tmp_path,
            logical_path="alpha.py",
            blocks=[CodeBlock(text="print(1)", language="python")],
        ),
        source_bundle(
            tmp_path,
            logical_path="beta.rs",
            blocks=[CodeBlock(text="fn main() {}", language="rust")],
        ),
    )
    recipe = recipe_for(
        tuple(item.source for item in bundles),
        "structured_field",
        row_schema="prompt_completion",
    )
    case = _complete(
        recipe,
        bundles,
        instruction_text=None,
        seed="quality-distributions-language-v1",
    )
    report = _report(case)
    assert _fact(report, "included-record-count").integer_value == 2
    assert _json(report, "language-distribution") == {"python": 1, "rust": 1}
    assert _fact(report, "language-evidence-qualified-count").integer_value == 2
    assert _fact(report, "language-evidence-unqualified-count").integer_value == 0


def test_mismatched_plan_identities_fail_closed(tmp_path: Path) -> None:
    first = _finished(
        tmp_path / "a",
        texts=(
            ("a-alpha.txt", "Alpha exact text."),
            ("a-beta.txt", "Beta exact text."),
        ),
        objective_kind="full_text",
        row_schema="text",
    )
    second = _finished(
        tmp_path / "b",
        texts=(
            ("b-alpha.txt", "Gamma exact text."),
            ("b-beta.txt", "Delta exact text."),
        ),
        objective_kind="full_text",
        row_schema="text",
    )
    with pytest.raises(QualityReportError, match="does not match"):
        report_dataset_distributions(
            recipe=first.recipe,
            construction=first.construction,
            curation=second.curation,
            split=first.split,
        )


def test_cli_and_service_still_have_no_quality_report_command() -> None:
    names = {command.name for command in app.registered_commands}
    assert "quality-report" not in names
    assert not hasattr(PipelineService(), "quality_report")
