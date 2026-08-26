"""Dataset quality intelligence. Item 13.5 adds leakage facts."""

from veriformis.quality.distributions import (
    DISTRIBUTION_FACT_NAMES,
    LANGUAGE_UNQUALIFIED,
    report_dataset_distributions,
)
from veriformis.quality.leakage import (
    LEAKAGE_FACT_NAMES,
    UNBOUND_REFERENCE_CORPUS,
    BoundReferenceCorpus,
    bound_reference_corpus,
    report_leakage_checks,
)
from veriformis.quality.near_duplicates import (
    NEAR_DUPLICATE_ALGORITHM_ID,
    NEAR_DUPLICATE_CLUSTER_THRESHOLD_PPM,
    NEAR_DUPLICATE_FACT_NAMES,
    report_near_duplicates,
)
from veriformis.quality.report import (
    REPORT_LIMITATIONS,
    QualityFact,
    QualityPolicyDecision,
    QualityRecommendation,
    QualityReport,
    assemble_quality_report,
    empty_quality_report,
    require_quality_report_not_enforcing,
)

__all__ = [
    "BoundReferenceCorpus",
    "DISTRIBUTION_FACT_NAMES",
    "LANGUAGE_UNQUALIFIED",
    "LEAKAGE_FACT_NAMES",
    "UNBOUND_REFERENCE_CORPUS",
    "NEAR_DUPLICATE_ALGORITHM_ID",
    "NEAR_DUPLICATE_CLUSTER_THRESHOLD_PPM",
    "NEAR_DUPLICATE_FACT_NAMES",
    "REPORT_LIMITATIONS",
    "QualityFact",
    "QualityPolicyDecision",
    "QualityRecommendation",
    "QualityReport",
    "assemble_quality_report",
    "bound_reference_corpus",
    "empty_quality_report",
    "report_dataset_distributions",
    "report_leakage_checks",
    "report_near_duplicates",
    "require_quality_report_not_enforcing",
]
