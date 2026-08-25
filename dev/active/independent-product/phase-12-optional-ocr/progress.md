# Phase 12 Progress

Append-only. Corrections add a later entry.

## 2026-08-25 — Phase 12 opened; item 12.1 in progress

**Status:** Packet created from clean `main` at
`e856af96043c9876affa275b5246e83541254d9d` (PR #104).

Item 12.1 opens the packet. `ocr-image` remains explicitly unsupported.
Empty-text PDF still refuses with `pdf.ocr-required` / `ocr-unsupported`.
There is no `ocr` extra. Operator instruction 2026-08-25: sequential PRs
now that the repository is public; implement 12.1 then 12.2 and stop for
the operator to check the evaluation before any OCR ADR.

**Next action:** Publish the item 12.1 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 12.2.

## 2026-08-25 — Item 12.1 local gates green

**Status:** Packet, tracking, and OCR-isolation tests are on
`phase12/01-ocr-packet`.

Local gates: `uv lock --check`; `ruff check src tests`;
`scripts/check_project_tracking.py` PASS; focused isolation 47 passed;
core pytest 2117 passed, 16 deselected, 1 expected durability warning;
`git diff --check` clean.

**Next action:** Open the item 12.1 pull request. Require every GitHub
check, merge, and synchronize clean main before item 12.2.

## 2026-08-25 — Item 12.2 evaluation recorded

**Status:** License-safe corpus, Tesseract 5.5.3 measurements, and the
engine comparison are on `phase12/02-ocr-engine-evaluation`.

Tesseract CER 0.00 on clean English, French, Latin, and the three-row
table. Degraded noise CER 0.1148. Default recognition of a 90° page
fails (CER 1.70); OSD reports the rotation. Image-only corpus PDFs
still refuse. Mixed digital/empty PDF keeps digital text. No `ocr`
extra. Surya weights fail the license gate. Cloud OCR remains excluded.

**Next action:** Open the item 12.2 pull request. Stop for the operator
to accept an OCR ADR, defer the phase, or request more evaluation. Do
not start items 12.3–12.8.

## 2026-08-25 — Operator accepted Tesseract 5; item 12.3 in progress

**Status:** Operator instruction after 12.2: accept Tesseract 5.

Item 12.3 publishes ADR-0016 and `veriformis.ocr-recovery-identity/v1`.
The pin names Tesseract 5, measured languages `eng`/`fra`/`lat`, PSM 6,
explicit `osd-rotate/v1`, and `executable=false`. Image-only PDF still
refuses. There is no `ocr` extra.

**Next action:** Publish the item 12.3 pull request. Do not start item
12.4 until it merges.

## 2026-08-25 — Item 12.3 local gates green

**Status:** ADR-0016, identity pin, and tests are on
`phase12/03-ocr-adr-identities`.

Local gates: `uv lock --check`; `ruff check src tests`; tracking PASS;
focused OCR/parser/taxonomy/tracking 37 passed; core pytest 2131 passed,
16 deselected, 1 expected durability warning; `git diff --check` clean.

**Next action:** Open the item 12.3 pull request. Require every GitHub
check. Do not start item 12.4 until it merges.

## 2026-08-25 — Item 12.4 recovery paths

**Status:** Digital, OCR, and merged classification is on
`phase12/04-recovery-paths`.

Pages with a text layer stay digital and are never sent to an OCR
provider. Empty pages are `ocr`. Mixed documents are `merged`. Default
parse still refuses image-only PDFs. A test provider can recover empty
pages without replacing digital text.

**Next action:** Open the item 12.4 pull request after #107 merges.

## 2026-08-25 — Item 12.4 local gates green

**Status:** Recovery-path classification is on `phase12/04-recovery-paths`.

Local gates: tracking PASS; ruff pass; focused OCR/PDF 73 passed earlier,
then 27 after tracking edits; core pytest 2139 passed, 16 deselected, 1
expected durability warning.

**Next action:** Merge #107, then open the item 12.4 pull request.

## 2026-08-25 — Item 12.5 confidence thresholds

**Status:** Warn / review / refuse policy is on
`phase12/05-confidence-thresholds`. Refused OCR text is omitted from the
stream and retained on `held_text`.

**Next action:** Open the item 12.5 pull request after #108 merges.

## 2026-08-25 — Item 12.6 preview and review hooks

**Status:** `ocr-preview` is on PipelineService, CLI, and MCP.
Pending review is a page flag. Sources are not mutated.

**Next action:** Open the item 12.6 pull request after #109 (12.5) merges.

## 2026-08-25 — Item 12.7 OCR extra

**Status:** Extra `ocr = []`. `TesseractProvider` uses a local tesseract
binary. Core tests skip when tesseract is absent.

**Next action:** Open the item 12.7 pull request after 12.6 merges.

## 2026-08-25 — Item 12.8 harness and closeout

**Status:** No-network, missing tessdata, corrupt raster, and identity
replay tests. Packet closeout. Phase 12 completed. Do not start Phase 13.
