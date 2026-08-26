"""Dataset quality intelligence. Item 13.6 adds tokenizer simulations."""

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
from veriformis.quality.tokenizer import (
    TOKENIZER_FACT_NAMES,
    TOKENIZER_UNBOUND,
    BoundTokenizerPin,
    bound_tokenizer_pin,
    report_tokenizer_simulations,
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
    "BoundTokenizerPin",
    "DISTRIBUTION_FACT_NAMES",
    "LANGUAGE_UNQUALIFIED",
    "LEAKAGE_FACT_NAMES",
    "UNBOUND_REFERENCE_CORPUS",
    "NEAR_DUPLICATE_ALGORITHM_ID",
    "NEAR_DUPLICATE_CLUSTER_THRESHOLD_PPM",
    "NEAR_DUPLICATE_FACT_NAMES",
    "REPORT_LIMITATIONS",
    "TOKENIZER_FACT_NAMES",
    "TOKENIZER_UNBOUND",
    "QualityFact",
    "QualityPolicyDecision",
    "QualityRecommendation",
    "QualityReport",
    "assemble_quality_report",
    "bound_reference_corpus",
    "bound_tokenizer_pin",
    "empty_quality_report",
    "report_dataset_distributions",
    "report_leakage_checks",
    "report_near_duplicates",
    "report_tokenizer_simulations",
    "require_quality_report_not_enforcing",
]
