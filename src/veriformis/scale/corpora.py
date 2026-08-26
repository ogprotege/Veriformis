"""Deterministic materialization of scale-corpus specs."""

from __future__ import annotations

from pathlib import Path

from veriformis.errors import ScaleError
from veriformis.identity import sha256_digest
from veriformis.scale.models import (
    ScaleCorpus,
    ScaleCorpusFile,
    ScaleCorpusSpec,
    duplicate_indexes,
    encode_record,
    record_payload,
)


def render_text_pdf(pages: tuple[str, ...]) -> bytes:
    """Render a deterministic latin-1 text PDF with one line per page."""
    if not pages:
        raise ScaleError("PDF must contain at least one page")
    encoded_pages: list[bytes] = []
    for page in pages:
        try:
            encoded_pages.append(page.encode("latin-1"))
        except UnicodeEncodeError as exc:
            raise ScaleError("PDF page text must be latin-1") from exc

    n = len(pages)
    font_id = 3 + (2 * n)
    catalog = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{4 + (2 * index)} 0 R" for index in range(n))
    pages_obj = f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode("ascii")
    bodies: list[bytes] = [catalog, pages_obj]
    for index, raw in enumerate(encoded_pages):
        escaped = (
            raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
        )
        stream = b"BT /F1 12 Tf 72 720 Td (" + escaped + b") Tj ET"
        content = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
        )
        page = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {3 + (2 * index)} 0 R /Resources << /Font << "
            f"/F1 {font_id} 0 R >> >> >>"
        ).encode("ascii")
        bodies.append(content)
        bodies.append(page)
    bodies.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(bodies, start=1):
        offsets.append(len(out))
        out.extend(f"{index} 0 obj\n".encode("ascii"))
        out.extend(body)
        out.extend(b"\nendobj\n")
    xref_at = len(out)
    out.extend(f"xref\n0 {len(bodies) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    out.extend(
        (
            f"trailer << /Size {len(bodies) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_at}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(out)


def _split_counts(record_count: int, file_count: int) -> tuple[int, ...]:
    base, extra = divmod(record_count, file_count)
    counts = [base] * file_count
    for index in range(extra):
        counts[index] += 1
    if any(count < 1 for count in counts):
        raise ScaleError("every corpus file must contain at least one record")
    return tuple(counts)


def _records(spec: ScaleCorpusSpec) -> tuple[str, ...]:
    copies = duplicate_indexes(
        record_count=spec.record_count,
        duplicate_rate_ppm=spec.duplicate_rate_ppm,
    )
    payloads: list[str] = []
    first = record_payload(seed=spec.seed, index=0, row_length=spec.row_length)
    for index in range(spec.record_count):
        payload = (
            first
            if index in copies
            else record_payload(seed=spec.seed, index=index, row_length=spec.row_length)
        )
        payloads.append(payload)
    return tuple(payloads)


def _file_bytes(spec: ScaleCorpusSpec, records: tuple[str, ...]) -> bytes:
    if spec.input_mode == "dataset-row":
        lines = tuple(encode_record(spec=spec, payload=item) for item in records)
        return ("\n".join(lines) + "\n").encode("utf-8")
    if spec.pdf_pages > 0:
        return render_text_pdf(records)
    paragraphs = "\n\n".join(records)
    return f"# {spec.corpus_id}\n\n{paragraphs}\n".encode("utf-8")


def _file_name(spec: ScaleCorpusSpec, index: int) -> str:
    stem = f"{spec.corpus_id}-{index:04d}"
    if spec.input_mode == "dataset-row":
        return f"{stem}.jsonl"
    if spec.pdf_pages > 0:
        return f"{stem}.pdf"
    return f"{stem}.md"


def ci_tiny_specs() -> tuple[ScaleCorpusSpec, ...]:
    """Tiny CI specs covering the roadmap corpus dimensions."""
    return (
        ScaleCorpusSpec.create(
            corpus_id="ci-tiny-markdown",
            input_mode="document-source",
            file_count=2,
            record_count=4,
            row_length=48,
            nesting_depth=0,
            pdf_pages=0,
            duplicate_rate_ppm=0,
            container="split-jsonl-directory",
            seed="ci-tiny-markdown",
        ),
        ScaleCorpusSpec.create(
            corpus_id="ci-tiny-jsonl",
            input_mode="dataset-row",
            file_count=2,
            record_count=4,
            row_length=40,
            nesting_depth=0,
            pdf_pages=0,
            duplicate_rate_ppm=0,
            container="json",
            seed="ci-tiny-jsonl",
        ),
        ScaleCorpusSpec.create(
            corpus_id="ci-tiny-nested",
            input_mode="dataset-row",
            file_count=1,
            record_count=2,
            row_length=24,
            nesting_depth=2,
            pdf_pages=0,
            duplicate_rate_ppm=0,
            container="split-jsonl-directory",
            seed="ci-tiny-nested",
        ),
        ScaleCorpusSpec.create(
            corpus_id="ci-tiny-pdf",
            input_mode="document-source",
            file_count=1,
            record_count=2,
            row_length=16,
            nesting_depth=0,
            pdf_pages=2,
            duplicate_rate_ppm=0,
            container="parquet",
            seed="ci-tiny-pdf",
        ),
        ScaleCorpusSpec.create(
            corpus_id="ci-tiny-duplicates",
            input_mode="document-source",
            file_count=2,
            record_count=4,
            row_length=32,
            nesting_depth=0,
            pdf_pages=0,
            duplicate_rate_ppm=500000,
            container="constrained-csv",
            seed="ci-tiny-duplicates",
        ),
    )


def spec_by_corpus_id(corpus_id: str) -> ScaleCorpusSpec:
    """Return one packaged tiny spec. Unknown ids fail closed."""
    for spec in ci_tiny_specs():
        if spec.corpus_id == corpus_id:
            return spec
    raise ScaleError(f"unknown scale corpus id {corpus_id!r}")


def materialize_scale_corpus(spec: ScaleCorpusSpec, destination: Path) -> ScaleCorpus:
    """Write the spec into an empty directory and return the measured corpus."""
    dest = destination.expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    if any(dest.iterdir()):
        raise ScaleError("scale corpus destination must be empty")
    payloads = _records(spec)
    counts = _split_counts(spec.record_count, spec.file_count)
    cursor = 0
    files: list[ScaleCorpusFile] = []
    for index, count in enumerate(counts):
        chunk = payloads[cursor : cursor + count]
        cursor += count
        name = _file_name(spec, index)
        data = _file_bytes(spec, chunk)
        path = dest / name
        path.write_bytes(data)
        files.append(
            ScaleCorpusFile(
                path=name,
                digest=sha256_digest(data),
                size=len(data),
            )
        )
    ordered = tuple(sorted(files, key=lambda item: item.path))
    total = sum(item.size for item in ordered)
    return ScaleCorpus.create(spec=spec, files=ordered, total_bytes=total)
