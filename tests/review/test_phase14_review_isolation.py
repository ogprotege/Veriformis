"""Phase 14 isolation: default review stays none; Mac Review is not in this packet."""

from __future__ import annotations

import inspect

from veriformis.cli import app, construct
from veriformis.construction import DatasetRecipe, ReviewEvidence
from veriformis.contracts import (
    FINISHED_DATASET_SCHEMA_IDS,
    V1_FINISHED_DATASET_GATES,
)
from veriformis.datasets.models import CurationPolicy
from veriformis.mcp.server import create_mcp_server
from veriformis.ocr.preview import OcrPagePreview, OcrPreview
from veriformis.pipeline import PipelineService
from veriformis.quality import V1_QUALITY_GATES


def test_seventeen_finished_dataset_gates_are_unchanged() -> None:
    assert V1_FINISHED_DATASET_GATES == (
        "construction-replay",
        "record-lifecycle",
        "curation",
        "deduplication",
        "quality",
        "balance",
        "coverage",
        "split",
        "leakage",
        "row-binding",
        "objective",
        "schema",
        "encoding",
        "masking",
        "partition-nonempty",
        "aptus-row-shape",
        "snapshot",
    )
    assert len(V1_FINISHED_DATASET_GATES) == 17


def test_construction_review_policy_defaults_to_none() -> None:
    assert DatasetRecipe.model_fields["review_policy"].default == "none"


def test_review_evidence_is_unsigned_local_attestation() -> None:
    fields = set(ReviewEvidence.model_fields)
    assert fields == {
        "candidate_id",
        "rationale",
        "review_id",
        "reviewer_id",
        "schema_version",
        "verdict",
    }
    assert "signature" not in fields
    assert "public_key" not in fields


def test_cli_exposes_review_exchange_not_construct_reviews() -> None:
    names = {command.name for command in app.registered_commands}
    assert "review-export" in names
    assert "review-import" in names
    assert "review-submit" in names
    assert "review-queue" not in names
    parameters = inspect.signature(construct).parameters
    assert "require_review" in parameters
    assert "reviews" not in parameters


def test_mcp_exposes_review_exchange_tools() -> None:
    tools = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert "export_review" in tools
    assert "import_review" in tools
    assert "submit_review" in tools
    assert "review_queue" not in tools
    assert "review-queue" not in tools


def test_pipeline_service_submits_review_packets() -> None:
    service = PipelineService()
    assert hasattr(service, "export_review_packet")
    assert hasattr(service, "import_review_packet")
    assert hasattr(service, "submit_review")
    assert not hasattr(service, "review_queue")
    parameters = inspect.signature(PipelineService.construct).parameters
    assert "reviews" not in parameters


def test_ocr_preview_is_a_hook_not_a_queue() -> None:
    assert OcrPreview.model_fields["schema_id"].default == "veriformis.ocr-preview/v1"
    assert "queue_id" not in OcrPreview.model_fields
    assert "pending_review" in OcrPagePreview.model_fields
    assert "verdict" not in OcrPagePreview.model_fields


def test_quality_heuristics_are_not_admitted_to_block_seal() -> None:
    assert V1_QUALITY_GATES
    assert all(item.admitted_to_block is False for item in V1_QUALITY_GATES)
    policy = CurationPolicy.create(minimum_target_characters=1)
    assert policy.near_duplicate_policy == "disabled"


def test_finished_dataset_schemas_have_no_review_queue() -> None:
    assert all("review-queue" not in schema for schema in FINISHED_DATASET_SCHEMA_IDS)
    assert all("review-exchange" not in schema for schema in FINISHED_DATASET_SCHEMA_IDS)
