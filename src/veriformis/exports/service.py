"""Verified-bundle-only composition service for derived exports.

Phase 4 builds every export operation through this service. The current
increments establish a typed, descriptor-anchored source boundary, fail-closed
trust admission, source-derived plan population, and private atomic exact-byte
publication without promoting Phase 5 containers.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass

from veriformis.bundle import (
    VALIDATION_PATH,
    FinishedBundleManifest,
    VerificationResult,
    VerifiedFinishedBundle,
    inspect_finished_bundle,
)
from veriformis.datasets import (
    DatasetValidationReport,
    ProductRow,
    RowProvenance,
    RowSet,
    dataset_validation_report_from_json_bytes,
    product_row_from_json_bytes,
    row_provenance_from_json_bytes,
    row_set_from_json_bytes,
)
from veriformis.errors import (
    ExportContractError,
    ExportVerificationError,
    VeriformisError,
)
from veriformis.exports.models import (
    ExportConsumerProfile,
    ExportContainerProfile,
    ExportDependencyBinding,
    ExportFilePlan,
    ExportMembershipEntry,
    ExportMembershipProjection,
    ExportPlan,
    SourceTrustGrade,
    SourceTrustPolicy,
)
from veriformis.exports._publication import (
    CancellationCheck,
    ExportPublicationOutcome,
    _publish_exact_export,
)
from veriformis.identity import lossless_json_bytes, sha256_digest


_SOURCE_TRUST_POLICIES = frozenset(
    {"require_external_digest", "allow_self_consistent"}
)


@dataclass(frozen=True, slots=True)
class _RenderedDerivative:
    """Test-injected renderer output before service-owned publication."""

    files: tuple[tuple[str, bytes], ...]
    train_rows: tuple[ProductRow, ...]
    evaluation_rows: tuple[ProductRow, ...]
    provenance: tuple[RowProvenance, ...]


class ExportService:
    """Own export policy beneath :class:`PipelineService`.

    Adapters must call the Python composition root. They must never copy or
    rewrite bundle files directly. Phase 4.6 adds private exact-byte destination
    enforcement, receipts, publication, and verification here without changing
    that boundary; public adapters remain later work.
    """

    def verified_source(
        self,
        bundle: str | os.PathLike[str],
        *,
        source_trust_policy: SourceTrustPolicy = "require_external_digest",
        expected_manifest_sha256: str | None = None,
    ) -> VerifiedFinishedBundle:
        """Admit one verified source under an explicit, fail-closed trust policy.

        Trusted admission requires a retained expected manifest digest. The
        lower-trust self-consistent path must be requested explicitly. If an
        expected digest is supplied under either policy, a mismatch fails
        instead of falling back to self-consistent verification.
        """
        if (
            type(source_trust_policy) is not str
            or source_trust_policy not in _SOURCE_TRUST_POLICIES
        ):
            raise ExportContractError(
                "source_trust_policy must be require_external_digest or "
                "allow_self_consistent"
            )
        if (
            source_trust_policy == "require_external_digest"
            and expected_manifest_sha256 is None
        ):
            raise ExportContractError(
                "require_external_digest source trust needs a retained "
                "expected_manifest_sha256"
            )

        source = inspect_finished_bundle(
            bundle,
            expected_manifest_sha256=expected_manifest_sha256,
        )
        expected_grade: SourceTrustGrade = (
            "external_digest"
            if expected_manifest_sha256 is not None
            else "self_consistent"
        )
        if source.verification.trust_grade != expected_grade:
            raise ExportVerificationError(
                "source verification trust grade differs from the supplied "
                "trust evidence"
            )
        if (
            expected_manifest_sha256 is not None
            and source.verification.manifest_sha256
            != expected_manifest_sha256
        ):
            raise ExportVerificationError(
                "source verification manifest digest differs from the retained "
                "expected digest"
            )
        return source

    def create_plan(
        self,
        bundle: str | os.PathLike[str],
        *,
        container_profile: ExportContainerProfile,
        consumer_profile: ExportConsumerProfile | None = None,
        dependencies: Sequence[ExportDependencyBinding],
        file_plans: Sequence[ExportFilePlan],
        source_trust_policy: SourceTrustPolicy = "require_external_digest",
        expected_manifest_sha256: str | None = None,
    ) -> ExportPlan:
        """Create one portable derivative plan from one verified source read.

        All source, objective, row, split, and membership facts are derived
        from the immutable result returned by :meth:`verified_source`. Callers
        provide only container-specific profile, dependency, and output-file
        evidence. Publication and destination verification are later Phase 4
        operations.
        """
        source = self.verified_source(
            bundle,
            source_trust_policy=source_trust_policy,
            expected_manifest_sha256=expected_manifest_sha256,
        )
        try:
            plan, _ = _plan_from_verified_source(
                source,
                source_trust_policy=source_trust_policy,
                container_profile=container_profile,
                consumer_profile=consumer_profile,
                dependencies=dependencies,
                file_plans=file_plans,
            )
            return plan
        except (
            AttributeError,
            RecursionError,
            TypeError,
            UnicodeError,
            ValueError,
        ) as exc:
            if isinstance(exc, (ExportContractError, ExportVerificationError)):
                raise
            raise ExportContractError(f"invalid export plan evidence: {exc}") from exc

    def validate_derivative_membership(
        self,
        plan: ExportPlan,
        *,
        candidate_train_rows: Sequence[ProductRow],
        candidate_evaluation_rows: Sequence[ProductRow],
        candidate_provenance: Sequence[RowProvenance],
    ) -> ExportMembershipProjection:
        """Require candidate semantic rows to preserve the planned source exactly.

        The candidate row sequences retain the source's logical train and
        evaluation partitions even when a later physical container combines
        them. This operation validates normalized in-memory evidence only;
        filesystem publication and independent replay of produced bytes are
        later Phase 4 boundaries.
        """
        try:
            checked_plan = ExportPlan.from_json_bytes(
                lossless_json_bytes(plan.model_dump(mode="json"))
            )
            supplied_train_rows = tuple(candidate_train_rows)
            supplied_evaluation_rows = tuple(candidate_evaluation_rows)
            supplied_provenance = tuple(candidate_provenance)
            train_rows = tuple(
                product_row_from_json_bytes(
                    lossless_json_bytes(item.model_dump(mode="json"))
                )
                for item in supplied_train_rows
            )
            evaluation_rows = tuple(
                product_row_from_json_bytes(
                    lossless_json_bytes(item.model_dump(mode="json"))
                )
                for item in supplied_evaluation_rows
            )
            provenance = tuple(
                row_provenance_from_json_bytes(
                    lossless_json_bytes(item.model_dump(mode="json"))
                )
                for item in supplied_provenance
            )
            candidate_row_set = RowSet.create(
                plan_id=checked_plan.finished_dataset_plan_id,
                serialization_plan_id=checked_plan.serialization_plan_id,
                recipe_id=checked_plan.recipe_id,
                construction_result_id=checked_plan.construction_result_id,
                curation_result_id=checked_plan.curation_result_id,
                split_result_id=checked_plan.split_result_id,
                row_schema=checked_plan.row_schema,
                train_rows=train_rows,
                evaluation_rows=evaluation_rows,
                provenance=provenance,
            )
            objective_ids = {item.objective_id for item in provenance}
            emitted_source_ids = {
                source_id for item in provenance for source_id in item.source_ids
            }
            if objective_ids != {checked_plan.objective_id}:
                raise ExportVerificationError(
                    "candidate derivative objective differs from its export plan"
                )
            if emitted_source_ids != set(checked_plan.source_ids):
                raise ExportVerificationError(
                    "candidate derivative source scope differs from its export plan"
                )
            if candidate_row_set.row_set_id != checked_plan.row_set_id:
                raise ExportVerificationError(
                    "candidate derivative changes the source row set"
                )
            projection = _membership_projection_from_row_set(candidate_row_set)
            if (
                projection != checked_plan.membership_projection
                or projection.canonical_bytes()
                != checked_plan.membership_projection.canonical_bytes()
            ):
                raise ExportVerificationError(
                    "candidate derivative changes source membership or semantics"
                )
            return projection
        except ExportVerificationError:
            raise
        except (
            AttributeError,
            RecursionError,
            TypeError,
            UnicodeError,
            ValueError,
            VeriformisError,
        ) as exc:
            raise ExportVerificationError(
                f"invalid candidate derivative membership evidence: {exc}"
            ) from exc

    def publish(
        self,
        plan: ExportPlan,
        bundle: str | os.PathLike[str],
        destination_root: str | os.PathLike[str],
        *,
        expected_manifest_sha256: str | None = None,
        cancellation_check: CancellationCheck | None = None,
    ) -> ExportPublicationOutcome:
        """Atomically publish one test-injected exact-byte derivative.

        Phase 4.6 intentionally has no renderer-selection argument or shipped
        implementation.  A conformance-only subclass may override
        :meth:`_render_derivative`; product discovery and public surfaces remain
        later Phase 4 work.
        """
        if cancellation_check is not None and not callable(cancellation_check):
            raise ExportContractError("cancellation_check must be callable")
        try:
            checked_plan = ExportPlan.from_json_bytes(plan.canonical_bytes())
        except (
            AttributeError,
            RecursionError,
            TypeError,
            UnicodeError,
            ValueError,
            VeriformisError,
        ) as exc:
            if isinstance(exc, ExportVerificationError):
                raise
            raise ExportContractError(f"invalid export publication plan: {exc}") from exc
        if checked_plan.container_profile.determinism_claim != "portable_exact_bytes":
            raise ExportContractError(
                "Phase 4.6 publication supports portable_exact_bytes plans only"
            )
        if checked_plan.source_trust_grade == "external_digest":
            if expected_manifest_sha256 is None:
                raise ExportContractError(
                    "external_digest publication requires separately retained "
                    "expected_manifest_sha256"
                )
            if expected_manifest_sha256 != checked_plan.source_manifest_sha256:
                raise ExportContractError(
                    "publication trust evidence differs from the export plan"
                )
        elif expected_manifest_sha256 is not None:
            raise ExportContractError(
                "self_consistent publication cannot silently change its trust grade; "
                "create a new export plan with the retained digest"
            )

        _run_cancellation_check(cancellation_check)
        source = self.verified_source(
            bundle,
            source_trust_policy=checked_plan.source_trust_policy,
            expected_manifest_sha256=expected_manifest_sha256,
        )
        rebuilt_plan, source_row_set = _plan_from_verified_source(
            source,
            source_trust_policy=checked_plan.source_trust_policy,
            container_profile=checked_plan.container_profile,
            consumer_profile=checked_plan.consumer_profile,
            dependencies=checked_plan.dependencies,
            file_plans=checked_plan.file_plans,
        )
        if (
            rebuilt_plan != checked_plan
            or rebuilt_plan.canonical_bytes() != checked_plan.canonical_bytes()
        ):
            raise ExportVerificationError(
                "reverified export source differs from the supplied export plan"
            )

        _run_cancellation_check(cancellation_check)
        try:
            rendered = self._render_derivative(checked_plan, source_row_set)
            files = tuple(rendered.files)
            train_rows = tuple(rendered.train_rows)
            evaluation_rows = tuple(rendered.evaluation_rows)
            provenance = tuple(rendered.provenance)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ExportVerificationError(
                f"invalid injected renderer result: {exc}"
            ) from exc
        _run_cancellation_check(cancellation_check)
        self.validate_derivative_membership(
            checked_plan,
            candidate_train_rows=train_rows,
            candidate_evaluation_rows=evaluation_rows,
            candidate_provenance=provenance,
        )
        _run_cancellation_check(cancellation_check)
        return _publish_exact_export(
            destination_root,
            source_root=source.bundle_path,
            plan=checked_plan,
            files=files,
            cancellation_check=cancellation_check,
        )

    def _render_derivative(
        self,
        plan: ExportPlan,
        source_row_set: RowSet,
    ) -> _RenderedDerivative:
        """Resolve no product renderer; test-only subclasses may override it."""
        del plan, source_row_set
        raise ExportContractError(
            "no verified export renderer is installed; Phase 4 conformance "
            "rendering is test-injected only"
        )


def _run_cancellation_check(check: CancellationCheck | None) -> None:
    if check is not None:
        check()


def _plan_from_verified_source(
    source: VerifiedFinishedBundle,
    *,
    source_trust_policy: SourceTrustPolicy,
    container_profile: ExportContainerProfile,
    consumer_profile: ExportConsumerProfile | None,
    dependencies: Sequence[ExportDependencyBinding],
    file_plans: Sequence[ExportFilePlan],
) -> tuple[ExportPlan, RowSet]:
    """Build a plan and return the same freshly closed source row set."""
    (
        report,
        row_set,
        verification,
        objective_id,
        membership_projection,
    ) = _source_plan_evidence(source)
    snapshot = report.snapshot
    plan = ExportPlan.create(
        source_bundle_id=verification.bundle_id,
        source_manifest_sha256=verification.manifest_sha256,
        source_content_root_sha256=verification.content_root_sha256,
        source_verification_id=verification.verification_id,
        source_trust_policy=source_trust_policy,
        source_trust_grade=verification.trust_grade,
        dataset_snapshot_id=snapshot.snapshot_id,
        validation_report_id=report.report_id,
        finished_dataset_plan_id=snapshot.plan_id,
        recipe_id=snapshot.recipe_id,
        objective_id=objective_id,
        construction_result_id=snapshot.construction_result_id,
        curation_result_id=snapshot.curation_result_id,
        serialization_plan_id=row_set.serialization_plan_id,
        split_result_id=snapshot.split_result_id,
        row_set_id=snapshot.row_set_id,
        source_ids=snapshot.source_ids,
        row_schema=row_set.row_schema,
        container_profile=container_profile,
        consumer_profile=consumer_profile,
        dependencies=dependencies,
        membership_projection=membership_projection,
        file_plans=file_plans,
    )
    return plan, row_set


def _source_plan_evidence(
    source: VerifiedFinishedBundle,
) -> tuple[
    DatasetValidationReport,
    RowSet,
    VerificationResult,
    str,
    ExportMembershipProjection,
]:
    """Close duplicated source facts and derive its membership projection."""
    try:
        manifest_bytes = source.manifest.canonical_bytes()
        manifest = FinishedBundleManifest.from_json_bytes(manifest_bytes)
        report = dataset_validation_report_from_json_bytes(
            lossless_json_bytes(source.validation_report.model_dump(mode="json"))
        )
        row_set = row_set_from_json_bytes(
            lossless_json_bytes(source.row_set.model_dump(mode="json"))
        )
        verification = VerificationResult.from_json_bytes(
            lossless_json_bytes(source.verification.model_dump(mode="json"))
        )
    except (
        AttributeError,
        RecursionError,
        TypeError,
        UnicodeError,
        ValueError,
        VeriformisError,
    ) as exc:
        raise ExportVerificationError(
            f"invalid verified export source model evidence: {exc}"
        ) from exc
    snapshot = report.snapshot
    manifest_sha256 = sha256_digest(manifest_bytes)
    report_bytes = lossless_json_bytes(report.model_dump(mode="json"))
    row_set_bytes = lossless_json_bytes(row_set.model_dump(mode="json"))

    if (
        manifest.bundle_id != verification.bundle_id
        or manifest.dataset_snapshot_id != verification.dataset_snapshot_id
        or manifest.validation_report_id != verification.validation_report_id
        or manifest.content_root_sha256 != verification.content_root_sha256
        or manifest_sha256 != verification.manifest_sha256
        or report.report_id != verification.validation_report_id
        or report.snapshot_id != verification.dataset_snapshot_id
        or report.status != "passed"
        or snapshot.snapshot_id != verification.dataset_snapshot_id
        or len(manifest.files) != verification.payload_file_count
        or row_set.total_row_count != verification.declared_record_count
    ):
        raise ExportVerificationError(
            "verified export source identities or counts do not close"
        )
    if (
        row_set.plan_id != snapshot.plan_id
        or row_set.recipe_id != snapshot.recipe_id
        or row_set.construction_result_id != snapshot.construction_result_id
        or row_set.curation_result_id != snapshot.curation_result_id
        or row_set.split_result_id != snapshot.split_result_id
        or row_set.row_set_id != snapshot.row_set_id
    ):
        raise ExportVerificationError(
            "verified export row-set identities differ from the dataset snapshot"
        )
    manifest_files = {item.path: item for item in manifest.files}
    for binding in snapshot.file_bindings:
        descriptor = manifest_files.get(binding.path)
        if descriptor is None or (
            descriptor.sha256,
            descriptor.size,
            descriptor.record_count,
            descriptor.role,
            descriptor.media_type,
        ) != (
            binding.sha256,
            binding.byte_size,
            binding.record_count,
            binding.role,
            binding.media_type,
        ):
            raise ExportVerificationError(
                "verified export manifest differs from the dataset file snapshot"
            )
    validation_descriptor = manifest_files.get(VALIDATION_PATH)
    if validation_descriptor is None or (
        validation_descriptor.sha256,
        validation_descriptor.size,
    ) != (sha256_digest(report_bytes), len(report_bytes)):
        raise ExportVerificationError(
            "verified export manifest differs from the validation report"
        )
    row_set_binding = next(
        item for item in snapshot.artifact_bindings if item.role == "row-set"
    )
    if (row_set_binding.sha256, row_set_binding.byte_size) != (
        sha256_digest(row_set_bytes),
        len(row_set_bytes),
    ):
        raise ExportVerificationError(
            "verified export row set differs from its snapshot artifact binding"
        )
    if len(snapshot.file_bindings) != 3:
        raise ExportVerificationError(
            "verified export snapshot has an incomplete file registry"
        )
    train_binding, evaluation_binding, provenance_binding = snapshot.file_bindings
    if (
        (
            train_binding.sha256,
            train_binding.byte_size,
            train_binding.record_count,
        )
        != (
            row_set.train_jsonl_sha256,
            row_set.train_jsonl_byte_size,
            row_set.train_row_count,
        )
        or (
            evaluation_binding.sha256,
            evaluation_binding.byte_size,
            evaluation_binding.record_count,
        )
        != (
            row_set.evaluation_jsonl_sha256,
            row_set.evaluation_jsonl_byte_size,
            row_set.evaluation_row_count,
        )
        or (
            provenance_binding.sha256,
            provenance_binding.byte_size,
            provenance_binding.record_count,
        )
        != (
            row_set.provenance_jsonl_sha256,
            row_set.provenance_jsonl_byte_size,
            row_set.total_row_count,
        )
    ):
        raise ExportVerificationError(
            "verified export row bytes differ from the dataset snapshot"
        )

    rows = (*row_set.train_rows, *row_set.evaluation_rows)
    if not rows or len(rows) != len(row_set.provenance):
        raise ExportVerificationError(
            "verified export source has incomplete row provenance"
        )
    objective_ids: set[str] = set()
    emitted_source_ids: set[str] = set()
    try:
        for row, provenance in zip(rows, row_set.provenance, strict=True):
            objective_ids.add(provenance.objective_id)
            emitted_source_ids.update(provenance.source_ids)
            if (
                provenance.plan_id != snapshot.plan_id
                or provenance.recipe_id != snapshot.recipe_id
                or provenance.construction_result_id
                != snapshot.construction_result_id
                or provenance.curation_result_id != snapshot.curation_result_id
                or provenance.split_result_id != snapshot.split_result_id
                or provenance.serialization_plan_id
                != row_set.serialization_plan_id
                or provenance.row_id != row.row_id
                or provenance.record_id != row.record_id
                or provenance.payload_sha256 != row.payload_sha256
            ):
                raise ExportVerificationError(
                    "verified export provenance differs from its source row"
                )
        if len(objective_ids) != 1:
            raise ExportVerificationError(
                "verified export source must bind one training objective"
            )
        if emitted_source_ids != set(snapshot.source_ids):
            raise ExportVerificationError(
                "verified export rows do not cover the dataset source scope"
            )
        projection = _membership_projection_from_row_set(row_set)
    except ExportVerificationError:
        raise
    except (
        AttributeError,
        RecursionError,
        TypeError,
        UnicodeError,
        ValueError,
        VeriformisError,
    ) as exc:
        raise ExportVerificationError(
            f"invalid verified export source evidence: {exc}"
        ) from exc
    return (
        report,
        row_set,
        verification,
        next(iter(objective_ids)),
        projection,
    )


def _membership_projection_from_row_set(
    row_set: RowSet,
) -> ExportMembershipProjection:
    """Derive one complete ordered membership projection from aligned rows."""
    rows = (*row_set.train_rows, *row_set.evaluation_rows)
    entries = tuple(
        ExportMembershipEntry.create(
            record_id=row.record_id,
            row_id=row.row_id,
            provenance_id=provenance.provenance_id,
            assignment_id=provenance.assignment_id,
            leakage_group_id=provenance.leakage_group_id,
            partition=provenance.partition,
            ordinal=provenance.ordinal,
            payload_sha256=row.payload_sha256,
        )
        for row, provenance in zip(rows, row_set.provenance, strict=True)
    )
    return ExportMembershipProjection.create(
        split_result_id=row_set.split_result_id,
        row_set_id=row_set.row_set_id,
        row_schema=row_set.row_schema,
        entries=entries,
    )


DEFAULT_EXPORT_SERVICE = ExportService()


__all__ = ["DEFAULT_EXPORT_SERVICE", "ExportService"]
