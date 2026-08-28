"""Verified-bundle-only composition service for derived exports.

Phase 4 built every export operation through this service. Phase 5 installs
reviewed internal container implementations in the immutable production
catalog while retaining the same source, plan, membership, and publication
boundary.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from veriformis.bundle import (
    VALIDATION_PATH,
    FinishedBundleManifest,
    VerificationResult,
    VerifiedFinishedBundle,
    inspect_finished_bundle,
)
from veriformis.bundle.verifier import (
    IMPORTED_BUNDLE_ROW_SET_SCHEMA,
    ImportedBundleRowSet,
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
from veriformis.taxonomy import (
    CANDIDATE_CONSUMER_PROFILES,
    UNEXECUTABLE_CONSUMER_PROFILE_ITEMS,
    UNEXECUTABLE_PHYSICAL_CONTAINER_ITEMS,
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
from veriformis.exports.api import (
    ExportDiscovery,
    ExportDryRunPreview,
    ExportDryRunRequest,
    ExportDryRunRequestV2,
    ExportExecuteRequest,
    ExportExecuteRequestV2,
    ExportInspectRequest,
    ExportInspection,
    ExportVerifiedOutcome,
    ExportVerifyRequest,
    ExportVerifyRequestV2,
    _validate_executable_plan_response_budget,
)
from veriformis.exports._publication import (
    CancellationCheck,
    ExportPublicationOutcome,
    _inspect_export_directory,
    _publish_exact_export,
    _publish_semantic_export,
    _verify_export_directory,
)
from veriformis.exports._implementation import (
    _ExportImplementation,
    _RenderedDerivative,
    _ReplayedDerivative,
)
from veriformis.exports.canonical_json import CANONICAL_JSON_IMPLEMENTATION
from veriformis.exports.constrained_csv import (
    CONSTRAINED_CSV_IMPLEMENTATION,
)
from veriformis.exports.paths import validate_export_relative_path
from veriformis.exports.arrow import ARROW_IMPLEMENTATION
from veriformis.exports.hugging_face_dataset import HF_DATASET_IMPLEMENTATION
from veriformis.exports.parquet import PARQUET_IMPLEMENTATION
from veriformis.exports.split_jsonl import SPLIT_JSONL_IMPLEMENTATION
from veriformis.profiles.aptus import APTUS_IMPLEMENTATION
from veriformis.profiles.axolotl import AXOLOTL_IMPLEMENTATION
from veriformis.profiles.llama_factory import LLAMA_FACTORY_IMPLEMENTATION
from veriformis.profiles.mlx_lm import MLX_LM_IMPLEMENTATION
from veriformis.profiles.trl import TRL_IMPLEMENTATION
from veriformis.identity import lossless_json_bytes, sha256_digest


_SOURCE_TRUST_POLICIES = frozenset(
    {"require_external_digest", "allow_self_consistent"}
)

_SelectedExportRequest = (
    ExportDryRunRequest
    | ExportDryRunRequestV2
    | ExportExecuteRequest
    | ExportExecuteRequestV2
    | ExportVerifyRequest
    | ExportVerifyRequestV2
)


class ExportService:
    """Own export policy beneath :class:`PipelineService`.

    Adapters must call the Python composition root. They must never copy or
    rewrite bundle files directly. Phase 4.6 adds private destination
    enforcement, receipts, publication, and verification. Phase 4.7 adds
    private two-render exact comparison and semantic reconstruction without
    changing that boundary. Phase 4.8 exposes only the typed operations through
    the composition root and a private implementation catalog. Phase 5.1 adds
    the first reviewed generic container to that catalog. Phase 5.2 adds
    canonical JSON without changing the service boundary.
    """

    def __init__(
        self,
        *,
        _implementations: Sequence[_ExportImplementation] | None = None,
    ) -> None:
        """Build one immutable private catalog from reviewed implementations."""
        implementations = (
            (
                SPLIT_JSONL_IMPLEMENTATION,
                CANONICAL_JSON_IMPLEMENTATION,
                CONSTRAINED_CSV_IMPLEMENTATION,
                PARQUET_IMPLEMENTATION,
                ARROW_IMPLEMENTATION,
                HF_DATASET_IMPLEMENTATION,
                TRL_IMPLEMENTATION,
                MLX_LM_IMPLEMENTATION,
                AXOLOTL_IMPLEMENTATION,
                LLAMA_FACTORY_IMPLEMENTATION,
                APTUS_IMPLEMENTATION,
            )
            if _implementations is None
            else tuple(_implementations)
        )
        if any(not isinstance(item, _ExportImplementation) for item in implementations):
            raise ExportContractError(
                "export implementations must use the private implementation type"
            )
        selectors = tuple(item.descriptor.selector for item in implementations)
        if len(selectors) != len(set(selectors)):
            raise ExportContractError("export implementation selectors must be unique")
        self._implementations = tuple(
            sorted(
                implementations,
                key=lambda item: (
                    item.descriptor.selector[0],
                    item.descriptor.selector[1],
                    item.descriptor.selector[2] or "",
                    item.descriptor.selector[3] or 0,
                ),
            )
        )

    def discover_exports(self) -> ExportDiscovery:
        """Return truthful, deterministic executable-profile discovery."""
        return ExportDiscovery.create(
            tuple(item.descriptor for item in self._catalog())
        )

    def dry_run_export(
        self,
        request: ExportDryRunRequest | ExportDryRunRequestV2,
    ) -> ExportPlan:
        """Derive one exact plan without touching or publishing a destination."""
        if type(request) is ExportDryRunRequest:
            checked = ExportDryRunRequest.from_json_bytes(request.canonical_bytes())
        elif type(request) is ExportDryRunRequestV2:
            checked = ExportDryRunRequestV2.from_json_bytes(request.canonical_bytes())
        else:
            raise ExportContractError(
                "dry_run_export requires an exact dry-run request type"
            )
        implementation = self._resolve_implementation(checked)
        return self._plan_registered_export(checked, implementation)

    def dry_run_export_preview(
        self,
        request: ExportDryRunRequest | ExportDryRunRequestV2,
    ) -> ExportDryRunPreview:
        """Derive one plan-bound preview without renderer or destination access."""
        if type(request) is ExportDryRunRequest:
            checked = ExportDryRunRequest.from_json_bytes(request.canonical_bytes())
        elif type(request) is ExportDryRunRequestV2:
            checked = ExportDryRunRequestV2.from_json_bytes(request.canonical_bytes())
        else:
            raise ExportContractError(
                "dry_run_export_preview requires an exact dry-run request type"
            )
        implementation = self._resolve_implementation(checked)
        plan, row_set = self._plan_registered_export_evidence(
            checked,
            implementation,
        )
        return ExportDryRunPreview.create(plan=plan, row_set=row_set)

    def inspect_export(
        self,
        request: ExportInspectRequest,
        *,
        cancellation_check: CancellationCheck | None = None,
    ) -> ExportInspection:
        """Inspect self-described physical bytes without asserting source trust."""
        checked = ExportInspectRequest.from_json_bytes(request.canonical_bytes())
        receipt = _inspect_export_directory(
            checked.destination_root,
            cancellation_check=cancellation_check,
        )
        return ExportInspection(
            destination_root=Path(os.path.abspath(checked.destination_root)),
            inspection_scope="self_described_physical",
            receipt=receipt,
        )

    def execute_export(
        self,
        request: ExportExecuteRequest | ExportExecuteRequestV2,
        *,
        cancellation_check: CancellationCheck | None = None,
    ) -> ExportPublicationOutcome:
        """Re-derive, anchor, render twice, and atomically publish one profile."""
        if cancellation_check is not None and not callable(cancellation_check):
            raise ExportContractError("cancellation_check must be callable")
        if type(request) is ExportExecuteRequest:
            checked = ExportExecuteRequest.from_json_bytes(request.canonical_bytes())
        elif type(request) is ExportExecuteRequestV2:
            checked = ExportExecuteRequestV2.from_json_bytes(request.canonical_bytes())
        else:
            raise ExportContractError(
                "execute_export requires an exact execute request type"
            )
        implementation = self._resolve_implementation(checked)
        plan = self._plan_registered_export(
            checked,
            implementation,
            cancellation_check=cancellation_check,
        )
        if plan.export_plan_id != checked.expected_export_plan_id:
            raise ExportVerificationError(
                "execution plan differs from the operator-confirmed dry run"
            )
        bound = _ImplementationBoundExportService(self, implementation)
        return bound.publish(
            plan,
            checked.bundle,
            checked.destination_root,
            expected_manifest_sha256=checked.expected_manifest_sha256,
            cancellation_check=cancellation_check,
        )

    def verify_export(
        self,
        request: ExportVerifyRequest | ExportVerifyRequestV2,
        *,
        cancellation_check: CancellationCheck | None = None,
    ) -> ExportVerifiedOutcome:
        """Re-derive the expected plan from source, then verify visible bytes."""
        if cancellation_check is not None and not callable(cancellation_check):
            raise ExportContractError("cancellation_check must be callable")
        if type(request) is ExportVerifyRequest:
            checked = ExportVerifyRequest.from_json_bytes(request.canonical_bytes())
        elif type(request) is ExportVerifyRequestV2:
            checked = ExportVerifyRequestV2.from_json_bytes(request.canonical_bytes())
        else:
            raise ExportContractError(
                "verify_export requires an exact verify request type"
            )
        implementation = self._resolve_implementation(checked)
        plan = self._plan_registered_export(
            checked,
            implementation,
            cancellation_check=cancellation_check,
        )
        if plan.export_plan_id != checked.expected_export_plan_id:
            raise ExportVerificationError(
                "verification plan differs from the operator-confirmed dry run"
            )
        bound = _ImplementationBoundExportService(self, implementation)
        replay_callback = None
        if plan.container_profile.determinism_claim == "semantic_content_only":
            plan_bytes = plan.canonical_bytes()

            def replay_callback(
                files: tuple[tuple[str, bytes], ...],
            ) -> tuple[tuple[str, bytes], ...]:
                return bound._replay_and_validate(
                    plan_bytes,
                    files,
                    cancellation_check=cancellation_check,
                )

        receipt, verification = _verify_export_directory(
            checked.destination_root,
            expected_plan=plan,
            cancellation_check=cancellation_check,
            semantic_replay=replay_callback,
        )
        return ExportVerifiedOutcome(
            destination_root=Path(os.path.abspath(checked.destination_root)),
            receipt=receipt,
            verification=verification,
        )

    def _catalog(self) -> tuple[_ExportImplementation, ...]:
        """Support pre-4.8 test subclasses that did not call ``super().__init__``."""
        return getattr(self, "_implementations", ())

    def _resolve_implementation(
        self,
        request: _SelectedExportRequest,
    ) -> _ExportImplementation:
        _refuse_unexecutable_container_id(request.container_id)
        _refuse_unexecutable_consumer_id(request.consumer_id)
        selector = (
            request.container_id,
            request.container_version,
            request.consumer_id,
            request.consumer_profile_version,
        )
        if (
            request.container_id == "split-jsonl-directory"
            and request.consumer_id is None
        ):
            from veriformis.extensions.runtime import bound_split_jsonl_exporter

            implementation = bound_split_jsonl_exporter(catalog=self._catalog())
            if implementation.descriptor.selector != selector:
                raise ExportContractError(
                    "no executable export implementation matches the exact selector"
                )
            return implementation
        for implementation in self._catalog():
            if implementation.descriptor.selector == selector:
                return implementation
        raise ExportContractError(
            "no executable export implementation matches the exact selector"
        )

    def _plan_registered_export(
        self,
        request: _SelectedExportRequest,
        implementation: _ExportImplementation,
        *,
        cancellation_check: CancellationCheck | None = None,
    ) -> ExportPlan:
        return self._plan_registered_export_evidence(
            request,
            implementation,
            cancellation_check=cancellation_check,
        )[0]

    def _plan_registered_export_evidence(
        self,
        request: _SelectedExportRequest,
        implementation: _ExportImplementation,
        *,
        cancellation_check: CancellationCheck | None = None,
    ) -> tuple[ExportPlan, RowSet]:
        """Plan once and retain the exact strict row-set snapshot it binds."""
        _run_cancellation_check(cancellation_check)
        configured = isinstance(
            request,
            (ExportDryRunRequestV2, ExportExecuteRequestV2, ExportVerifyRequestV2),
        )
        options = self._parse_container_options(request, implementation)
        source = self.verified_source(
            request.bundle,
            source_trust_policy=request.source_trust_policy,
            expected_manifest_sha256=request.expected_manifest_sha256,
        )
        _run_cancellation_check(cancellation_check)
        descriptor = implementation.descriptor
        try:
            source_evidence = _source_plan_evidence(source)
            source_row_set = source_evidence[1]
            if isinstance(source_row_set, ImportedBundleRowSet):
                planner_row_set = source_row_set
            else:
                planner_row_set = row_set_from_json_bytes(
                    lossless_json_bytes(source_row_set.model_dump(mode="json"))
                )
            if planner_row_set.row_schema not in descriptor.supported_row_schemas:
                if (
                    descriptor.selector
                    == CONSTRAINED_CSV_IMPLEMENTATION.descriptor.selector
                    and planner_row_set.row_schema == "messages"
                ):
                    raise ExportContractError(
                        "export selector 'constrained-csv' v1 does not support "
                        "source row schema 'messages'; use split-jsonl-directory "
                        "v1 or json v1 to preserve nested values"
                    )
                raise ExportContractError(
                    f"export selector {descriptor.container_profile.container_id!r} "
                    f"v{descriptor.container_profile.container_version} does not "
                    f"support source row schema {planner_row_set.row_schema!r}; "
                    "choose a discovered profile that lists that schema"
                )
            if not configured:
                file_plans = tuple(
                    implementation.file_planner(descriptor, planner_row_set)
                )
            else:
                if implementation.configured_file_planner is None:
                    raise ExportContractError(
                        "selected export implementation does not accept "
                        "container_options"
                    )
                file_plans = tuple(
                    implementation.configured_file_planner(
                        descriptor,
                        planner_row_set,
                        options,
                    )
                )
            plan, planned_row_set = _plan_from_source_evidence(
                source_evidence,
                source_trust_policy=request.source_trust_policy,
                container_profile=descriptor.container_profile,
                consumer_profile=descriptor.consumer_profile,
                dependencies=descriptor.dependencies,
                file_plans=file_plans,
            )
            if plan.overwrite_policy != request.overwrite_policy:
                raise ExportContractError(
                    "requested overwrite policy differs from the export contract"
                )
            if (
                planned_row_set != planner_row_set
                or lossless_json_bytes(planned_row_set.model_dump(mode="json"))
                != lossless_json_bytes(planner_row_set.model_dump(mode="json"))
            ):
                raise ExportContractError(
                    "registered export planner row set changed within one dry run"
                )
            _validate_executable_plan_response_budget(plan)
            _run_cancellation_check(cancellation_check)
            return plan, planned_row_set
        except (ExportContractError, ExportVerificationError):
            raise
        except (
            AttributeError,
            RecursionError,
            TypeError,
            UnicodeError,
            ValueError,
            VeriformisError,
        ) as exc:
            raise ExportContractError(
                f"invalid registered export planning evidence: {exc}"
            ) from exc

    def _parse_container_options(
        self,
        request: _SelectedExportRequest,
        implementation: _ExportImplementation,
    ) -> object:
        """Validate selected container options before source or destination access."""
        if not isinstance(
            request,
            (ExportDryRunRequestV2, ExportExecuteRequestV2, ExportVerifyRequestV2),
        ):
            return None
        raw: Mapping[str, object] = request.container_options
        parser = implementation.options_parser
        if parser is None:
            raise ExportContractError(
                "selected export implementation does not accept container_options"
            )
        try:
            return parser(raw)
        except ExportContractError:
            raise
        except (
            AttributeError,
            RecursionError,
            TypeError,
            UnicodeError,
            ValueError,
            VeriformisError,
        ) as exc:
            raise ExportContractError(f"invalid container_options: {exc}") from exc

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
            if _is_imported_export_plan(checked_plan):
                from veriformis.mapping.finish import ImportedRowProvenance

                provenance = tuple(
                    ImportedRowProvenance.model_validate(
                        item.model_dump(mode="json")
                    )
                    for item in supplied_provenance
                )
                candidate_row_set = _imported_candidate_row_set(
                    checked_plan,
                    train_rows=train_rows,
                    evaluation_rows=evaluation_rows,
                    provenance=provenance,
                )
            else:
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
            if (
                not _is_imported_export_plan(checked_plan)
                and candidate_row_set.row_set_id != checked_plan.row_set_id
            ):
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
        """Atomically publish one test-injected deterministic derivative.

        This lower-level operation intentionally has no caller-supplied
        renderer-selection argument. The base hooks remain injection-only;
        shipped implementations bind them through exact private catalog
        selection before this publication primitive is called.
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
            if isinstance(exc, (ExportContractError, ExportVerificationError)):
                raise
            raise ExportContractError(f"invalid export publication plan: {exc}") from exc
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
        _run_cancellation_check(cancellation_check)
        rebuilt_plan, source_row_set = _plan_from_verified_source(
            source,
            source_trust_policy=checked_plan.source_trust_policy,
            container_profile=checked_plan.container_profile,
            consumer_profile=checked_plan.consumer_profile,
            dependencies=checked_plan.dependencies,
            file_plans=checked_plan.file_plans,
        )
        _run_cancellation_check(cancellation_check)
        if (
            rebuilt_plan != checked_plan
            or rebuilt_plan.canonical_bytes() != checked_plan.canonical_bytes()
        ):
            raise ExportVerificationError(
                "reverified export source differs from the supplied export plan"
            )

        plan_bytes = checked_plan.canonical_bytes()
        row_set_bytes = lossless_json_bytes(source_row_set.model_dump(mode="json"))
        first_files = self._render_and_validate(
            plan_bytes,
            row_set_bytes,
            cancellation_check=cancellation_check,
        )
        second_files = self._render_and_validate(
            plan_bytes,
            row_set_bytes,
            cancellation_check=cancellation_check,
        )

        if checked_plan.container_profile.determinism_claim == "portable_exact_bytes":
            if first_files != second_files:
                raise ExportVerificationError(
                    "portable exact renderer executions produced different byte trees"
                )
            _run_cancellation_check(cancellation_check)
            return _publish_exact_export(
                destination_root,
                source_root=source.bundle_path,
                plan=checked_plan,
                files=first_files,
                cancellation_check=cancellation_check,
            )

        first_semantics = self._replay_and_validate(
            plan_bytes,
            first_files,
            cancellation_check=cancellation_check,
        )
        second_semantics = self._replay_and_validate(
            plan_bytes,
            second_files,
            cancellation_check=cancellation_check,
        )
        if first_semantics != second_semantics:
            raise ExportVerificationError(
                "semantic renderer executions produced different canonical content"
            )
        _run_cancellation_check(cancellation_check)

        def replay_staged(
            replay_files: tuple[tuple[str, bytes], ...],
        ) -> tuple[tuple[str, bytes], ...]:
            return self._replay_and_validate(
                plan_bytes,
                replay_files,
                cancellation_check=cancellation_check,
            )

        return _publish_semantic_export(
            destination_root,
            source_root=source.bundle_path,
            plan=checked_plan,
            files=first_files,
            expected_semantic_preimages=first_semantics,
            semantic_replay=replay_staged,
            cancellation_check=cancellation_check,
        )

    def _render_and_validate(
        self,
        plan_bytes: bytes,
        source_row_set_bytes: bytes,
        *,
        cancellation_check: CancellationCheck | None,
    ) -> tuple[tuple[str, bytes], ...]:
        """Run one renderer against fresh strict inputs and freeze its result."""
        _run_cancellation_check(cancellation_check)
        try:
            plan = ExportPlan.from_json_bytes(plan_bytes)
            source_row_set = _export_row_set_from_bytes(source_row_set_bytes)
            rendered = self._render_derivative(plan, source_row_set)
            files = _normalize_file_bytes(
                plan,
                rendered.files,
                evidence_label="renderer output",
                require_exact_plan_bytes=(
                    plan.container_profile.determinism_claim
                    == "portable_exact_bytes"
                ),
            )
            train_rows = tuple(rendered.train_rows)
            evaluation_rows = tuple(rendered.evaluation_rows)
            provenance = tuple(rendered.provenance)
        except (AttributeError, TypeError, UnicodeError, ValueError, VeriformisError) as exc:
            if isinstance(exc, (ExportContractError, ExportVerificationError)):
                raise
            raise ExportVerificationError(
                f"invalid injected renderer result: {exc}"
            ) from exc
        _run_cancellation_check(cancellation_check)
        self.validate_derivative_membership(
            plan,
            candidate_train_rows=train_rows,
            candidate_evaluation_rows=evaluation_rows,
            candidate_provenance=provenance,
        )
        _run_cancellation_check(cancellation_check)
        return files

    def _replay_and_validate(
        self,
        plan_bytes: bytes,
        files: Sequence[tuple[str, bytes]],
        *,
        cancellation_check: CancellationCheck | None,
    ) -> tuple[tuple[str, bytes], ...]:
        """Reconstruct and validate canonical semantics from one byte tree."""
        _run_cancellation_check(cancellation_check)
        try:
            plan = ExportPlan.from_json_bytes(plan_bytes)
            frozen_files = _normalize_file_bytes(
                plan,
                files,
                evidence_label="semantic replay input",
                require_exact_plan_bytes=False,
            )
            replayed = self._replay_derivative(plan, frozen_files)
            semantic_contents = _normalize_semantic_contents(
                plan,
                replayed.semantic_contents,
            )
            train_rows = tuple(replayed.train_rows)
            evaluation_rows = tuple(replayed.evaluation_rows)
            provenance = tuple(replayed.provenance)
        except (AttributeError, TypeError, UnicodeError, ValueError, VeriformisError) as exc:
            if isinstance(exc, (ExportContractError, ExportVerificationError)):
                raise
            raise ExportVerificationError(
                f"invalid injected semantic replay result: {exc}"
            ) from exc
        _run_cancellation_check(cancellation_check)
        self.validate_derivative_membership(
            plan,
            candidate_train_rows=train_rows,
            candidate_evaluation_rows=evaluation_rows,
            candidate_provenance=provenance,
        )
        _run_cancellation_check(cancellation_check)
        return semantic_contents

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

    def _replay_derivative(
        self,
        plan: ExportPlan,
        files: tuple[tuple[str, bytes], ...],
    ) -> _ReplayedDerivative:
        """Resolve no semantic decoder; test-only subclasses may override it."""
        del plan, files
        raise ExportContractError(
            "no verified export semantic replayer is installed; Phase 4 "
            "conformance replay is test-injected only"
        )


