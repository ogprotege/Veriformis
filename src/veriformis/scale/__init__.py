"""Scale-corpus generators. No published tiers or streaming APIs."""

from veriformis.scale.corpora import ci_tiny_specs, materialize_scale_corpus, render_text_pdf
from veriformis.scale.models import (
    GENERIC_SCALE_CONTAINERS,
    ScaleCorpus,
    ScaleCorpusFile,
    ScaleCorpusSpec,
    duplicate_indexes,
    record_payload,
)

__all__ = [
    "GENERIC_SCALE_CONTAINERS",
    "ScaleCorpus",
    "ScaleCorpusFile",
    "ScaleCorpusSpec",
    "ci_tiny_specs",
    "duplicate_indexes",
    "materialize_scale_corpus",
    "record_payload",
    "render_text_pdf",
]
