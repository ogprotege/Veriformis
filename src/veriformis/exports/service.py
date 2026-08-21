"""Verified-bundle-only composition service for derived exports.

Phase 4 builds every export operation through this service. The current
read-only increments establish a typed, descriptor-anchored source boundary
and fail-closed trust admission without promoting Phase 5 containers.
"""

from __future__ import annotations

import os

from veriformis.bundle import VerifiedFinishedBundle, inspect_finished_bundle
from veriformis.errors import ExportContractError, ExportVerificationError
from veriformis.exports.models import SourceTrustGrade, SourceTrustPolicy


_SOURCE_TRUST_POLICIES = frozenset(
    {"require_external_digest", "allow_self_consistent"}
)


class ExportService:
    """Own export policy beneath :class:`PipelineService`.

    Adapters must call the Python composition root. They must never copy or
    rewrite bundle files directly. Later Phase 4 increments add plans,
    receipts, publication, and verification here without changing that
    boundary.
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


DEFAULT_EXPORT_SERVICE = ExportService()


__all__ = ["DEFAULT_EXPORT_SERVICE", "ExportService"]