class _ImplementationBoundExportService(ExportService):
    """Bind one private catalog implementation to the hardened publisher."""

    def __init__(
        self,
        owner: ExportService,
        implementation: _ExportImplementation,
    ) -> None:
        super().__init__(_implementations=(implementation,))
        self._owner = owner
        self._implementation = implementation

    def verified_source(
        self,
        bundle: str | os.PathLike[str],
        *,
        source_trust_policy: SourceTrustPolicy = "require_external_digest",
        expected_manifest_sha256: str | None = None,
    ) -> VerifiedFinishedBundle:
        return self._owner.verified_source(
            bundle,
            source_trust_policy=source_trust_policy,
            expected_manifest_sha256=expected_manifest_sha256,
        )

    def validate_derivative_membership(
        self,
        plan: ExportPlan,
        *,
        candidate_train_rows: Sequence[ProductRow],
        candidate_evaluation_rows: Sequence[ProductRow],
        candidate_provenance: Sequence[RowProvenance],
    ) -> ExportMembershipProjection:
        return self._owner.validate_derivative_membership(
            plan,
            candidate_train_rows=candidate_train_rows,
            candidate_evaluation_rows=candidate_evaluation_rows,
            candidate_provenance=candidate_provenance,
        )

    def _render_derivative(
        self,
        plan: ExportPlan,
        source_row_set: RowSet,
    ) -> _RenderedDerivative:
        return self._implementation.renderer(plan, source_row_set)

    def _replay_derivative(
        self,
        plan: ExportPlan,
        files: tuple[tuple[str, bytes], ...],
    ) -> _ReplayedDerivative:
        replayer = self._implementation.semantic_replayer
        if replayer is None:
            raise ExportContractError(
                "portable exact export implementation has no semantic replayer"
            )
        return replayer(plan, files)


