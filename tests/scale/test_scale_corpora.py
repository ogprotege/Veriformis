"""Phase 15.2: deterministic scale-corpus generators."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from veriformis.contracts import (
    SCALE_CORPUS_SCHEMA_ID,
    SCALE_CORPUS_SPEC_SCHEMA_ID,
)
from veriformis.errors import ScaleError
from veriformis.scale import (
    GENERIC_SCALE_CONTAINERS,
    ScaleCorpusSpec,
    ci_tiny_specs,
    materialize_scale_corpus,
    record_payload,
    render_text_pdf,
)


def _markdown_spec(**overrides: object) -> ScaleCorpusSpec:
    payload = {
        "corpus_id": "ci-unit-markdown",
        "input_mode": "document-source",
        "file_count": 2,
        "record_count": 4,
        "row_length": 32,
        "nesting_depth": 0,
        "pdf_pages": 0,
        "duplicate_rate_ppm": 0,
        "container": "split-jsonl-directory",
        "seed": "unit-markdown",
    }
    payload.update(overrides)
    return ScaleCorpusSpec.create(**payload)  # type: ignore[arg-type]


def test_named_seed_replays_the_same_bytes(tmp_path: Path) -> None:
    spec = _markdown_spec()
    first = materialize_scale_corpus(spec, tmp_path / "a")
    second = materialize_scale_corpus(spec, tmp_path / "b")
    assert first == second
    assert first.spec_id == spec.spec_id
    assert first.schema_id == SCALE_CORPUS_SCHEMA_ID
    assert spec.schema_id == SCALE_CORPUS_SPEC_SCHEMA_ID
    for item in first.files:
        left = (tmp_path / "a" / item.path).read_bytes()
        right = (tmp_path / "b" / item.path).read_bytes()
        assert left == right
        assert item.size == len(left)


def test_different_seeds_change_bytes(tmp_path: Path) -> None:
    first = materialize_scale_corpus(_markdown_spec(), tmp_path / "a")
    second = materialize_scale_corpus(
        _markdown_spec(seed="unit-markdown-b"),
        tmp_path / "b",
    )
    assert first.corpus_id != second.corpus_id
    assert (tmp_path / "a" / first.files[0].path).read_bytes() != (
        tmp_path / "b" / second.files[0].path
    ).read_bytes()


def test_unicode_payload_is_exact() -> None:
    payload = record_payload(seed="unit-unicode", index=0, row_length=8)
    assert "café" in payload or payload.startswith("café") or "é" in payload
    assert len(payload) == 8
    assert payload.encode("utf-8")


def test_jsonl_and_markdown_preserve_unicode(tmp_path: Path) -> None:
    markdown = materialize_scale_corpus(_markdown_spec(), tmp_path / "md")
    text = (tmp_path / "md" / markdown.files[0].path).read_text(encoding="utf-8")
    assert "café" in text
    spec = ScaleCorpusSpec.create(
        corpus_id="ci-unit-jsonl",
        input_mode="dataset-row",
        file_count=1,
        record_count=2,
        row_length=24,
        nesting_depth=0,
        pdf_pages=0,
        duplicate_rate_ppm=0,
        container="json",
        seed="unit-jsonl",
    )
    corpus = materialize_scale_corpus(spec, tmp_path / "jsonl")
    line = (tmp_path / "jsonl" / corpus.files[0].path).read_text(encoding="utf-8").splitlines()[0]
    row = json.loads(line)
    assert "café" in row["text"]


def test_nested_jsonl_has_requested_depth(tmp_path: Path) -> None:
    spec = ScaleCorpusSpec.create(
        corpus_id="ci-unit-nested",
        input_mode="dataset-row",
        file_count=1,
        record_count=1,
        row_length=16,
        nesting_depth=3,
        pdf_pages=0,
        duplicate_rate_ppm=0,
        container="split-jsonl-directory",
        seed="unit-nested",
    )
    corpus = materialize_scale_corpus(spec, tmp_path)
    row = json.loads((tmp_path / corpus.files[0].path).read_text(encoding="utf-8").splitlines()[0])
    assert len(row["messages"]) == 3
    assert row["messages"][0]["role"] == "system"


def test_pdf_page_count_matches_spec(tmp_path: Path) -> None:
    spec = ScaleCorpusSpec.create(
        corpus_id="ci-unit-pdf",
        input_mode="document-source",
        file_count=1,
        record_count=3,
        row_length=12,
        nesting_depth=0,
        pdf_pages=3,
        duplicate_rate_ppm=0,
        container="parquet",
        seed="unit-pdf",
    )
    corpus = materialize_scale_corpus(spec, tmp_path)
    payload = (tmp_path / corpus.files[0].path).read_bytes()
    assert payload.startswith(b"%PDF-1.4")
    assert payload.count(b"/Type /Page ") == 3
    replay = render_text_pdf(("page-a", "page-b"))
    assert replay == render_text_pdf(("page-a", "page-b"))
    assert replay != render_text_pdf(("page-b", "page-a"))


def test_duplicate_rate_copies_later_records(tmp_path: Path) -> None:
    spec = _markdown_spec(duplicate_rate_ppm=500000)
    corpus = materialize_scale_corpus(spec, tmp_path)
    text = "\n".join(
        (tmp_path / item.path).read_text(encoding="utf-8") for item in corpus.files
    )
    first = record_payload(seed=spec.seed, index=0, row_length=spec.row_length)
    assert text.count(first) == 3


def test_ci_tiny_specs_cover_roadmap_dimensions(tmp_path: Path) -> None:
    specs = ci_tiny_specs()
    assert {item.corpus_id for item in specs} == {
        "ci-tiny-duplicates",
        "ci-tiny-jsonl",
        "ci-tiny-markdown",
        "ci-tiny-nested",
        "ci-tiny-pdf",
    }
    modes = {item.input_mode for item in specs}
    assert modes == {"dataset-row", "document-source"}
    assert any(item.pdf_pages > 0 for item in specs)
    assert any(item.nesting_depth > 0 for item in specs)
    assert any(item.duplicate_rate_ppm > 0 for item in specs)
    assert set(item.container for item in specs) <= set(GENERIC_SCALE_CONTAINERS)
    for spec in specs:
        dest = tmp_path / spec.corpus_id
        corpus = materialize_scale_corpus(spec, dest)
        assert corpus.file_count == spec.file_count
        assert corpus.total_bytes == sum(
            (dest / item.path).stat().st_size for item in corpus.files
        )


def test_invalid_specs_fail_closed() -> None:
    with pytest.raises((ScaleError, ValidationError)):
        _markdown_spec(file_count=0)
    with pytest.raises((ScaleError, ValidationError)):
        _markdown_spec(record_count=1, file_count=2)
    with pytest.raises((ScaleError, ValidationError)):
        _markdown_spec(duplicate_rate_ppm=1000001)
    with pytest.raises((ScaleError, ValidationError)):
        _markdown_spec(seed="Unit Seed")
    with pytest.raises((ScaleError, ValidationError)):
        _markdown_spec(container="minimal-v1")
    with pytest.raises((ScaleError, ValidationError)):
        ScaleCorpusSpec.create(
            corpus_id="ci-bad-csv",
            input_mode="dataset-row",
            file_count=1,
            record_count=1,
            row_length=8,
            nesting_depth=1,
            pdf_pages=0,
            duplicate_rate_ppm=0,
            container="constrained-csv",
            seed="unit-bad-csv",
        )
    with pytest.raises((ScaleError, ValidationError)):
        ScaleCorpusSpec.create(
            corpus_id="ci-bad-pdf",
            input_mode="dataset-row",
            file_count=1,
            record_count=1,
            row_length=8,
            nesting_depth=0,
            pdf_pages=1,
            duplicate_rate_ppm=0,
            container="json",
            seed="unit-bad-pdf",
        )


def test_non_empty_destination_fails_closed(tmp_path: Path) -> None:
    dest = tmp_path / "used"
    dest.mkdir()
    (dest / "stale.txt").write_text("no", encoding="utf-8")
    with pytest.raises(ScaleError, match="empty"):
        materialize_scale_corpus(_markdown_spec(), dest)


def test_generic_scale_containers_exclude_bundle_profiles() -> None:
    assert "split-jsonl-directory" in GENERIC_SCALE_CONTAINERS
    assert "json" in GENERIC_SCALE_CONTAINERS
    assert "minimal-v1" not in GENERIC_SCALE_CONTAINERS
    assert "deterministic-vfbundle-zip-v1" not in GENERIC_SCALE_CONTAINERS
