# ADR-0016 — Optional Local Tesseract 5 OCR

**Status:** Accepted

**Date:** 2026-08-25

**Decider:** Operator instruction after Phase 12.2 evaluation: accept Tesseract 5

## Context and evidence

Image-only and empty-text PDFs refuse with `pdf.ocr-required` /
`ocr-unsupported`. `ocr-image` is `explicitly_unsupported` (ADR-0008).
Phase 12.2 compared local engines on a retained, license-safe corpus
(`tests/fixtures/phase12/ocr-eval/`) and recorded Tesseract 5.5.3
measurements in the Phase 12 packet.

Hard gates: local, offline, no network during parse, license compatible
with Veriformis MIT, Linux and macOS, CPU, pinnable engine/model/language/
version. Tesseract 5 (Apache-2.0) met those gates. Surya weights fail the
license gate. Cloud OCR is a roadmap non-goal. Other neural engines were
not measured as product engines.

## Decision

1. The optional OCR engine is Tesseract 5. Identities are
   `veriformis.ocr-recovery-identity/v1`. The engine binary and tessdata
   files are not core install. Extra `ocr` waits for item 12.7.
2. Digital text is authoritative. OCR MUST NOT silently replace a
   recoverable text layer. Distinguishing digital, OCR, and merged recovery
   is item 12.4. Until that item, image-only PDF still refuses.
3. `ocr-image` stays `explicitly_unsupported` until a later item emits
   recovery. This ADR authorizes Tesseract; it does not promote the family.
4. Rotation is an explicit preprocess (`osd-rotate/v1`). Default recognition
   without that preprocess is not a supported path. Handwriting is
   unsupported. Cloud OCR is forbidden. Parse MUST NOT open a network
   socket.
5. Admitted languages in v1 are those measured in 12.2: `eng`, `fra`,
   `lat`. Other tessdata packs fail closed until a later pin. Recognition
   PSM is `6`. Tessdata bytes are part of page identity (SHA-256).
6. Every OCR character later emitted MUST bind engine, engine version,
   language, tessdata digest, page index, raster digest, preprocess list,
   and coordinates. Confidence fields exist; thresholds are item 12.5.

## Consequences

- Core pytest and core install still do not import Tesseract.
- A later extra cannot become a core release dependency without a new ADR.
- Promoting `ocr-image` still requires a support-registry change in the
  same pull request that makes recovery executable.

## Alternatives considered

- Deferring Phase 12: rejected by the operator after 12.2.
- Admitting PaddleOCR, EasyOCR, RapidOCR, or Surya: rejected; license,
  download, or unmeasured.
- Silent OSD rotation: rejected; 12.2 default PSM failed the rotated page.
- Promoting `ocr-image` in this item: rejected; identities land before
  recovery.

## Verification

Item 12.3 publishes this ADR, the identity contract, and the Tesseract 5
pin with `executable=false`. Image-only PDF still refuses. Items 12.4–12.8
add recovery paths, thresholds, review hooks, the extra, and the
no-network harness.

## Review triggers

Any new OCR engine; tessdata or language admission; promoting `ocr-image`;
declaring extra `ocr`; silent replacement of digital text; network during
parse; handwriting support claims.
