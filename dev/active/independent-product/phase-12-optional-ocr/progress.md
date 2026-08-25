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
