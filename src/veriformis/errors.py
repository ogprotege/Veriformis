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
