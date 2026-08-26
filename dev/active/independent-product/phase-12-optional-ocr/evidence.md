# Phase 12 Evidence

**Status:** Complete — Phase 12 closeout PR #112 at
`892939f527974b69282296ded04eb3b43643554f`

**Opened:** 2026-08-25

## Predecessor evidence

Phase 11 completed. Items 11.1–11.8 merged as PR #104 at
`e856af96043c9876affa275b5246e83541254d9d`.

Operator compile of Pius X *Pascendi Dominici Gregis* at
`/Users/biscuit/Documents/Veriformis` (`2026-08-24T13-54-52Z`): `full_text`
/`text`, 31 train / 0 evaluation, manifest
`94b63232166aeedc9db797fdc0ec0167b2135d8c01bd3934635250a0a2245ace`. Seal
`self_consistent`; zip `external_digest`. Recorded in
[operator-compile-2026-08-24-pascendi.md](../operator-compile-2026-08-24-pascendi.md).

## Source-verified starting facts

| Fact | Grade | Source |
| --- | --- | --- |
| `ocr-image` is explicitly unsupported | `source-verified` | `src/veriformis/taxonomy.py` |
| Empty-text PDF refuses with `pdf.ocr-required` and `ocr-unsupported` | `source-verified` | `src/veriformis/parsers/pdf.py` |
| Digitally born PDF extracts the text layer via pypdfium2 | `source-verified` | `src/veriformis/parsers/pdf.py` |
| Extra `ocr` is declared empty | `source-verified` | `pyproject.toml` |
| Collection ingest does not change suffix dispatch | `source-verified` | Phase 11 closeout; ADR-0015 |

## Required item 12.1 evidence

- [x] Packet opened; Phase 12 `in_progress`; Phase 11 merge cited.
- [x] `ocr-image` remains explicitly unsupported and is absent from
      implemented discovery.
- [x] Empty-text PDF still refuses; digitally born PDF still extracts text.
- [x] No `ocr` extra; lock extras list unchanged; OCR engine packages absent
      from the lock.
- [x] Core parse does not import OCR libraries.
- [x] Focused isolation tests, tracking, Ruff, lock, and diff check.

## Required item 12.2 evidence

- [x] Retained license-safe corpus under `tests/fixtures/phase12/ocr-eval/`.
- [x] Languages, scan rasters, mixed PDF, rotation, table, degraded noise,
      handwriting exclusion, and CJK desk-note.
- [x] Tesseract 5.5.3 measured: CER, runtime, RSS, tessdata sizes, OSD probe.
- [x] Desk comparison of RapidOCR, PaddleOCR, EasyOCR, docTR, Surya, Apple
      Vision, OCRmyPDF, and cloud OCR.
- [x] Image-only corpus PDFs still refuse; mixed PDF keeps digital text.
- [x] No `ocr` extra; `ocr-image` still explicitly unsupported.
- [x] Operator accepted Tesseract 5.
- [x] Repository fixture inventory in `docs/governance/corpus-demand-matrix.json`
      updated for the retained corpus.

## Required item 12.3 evidence

- [x] ADR-0016 accepted: optional local Tesseract 5.
- [x] `veriformis.ocr-recovery-identity/v1` names engine, tessdata, page,
      raster, preprocess, boxes, confidence, and limitations.
- [x] Pin `executable=false`; `require_ocr_recovery_not_executable` fails closed.
- [x] Unknown language, PSM, preprocess, and digest fail closed.
- [x] `ocr-image` still unsupported; no `ocr` extra; empty-text PDF still
      refuses; identity import does not load Tesseract.

## Required item 12.4 evidence

- [x] Pages classify as digital, ocr, or a merged document.
- [x] OCR provider is never called for a digital page.
- [x] A request carrying digital text fails closed.
- [x] Mixed PDF keeps digital text; with a test provider, empty pages recover
      as OCR without replacing digital text.
- [x] Image-only PDF without a provider still refuses.

## Required item 12.5 evidence

- [x] Confidence policy v1: accept / warn / review / refuse.
- [x] Refused OCR text is omitted from the stream and retained on
      `held_text`. Digital pages are not scored.

## Required item 12.6 evidence

- [x] Read-only `ocr-preview` on PipelineService, CLI, and MCP.
- [x] Pending review is a page flag. Sources are not mutated.

## Required item 12.7 evidence

- [x] Extra `ocr = []`. Core install does not import an OCR wheel.
- [x] `TesseractProvider` recovers empty pages through a local subprocess
      when a caller supplies it.

## Required item 12.8 evidence

- [x] Missing tessdata, missing binary, corrupt raster, identity replay,
      and no-network Tesseract recovery.
- [x] Default parse still refuses image-only PDF. `ocr-image` stays
      explicitly unsupported. Phase 12 closeout. Do not start Phase 13.

## Local gates (2026-08-25)

Item 12.1: focused isolation 47 passed; core pytest 2117 passed, 16
deselected, 1 expected durability warning.

Item 12.2: `uv lock --check`; `ruff check src tests scripts`; tracking
PASS; focused Phase 12 and corpus-matrix tests passed; core pytest 2122
passed then 1 corpus-matrix miss, fixed by updating the fixture
inventory; `git diff --check` clean.

Item 12.3: `uv lock --check`; `ruff check src tests`; tracking PASS;
focused OCR/parser/taxonomy/tracking 37 passed; core pytest 2131 passed,
16 deselected, 1 expected durability warning; `git diff --check` clean.

Item 12.8 closeout: core pytest 2156 passed, 16 deselected, 1 expected
durability warning. Closeout merged as PR #112 at
`892939f527974b69282296ded04eb3b43643554f` after GitHub checks passed.
