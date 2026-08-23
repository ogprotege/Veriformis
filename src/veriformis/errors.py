# src/veriformis/errors.py
"""Typed errors shared by every surface (CLI, MCP, GUI)."""
from __future__ import annotations


class VeriformisError(Exception):
    code = "veriformis-error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ParseError(VeriformisError):
    code = "parse-error"


class UnsupportedInputError(VeriformisError):
    code = "unsupported-input"


class RuleError(VeriformisError):
    code = "rule-error"


class CleaningPlanError(VeriformisError):
    """A serialized cleaning plan is stale, altered, or cannot be replayed."""

    code = "cleaning-plan-invalid"


class EvidenceError(VeriformisError):
    """Source evidence is missing, altered, or cannot be reconstructed."""

    code = "source-evidence-invalid"


class ConstructionError(VeriformisError):
    """A recipe or construction result is invalid or cannot be replayed."""

    code = "construction-invalid"


class CurationError(VeriformisError):
    """Curation policy or results are incomplete, altered, or unreplayable."""

    code = "curation-invalid"


class SplitError(VeriformisError):
    """A leakage group or authoritative split assignment is invalid."""

    code = "split-invalid"


class SerializationError(VeriformisError):
    """A product row invents semantics or diverges from its accepted record."""

    code = "serialization-invalid"


class DatasetValidationError(VeriformisError):
    """The finished-dataset snapshot or validation report is invalid."""

    code = "dataset-validation-invalid"


class SealError(VeriformisError):
    """An exact validated dataset cannot be sealed or published safely."""

    code = "seal-invalid"


class BundleVerificationError(VeriformisError):
    """A sealed bundle is malformed, open-ended, altered, or untrusted."""

    code = "bundle-invalid"


class InvalidIRError(VeriformisError):
    """Persisted document IR violates the versioned schema or provenance rules."""

    code = "invalid-ir"


class WorkspaceNotFoundError(VeriformisError):
    code = "workspace-not-found"


class WorkspaceLockedError(VeriformisError):
    code = "workspace-locked"


class WorkspaceRevisionConflict(VeriformisError):
    code = "workspace-revision-conflict"

    def __init__(self, expected: str, actual: str):
        self.expected = expected
        self.actual = actual
        super().__init__(f"workspace revision changed: expected {expected}, found {actual}")


class WorkspaceCorruptError(VeriformisError):
    code = "workspace-corrupt"


class UnsupportedWorkspaceVersionError(VeriformisError):
    code = "unsupported-workspace-version"


class MissingStageInputError(VeriformisError):
    code = "missing-stage-input"


class StaleStageError(VeriformisError):
    code = "stale-stage"


class ArtifactDigestMismatchError(VeriformisError):
    code = "artifact-digest-mismatch"


class DuplicateIdentityError(VeriformisError):
    code = "duplicate-identity"


class InvalidSourceLocatorError(VeriformisError):
    code = "invalid-source-locator"


class LegacyWorkspaceAmbiguousError(VeriformisError):
    code = "legacy-workspace-ambiguous"


class LegacySourceUnavailableError(VeriformisError):
    code = "legacy-source-unavailable"


class GateFailure(VeriformisError):
    code = "gate-failure"


class TaxonomyError(VeriformisError):
    """A taxonomy identifier or axis combination is unknown or incompatible."""

    code = "taxonomy-invalid"


class GoalCatalogError(VeriformisError):
    """The versioned goal catalog is malformed, tampered, or not closed over the taxonomy."""

    code = "goal-catalog-invalid"


class GoalInstructionError(VeriformisError):
    """A supplied goal instruction is absent, inapplicable, or untruthful."""

    code = "goal-instruction-invalid"

    def __init__(self, message: str, *, reason_codes: tuple[str, ...]):
        self.reason_codes = reason_codes
        super().__init__(message)


class CompilePreflightError(VeriformisError):
    """Compile preflight cannot produce one complete truthful response."""

    code = "compile-preflight-invalid"


class ExportContractError(VeriformisError):
    """A versioned export plan, profile, binding, or receipt is invalid."""

    code = "export-contract-invalid"


class ExportVerificationError(VeriformisError):
    """A derived export is malformed, altered, incomplete, or untrusted."""

    code = "export-verification-invalid"