def _run_cancellation_check(check: CancellationCheck | None) -> None:
    if check is not None:
        check()


def _normalize_file_bytes(
    plan: ExportPlan,
    entries: Sequence[tuple[str, bytes]],
    *,
    evidence_label: str,
    require_exact_plan_bytes: bool,
) -> tuple[tuple[str, bytes], ...]:
    """Freeze one complete path-to-bytes tree in canonical plan order."""
    try:
        supplied = tuple(entries)
    except (TypeError, ValueError) as exc:
        raise ExportVerificationError(
            f"{evidence_label} must be a finite sequence: {exc}"
        ) from exc
    copied: dict[str, bytes] = {}
    for entry in supplied:
        if type(entry) is not tuple or len(entry) != 2:
            raise ExportVerificationError(
                f"{evidence_label} entries must be exact (path, bytes) tuples"
            )
        path, data = entry
        if type(path) is not str or type(data) is not bytes:
            raise ExportVerificationError(
                f"{evidence_label} entries must contain an exact string and bytes"
            )
        try:
            validate_export_relative_path(path)
        except ValueError as exc:
            raise ExportVerificationError(
                f"{evidence_label} contains unsafe export path {path!r}: {exc}"
            ) from exc
        if path in copied:
            raise ExportVerificationError(
                f"{evidence_label} contains duplicate export path {path!r}"
            )
        copied[path] = data
    expected_paths = {item.path for item in plan.file_plans}
    if set(copied) != expected_paths:
        raise ExportVerificationError(
            f"{evidence_label} does not match the complete planned file set; "
            f"missing={sorted(expected_paths - set(copied))!r}, "
            f"extra={sorted(set(copied) - expected_paths)!r}"
        )
    normalized = tuple((item.path, copied[item.path]) for item in plan.file_plans)
    if require_exact_plan_bytes:
        for file_plan, (_, data) in zip(
            plan.file_plans,
            normalized,
            strict=True,
        ):
            if (
                sha256_digest(data) != file_plan.expected_sha256
                or len(data) != file_plan.expected_byte_size
            ):
                raise ExportVerificationError(
                    "renderer bytes differ from the exact plan for "
                    f"{file_plan.path!r}"
                )
    return normalized


