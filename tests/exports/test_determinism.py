"""Phase 4.7 deterministic-render and semantic-replay conformance tests."""

from __future__ import annotations

import base64
import importlib.util
import inspect
import json
import os
from pathlib import Path

import pytest

from veriformis.datasets import (
    RowSet,
)
from veriformis.errors import ExportContractError, ExportVerificationError
from veriformis.exports import (
    EXPORT_RECEIPT_PATH,
    ExportContainerProfile,
    ExportFilePlan,
    ExportPlan,
    ExportService,
)
from veriformis.exports import _publication as publication_module
from veriformis.exports import service as service_module
from veriformis.identity import lossless_json_bytes, sha256_digest
from veriformis.pipeline import PipelineService

from support.bundles import (
    EXPECTED_MANIFEST_SHA256,
    _materialize_bundle,
    _tree_bytes,
)

from support.export_semantic import (
    SEMANTIC_DATA_PATH,
    _SemanticService,
    _clone_provenance,
    _clone_rows,
    _consumer,
    _dependencies,
    _semantic_files,
    _semantic_plan,
    _source_row_set,
)

DETERMINISM_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "regressions"
    / "fixtures"
    / "phase4"
    / "determinism.json"
)

FROZEN_DETERMINISM = json.loads(DETERMINISM_FIXTURE.read_text(encoding="utf-8"))


def _tree_sha256(root: Path) -> str:
    encoded = [
        {
            "base64": base64.b64encode(data).decode("ascii"),
            "path": path,
        }
        for path, data in _tree_bytes(root).items()
    ]
    return sha256_digest(lossless_json_bytes(encoded))


def _exact_files(row_set: RowSet) -> tuple[tuple[str, bytes], ...]:
    return (
        (
            "data/evaluation.jsonl",
            b"".join(
                lossless_json_bytes(row.payload) + b"\n"
                for row in row_set.evaluation_rows
            ),
        ),
        (
            "data/train.jsonl",
            b"".join(
                lossless_json_bytes(row.payload) + b"\n" for row in row_set.train_rows
            ),
        ),
        (
            "metadata/schema.json",
            lossless_json_bytes({"row_schema": row_set.row_schema}),
        ),
    )


def _exact_plan(service: ExportService, bundle: Path) -> ExportPlan:
    files = _exact_files(_source_row_set(bundle))
    plans = tuple(
        ExportFilePlan.create(
            path=path,
            role={
                "data/evaluation.jsonl": "evaluation-partition",
                "data/train.jsonl": "training-partition",
                "metadata/schema.json": "schema-metadata",
            }[path],
            media_type=(
                "application/jsonl" if path.startswith("data/") else "application/json"
            ),
            membership_scope={
                "data/evaluation.jsonl": "evaluation",
                "data/train.jsonl": "train",
                "metadata/schema.json": "none",
            }[path],
            record_count={
                "data/evaluation.jsonl": 2,
                "data/train.jsonl": 1,
                "metadata/schema.json": None,
            }[path],
            semantic_content_sha256=None,
            expected_sha256=sha256_digest(data),
            expected_byte_size=len(data),
        )
        for path, data in files
    )
    return service.create_plan(
        bundle,
        container_profile=ExportContainerProfile.create(
            container_id="phase4-conformance-exact-directory",
            container_version=7,
            determinism_claim="portable_exact_bytes",
        ),
        consumer_profile=_consumer(),
        dependencies=_dependencies(),
        file_plans=plans,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )


