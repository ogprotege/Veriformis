"""Verified-bundle-only composition service for derived exports.

Phase 4 builds every export operation through this service. The opening
increment deliberately exposes no container writer: it establishes a typed,
descriptor-anchored source boundary without promoting Phase 5 containers.
"""

from __future__ import annotations

import os
from pathlib import Path

from veriformis.bundle import VerifiedFinishedBundle, inspect_finished_bundle


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
        expected_manifest_sha256: str | None = None,
    ) -> VerifiedFinishedBundle:
        """Return immutable source semantics reconstructed during verification."""
        return inspect_finished_bundle(
            Path(bundle),
            expected_manifest_sha256=expected_manifest_sha256,
        )


DEFAULT_EXPORT_SERVICE = ExportService()


__all__ = ["DEFAULT_EXPORT_SERVICE", "ExportService"]