def _normalize_semantic_contents(
    plan: ExportPlan,
    entries: Sequence[tuple[str, bytes]],
) -> tuple[tuple[str, bytes], ...]:
    """Freeze and verify canonical semantic preimages in plan-path order."""
    if plan.container_profile.determinism_claim != "semantic_content_only":
        raise ExportContractError(
            "semantic replay requires a semantic_content_only export plan"
        )
    normalized = _normalize_file_bytes(
        plan,
        entries,
        evidence_label="semantic replay output",
        require_exact_plan_bytes=False,
    )
    for file_plan, (_, canonical_content) in zip(
        plan.file_plans,
        normalized,
        strict=True,
    ):
        if sha256_digest(canonical_content) != file_plan.semantic_content_sha256:
            raise ExportVerificationError(
                "replayed semantic content differs from the plan for "
                f"{file_plan.path!r}"
            )
    return normalized


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
    return _plan_from_source_evidence(
        _source_plan_evidence(source),
        source_trust_policy=source_trust_policy,
        container_profile=container_profile,
        consumer_profile=consumer_profile,
        dependencies=dependencies,
        file_plans=file_plans,
    )


def _plan_from_source_evidence(
    evidence: tuple[
        DatasetValidationReport,
        RowSet,
        VerificationResult,
        str,
        ExportMembershipProjection,
    ],
    *,
    source_trust_policy: SourceTrustPolicy,
    container_profile: ExportContainerProfile,
    consumer_profile: ExportConsumerProfile | None,
    dependencies: Sequence[ExportDependencyBinding],
    file_plans: Sequence[ExportFilePlan],
) -> tuple[ExportPlan, RowSet]:
    """Build a plan from one already captured strict source-evidence snapshot."""
    report, row_set, verification, objective_id, membership_projection = evidence
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
        construction_result_id=(
            getattr(snapshot, "construction_result_id", None)
            or snapshot.mapping_result_id
        ),
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


