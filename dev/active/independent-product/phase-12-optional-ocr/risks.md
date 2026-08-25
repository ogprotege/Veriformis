# Phase 12 Risk Register

**Status:** Open

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P12-R1 | Controlled for 12.1 | High | High | Discovery or docs imply OCR support before an ADR | Taxonomy stays `explicitly_unsupported`; isolation tests |
| P12-R2 | Controlled for 12.1 | High | High | OCR libraries leak into core install or core pytest | No `ocr` extra; lock has no OCR engine packages; import probe |
| P12-R3 | Controlled for 12.1 | High | High | Empty-text PDF starts extracting invented text | Existing `pdf.ocr-required` refusal; 12.1 fixture proof |
| P12-R4 | Open | High | High | OCR silently replaces a recoverable digital text layer | Roadmap item 4; blocked until ADR |
| P12-R5 | Open | Medium | High | Cloud OCR or network model fetch during parse | Explicit non-goal; 12.8 harness if ADR accepted |
| P12-R6 | Open | Medium | High | Engine choice without retained corpus evidence | 12.2 evaluation before ADR |
| P12-R7 | Open | Medium | Medium | Handwriting advertised as supported | Explicit exclusion; U7 |
| P12-R8 | Controlled for 12.1 | Low | High | Phase 13 quality work starts from this packet | Packet and ledger forbid it |
