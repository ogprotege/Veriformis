"""Release pins. Loading the 1.0 support matrix is not a version bump."""

from veriformis.release.matrix import (
    REQUIRED_EXCLUSIONS,
    SupportMatrix,
    support_matrix,
    support_matrix_discovery,
    support_matrix_json,
)

__all__ = [
    "REQUIRED_EXCLUSIONS",
    "SupportMatrix",
    "support_matrix",
    "support_matrix_discovery",
    "support_matrix_json",
]
