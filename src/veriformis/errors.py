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


class InputModeError(VeriformisError):
    """An input mode is unknown, malformed, or not yet executable."""

    code = "input-mode-unavailable"


class MappingError(VeriformisError):
    """A mapping plan, imported record, or mapping contract is invalid."""

    code = "mapping-invalid"


class RowSourceError(MappingError):
    """A captured existing-dataset file is malformed or unsupported."""

    code = "row-source-invalid"


class GoalCatalogError(VeriformisError):
    """The versioned goal catalog is malformed, tampered, or not closed over the taxonomy."""

    code = "goal-catalog-invalid"


class InstructionRequiredError(GoalCatalogError):
    """An instruction-and-output row was given an empty operator instruction."""

    code = "instruction-required"


class InstructionNotApplicableError(GoalCatalogError):
    """An instruction was supplied for a representation that does not use one."""

    code = "instruction-not-applicable"


class InstructionTruthfulnessError(GoalCatalogError):
    """An operator instruction fails the deterministic truthfulness check."""

    code = "instruction-untruthful"


class CompilePreflightError(VeriformisError):
    """Compile preflight cannot produce one complete truthful response."""

    code = "compile-preflight-invalid"


class CollectionError(VeriformisError):
    """A collection plan cannot be built or is unsafe to execute."""

    code = "collection-invalid"


class CollectionLimitError(CollectionError):
    """A collection exceeded a declared file, byte, or walk limit."""

    code = "collection-limit"


class OcrIdentityError(VeriformisError):
    """An OCR recovery identity is invalid or not yet executable."""

    code = "ocr-identity-invalid"


class QualityReportError(VeriformisError):
    """A quality report mixes layers or claims enforcement it does not have."""

    code = "quality-report-invalid"


class ReviewError(VeriformisError):
    """A review bundle, waiver, or correction violates its v1 contract."""

    code = "review-invalid"


class ScaleError(VeriformisError):
    """A scale corpus spec or materialization violates its v1 contract."""

    code = "scale-invalid"


class ScaleCancelled(ScaleError):
    """A scale baseline stopped at a cooperative between-stage checkpoint."""

    code = "scale-cancelled"


class ExtensionProtocolError(VeriformisError):
    """An extension declaration is malformed, unknown, or not yet executable."""

    code = "extension-protocol-invalid"


class FamilyAdmissionError(VeriformisError):
    """An advanced-family admission pin is malformed, unknown, or not executable."""

    code = "family-admission-invalid"


class WorkbenchAdapterError(VeriformisError):
    """A workbench-adapter pin is malformed, unknown, or not a screen execute."""

    code = "workbench-adapter-invalid"


class ProjectSpecError(VeriformisError):
    """A project-spec pin is malformed, unknown, or not an execute."""

    code = "project-spec-invalid"


class PublicationAdapterError(VeriformisError):
    """A publication-adapter pin is malformed, unknown, or not an upload."""

    code = "publication-adapter-invalid"


class SupportMatrixError(VeriformisError):
    """A 1.0 support-matrix pin is malformed, unknown, or over-claims."""

    code = "support-matrix-invalid"


class ExportContractError(VeriformisError):
    """A versioned export plan, profile, binding, or receipt is invalid."""

    code = "export-contract-invalid"


class ExportVerificationError(VeriformisError):
    """A derived export is malformed, altered, incomplete, or untrusted."""

    code = "export-verification-invalid"