def _refuse_unexecutable_container_id(container_id: str) -> None:
    """Fail closed on planned columnar containers before catalog lookup."""
    later_item = UNEXECUTABLE_PHYSICAL_CONTAINER_ITEMS.get(container_id)
    if later_item is not None:
        raise ExportContractError(
            f"physical container {container_id!r} is planned for item {later_item}"
        )


def _refuse_unexecutable_consumer_id(consumer_id: str | None) -> None:
    """Fail closed on planned or candidate trainer profiles before catalog lookup."""
    if consumer_id is None:
        return
    later_item = UNEXECUTABLE_CONSUMER_PROFILE_ITEMS.get(consumer_id)
    if later_item is not None:
        raise ExportContractError(
            f"consumer profile {consumer_id!r} is planned for item {later_item}; "
            "generic exports keep consumer_id null until that item"
        )
    if consumer_id in CANDIDATE_CONSUMER_PROFILES:
        raise ExportContractError(
            f"consumer profile {consumer_id!r} is a Phase 10 candidate; "
            "it is not executable"
        )


def _export_row_set_from_bytes(data: bytes) -> RowSet | ImportedBundleRowSet:
    import json

    payload = json.loads(data.decode("utf-8"))
    if (
        isinstance(payload, dict)
        and payload.get("schema_version") == IMPORTED_BUNDLE_ROW_SET_SCHEMA
    ):
        return ImportedBundleRowSet.from_dump(payload)
    return row_set_from_json_bytes(data)