class _ExactService(ExportService):
    def __init__(
        self,
        *,
        mutate_second: bool = False,
        mutate_second_same_size: bool = False,
        omit_second: bool = False,
        poison_first_input: bool = False,
    ) -> None:
        self.mutate_second = mutate_second
        self.mutate_second_same_size = mutate_second_same_size
        self.omit_second = omit_second
        self.poison_first_input = poison_first_input
        self.render_count = 0
        self.seen_plans: list[ExportPlan] = []
        self.seen_row_sets: list[RowSet] = []
        self.seen_train_text: list[str] = []

    def _render_derivative(
        self,
        plan: ExportPlan,
        source_row_set: RowSet,
    ) -> service_module._RenderedDerivative:
        self.render_count += 1
        self.seen_plans.append(plan)
        self.seen_row_sets.append(source_row_set)
        self.seen_train_text.append(source_row_set.train_rows[0].payload["text"])
        files = _exact_files(source_row_set)
        train_rows = _clone_rows(source_row_set.train_rows)
        evaluation_rows = _clone_rows(source_row_set.evaluation_rows)
        provenance = _clone_provenance(source_row_set.provenance)
        if self.poison_first_input and self.render_count == 1:
            source_row_set.train_rows[0].payload["text"] = "poisoned input"
        if self.mutate_second and self.render_count == 2:
            files = tuple(
                (path, data + b" " if path == "data/train.jsonl" else data)
                for path, data in files
            )
        if self.mutate_second_same_size and self.render_count == 2:
            files = tuple(
                (
                    path,
                    b"X" + data[1:] if path == "data/train.jsonl" else data,
                )
                for path, data in files
            )
        if self.omit_second and self.render_count == 2:
            files = files[:-1]
        if self.render_count == 1:
            files = tuple(reversed(files))
        return service_module._RenderedDerivative(
            files=files,
            train_rows=train_rows,
            evaluation_rows=evaluation_rows,
            provenance=provenance,
        )


class _RenderOnlySemanticService(ExportService):
    def __init__(self) -> None:
        self.render_count = 0

    def _render_derivative(
        self,
        plan: ExportPlan,
        source_row_set: RowSet,
    ) -> service_module._RenderedDerivative:
        del plan
        self.render_count += 1
        return service_module._RenderedDerivative(
            files=_semantic_files(source_row_set, pretty=False),
            train_rows=_clone_rows(source_row_set.train_rows),
            evaluation_rows=_clone_rows(source_row_set.evaluation_rows),
            provenance=_clone_provenance(source_row_set.provenance),
        )


class _PathBomb:
    def __fspath__(self) -> str:
        raise AssertionError("destination was accessed before evidence closed")


def _publish(
    service: ExportService,
    plan: ExportPlan,
    bundle: Path,
    destination: os.PathLike[str],
):
    return service.publish(
        plan,
        bundle,
        destination,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )


def test_frozen_determinism_fixture_names_only_test_conformance() -> None:
    assert FROZEN_DETERMINISM == {
        "exact": {
            "plan_canonical_sha256": FROZEN_DETERMINISM["exact"][
                "plan_canonical_sha256"
            ],
            "receipt_canonical_sha256": FROZEN_DETERMINISM["exact"][
                "receipt_canonical_sha256"
            ],
            "tree_sha256": FROZEN_DETERMINISM["exact"]["tree_sha256"],
            "verification_canonical_sha256": FROZEN_DETERMINISM["exact"][
                "verification_canonical_sha256"
            ],
        },
        "fixture_version": 1,
        "profile_scope": "phase4-test-conformance-only",
        "semantic": {
            "plan_canonical_sha256": FROZEN_DETERMINISM["semantic"][
                "plan_canonical_sha256"
            ],
            "receipt_canonical_sha256": FROZEN_DETERMINISM["semantic"][
                "receipt_canonical_sha256"
            ],
            "tree_sha256": FROZEN_DETERMINISM["semantic"]["tree_sha256"],
            "verification_canonical_sha256": FROZEN_DETERMINISM["semantic"][
                "verification_canonical_sha256"
            ],
        },
        "source_fixture": (
            "tests/regressions/fixtures/phase3/"
            "pre-taxonomy-full-text.vfbundle.json"
        ),
        "source_manifest_sha256": EXPECTED_MANIFEST_SHA256,
    }
    for mode in ("exact", "semantic"):
        assert all(
            len(value) == 64 and value == value.lower()
            for value in FROZEN_DETERMINISM[mode].values()
        )


