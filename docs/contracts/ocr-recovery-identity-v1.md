# OCR Recovery Identity Contract v1

**Contract ID:** `veriformis.ocr-recovery-identity`

**Contract version:** `1`

**Schema:** `veriformis.ocr-recovery-identity/v1`

**Status:** Identity pin through independent-product Phase 12.3. Recovery is
not executable. Image-only PDF still refuses.

**Last reviewed:** 2026-08-25

**Authority:** [ADR-0016](../adr/0016-optional-local-tesseract-ocr.md)

## Purpose

Name the optional OCR engine, tessdata, page/image digests, coordinates,
confidence, and preprocess transforms so a later recovery path can bind
every emitted character. This contract does not recover text.

## Engine pin

| Field | v1 value |
| --- | --- |
| `engine_id` | `tesseract` |
| `engine_family` | `tesseract-5` |
| `license` | Apache-2.0 |
| `min_version` | `5.0.0` |
| `measured_version` | `5.5.3` (Phase 12.2) |
| `admitted_languages` | `eng`, `fra`, `lat` |
| `admitted_psm` | `6` |
| `executable` | `false` |
| `extra` | `ocr` |
| `extra_declared` | `false` |

Tessdata files are identity. A later parse records the SHA-256 of the
exact `*.traineddata` bytes used, not a floating distro path.

## Page identity

One OCR page record contains:

| Field | Meaning |
| --- | --- |
| `source_sha256` | Raw source file digest |
| `page_index` | 1-based page number |
| `raster_sha256` | Exact bytes fed to Tesseract |
| `tessdata_language` | One admitted language |
| `tessdata_sha256` | Exact traineddata digest |
| `engine_id` / `engine_version` | Runtime Tesseract |
| `psm` | Admitted page segmentation mode |
| `preprocess` | Ordered named transforms |
| `boxes` | Page-space rectangles with an explicit unit |
| `confidence` | Optional mean, minimum, word count on 0..100 |
| `recovery_path` | `ocr` for Tesseract-recovered pages |

Page identity id is `derive_id("ocr-page", …)`. Recovered text is not in
the identity preimage.

## Recovery paths (item 12.4)

| Path | Meaning |
| --- | --- |
| `digital` | Page exposed an extractable text layer. That text is the recovery. |
| `ocr` | Page exposed no text layer. OCR may recover it; without a provider it stays empty. |
| `merged` | Document has both digital and OCR pages. |

OCR is never invoked for a digital page. A provider request that carries
digital text fails closed. Default parse still has no provider: image-only
PDFs refuse; mixed PDFs keep digital text and omit empty pages.

## Preprocess identifiers

| ID | Meaning |
| --- | --- |
| `render-pdf-page/v1` | Rasterize one PDF page with pinned pypdfium2 |
| `osd-rotate/v1` | Explicit orientation then rotate; never silent |

Unknown transform ids fail closed. Parameter object keys are sorted.

## Bounding boxes

`unit` is `pdf-point` or `raster-pixel`. `page_index` is 1-based.
`(x0, y0)` is the origin corner; `(x1, y1)` must not precede it.

## Limitations

`handwriting-unsupported`, `cloud-ocr-forbidden`, `no-network`,
`rotation-requires-explicit-preprocess`, `ocr-recovery-not-executable`.

## Non-goals

Running Tesseract in production parse. Promoting `ocr-image`. Declaring
extra `ocr`. Confidence thresholds (item 12.5). Page preview UI (item
12.6). Handwriting. Cloud OCR. Silent replacement of digital text.
