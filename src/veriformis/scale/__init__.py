"""Scale-corpus generators and named-hardware baseline harness."""

from veriformis.scale.baseline import (
    compile_document_corpus,
    record_scale_hardware,
    request_scale_cancellation,
    run_named_tiny_baseline,
    run_scale_baseline,
)
from veriformis.scale.corpora import (
    ci_tiny_specs,
    materialize_scale_corpus,
    measurement_ladder_specs,
    packaged_scale_specs,
    render_text_pdf,
    spec_by_corpus_id,
)
from veriformis.scale.models import (
    BASELINE_LIMITATIONS,
    BASELINE_STAGES,
    GENERIC_SCALE_CONTAINERS,
    ScaleBaselineMetrics,
    ScaleBaselineReport,
    ScaleCorpus,
    ScaleCorpusFile,
    ScaleCorpusSpec,
    ScaleHardware,
    duplicate_indexes,
    record_payload,
)

__all__ = [
    "BASELINE_LIMITATIONS",
    "BASELINE_STAGES",
    "GENERIC_SCALE_CONTAINERS",
    "ScaleBaselineMetrics",
    "ScaleBaselineReport",
    "ScaleCorpus",
    "ScaleCorpusFile",
    "ScaleCorpusSpec",
    "ScaleHardware",
    "ci_tiny_specs",
    "compile_document_corpus",
    "duplicate_indexes",
    "materialize_scale_corpus",
    "measurement_ladder_specs",
    "packaged_scale_specs",
    "record_payload",
    "record_scale_hardware",
    "render_text_pdf",
    "request_scale_cancellation",
    "run_named_tiny_baseline",
    "run_scale_baseline",
    "spec_by_corpus_id",
]