def test_exact_rerender_uses_fresh_strict_inputs_and_freezes_tree(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service = _ExactService(poison_first_input=True)
    plan = _exact_plan(service, bundle)
    destination = tmp_path / "exact"

    outcome = _publish(service, plan, bundle, destination)

    assert service.render_count == 2
    assert service.seen_plans[0] is not service.seen_plans[1]
    assert service.seen_row_sets[0] is not service.seen_row_sets[1]
    assert service.seen_train_text == [service.seen_train_text[0]] * 2
    assert "naïve" in service.seen_train_text[0]
    assert (
        _tree_bytes(destination)["data/train.jsonl"]
        == dict(_exact_files(_source_row_set(bundle)))["data/train.jsonl"]
    )
    assert set(_tree_bytes(destination)) == {
        "data/evaluation.jsonl",
        "data/train.jsonl",
        "metadata/schema.json",
        EXPORT_RECEIPT_PATH,
    }
    assert sha256_digest(plan.canonical_bytes()) == (
        FROZEN_DETERMINISM["exact"]["plan_canonical_sha256"]
    )
    assert (
        sha256_digest(outcome.receipt.canonical_bytes())
        == FROZEN_DETERMINISM["exact"]["receipt_canonical_sha256"]
    )
    assert (
        sha256_digest(outcome.verification.canonical_bytes())
        == FROZEN_DETERMINISM["exact"]["verification_canonical_sha256"]
    )
    assert _tree_sha256(destination) == FROZEN_DETERMINISM["exact"]["tree_sha256"]


@pytest.mark.parametrize(
    ("service", "message"),
    (
        (_ExactService(mutate_second=True), "differ from the exact plan"),
        (_ExactService(omit_second=True), "complete planned file set"),
    ),
)
def test_exact_rerender_mismatch_fails_before_destination_access(
    tmp_path: Path,
    service: _ExactService,
    message: str,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    plan = _exact_plan(service, bundle)

    with pytest.raises(ExportVerificationError, match=message):
        _publish(service, plan, bundle, _PathBomb())

    assert service.render_count == 2
    assert not list(tmp_path.glob(".veriformis-export-*"))


def test_exact_rerender_compares_bytes_even_if_digest_check_is_collided(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service = _ExactService(mutate_second_same_size=True)
    plan = _exact_plan(service, bundle)
    expected = {
        item.path: item.expected_sha256 for item in plan.file_plans
    }
    changed_train = b"X" + dict(_exact_files(_source_row_set(bundle)))[
        "data/train.jsonl"
    ][1:]
    real_sha256 = service_module.sha256_digest

    def collision_for_test_only(data: bytes) -> str:
        if data == changed_train:
            digest = expected["data/train.jsonl"]
            assert digest is not None
            return digest
        return real_sha256(data)

    monkeypatch.setattr(service_module, "sha256_digest", collision_for_test_only)

    with pytest.raises(ExportVerificationError, match="different byte trees"):
        _publish(service, plan, bundle, _PathBomb())

    assert service.render_count == 2
    assert not list(tmp_path.glob(".veriformis-export-*"))


def test_semantic_equivalent_encodings_replay_and_bind_actual_instance_bytes(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    compact_first = _SemanticService(first_pretty=False)
    plan = _semantic_plan(compact_first, bundle)
    compact_destination = tmp_path / "semantic-compact"
    compact = _publish(compact_first, plan, bundle, compact_destination)

    pretty_first = _SemanticService(first_pretty=True)
    pretty_destination = tmp_path / "semantic-pretty"
    pretty = _publish(pretty_first, plan, bundle, pretty_destination)

    assert compact_first.render_count == pretty_first.render_count == 2
    assert compact_first.replay_count == pretty_first.replay_count == 3
    assert compact_first.replay_inputs[0] != compact_first.replay_inputs[1]
    assert compact_first.replay_inputs[0] == compact_first.replay_inputs[2]
    assert pretty_first.replay_inputs[0] == pretty_first.replay_inputs[2]
    assert compact.receipt.export_plan == pretty.receipt.export_plan == plan
    assert compact.receipt.export_receipt_id != pretty.receipt.export_receipt_id
    assert compact.verification.export_verification_id != (
        pretty.verification.export_verification_id
    )
    compact_binding = next(
        item for item in compact.receipt.files if item.path == SEMANTIC_DATA_PATH
    )
    pretty_binding = next(
        item for item in pretty.receipt.files if item.path == SEMANTIC_DATA_PATH
    )
    assert compact_binding.semantic_content_sha256 == (
        pretty_binding.semantic_content_sha256
    )
    assert compact_binding.sha256 != pretty_binding.sha256
    assert compact_binding.byte_size != pretty_binding.byte_size
    assert sha256_digest(plan.canonical_bytes()) == (
        FROZEN_DETERMINISM["semantic"]["plan_canonical_sha256"]
    )
    assert (
        sha256_digest(compact.receipt.canonical_bytes())
        == FROZEN_DETERMINISM["semantic"]["receipt_canonical_sha256"]
    )
    assert (
        sha256_digest(compact.verification.canonical_bytes())
        == FROZEN_DETERMINISM["semantic"]["verification_canonical_sha256"]
    )
    assert _tree_sha256(compact_destination) == (
        FROZEN_DETERMINISM["semantic"]["tree_sha256"]
    )


def test_semantic_plan_without_private_replayer_fails_closed(tmp_path: Path) -> None:
    bundle = _materialize_bundle(tmp_path)
    service = _RenderOnlySemanticService()
    plan = _semantic_plan(service, bundle)

    with pytest.raises(ExportContractError, match="semantic replayer.*test-injected"):
        _publish(service, plan, bundle, _PathBomb())

    assert service.render_count == 2
    assert not list(tmp_path.glob(".veriformis-export-*"))


def test_visible_semantic_verification_replays_descriptor_read_bytes(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service = _SemanticService()
    plan = _semantic_plan(service, bundle)
    destination = tmp_path / "semantic-visible"
    outcome = _publish(service, plan, bundle, destination)

    with pytest.raises(ExportContractError, match="semantic replay callback"):
        publication_module._verify_export_directory(
            destination,
            expected_plan=plan,
        )

    replay_count = service.replay_count

    def replay(files: tuple[tuple[str, bytes], ...]):
        return service._replay_and_validate(
            plan.canonical_bytes(),
            files,
            cancellation_check=None,
        )

    receipt, verification = publication_module._verify_export_directory(
        destination,
        expected_plan=plan,
        semantic_replay=replay,
    )
    assert (receipt, verification) == (outcome.receipt, outcome.verification)
    assert service.replay_count == replay_count + 1

    (destination / SEMANTIC_DATA_PATH).write_bytes(b"{}")
    with pytest.raises(ExportVerificationError):
        publication_module._verify_export_directory(
            destination,
            expected_plan=plan,
            semantic_replay=replay,
        )


def test_renderer_claims_cannot_hide_semantic_byte_mutation(tmp_path: Path) -> None:
    bundle = _materialize_bundle(tmp_path)
    service = _SemanticService(omit_last_evaluation=True)
    plan = _semantic_plan(service, bundle)

    with pytest.raises(ExportVerificationError, match="replayed semantic content"):
        _publish(service, plan, bundle, _PathBomb())

    assert service.render_count == 2
    assert service.replay_count == 1
    assert not list(tmp_path.glob(".veriformis-export-*"))


@pytest.mark.parametrize("mutation", ("rows", "provenance"))
def test_semantic_replay_membership_is_validated_beyond_preimage_hashes(
    tmp_path: Path,
    mutation: str,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service = _SemanticService(replay_membership_mutation=mutation)
    plan = _semantic_plan(service, bundle)

    with pytest.raises(ExportVerificationError, match="candidate derivative"):
        _publish(service, plan, bundle, _PathBomb())

    assert service.render_count == 2
    assert service.replay_count == 1
    assert not list(tmp_path.glob(".veriformis-export-*"))


def test_semantic_replay_compares_canonical_bytes_not_only_hashes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service = _SemanticService(change_second_preimage=True)
    plan = _semantic_plan(service, bundle)
    planned_digests = {
        item.path: item.semantic_content_sha256 for item in plan.file_plans
    }
    real_sha256 = service_module.sha256_digest

    def collision_for_test_only(data: bytes) -> str:
        if service.original_preimages is not None:
            for path, preimage in service.original_preimages:
                if data == preimage or data == preimage + b" ":
                    digest = planned_digests[path]
                    assert digest is not None
                    return digest
        return real_sha256(data)

    monkeypatch.setattr(service_module, "sha256_digest", collision_for_test_only)

    with pytest.raises(ExportVerificationError, match="different canonical content"):
        _publish(service, plan, bundle, _PathBomb())

    assert service.replay_count == 2
    assert service.changed_preimages != service.original_preimages
    assert not list(tmp_path.glob(".veriformis-export-*"))


def test_staged_semantic_replay_rejects_byte_tamper_and_cleans_up(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = publication_module._verify_staged_export

    def tamper_before_replay(root_descriptor: int, **kwargs):
        descriptor = os.open(
            SEMANTIC_DATA_PATH,
            os.O_WRONLY | os.O_TRUNC,
            dir_fd=root_descriptor,
        )
        try:
            os.write(descriptor, b"{}")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return original(root_descriptor, **kwargs)

    monkeypatch.setattr(
        publication_module,
        "_verify_staged_export",
        tamper_before_replay,
    )
    bundle = _materialize_bundle(tmp_path)
    service = _SemanticService()
    plan = _semantic_plan(service, bundle)
    destination = tmp_path / "tampered"

    with pytest.raises(ExportVerificationError):
        _publish(service, plan, bundle, destination)

    assert service.render_count == 2
    assert service.replay_count == 3
    assert not destination.exists()
    assert not list(tmp_path.glob(".veriformis-export-*"))


def test_determinism_runtime_does_not_leak_to_public_or_support_surfaces() -> None:
    import veriformis.exports as exports

    assert list(inspect.signature(ExportService.publish).parameters) == [
        "self",
        "plan",
        "bundle",
        "destination_root",
        "expected_manifest_sha256",
        "cancellation_check",
    ]
    assert importlib.util.find_spec("veriformis.exports.publication") is None
    for name in (
        "_RenderedDerivative",
        "_ReplayedDerivative",
        "publish_semantic_export",
        "semantic_replay",
    ):
        assert name not in exports.__all__
        assert not hasattr(exports, name)
    assert "ExportPublicationOutcome" in exports.__all__
    assert hasattr(exports, "ExportPublicationOutcome")
    assert "ExportPartialPublicationError" in exports.__all__
    assert hasattr(exports, "ExportPartialPublicationError")
    assert "CancellationCheck" in exports.__all__
    assert hasattr(exports, "CancellationCheck")

    runtime_names = {
        "destination_root",
        "render_count",
        "renderer",
        "replayer",
        "semantic_preimages",
    }
    assert runtime_names.isdisjoint(ExportPlan.model_fields)
    assert not hasattr(PipelineService, "publish_export")
    assert list(inspect.signature(PipelineService.verify_export).parameters) == [
        "self",
        "request",
        "cancellation_check",
    ]

    catalog = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "contracts"
            / "fixtures"
            / "taxonomy"
            / "v1"
            / "catalog.json"
        ).read_text(encoding="utf-8")
    )
    assert catalog["physical_container"] == [
        "minimal-v1",
        "deterministic-vfbundle-zip-v1",
        "deterministic-export-pack-zip-v1",
        "split-jsonl-directory",
        "json",
        "constrained-csv",
        "parquet",
        "arrow",
        "hugging-face-dataset",
    ]
    support_registry = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "governance"
        / "support-registry.json"
    ).read_text(encoding="utf-8")
    assert "phase4-conformance" not in support_registry
    assert "semantic-replayer" not in support_registry
