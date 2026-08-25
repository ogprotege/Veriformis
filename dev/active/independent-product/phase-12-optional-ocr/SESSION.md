# Phase 12 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-25

**Local branch:** `phase12/04-recovery-paths` from
`phase12/03-ocr-adr-identities`.

**Predecessor:** Item 12.3 (PR #107).

**Completed:** 12.1–12.3. Operator accepted Tesseract 5.

**Current item:** 12.4 Distinguish digital, OCR, and merged recovery

**Not started:** 12.5–12.8. Do not start Phase 13 from this packet.

**12.4 design:** Classify pages. Never OCR digital text. Provider is
opt-in; default parse still refuses image-only PDFs.
