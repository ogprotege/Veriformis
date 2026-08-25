# Phase 12.2 OCR Engine Evaluation

**Status:** Recorded 2026-08-25. Operator accepted Tesseract 5.

**Does not change product behavior.** `ocr-image` remains
`explicitly_unsupported`. There is no `ocr` extra. Image-only PDFs still
refuse.

## What was measured

A retained, license-safe corpus lives at
`tests/fixtures/phase12/ocr-eval/`. Pages are original Veriformis fixture
text, not third-party scans. Helvetica (PDF standard-14) is the only font.
Rasters come from pinned `pypdfium2` 5.12.1 at 200 dpi. Rebuild:

```bash
uv run python scripts/phase12_ocr_eval.py build
uv run python scripts/phase12_ocr_eval.py measure
```

Coverage against the roadmap list:

| Roadmap item | Corpus case | Result |
| --- | --- | --- |
| Languages | `clean-en`, `fra-accents`, `lat-print` | Tesseract CER 0.00 after whitespace/accent normalization |
| Scans | rasters of the text-layer PDFs | Same as clean-print; these are rendered pages, not camera photos |
| Mixed text/images | `mixed-en.text.pdf` | Veriformis extracts page-1 digital text and warns `pdf.empty-text-pages`; it does not refuse the whole document |
| Rotation | `rotated-en` | Default Tesseract PSM 6 CER 1.70 (unusable). OSD reports 90° / rotate 270° at low confidence (3.35) |
| Tables | `table-en` | Tesseract CER 0.00 on this three-row aligned table |
| Handwriting | excluded | Roadmap non-goal; no sample retained |
| Degraded pages | `degraded-en` | Deterministic 1.6% pixel noise; Tesseract CER 0.1148 |
| CJK | not rasterized | Standard-14 Helvetica has no CJK glyphs; language-pack facts are desk-evaluated only |

Image-only PDFs of every raster refuse with `pdf.ocr-required` /
`ocr-unsupported`. Digitally born text PDFs still extract the text layer.

Machine: macOS 26.6.2 arm64. Tesseract 5.5.3 (Homebrew), `eng.traineddata`
4 113 088 bytes, `fra` 1 130 365, `lat` 3 187 463. Peak resident set about
40–55 MiB. Wall time 0.06–0.10 s per page. No sockets opened by the
evaluation script. Numeric rows are in
[evaluation-results.json](evaluation-results.json).

## Engine comparison

| Engine | License | Offline after install | Linux + macOS | CPU-only | Deterministic pin | First-run network | Model / install size | Measured on this corpus |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Tesseract 5 | Apache-2.0 | Yes, local tessdata | Yes | Yes | Yes, if binary + traineddata are pinned | No | ~4 MiB `eng`; language packs extra | Yes |
| OCRmyPDF | MPL-2.0 | Wrapper around Tesseract | Yes | Yes | Same as Tesseract | Not a recognizer | Wrapper | Present locally 17.10.0; not used as a parser |
| RapidOCR 3.9.2 | Apache-2.0 | If ONNX weights are vendored | Yes | Yes | Medium | `requests` is a runtime dependency | Wheel ~27 MiB plus ONNX | Desk only |
| PaddleOCR | Apache-2.0 | After models are present | Yes | Optional GPU | Medium | Commonly fetches models | ~150–500 MiB | Desk only |
| EasyOCR | Apache-2.0 | After models are present | Yes | Optional GPU | Medium | Downloads PyTorch weights | ~0.5–1.5 GiB | Desk only |
| docTR | Apache-2.0 | After models are present | Yes | Optional GPU | Medium | Downloads | ~400 MiB | Desk only |
| Surya | Code Apache-2.0; weights modified Open RAIL-M with a $5 M funding/revenue cap and a paid commercial path | After weights | GPU preferred | No as a product default | Weight license is not a clean MIT companion | Downloads | ~650 M params | Desk only |
| Apple Vision / ocrmac | Apple system | macOS only | No | Yes | Not portable to Linux CI | No | 0 extra | Desk only |
| Cloud OCR | Proprietary | No | N/A | N/A | No | Yes | N/A | Excluded (roadmap non-goal) |

## Hard gates for an optional Veriformis extra

An admitted engine must:

1. Be locally runnable with no network during parse.
2. Carry a license that can sit beside Veriformis MIT without a revenue cap
   on the weights.
3. Run on Linux CI and macOS.
4. Be pinnable (engine, model, language, version).
5. Stay out of the core extra until item 12.7.
6. Never silently replace a recoverable digital text layer.
7. Treat handwriting as unsupported or explicitly limited.

Tesseract 5 is the only candidate that met every hard gate and that was
measured on the retained corpus. Rotation fails unless orientation is an
**explicit** preprocess (OSD detected 90° here; default recognition did
not). Degraded pages keep most of the sentence with extra glyphs.
Three-row tables succeeded; that is not a general table claim.

Surya weights fail the license gate. Cloud OCR fails the offline gate.
Apple Vision fails Linux. PaddleOCR, EasyOCR, RapidOCR, and docTR remain
possible later seconds only if models are vendored with a no-network pin
and a later corpus that Tesseract cannot meet (CJK, camera photos, dense
layout). They were not measured here and must not be implied implemented.

## Operator decision (12.2 exit)

Recorded 2026-08-25: the operator chose **1. Accept Tesseract 5**.

ADR-0016 and item 12.3 pin identities. Digital text stays first. Rotation
is an explicit preprocess. Handwriting stays excluded. The `ocr` extra
waits for 12.7. Thresholds remain item 12.5.
