# Phase 12 Decision Index

**Status:** Active

| Decision | State | Basis |
| --- | --- | --- |
| Phase 12 executes as sequential green pull requests; packet opening is 12.1; closeout folds into 12.8 if the ADR is accepted | Accepted | Phase 6–10 precedent; operator instruction 2026-08-25 |
| Repository is public; each item is its own pull request | Accepted | Operator instruction 2026-08-25 (private Actions cost) |
| Stop after 12.2 for operator ADR or deferral | Accepted | Roadmap items 1–2; operator instruction 2026-08-25 |
| `ocr-image` stays explicitly unsupported in 12.1 | Accepted | ADR-0008; honesty pattern of Phase 8.1 / 10.1 |
| No `ocr` extra in 12.1 or 12.2 | Accepted | Extra isolation belongs to 12.7 after ADR |
| Never silently replace digital text with OCR | Accepted | Roadmap non-goal and work item 4 |
| No cloud OCR | Accepted | Roadmap non-goal; offline deterministic v1 |
| No handwriting guarantee | Accepted | Roadmap non-goal |
| Do not start Phase 13 from this packet | Accepted | Roadmap dependency and standing constraint |
| Item 12.2 measures Tesseract on a retained corpus and desk-evaluates other engines; it does not admit an engine | Accepted | Roadmap items 1–2; operator chooses ADR or deferral |
| Handwriting and cloud OCR stay excluded from the corpus | Accepted | Roadmap non-goals |
| CJK is desk-evaluated only in 12.2 (no standard-14 glyphs) | Accepted | Helvetica cannot rasterize CJK |
| Operator accepted Tesseract 5 | Accepted | Operator instruction 2026-08-25 after 12.2 |
| ADR-0016 and ocr-recovery-identity v1 land in 12.3; recovery is not executable | Accepted | Identities before parser path (12.4) |
| Admitted languages are `eng`, `fra`, `lat`; PSM is 6 | Accepted | 12.2 measurements |
| Rotation is explicit `osd-rotate/v1` | Accepted | Default PSM failed the rotated page |
| Digital pages are never passed to an OCR provider | Accepted | ADR-0016; item 12.4 |
| Default parse has no OCR provider; image-only still refuses | Accepted | Extra and executable recovery wait for 12.7 |
