"""Dataset quality intelligence. Item 13.9 previews gates; none block seal."""

from veriformis.quality.detectors import (
    DETECTOR_FACT_NAMES,
    DETECTOR_SET_ID,
    report_policy_detectors,
)
from veriformis.quality.distributions import (
    DISTRIBUTION_FACT_NAMES,
    LANGUAGE_UNQUALIFIED,
    report_dataset_distributions,
)
from veriformis.quality.gates import (
    GATE_FACT_NAMES,
    LABELED_FIXTURE_SET_ID,
    LABELED_FIXTURES,
    QUALITY_GATE_POLICY_ID,
    V1_QUALITY_GATES,
    LabeledFixture,
    QualityGateSpec,
    preview_quality_gates,
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
from veriformis.quality.split_findings import (
    SPLIT_FINDING_FACT_NAMES,
    report_split_findings,
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
    "DETECTOR_FACT_NAMES",
    "DETECTOR_SET_ID",
    "DISTRIBUTION_FACT_NAMES",
    "GATE_FACT_NAMES",
    "LABELED_FIXTURE_SET_ID",
    "LABELED_FIXTURES",
    "LabeledFixture",
    "QUALITY_GATE_POLICY_ID",
    "QualityGateSpec",
    "LANGUAGE_UNQUALIFIED",
    "LEAKAGE_FACT_NAMES",
    "UNBOUND_REFERENCE_CORPUS",
    "NEAR_DUPLICATE_ALGORITHM_ID",
    "NEAR_DUPLICATE_CLUSTER_THRESHOLD_PPM",
    "NEAR_DUPLICATE_FACT_NAMES",
    "REPORT_LIMITATIONS",
    "SPLIT_FINDING_FACT_NAMES",
    "TOKENIZER_FACT_NAMES",
    "TOKENIZER_UNBOUND",
    "QualityFact",
    "QualityPolicyDecision",
    "QualityRecommendation",
    "QualityReport",
    "V1_QUALITY_GATES",
    "assemble_quality_report",
    "bound_reference_corpus",
    "bound_tokenizer_pin",
    "empty_quality_report",
    "report_dataset_distributions",
    "report_leakage_checks",
    "preview_quality_gates",
    "report_near_duplicates",
    "report_policy_detectors",
    "report_split_findings",
    "report_tokenizer_simulations",
    "require_quality_report_not_enforcing",
]