def _imported_source_plan_evidence(
    source: VerifiedFinishedBundle,
    manifest: FinishedBundleManifest,
    manifest_bytes: bytes,
) -> tuple[Any, ImportedBundleRowSet, VerificationResult, str, ExportMembershipProjection]:
    report = source.validation_report
    row_set = source.row_set
    verification = VerificationResult.from_json_bytes(
        lossless_json_bytes(source.verification.model_dump(mode="json"))
    )
    snapshot = report.snapshot
    manifest_sha256 = sha256_digest(manifest_bytes)
    report_bytes = lossless_json_bytes(report.model_dump(mode="json"))
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
        or row_set.plan_id != snapshot.plan_id
        or row_set.recipe_id != snapshot.recipe_id
        or row_set.mapping_result_id != snapshot.mapping_result_id
        or row_set.curation_result_id != snapshot.curation_result_id
        or row_set.split_result_id != snapshot.split_result_id
        or row_set.row_set_id != snapshot.row_set_id
    ):
        raise ExportVerificationError(
            "verified export source identities or counts do not close"
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
    if len(snapshot.file_bindings) != 3:
        raise ExportVerificationError(
            "verified export snapshot has an incomplete file registry"
        )
    rows = (*row_set.train_rows, *row_set.evaluation_rows)
    if not rows or len(rows) != len(row_set.provenance):
        raise ExportVerificationError(
            "verified export source has incomplete row provenance"
        )
    objective_ids: set[str] = set()
    emitted_source_ids: set[str] = set()
    for row, provenance in zip(rows, row_set.provenance, strict=True):
        objective_ids.add(provenance.objective_id)
        emitted_source_ids.update(provenance.source_ids)
        if (
            provenance.plan_id != snapshot.plan_id
            or provenance.recipe_id != snapshot.recipe_id
            or provenance.mapping_result_id != snapshot.mapping_result_id
            or provenance.curation_result_id != snapshot.curation_result_id
            or provenance.split_result_id != snapshot.split_result_id
            or provenance.serialization_plan_id != row_set.serialization_plan_id
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
    return (
        report,
        row_set,
        verification,
        next(iter(objective_ids)),
        _membership_projection_from_row_set(row_set),
    )


def _is_imported_export_plan(plan: ExportPlan) -> bool:
    return plan.construction_result_id.startswith("imr-")


def _imported_candidate_row_set(
    plan: ExportPlan,
    *,
    train_rows: tuple[ProductRow, ...],
    evaluation_rows: tuple[ProductRow, ...],
    provenance: tuple[Any, ...],
) -> ImportedBundleRowSet:
    empty = "0" * 64
    return ImportedBundleRowSet(
        row_schema=plan.row_schema,
        train_rows=train_rows,
        evaluation_rows=evaluation_rows,
        provenance=provenance,
        row_set_id=plan.row_set_id,
        split_result_id=plan.split_result_id,
        plan_id=plan.finished_dataset_plan_id,
        recipe_id=plan.recipe_id,
        mapping_result_id=plan.construction_result_id,
        construction_result_id=plan.construction_result_id,
        curation_result_id=plan.curation_result_id,
        serialization_plan_id=plan.serialization_plan_id,
        train_jsonl_sha256=empty,
        train_jsonl_byte_size=0,
        evaluation_jsonl_sha256=empty,
        evaluation_jsonl_byte_size=0,
        provenance_jsonl_sha256=empty,
        provenance_jsonl_byte_size=0,
        train_row_count=len(train_rows),
        evaluation_row_count=len(evaluation_rows),
        total_row_count=len(train_rows) + len(evaluation_rows),
    )


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
        if isinstance(source.row_set, ImportedBundleRowSet):
            return _imported_source_plan_evidence(
                source,
                manifest,
                manifest_bytes,
            )
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
